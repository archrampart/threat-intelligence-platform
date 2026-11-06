"""Threat intelligence report: one normalised model, rendered as HTML, PDF or CSV.

Design goals (the previous report listed every queried source for every IOC, mostly
"-" rows, so 100 IOCs produced ~136 PDF pages):

* Lead with what matters: an executive summary and the IOCs that have signals.
* Evidence, not noise: per IOC only sources that returned a verdict are shown;
  sources with no opinion, errors and skipped sources are summarised as counts.
* One IOC = one row (latest query wins), sorted by risk.
* Risk levels use the same thresholds as the rest of the platform.
"""

from __future__ import annotations

import csv
import io
from collections import Counter
from datetime import datetime, timezone
from html import escape
from typing import Any, Optional

LEVELS = ["high", "medium", "low", "clean", "unknown"]
LEVEL_LABEL = {"high": "High", "medium": "Medium", "low": "Low", "clean": "Clean", "unknown": "No verdict"}
LEVEL_COLOR = {"high": "#dc2626", "medium": "#ea580c", "low": "#ca8a04", "clean": "#16a34a", "unknown": "#64748b"}
LEVEL_BG = {"high": "#fef2f2", "medium": "#fff7ed", "low": "#fefce8", "clean": "#f0fdf4", "unknown": "#f8fafc"}
TYPE_LABEL = {"ip": "IP", "domain": "Domain", "url": "URL", "hash": "Hash", "email": "Email", "cve": "CVE"}


def level_for(score: Optional[float]) -> str:
    """Same thresholds as IOCService._calculate_overall_risk."""
    if score is None:
        return "unknown"
    if score >= 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    if score >= 0.2:
        return "low"
    return "clean"


def _parse_dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _fmt_dt(value: Any, with_time: bool = True) -> str:
    dt = _parse_dt(value)
    if not dt:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M UTC" if with_time else "%Y-%m-%d")


def build_model(report_data: dict, source_names: Optional[dict[str, str]] = None) -> dict:
    """Turn raw report data (queries + per-source results) into the report model."""
    source_names = source_names or {}
    latest: dict[tuple[str, str], dict] = {}
    for query in report_data.get("queries", []) or []:
        key = (str(query.get("ioc_type", "")).lower(), str(query.get("ioc_value", "")).strip().lower())
        current = latest.get(key)
        if current is None or (_parse_dt(query.get("query_date")) or datetime.min.replace(tzinfo=timezone.utc)) > (
            _parse_dt(current.get("query_date")) or datetime.min.replace(tzinfo=timezone.utc)
        ):
            latest[key] = query

    findings = []
    source_hits: Counter[str] = Counter()
    for query in latest.values():
        evidence = []
        counts = Counter()
        for ti in query.get("threat_intelligence", []) or []:
            processed = ti.get("processed_data") or {}
            status = processed.get("status", "error")
            score = processed.get("risk_score", ti.get("confidence_score"))
            if status == "skipped":
                counts["skipped"] += 1
            elif status != "success":
                counts["error"] += 1
            elif score is None:
                counts["no_signal"] += 1
            else:
                counts["verdict"] += 1
                name = ti.get("source", "")
                description = processed.get("description") or ""
                if description.startswith("Query completed with status"):
                    description = ""
                evidence.append(
                    {
                        "source": source_names.get(name, name.replace("_", " ").title()),
                        "score": float(score),
                        "level": level_for(float(score)),
                        "description": description,
                    }
                )
                if float(score) > 0:
                    source_hits[source_names.get(name, name)] += 1
        evidence.sort(key=lambda e: e["score"], reverse=True)
        score = query.get("risk_score")
        level = query.get("status") if query.get("status") in LEVELS else level_for(score)
        findings.append(
            {
                "ioc_type": str(query.get("ioc_type", "")).lower(),
                "ioc_value": str(query.get("ioc_value", "")),
                "level": level,
                "score": score,
                "query_date": query.get("query_date"),
                "evidence": evidence,
                "checked": sum(counts.values()),
                "counts": dict(counts),
            }
        )

    findings.sort(key=lambda f: (LEVELS.index(f["level"]), -(f["score"] or 0), f["ioc_type"], f["ioc_value"]))
    by_level = Counter(f["level"] for f in findings)
    dates = [d for d in (_parse_dt(f["query_date"]) for f in findings) if d]
    scored = [f["score"] for f in findings if f["score"] is not None]
    return {
        "title": report_data.get("title") or "Threat Intelligence Report",
        "description": report_data.get("description") or "",
        "generated_at": report_data.get("generated_at") or datetime.now(timezone.utc).isoformat(),
        "period": (min(dates), max(dates)) if dates else None,
        "total": len(findings),
        "duplicates_merged": max(0, len(report_data.get("queries", []) or []) - len(findings)),
        "by_level": {lvl: by_level.get(lvl, 0) for lvl in LEVELS},
        "by_type": dict(Counter(f["ioc_type"] for f in findings).most_common()),
        "avg_score": round(sum(scored) / len(scored), 2) if scored else None,
        "top_sources": source_hits.most_common(8),
        "flagged": [f for f in findings if f["level"] in ("high", "medium", "low")],
        "clean": [f for f in findings if f["level"] == "clean"],
        "unknown": [f for f in findings if f["level"] == "unknown"],
    }


