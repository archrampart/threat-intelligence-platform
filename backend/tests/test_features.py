"""Tests for IOC extraction, STIX/MISP export and webhook notifications."""

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole
from app.services import notifier
from app.services.intel_export import stix_pattern, to_misp_event, to_stix_bundle
from app.utils.ioc_extractor import extract_iocs, refang


def _user(db, role=UserRole.ANALYST):
    user = User(
        id=str(uuid4()),
        username=f"u{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
        password_hash=get_password_hash("Sup3rS3cretPass!"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user, {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}


# --------------------------------------------------------------------------- extraction


def test_refang():
    assert refang("hxxps://evil[.]com/a") == "https://evil.com/a"
    assert refang("1.2.3[.]4 and bad(dot)org user[at]mail[.]ru") == "1.2.3.4 and bad.org user@mail.ru"


def test_extract_iocs_from_report_text():
    text = """
    The loader (invoice.pdf / dropper.exe) beacons to hxxps://cdn-update[.]top/gate.php?id=1,
    falls back to 185.220.101[.]7 and c2.example-bad[.]net. Contact: ops[at]evil-mail[.]ru.
    SHA256 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 exploits CVE-2024-3400.
    Loopback 127.0.0.1 is ignored.
    """
    iocs, truncated = extract_iocs(text)
    pairs = {(i["ioc_type"], i["ioc_value"]) for i in iocs}
    assert ("url", "https://cdn-update.top/gate.php?id=1") in pairs
    assert ("ip", "185.220.101.7") in pairs
    assert ("domain", "c2.example-bad.net") in pairs
    assert ("email", "ops@evil-mail.ru") in pairs
    assert ("hash", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855") in pairs
    assert ("cve", "CVE-2024-3400") in pairs
    values = {v for _, v in pairs}
    assert "invoice.pdf" not in values and "dropper.exe" not in values  # file names, not domains
    assert "cdn-update.top" not in values  # already part of the URL
    assert "127.0.0.1" not in values
    assert truncated is False


def test_extract_dedupes_and_limits():
    iocs, truncated = extract_iocs(" ".join(f"10.0.{i // 250}.{i % 250 + 1}" for i in range(30)) + " 10.0.0.1", limit=10)
    assert len(iocs) == 10 and truncated is True


def test_extract_endpoint(client, db_session):
    _, headers = _user(db_session, UserRole.VIEWER)
    r = client.post("/api/v1/ioc/extract", json={"text": "bad[.]example[.]org 8.8.8.8"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["count"] == 2
    assert client.post("/api/v1/ioc/extract", json={"text": "x"}).status_code == 401


# --------------------------------------------------------------------------- export

_ITEMS = [
    {"ioc_type": "ip", "ioc_value": "1.2.3.4", "status": "high", "risk_score": 0.92,
     "query_date": "2026-11-01T10:00:00+00:00", "queried_sources": [{"source": "feodotracker", "risk_score": 0.95}]},
    {"ioc_type": "ip", "ioc_value": "1.2.3.4", "status": "low", "risk_score": 0.1, "query_date": "2026-10-01T10:00:00+00:00"},
    {"ioc_type": "hash", "ioc_value": "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855",
     "status": "clean", "risk_score": 0.0, "query_date": "2026-11-02T10:00:00Z"},
    {"ioc_type": "url", "ioc_value": "http://x.test/a'b", "status": "medium", "risk_score": 0.6, "query_date": None},
]


def test_stix_patterns():
    assert stix_pattern("ip", "2001:db8::1") == "[ipv6-addr:value = '2001:db8::1']"
    assert stix_pattern("url", "http://x/a'b") == "[url:value = 'http://x/a\\'b']"
    assert stix_pattern("hash", "a" * 40) == "[file:hashes.'SHA-1' = '" + "a" * 40 + "']"
    assert stix_pattern("cve", "CVE-1") is None


def test_stix_bundle_dedupes_to_latest_and_is_stable():
    bundle = to_stix_bundle(_ITEMS)
    indicators = [o for o in bundle["objects"] if o["type"] == "indicator"]
    assert len(indicators) == 3
    ip = next(o for o in indicators if "ipv4" in o["pattern"])
    assert ip["confidence"] == 92 and ip["x_tip_risk_level"] == "high"
    assert ip["indicator_types"] == ["malicious-activity"]
    assert "feodotracker" in ip["description"]
    assert to_stix_bundle(_ITEMS)["objects"][1]["id"] in {o["id"] for o in bundle["objects"]}  # deterministic ids
    json.dumps(bundle)


def test_misp_event():
    event = to_misp_event(_ITEMS)["Event"]
    types = {a["type"]: a for a in event["Attribute"]}
    assert set(types) == {"ip-dst", "sha256", "url"}
    assert types["ip-dst"]["to_ids"] is True and types["sha256"]["to_ids"] is False
    assert event["threat_level_id"] == "1"


def test_export_endpoint_formats(client, db_session):
    _, headers = _user(db_session)
    for fmt in ("stix", "misp", "json"):
        r = client.get(f"/api/v1/ioc/history/export?format={fmt}", headers=headers)
        assert r.status_code == 200, (fmt, r.text)
        assert "attachment" in r.headers["content-disposition"]
    assert client.get("/api/v1/ioc/history/export?format=xml", headers=headers).status_code == 422


# --------------------------------------------------------------------------- notifications


def test_payload_formats():
    slack = notifier.build_payload("slack", "T", "M", "high")
    assert slack["text"] == "[HIGH] T"
    teams = notifier.build_payload("teams", "T", "M", "critical")
    assert teams["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"
    assert notifier.build_payload("generic", "T", "M", "low", {"alert_id": "1"})["alert_id"] == "1"


def test_severity_threshold_and_disabled():
    with patch.object(notifier.threading, "Thread") as thread:
        notifier.notify_user_async({"enabled": True, "webhook_url": "https://h", "min_severity": "high"}, "t", "m", "medium")
        notifier.notify_user_async({"enabled": False, "webhook_url": "https://h", "min_severity": "low"}, "t", "m", "critical")
        thread.assert_not_called()
        notifier.notify_user_async({"enabled": True, "webhook_url": "https://h", "min_severity": "high"}, "t", "m", "critical")
        thread.assert_called_once()


def test_webhook_blocks_internal_destination():
    ok, detail = notifier.send_webhook("http://169.254.169.254/latest", {"x": 1})
    assert ok is False and "Blocked" in detail


def test_notification_settings_api_encrypts_and_masks(client, db_session):
    user, headers = _user(db_session)
    url = "https://hooks.slack.com/services/T000/B000/SECRETTOKEN1234"
    with patch("app.core.url_guard.validate_outbound_url", lambda u: u):
        r = client.put(
            "/api/v1/auth/notifications",
            json={"enabled": True, "webhook_url": url, "format": "slack", "min_severity": "medium"},
            headers=headers,
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["webhook_configured"] is True
    assert "SECRETTOKEN" not in json.dumps(body) and body["webhook_url_masked"].endswith("1234")

    db_session.refresh(user)
    stored = user.profile_json["notifications"]
    assert "webhook_url" not in stored and url not in json.dumps(stored)  # encrypted at rest

    # Updating without a URL keeps the stored one
    r = client.put("/api/v1/auth/notifications", json={"enabled": False, "format": "teams"}, headers=headers)
    assert r.json()["webhook_configured"] is True and r.json()["format"] == "teams"

    assert client.put("/api/v1/auth/notifications", json={"webhook_url": "http://plain.example.com"},
                      headers=headers).status_code == 400


def test_alert_creation_triggers_webhook(db_session):
    from app.models.alert import AlertSeverity, AlertType
    from app.schemas.alert import AlertCreate
    from app.services.alert_service import AlertService

    user, _ = _user(db_session)
    with patch("app.services.notifier.notify_user_async") as notify:
        AlertService(db_session).create_alert(
            user.id,
            AlertCreate(alert_type=list(AlertType)[0], severity=AlertSeverity.HIGH, title="Risk up", message="1.2.3.4"),
        )
    notify.assert_called_once()
    assert notify.call_args.kwargs["severity"] == "high"


def test_strong_signal_is_not_diluted_by_weak_sources():
    from app.schemas.ioc import IOCSourceResult
    from app.services.ioc_service import IOCService

    def r(score):
        return IOCSourceResult(source="s", status="success", risk_score=score, description="", raw=None)

    service = IOCService.__new__(IOCService)
    # Feodo C2 hit (0.95) + VirusTotal 0.1 + OTX 0.6 -> still high
    assert service._calculate_overall_risk([r(0.95), r(0.1), r(0.6)]) == "high"
    # A single capped weak source stays medium, mostly clean stays clean
    assert service._calculate_overall_risk([r(0.6)]) == "medium"
    assert service._calculate_overall_risk([r(0.1), r(0.0), r(0.0)]) == "clean"


def test_report_model_merges_repeats_and_hides_noise():
    from app.services.report_builder import build_model, render_pdf

    ti = lambda src, status, score, desc="": {  # noqa: E731
        "source": src, "confidence_score": score,
        "processed_data": {"status": status, "risk_score": score, "description": desc},
    }
    queries = [
        {"ioc_type": "ip", "ioc_value": "1.2.3.4", "status": "high", "risk_score": 0.83,
         "query_date": "2026-11-05T10:00:00+00:00",
         "threat_intelligence": [ti("feodotracker", "success", 0.95, "Listed in Feodo"), ti("virustotal", "success", 0.1),
                                 ti("otx", "success", None), ti("urlhaus", "skipped", None), ti("x", "error", None)]},
        {"ioc_type": "ip", "ioc_value": "1.2.3.4", "status": "unknown", "risk_score": None,
         "query_date": "2026-11-01T10:00:00+00:00", "threat_intelligence": []},
        {"ioc_type": "domain", "ioc_value": "example.org", "status": "unknown", "risk_score": None,
         "query_date": "2026-11-05T09:00:00+00:00", "threat_intelligence": [ti("otx", "success", None)]},
    ]
    model = build_model({"title": "T", "queries": queries}, {"feodotracker": "Feodo Tracker"})
    assert model["total"] == 2 and model["duplicates_merged"] == 1
    assert [f["ioc_value"] for f in model["flagged"]] == ["1.2.3.4"]
    finding = model["flagged"][0]
    assert finding["counts"] == {"verdict": 2, "no_signal": 1, "skipped": 1, "error": 1}
    assert finding["evidence"][0]["source"] == "Feodo Tracker"
    assert [f["ioc_value"] for f in model["unknown"]] == ["example.org"]
    pdf = render_pdf(model)
    assert pdf.startswith(b"%PDF")


def test_history_risk_filter_matches_stored_levels(client, db_session):
    from datetime import datetime, timezone

    from app.models.ioc_query import IOCQuery

    user, headers = _user(db_session)
    for value, status, score in [("a", "high", 0.95), ("b", "high", 0.85), ("c", "medium", 0.6), ("d", "low", 0.3),
                                 ("e", "clean", 0.0), ("f", "unknown", None)]:
        db_session.add(IOCQuery(id=str(uuid4()), user_id=user.id, ioc_type="domain", ioc_value=f"{value}.test",
                                status=status, risk_score=score, query_date=datetime.now(timezone.utc)))
    db_session.commit()

    def values(level):
        body = client.get(f"/api/v1/ioc/history?risk_level={level}", headers=headers).json()
        return sorted(i["ioc_value"][0] for i in body["items"])

    assert values("critical") == ["a"]
    assert values("high") == ["a", "b"]
    assert values("medium") == ["c"]
    assert values("low") == ["d"]
    assert values("clean") == ["e"]
    assert values("unknown") == ["f"]
