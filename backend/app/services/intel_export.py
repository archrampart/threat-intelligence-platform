"""Convert IOC query history into STIX 2.1 bundles and MISP events.

No external libraries: the output follows the STIX 2.1 JSON specification
(indicator objects with STIX patterns) and the MISP event JSON format, so it can be
imported into OpenCTI, MISP, Sentinel/Defender TI or any TAXII client.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

# Stable namespace so the same IOC always gets the same STIX id (dedupe on re-import)
_NAMESPACE = uuid.UUID("6f0b1b7e-3c2d-4c55-9a0e-2a5d0f1f6d11")
_PRODUCER = "Threat Intelligence Platform"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _ts(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    if isinstance(value, str) and value:
        try:
            return _ts(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            pass
    return _now()


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _hash_key(value: str) -> str:
    return {32: "MD5", 40: "SHA-1", 64: "SHA-256", 128: "SHA-512"}.get(len(value), "SHA-256")


def stix_pattern(ioc_type: str, value: str) -> Optional[str]:
    v = _escape(value.strip())
    if ioc_type == "ip":
        return f"[ipv6-addr:value = '{v}']" if ":" in value else f"[ipv4-addr:value = '{v}']"
    if ioc_type == "domain":
        return f"[domain-name:value = '{v}']"
    if ioc_type == "url":
        return f"[url:value = '{v}']"
    if ioc_type == "hash":
        return f"[file:hashes.'{_hash_key(value.strip())}' = '{v.lower()}']"
    if ioc_type == "email":
        return f"[email-addr:value = '{v}']"
    return None


def _confidence(score: Optional[float]) -> Optional[int]:
    return None if score is None else max(0, min(100, int(round(score * 100))))


def _latest(items: Iterable[dict]) -> list[dict]:
    """Keep the most recent query per IOC."""
    latest: dict[tuple[str, str], dict] = {}
    for item in items:
        key = (str(item.get("ioc_type", "")).lower(), str(item.get("ioc_value", "")).lower())
        if key not in latest or str(item.get("query_date", "")) > str(latest[key].get("query_date", "")):
            latest[key] = item
    return list(latest.values())


def to_stix_bundle(items: Iterable[dict]) -> dict:
    identity_id = f"identity--{uuid.uuid5(_NAMESPACE, _PRODUCER)}"
    created = _now()
    objects: list[dict] = [
        {
            "type": "identity",
            "spec_version": "2.1",
            "id": identity_id,
            "created": created,
            "modified": created,
            "name": _PRODUCER,
            "identity_class": "system",
        }
    ]
    for item in _latest(items):
        ioc_type = str(item.get("ioc_type", "")).lower()
        value = str(item.get("ioc_value", ""))
        pattern = stix_pattern(ioc_type, value)
        if not pattern:
            continue
        risk = item.get("status") or "unknown"
        seen = _ts(item.get("query_date"))
        indicator = {
            "type": "indicator",
            "spec_version": "2.1",
            "id": f"indicator--{uuid.uuid5(_NAMESPACE, f'{ioc_type}:{value.lower()}')}",
            "created_by_ref": identity_id,
            "created": seen,
            "modified": seen,
            "name": f"{ioc_type.upper()} {value}",
            "pattern": pattern,
            "pattern_type": "stix",
            "valid_from": seen,
            "indicator_types": ["malicious-activity"] if risk in ("high", "medium") else ["anomalous-activity"],
            "labels": [f"risk:{risk}"],
            "x_tip_risk_level": risk,
        }
        confidence = _confidence(item.get("risk_score"))
        if confidence is not None:
            indicator["confidence"] = confidence
        sources = [s.get("source") for s in item.get("queried_sources") or [] if s.get("risk_score")]
        if sources:
            indicator["description"] = "Signals from: " + ", ".join(sorted(set(filter(None, sources))))
        objects.append(indicator)
    return {"type": "bundle", "id": f"bundle--{uuid.uuid4()}", "objects": objects}


_MISP_TYPES = {
    "ip": ("ip-dst", "Network activity"),
    "domain": ("domain", "Network activity"),
    "url": ("url", "Network activity"),
    "email": ("email-src", "Payload delivery"),
}
_MISP_THREAT_LEVEL = {"high": "1", "medium": "2", "low": "3", "clean": "4", "unknown": "4"}


def _misp_hash_type(value: str) -> str:
    return {32: "md5", 40: "sha1", 64: "sha256", 128: "sha512"}.get(len(value), "sha256")


def to_misp_event(items: Iterable[dict], info: str = "IOC query export") -> dict:
    latest = _latest(items)
    attributes = []
    worst = "unknown"
    order = ["high", "medium", "low", "clean", "unknown"]
    for item in latest:
        ioc_type = str(item.get("ioc_type", "")).lower()
        value = str(item.get("ioc_value", ""))
        if ioc_type == "hash":
            misp_type, category = _misp_hash_type(value), "Payload delivery"
        elif ioc_type in _MISP_TYPES:
            misp_type, category = _MISP_TYPES[ioc_type]
        elif ioc_type == "cve":
            misp_type, category = "vulnerability", "External analysis"
        else:
            continue
        risk = item.get("status") or "unknown"
        if risk in order and order.index(risk) < order.index(worst):
            worst = risk
        attributes.append(
            {
                "uuid": str(uuid.uuid5(_NAMESPACE, f"misp:{ioc_type}:{value.lower()}")),
                "type": misp_type,
                "category": category,
                "value": value,
                "to_ids": risk in ("high", "medium"),
                "comment": f"risk={risk}"
                + (f", score={item.get('risk_score'):.2f}" if isinstance(item.get("risk_score"), (int, float)) else ""),
                "timestamp": str(int(datetime.fromisoformat(_ts(item.get("query_date")).replace("Z", "+00:00")).timestamp())),
            }
        )
    return {
        "Event": {
            "uuid": str(uuid.uuid4()),
            "info": info,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "threat_level_id": _MISP_THREAT_LEVEL.get(worst, "4"),
            "analysis": "1",
            "distribution": "0",
            "published": False,
            "Tag": [{"name": "tlp:amber"}],
            "Attribute": attributes,
        }
    }