def _evidence_text(finding: dict, limit: int = 4) -> str:
    parts = []
    for e in [x for x in finding["evidence"] if x["score"] > 0][:limit]:
        text = f"{e['source']} {round(e['score'] * 100)}%"
        if e["description"]:
            text += f" - {e['description']}"
        parts.append(text)
    more = len([x for x in finding["evidence"] if x["score"] > 0]) - limit
    if more > 0:
        parts.append(f"+{more} more")
    return "; ".join(parts)


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _coverage_text(finding: dict) -> str:
    """e.g. "3 verdicts · 16 no signal · 1 error" (skipped / unsupported sources are omitted)."""
    c = finding["counts"]
    bits = [_plural(c.get("verdict", 0), "verdict")]
    if c.get("no_signal"):
        bits.append(f"{c['no_signal']} no signal")
    if c.get("error"):
        bits.append(_plural(c["error"], "error"))
    return " · ".join(bits)


# --------------------------------------------------------------------------- HTML


# --------------------------------------------------------------------------- dark web

SEVERITIES = ["critical", "high", "medium", "low"]
SEV_COLOR = {"critical": "#b91c1c", "high": "#ea580c", "medium": "#ca8a04", "low": "#64748b"}
SEV_BG = {"critical": "#fef2f2", "high": "#fff7ed", "medium": "#fefce8", "low": "#f8fafc"}
DW_SOURCE_LABEL = {
    "ransomware": "Ransomware leak sites",
    "infostealer": "Infostealer logs",
    "breach": "Breaches",
    "forum": "Forums & markets",
    "telegram": "Telegram",
    "feed": "News & custom feeds",
}
ASSET_LABEL = {"domain": "Domain", "email_domain": "E-mail domain", "keyword": "Keyword"}


def build_darkweb_model(mentions: list[dict], assets: list[dict], start: Any = None, end: Any = None) -> dict:
    """Dark web exposure model. ``mentions`` are serialised DarkWebMention rows."""
    order = {s: i for i, s in enumerate(SEVERITIES)}
    items = sorted(
        mentions,
        key=lambda m: (order.get(m.get("severity"), 9),
                       -(_parse_dt(m.get("published_at")) or _parse_dt(m.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)).timestamp()),
    )
    by_asset = Counter(m.get("matched_term") for m in items)
    dates = [d for d in (_parse_dt(m.get("created_at")) for m in items) if d]
    return {
        "total": len(items),
        "by_severity": {s: sum(1 for m in items if m.get("severity") == s) for s in SEVERITIES},
        "by_source": dict(Counter(m.get("source") for m in items).most_common()),
        "assets": [
            {**a, "mentions": by_asset.get(a.get("value"), 0)} for a in sorted(assets, key=lambda a: (a.get("kind"), a.get("value")))
        ],
        "items": items,
        "period": (_parse_dt(start) or (min(dates) if dates else None), _parse_dt(end) or (max(dates) if dates else None)),
    }


