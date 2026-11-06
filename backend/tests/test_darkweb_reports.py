"""Dark web exposure reports and the dark web summary in IOC reports."""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.security import create_access_token, get_password_hash
from app.models.darkweb import DarkWebMention, MonitoredAsset
from app.models.report import Report
from app.models.user import User, UserRole


def _user(db, role=UserRole.ANALYST):
    user = User(id=str(uuid4()), username=f"rep{uuid4().hex[:6]}", email=f"{uuid4().hex[:6]}@example.com",
                password_hash=get_password_hash("Sup3rS3cretPass!"), role=role, is_active=True)
    db.add(user)
    db.commit()
    return user, {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}


def _mention(db, user, severity, source, title, days_ago=0):
    m = DarkWebMention(
        user_id=user.id, source=source, severity=severity, matched_term="acme.com", title=title,
        snippet=f"snippet <b>{title}</b>", url="https://example.org/post", actor="akira",
        fingerprint=uuid4().hex, created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    db.add(m)
    db.commit()
    return m


def _export(client, headers, report_id, fmt):
    r = client.post(f"/api/v1/reports/{report_id}/export", json={"format": fmt}, headers=headers)
    assert r.status_code == 200, r.text
    return r


def test_darkweb_report_all_formats_and_filters(client, db_session):
    user, headers = _user(db_session)
    other, _ = _user(db_session)
    db_session.add(MonitoredAsset(user_id=user.id, kind="domain", value="acme.com"))
    db_session.commit()
    _mention(db_session, user, "critical", "ransomware", "Akira leak site lists ACME")
    _mention(db_session, user, "high", "forum", "ACME database for sale")
    _mention(db_session, user, "medium", "telegram", "ACME mentioned in channel")
    _mention(db_session, user, "high", "breach", "Old breach", days_ago=40)
    _mention(db_session, other, "critical", "ransomware", "Someone else's mention")

    r = client.post("/api/v1/reports/", headers=headers, json={
        "title": "Exposure", "format": "PDF", "report_type": "darkweb",
        "start_date": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        "darkweb_min_severity": "high",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["report_type"] == "darkweb" and body["darkweb_mentions"] == 2  # critical + high in period

    pdf = _export(client, headers, body["id"], "PDF")
    assert pdf.content.startswith(b"%PDF")
    html = _export(client, headers, body["id"], "HTML").text
    assert "Akira leak site lists ACME" in html and "ACME database for sale" in html
    assert "ACME mentioned in channel" not in html  # below min severity
    assert "Old breach" not in html  # outside period
    assert "Someone else" not in html  # other user's data
    assert "<b>Akira" in html and "snippet <b>" not in html  # snippets escaped
    csv_rows = _export(client, headers, body["id"], "CSV").text.strip().splitlines()
    assert len(csv_rows) == 3 and csv_rows[0].startswith("severity,source")
    data = json.loads(_export(client, headers, body["id"], "JSON").text)
    assert len(data["darkweb"]["mentions"]) == 2

    r = client.post("/api/v1/reports/", headers=headers, json={
        "title": "Forum only", "format": "HTML", "report_type": "darkweb", "darkweb_sources": ["forum"],
    })
    assert r.json()["darkweb_mentions"] == 1


def test_ioc_report_with_darkweb_summary(client, db_session):
    user, headers = _user(db_session)
    _mention(db_session, user, "critical", "ransomware", "Akira leak site lists ACME")
    _mention(db_session, user, "low", "feed", "News mention")

    r = client.post("/api/v1/reports/", headers=headers,
                    json={"title": "IOC + DW", "format": "HTML", "include_darkweb": True})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["report_type"] == "ioc" and body["include_darkweb"] is True and body["darkweb_mentions"] == 2
    html = _export(client, headers, body["id"], "HTML").text
    assert "Dark web exposure (summary)" in html and "Akira leak site lists ACME" in html
    assert "News mention" not in html  # summary lists only critical/high
    assert "1 further mention (" in html
    assert _export(client, headers, body["id"], "PDF").content.startswith(b"%PDF")

    plain = client.post("/api/v1/reports/", headers=headers, json={"title": "IOC only", "format": "HTML"}).json()
    assert "Dark web exposure" not in _export(client, headers, plain["id"], "HTML").text


def test_viewer_cannot_create_darkweb_report(client, db_session):
    _, headers = _user(db_session, UserRole.VIEWER)
    r = client.post("/api/v1/reports/", headers=headers, json={"title": "x", "report_type": "darkweb"})
    assert r.status_code == 403


def test_schema_sync_adds_nullable_columns(tmp_path):
    from sqlalchemy import create_engine, inspect, text

    from app.db.schema_sync import add_missing_columns

    engine = create_engine(f"sqlite:///{tmp_path}/old.db")
    with engine.begin() as conn:  # a 2.0-era reports table without report_spec
        conn.execute(text("CREATE TABLE reports (id VARCHAR PRIMARY KEY, user_id VARCHAR NOT NULL, "
                          "title VARCHAR(200) NOT NULL, description TEXT, content TEXT, format VARCHAR(4) NOT NULL, "
                          "shared_link VARCHAR(500), ioc_query_ids JSON, shared_with_user_ids JSON, "
                          "created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"))
    added = add_missing_columns(engine)
    assert "reports.report_spec" in added
    assert "report_spec" in {c["name"] for c in inspect(engine).get_columns("reports")}
    assert add_missing_columns(engine) == []  # idempotent
    assert Report.__table__.c.report_spec.nullable
