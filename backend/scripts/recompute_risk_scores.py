"""Recompute stored IOC risk scores with the current source catalog rules.

Before 2.1.0 per-source scores were not normalised (e.g. AbuseIPDB 25 % counted as
"high") and the overall score was a fixed number per level (unknown -> 0.5), which the
dashboard counted as "high". This script re-derives every stored result from the raw
API responses that were saved with it.

Usage (from backend/):
    python -m scripts.recompute_risk_scores            # dry run, prints before/after
    python -m scripts.recompute_risk_scores --apply    # writes changes (timestamped .bak copy for SQLite)
"""

from __future__ import annotations

import argparse
import shutil
from collections import Counter
from types import SimpleNamespace
from typing import Any, Optional

from app.core.config import get_settings
from app.db.base import SessionLocal
from app.db.source_catalog import DEPRECATED_SOURCES
from app.models.api_source import APISource
from app.models.ioc_query import IOCQuery, ThreatIntelligenceData
from app.schemas.ioc import IOCSourceResult
from app.services.dynamic_api_client import DynamicAPIClient
from app.services.ioc_service import IOCService

_LEVEL_FALLBACK = {"high": 0.85, "medium": 0.6, "low": 0.3, "clean": 0.1}


def _bucket(score: Optional[float]) -> str:
    if score is None:
        return "unknown"
    if score >= 0.9:
        return "critical"
    if score >= 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def _source_score(source: Optional[APISource], status: str, raw: Any) -> tuple[str, Optional[float]]:
    """Return (status, normalised score) for one stored source result."""
    if source is None or source.name in DEPRECATED_SOURCES or not source.is_active:
        return "skipped", None
    if status != "success" or not isinstance(raw, dict):
        return status, None
    if raw.get("not_found"):
        return status, None
    request_config = source.request_config or {}
    response_config = source.response_config or {}
    if request_config.get("mode") == "feed":
        # Only results produced by the membership check carry "listed"; older runs
        # downloaded the whole feed without matching -> no signal.
        if raw.get("listed") is True:
            return status, float(response_config.get("listed_risk", 0.8))
        return status, None
    path = response_config.get("risk_score_path")
    if not path:
        return status, None
    client = DynamicAPIClient(
        SimpleNamespace(
            name=source.name,
            base_url=source.base_url,
            request_config=request_config,
            response_config=response_config,
            authentication_type=source.authentication_type,
        ),
        "",
    )
    return status, client._normalize_risk(client._extract_value(raw, path))


def recompute(apply: bool) -> None:
    db = SessionLocal()
    service = IOCService(db)
    sources = {s.name: s for s in db.query(APISource).all()}
    before: Counter[str] = Counter()
    after: Counter[str] = Counter()
    changed = 0

    try:
        queries = db.query(IOCQuery).all()
        for query in queries:
            before[_bucket(query.risk_score)] += 1
            rows = db.query(ThreatIntelligenceData).filter(ThreatIntelligenceData.ioc_query_id == query.id).all()

            if rows:
                results = []
                for row in rows:
                    processed = row.processed_data_json or {}
                    status, score = _source_score(sources.get(row.source_api), processed.get("status", "error"), row.raw_data_json)
                    results.append(
                        IOCSourceResult(
                            source=row.source_api,
                            status=status,
                            risk_score=score,
                            description=processed.get("description"),
                            raw=None,
                        )
                    )
                    if apply:
                        row.confidence_score = score
                        row.processed_data_json = {**processed, "status": status, "risk_score": score}
                level = service._calculate_overall_risk(results) or "unknown"
                score = service._average_risk(results)
                if apply and isinstance(query.results_json, dict):
                    by_source = {r.source: r for r in results}
                    stored = query.results_json.get("queried_sources") or []
                    for item in stored:
                        fresh = by_source.get(item.get("source"))
                        if fresh:
                            item["status"], item["risk_score"] = fresh.status, fresh.risk_score
                    query.results_json = {**query.results_json, "overall_risk": level, "queried_sources": stored}
            else:
                level = query.status or "unknown"
                score = _LEVEL_FALLBACK.get(level)

            if (query.status, query.risk_score) != (level, score):
                changed += 1
            after[_bucket(score)] += 1
            if apply:
                query.status, query.risk_score = level, score

        order = ["critical", "high", "medium", "low", "unknown"]
        print(f"{'bucket':10} {'before':>7} {'after':>7}")
        for key in order:
            print(f"{key:10} {before[key]:>7} {after[key]:>7}")
        print(f"\n{len(queries)} queries, {changed} changed")

        if apply:
            db.commit()
            print("Changes written.")
        else:
            db.rollback()
            print("Dry run - nothing written. Re-run with --apply.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the recomputed values")
    args = parser.parse_args()

    url = get_settings().database_url
    if args.apply and url.startswith("sqlite:///"):
        from datetime import datetime

        path = url.replace("sqlite:///", "", 1)
        backup = f"{path}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"  # never overwrite an older backup
        shutil.copy2(path, backup)
        print(f"Backup written to {backup}")
    recompute(args.apply)


if __name__ == "__main__":
    main()