def _period_text(period) -> str:
    if not period or not (period[0] or period[1]):
        return "-"
    return f"{_fmt_dt(period[0], False)} - {_fmt_dt(period[1], False)}"


def _darkweb_html(dw: dict, full: bool) -> str:
    e = escape
    limit = None if full else 10
    sev_cards = "".join(
        f'<div class="card" style="border-color:{SEV_COLOR[s]}"><div class="n" style="color:{SEV_COLOR[s]}">'
        f'{dw["by_severity"][s]}</div><div class="l">{s}</div></div>'
        for s in SEVERITIES
    )
    sources = ", ".join(f"{e(DW_SOURCE_LABEL.get(k, k))} {n}" for k, n in dw["by_source"].items()) or "None"
    assets = "".join(
        f"<tr><td>{e(ASSET_LABEL.get(a.get('kind'), a.get('kind') or ''))}</td><td class='ioc'>{e(a.get('value') or '')}</td>"
        f"<td class='num'>{a['mentions']}</td></tr>"
        for a in dw["assets"]
    )
    shown = dw["items"] if limit is None else [m for m in dw["items"] if m.get("severity") in ("critical", "high")][:limit]
    rows = "".join(
        "<tr>"
        f"<td><span class='badge' style='color:{SEV_COLOR.get(m.get('severity'), '#64748b')};"
        f"background:{SEV_BG.get(m.get('severity'), '#f8fafc')};border-color:{SEV_COLOR.get(m.get('severity'), '#64748b')}'>"
        f"{e(str(m.get('severity', '')).title())}</span></td>"
        f"<td>{e(DW_SOURCE_LABEL.get(m.get('source'), m.get('source') or ''))}</td>"
        f"<td><b>{e(m.get('title') or '')}</b>"
        + (f"<div class='muted'>{e((m.get('snippet') or '')[:400])}</div>" if m.get("snippet") else "")
        + (f"<div class='muted'>{e(m['url'])}</div>" if m.get("url") else "")
        + "</td>"
        f"<td class='ioc'>{e(m.get('matched_term') or '')}</td>"
        f"<td class='muted'>{e(m.get('actor') or '-')}<br/>{_fmt_dt(m.get('published_at') or m.get('created_at'), False)}</td>"
        "</tr>"
        for m in shown
    )
    table = (
        "<table><thead><tr><th>Severity</th><th>Source</th><th>Finding</th><th>Matched</th><th>Actor / date</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        if shown
        else "<p class='muted'>No critical or high dark web findings in this period.</p>"
    )
    heading = "Dark web findings" if full else "Dark web exposure (summary)"
    more = (
        f"<p class='muted'>{_plural(dw['total'] - len(shown), 'further mention')} (medium/low or beyond the top {limit}) "
        f"can be found in the dark web report.</p>"
        if not full and dw["total"] > len(shown)
        else ""
    )
    assets_table = (
        f"<h2>Monitored assets ({len(dw['assets'])})</h2><table><thead><tr><th>Type</th><th>Value</th>"
        f"<th>Mentions</th></tr></thead><tbody>{assets}</tbody></table>"
        if full and dw["assets"]
        else ""
    )
    return f"""
  <h2>{heading}</h2>
  <div class="cards cards4">{sev_cards}</div>
  <div class="facts">
    <div><b>Period:</b> {_period_text(dw['period'])} · <b>{dw['total']}</b> mentions of {len(dw['assets'])} monitored assets</div>
    <div><b>By source:</b> {sources}</div>
  </div>
  {assets_table}
  {"<h2>Findings (" + str(len(shown)) + ")</h2>" if full else ""}
  {table}
  {more}"""


def render_html(model: dict) -> str:
    e = escape
    if model.get("kind") == "darkweb":
        return _render_darkweb_html(model)
    period = (
        f"{_fmt_dt(model['period'][0], False)} - {_fmt_dt(model['period'][1], False)}" if model["period"] else "-"
    )
    cards = "".join(
        f'<div class="card" style="border-color:{LEVEL_COLOR[lvl]}"><div class="n" style="color:{LEVEL_COLOR[lvl]}">'
        f'{model["by_level"][lvl]}</div><div class="l">{LEVEL_LABEL[lvl]}</div></div>'
        for lvl in LEVELS
    )
    types = ", ".join(f"{TYPE_LABEL.get(t, t)} {n}" for t, n in model["by_type"].items()) or "-"
    top = ", ".join(f"{e(name)} ({n})" for name, n in model["top_sources"]) or "None"

    def badge(level: str) -> str:
        return (
            f'<span class="badge" style="color:{LEVEL_COLOR[level]};background:{LEVEL_BG[level]};'
            f'border-color:{LEVEL_COLOR[level]}">{LEVEL_LABEL[level]}</span>'
        )

    def score(value: Optional[float]) -> str:
        return "-" if value is None else f"{round(value * 100)}%"

    def evidence_html(finding: dict) -> str:
        items = []
        for ev in [x for x in finding["evidence"] if x["score"] > 0][:6]:
            text = f"<b>{e(ev['source'])}</b> {round(ev['score'] * 100)}%"
            if ev["description"]:
                text += f" - {e(ev['description'])}"
            items.append(f"<li>{text}</li>")
        return f"<ul>{''.join(items)}</ul><div class='muted'>{e(_coverage_text(finding))}</div>"

    flagged_rows = "".join(
        f"<tr><td>{e(TYPE_LABEL.get(f['ioc_type'], f['ioc_type']))}</td><td class='ioc'>{e(f['ioc_value'])}</td>"
        f"<td>{badge(f['level'])}</td><td class='num'>{score(f['score'])}</td>"
        f"<td>{evidence_html(f)}</td><td class='muted'>{_fmt_dt(f['query_date'])}</td></tr>"
        for f in model["flagged"]
    )

    def compact(rows: list[dict]) -> str:
        return "".join(
            f"<tr><td>{e(TYPE_LABEL.get(f['ioc_type'], f['ioc_type']))}</td><td class='ioc'>{e(f['ioc_value'])}</td>"
            f"<td class='muted'>{e(_coverage_text(f))}</td><td class='muted'>{_fmt_dt(f['query_date'])}</td></tr>"
            for f in rows
        )

    flagged_section = (
        f"<table><thead><tr><th>Type</th><th>Indicator</th><th>Risk</th><th>Score</th><th>Evidence</th>"
        f"<th>Checked</th></tr></thead><tbody>{flagged_rows}</tbody></table>"
        if model["flagged"]
        else "<p class='muted'>No indicator received a risk verdict from any source.</p>"
    )
    clean_section = (
        f"<h2>Clean ({len(model['clean'])})</h2><p class='muted'>Sources answered and scored these indicators as benign.</p>"
        f"<table><thead><tr><th>Type</th><th>Indicator</th><th>Coverage</th><th>Checked</th></tr></thead>"
        f"<tbody>{compact(model['clean'])}</tbody></table>"
        if model["clean"]
        else ""
    )
    unknown_section = (
        f"<h2>No verdict ({len(model['unknown'])})</h2><p class='muted'>No source had information or all lookups "
        f"failed - this is not the same as clean.</p><table><thead><tr><th>Type</th><th>Indicator</th>"
        f"<th>Coverage</th><th>Checked</th></tr></thead><tbody>{compact(model['unknown'])}</tbody></table>"
        if model["unknown"]
        else ""
    )
    merged = (
        f" · {model['duplicates_merged']} repeated queries merged (latest result kept)" if model["duplicates_merged"] else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(model['title'])}</title>
<style>
  body {{ font-family: -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; background: #f1f5f9; color: #0f172a; }}
  .page {{ max-width: 1100px; margin: 0 auto; background: #fff; padding: 40px 48px; }}
  .tlp {{ display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: .08em; color: #b45309; border: 1px solid #f59e0b; padding: 2px 8px; border-radius: 4px; }}
  h1 {{ margin: 12px 0 4px; font-size: 26px; }}
  h2 {{ margin: 32px 0 8px; font-size: 18px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }}
  .meta, .muted {{ color: #64748b; font-size: 13px; }}
  .cards {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin: 20px 0 8px; }}
  .cards4 {{ grid-template-columns: repeat(4, 1fr); }}
  .card {{ border: 1px solid; border-left-width: 4px; border-radius: 8px; padding: 12px 14px; }}
  .card .n {{ font-size: 26px; font-weight: 700; }}
  .card .l {{ font-size: 12px; color: #475569; text-transform: uppercase; letter-spacing: .04em; }}
  .facts {{ font-size: 13px; color: #334155; line-height: 1.7; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }}
  th {{ text-align: left; background: #f8fafc; color: #475569; font-weight: 600; padding: 8px; border-bottom: 2px solid #e2e8f0; }}
  td {{ padding: 8px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
  td.ioc {{ font-family: ui-monospace, Menlo, Consolas, monospace; word-break: break-all; max-width: 280px; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  ul {{ margin: 0; padding-left: 16px; }}
  .badge {{ display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px; border: 1px solid; }}
  footer {{ margin-top: 32px; font-size: 11px; color: #94a3b8; }}
  @media (max-width: 760px) {{ .page {{ padding: 20px; }} .cards {{ grid-template-columns: repeat(2, 1fr); }} }}
  @media print {{ body {{ background: #fff; }} .page {{ padding: 0; }} tr {{ break-inside: avoid; }} }}
</style></head>
<body><div class="page">
  <span class="tlp">TLP:AMBER</span>
  <h1>{e(model['title'])}</h1>
  {f"<p>{e(model['description'])}</p>" if model['description'] else ""}
  <div class="meta">Generated {_fmt_dt(model['generated_at'])} · Query period {period} · {model['total']} unique indicators{merged}</div>

  <h2>Executive summary</h2>
  <div class="cards">{cards}</div>
  <div class="facts">
    <div><b>Indicator types:</b> {types}</div>
    <div><b>Average score</b> (indicators with a verdict): {score(model['avg_score'])}</div>
    <div><b>Sources with most detections:</b> {top}</div>
  </div>

  <h2>Findings ({len(model['flagged'])})</h2>
  {flagged_section}
  {clean_section}
  {unknown_section}
  {_darkweb_html(model["darkweb"], full=False) if model.get("darkweb") else ""}

  <footer>Risk levels: High &ge; 80%, Medium &ge; 50%, Low &ge; 20%, Clean &lt; 20%. Score = 70% strongest source + 30% mean
  of the sources that returned a verdict. "No verdict" means no source had information. Generated by the Threat Intelligence
  Platform.</footer>
</div></body></html>"""


def _render_darkweb_html(model: dict) -> str:
    """Standalone dark web exposure report (same page shell as the IOC report)."""
    e = escape
    shell = render_html({
        "title": model["title"], "description": model["description"], "generated_at": model["generated_at"],
        "period": None, "total": 0, "duplicates_merged": 0, "by_level": {lvl: 0 for lvl in LEVELS}, "by_type": {},
        "avg_score": None, "top_sources": [], "flagged": [], "clean": [], "unknown": [],
    })
    head, rest = shell.split('<span class="tlp">TLP:AMBER</span>', 1)
    dw = model["darkweb"]
    body = f"""<span class="tlp">TLP:AMBER</span>
  <h1>{e(model['title'])}</h1>
  {f"<p>{e(model['description'])}</p>" if model['description'] else ""}
  <div class="meta">Dark web exposure report · Generated {_fmt_dt(model['generated_at'])}</div>
  {_darkweb_html(dw, full=True)}
  <footer>Sources: ransomware leak-site aggregators, infostealer statistics, breach catalogs, dark web forum reporting,
  Telegram channels and feeds configured in the platform. Findings are matches of monitored assets and require
  validation. Generated by the Threat Intelligence Platform.</footer>
</div></body></html>"""
    return head + body


# --------------------------------------------------------------------------- CSV


def render_csv(model: dict) -> str:
    def safe(value: Any) -> str:
        text = "" if value is None else str(value)
        return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text

    out = io.StringIO()
    writer = csv.writer(out)
    if model.get("kind") == "darkweb":
        writer.writerow(["severity", "source", "title", "matched_term", "actor", "published_at", "url", "snippet"])
        for m in model["darkweb"]["items"]:
            writer.writerow([
                m.get("severity"), DW_SOURCE_LABEL.get(m.get("source"), m.get("source")), safe(m.get("title")),
                safe(m.get("matched_term")), safe(m.get("actor")), _fmt_dt(m.get("published_at") or m.get("created_at")),
                safe(m.get("url")), safe((m.get("snippet") or "")[:500]),
            ])
        return out.getvalue()
    writer.writerow(["ioc_type", "ioc_value", "risk_level", "score", "evidence", "sources_checked", "query_date"])
    for f in model["flagged"] + model["clean"] + model["unknown"]:
        writer.writerow(
            [
                safe(f["ioc_type"]),
                safe(f["ioc_value"]),
                LEVEL_LABEL[f["level"]],
                "" if f["score"] is None else f"{f['score']:.2f}",
                safe(_evidence_text(f, limit=10)),
                f["checked"],
                _fmt_dt(f["query_date"]),
            ]
        )
    return out.getvalue()


# --------------------------------------------------------------------------- PDF


def _darkweb_pdf(story: list, dw: dict, full: bool, styles: tuple, header_style: list) -> None:
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    base, small, mono, h2 = styles
    e = escape
    story.append(Paragraph("Dark web findings" if full else "Dark web exposure (summary)", h2))
    cards = Table(
        [
            [Paragraph(f'<font size="16" color="{SEV_COLOR[s]}"><b>{dw["by_severity"][s]}</b></font>', base) for s in SEVERITIES],
            [Paragraph(s.upper(), small) for s in SEVERITIES],
        ],
        colWidths=[42 * mm] * 4,
    )
    style = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, 1), (-1, 1), 6)]
    for i, sev in enumerate(SEVERITIES):
        style += [("BOX", (i, 0), (i, 1), 0.6, colors.HexColor(SEV_COLOR[sev])),
                  ("BACKGROUND", (i, 0), (i, 1), colors.HexColor(SEV_BG[sev]))]
    cards.setStyle(TableStyle(style))
    story.append(cards)
    story.append(Spacer(1, 6))
    sources = ", ".join(f"{DW_SOURCE_LABEL.get(k, k)} {n}" for k, n in dw["by_source"].items()) or "None"
    story.append(Paragraph(f"<b>Period:</b> {_period_text(dw['period'])} · <b>{dw['total']}</b> mentions of "
                           f"{len(dw['assets'])} monitored assets", base))
    story.append(Paragraph(f"<b>By source:</b> {e(sources)}", base))

    if full and dw["assets"]:
        story.append(Paragraph(f"Monitored assets ({len(dw['assets'])})", h2))
        rows = [["Type", "Value", "Mentions"]] + [
            [Paragraph(ASSET_LABEL.get(a.get("kind"), a.get("kind") or ""), base), Paragraph(e(a.get("value") or ""), mono),
             Paragraph(str(a["mentions"]), base)]
            for a in dw["assets"]
        ]
        table = Table(rows, colWidths=[35 * mm, 115 * mm, 30 * mm], repeatRows=1)
        table.setStyle(TableStyle(header_style))
        story.append(table)

    shown = dw["items"] if full else [m for m in dw["items"] if m.get("severity") in ("critical", "high")][:10]
    if full:
        story.append(Paragraph(f"Findings ({len(shown)})", h2))
    if not shown:
        story.append(Paragraph("No critical or high dark web findings in this period.", small))
        return
    rows = [["Severity", "Source", "Finding", "Matched"]]
    for m in shown:
        sev = m.get("severity") or "low"
        text = f"<b>{e(m.get('title') or '')}</b>"
        if m.get("snippet"):
            text += f'<br/><font color="#475569" size="7">{e((m["snippet"] or "")[:300])}</font>'
        meta = " · ".join(filter(None, [e(m.get("actor") or ""), _fmt_dt(m.get("published_at") or m.get("created_at"), False)]))
        text += f'<br/><font color="#64748b" size="7">{meta}</font>'
        if m.get("url"):
            text += f'<br/><font color="#2563eb" size="7">{e(m["url"][:150])}</font>'
        rows.append([
            Paragraph(f'<font color="{SEV_COLOR.get(sev, "#64748b")}"><b>{sev.title()}</b></font>', base),
            Paragraph(e(DW_SOURCE_LABEL.get(m.get("source"), m.get("source") or "")), small),
            Paragraph(text, base),
            Paragraph(e(m.get("matched_term") or ""), mono),
        ])
    table = Table(rows, colWidths=[17 * mm, 25 * mm, 108 * mm, 30 * mm], repeatRows=1)
    table.setStyle(TableStyle(header_style))
    story.append(table)
    if not full and dw["total"] > len(shown):
        story.append(Paragraph(f"{_plural(dw['total'] - len(shown), 'further mention')} (medium/low or beyond the top 10) "
                               "can be found in the dark web report.", small))


def render_pdf(model: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    e = escape
    styles = getSampleStyleSheet()
    base = ParagraphStyle("base", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11)
    small = ParagraphStyle("small", parent=base, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#64748b"))
    mono = ParagraphStyle("mono", parent=base, fontName="Courier", fontSize=8, leading=10, wordWrap="CJK")
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=20, leading=24, alignment=0, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, leading=16, spaceBefore=12, spaceAfter=6,
                        textColor=colors.HexColor("#0f172a"))
    num = ParagraphStyle("num", parent=base, alignment=TA_RIGHT)

    def level_par(level: str) -> Paragraph:
        return Paragraph(f'<font color="{LEVEL_COLOR[level]}"><b>{LEVEL_LABEL[level]}</b></font>', base)

    def score(value: Optional[float]) -> str:
        return "-" if value is None else f"{round(value * 100)}%"

    story: list = []
    header_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#475569")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor("#cbd5e1")),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    is_darkweb = model.get("kind") == "darkweb"
    story.append(Paragraph('<font color="#b45309"><b>TLP:AMBER</b></font>', small))
    story.append(Paragraph(e(model["title"]), h1))
    if model["description"]:
        story.append(Paragraph(e(model["description"]), base))
    if not is_darkweb:
        period = (
            f"{_fmt_dt(model['period'][0], False)} - {_fmt_dt(model['period'][1], False)}" if model["period"] else "-"
        )
        merged = f" · {model['duplicates_merged']} repeated queries merged" if model["duplicates_merged"] else ""
        story.append(
            Paragraph(f"Generated {_fmt_dt(model['generated_at'])} · Query period {period} · "
                      f"{model['total']} unique indicators{merged}", small)
        )

        # Executive summary
        story.append(Paragraph("Executive summary", h2))
        cards = Table(
            [
                [Paragraph(f'<font size="16" color="{LEVEL_COLOR[l]}"><b>{model["by_level"][l]}</b></font>', base) for l in LEVELS],
                [Paragraph(LEVEL_LABEL[l].upper(), small) for l in LEVELS],
            ],
            colWidths=[34 * mm] * 5,
        )
        card_style = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, 1), (-1, 1), 6)]
        for i, lvl in enumerate(LEVELS):
            card_style += [
                ("BOX", (i, 0), (i, 1), 0.6, colors.HexColor(LEVEL_COLOR[lvl])),
                ("BACKGROUND", (i, 0), (i, 1), colors.HexColor(LEVEL_BG[lvl])),
            ]
        cards.setStyle(TableStyle(card_style))
        story.append(cards)
        story.append(Spacer(1, 6))
        types = ", ".join(f"{TYPE_LABEL.get(t, t)} {n}" for t, n in model["by_type"].items()) or "-"
        top = ", ".join(f"{e(name)} ({n})" for name, n in model["top_sources"]) or "None"
        for line in (
            f"<b>Indicator types:</b> {e(types)}",
            f"<b>Average score</b> (indicators with a verdict): {score(model['avg_score'])}",
            f"<b>Sources with most detections:</b> {top}",
        ):
            story.append(Paragraph(line, base))


        # Findings
        story.append(Paragraph(f"Findings ({len(model['flagged'])})", h2))
        if model["flagged"]:
            rows = [["Type", "Indicator", "Risk", "Score", "Evidence"]]
            for f in model["flagged"]:
                evidence = "<br/>".join(
                    f"<b>{e(ev['source'])}</b> {round(ev['score'] * 100)}%" + (f" - {e(ev['description'])}" if ev["description"] else "")
                    for ev in [x for x in f["evidence"] if x["score"] > 0][:5]
                )
                evidence += f'<br/><font color="#64748b" size="7">{e(_coverage_text(f))} · {_fmt_dt(f["query_date"])}</font>'
                rows.append(
                    [
                        Paragraph(TYPE_LABEL.get(f["ioc_type"], e(f["ioc_type"])), base),
                        Paragraph(e(f["ioc_value"]), mono),
                        level_par(f["level"]),
                        Paragraph(score(f["score"]), num),
                        Paragraph(evidence, base),
                    ]
                )
            table = Table(rows, colWidths=[17 * mm, 50 * mm, 17 * mm, 13 * mm, 83 * mm], repeatRows=1)
            table.setStyle(TableStyle(header_style))
            story.append(table)
        else:
            story.append(Paragraph("No indicator received a risk verdict from any source.", small))

        def compact_table(title: str, note: str, items: list[dict]) -> None:
            if not items:
                return
            story.append(KeepTogether([Paragraph(f"{title} ({len(items)})", h2), Paragraph(note, small), Spacer(1, 4)]))
            rows = [["Type", "Indicator", "Coverage", "Checked"]]
            for f in items:
                rows.append(
                    [
                        Paragraph(TYPE_LABEL.get(f["ioc_type"], e(f["ioc_type"])), base),
                        Paragraph(e(f["ioc_value"]), mono),
                        Paragraph(e(_coverage_text(f)), small),
                        Paragraph(_fmt_dt(f["query_date"]), small),
                    ]
                )
            table = Table(rows, colWidths=[17 * mm, 80 * mm, 50 * mm, 33 * mm], repeatRows=1)
            table.setStyle(TableStyle(header_style))
            story.append(table)

        compact_table("Clean", "Sources answered and scored these indicators as benign.", model["clean"])
        compact_table(
            "No verdict",
            "No source had information or all lookups failed - this is not the same as clean.",
            model["unknown"],
        )
        story.append(Spacer(1, 10))
        story.append(
            Paragraph(
                "Risk levels: High &gt;= 80%, Medium &gt;= 50%, Low &gt;= 20%, Clean &lt; 20%. Score = 70% strongest source "
                "+ 30% mean of the sources that returned a verdict.",
                small,
            )
        )

    if is_darkweb:
        story.append(Paragraph(f"Dark web exposure report · Generated {_fmt_dt(model['generated_at'])}", small))
        _darkweb_pdf(story, model["darkweb"], True, styles=(base, small, mono, h2), header_style=header_style)
    elif model.get("darkweb"):
        _darkweb_pdf(story, model["darkweb"], False, styles=(base, small, mono, h2), header_style=header_style)

    title = model["title"]

    def decorate(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.drawString(15 * mm, 10 * mm, f"{title[:80]} · TLP:AMBER")
        canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=18 * mm,
        title=title, author="Threat Intelligence Platform",
    )
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return buffer.getvalue()
