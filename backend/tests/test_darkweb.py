"""Dark web monitoring: matcher, Telegram parsing, scan logic and API (all network mocked)."""

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.core.security import create_access_token, get_password_hash
from app.models.darkweb import DarkWebMention, MonitoredAsset, TelegramAccount, TelegramChannel
from app.models.user import User, UserRole
from app.services.darkweb import feeds, telegram
from app.services.darkweb.matcher import Asset, Matcher, normalise, validate
from app.services.darkweb.service import DarkWebMonitor


FAKE_API_HASH = "x" * 32  # obviously fake test value


def _user(db, role=UserRole.ANALYST):
    user = User(id=str(uuid4()), username=f"dw{uuid4().hex[:6]}", email=f"{uuid4().hex[:6]}@example.com",
                password_hash=get_password_hash("Sup3rS3cretPass!"), role=role, is_active=True)
    db.add(user)
    db.commit()
    return user, {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}


# --------------------------------------------------------------------------- matcher


def test_domain_matching_rules():
    m = Matcher([Asset("a", "u", "domain", "acme.com")])
    assert m.find("data from vpn.acme.com dumped")
    assert m.find("ACME.COM")
    assert not m.find("evil-acme.com phishing kit")  # different registrable name
    assert not m.find("acme.com.tr")  # different domain
    assert m.find("Victim list: acme.com.")  # sentence punctuation is fine


def test_keyword_and_email_matching():
    m = Matcher([Asset("k", "u", "keyword", "Contoso"), Asset("e", "u", "email_domain", "contoso.org")])
    assert {a.id for a in m.find("Contoso employees")} == {"k"}
    assert not m.find("contosoland")  # whole word only
    # the e-mail domain matches; the brand keyword legitimately matches inside the domain too
    assert {a.id for a in m.find("leak: john@mail.contoso.org:pass")} == {"e", "k"}
    assert {a.id for a in m.find("john@contoso.org.evil.net")} == {"k"}  # not the e-mail domain


def test_normalise_and_validate():
    assert normalise("domain", " https://www.Acme.com/path ") == "acme.com"
    assert normalise("email_domain", "@Acme.com") == "acme.com"
    assert validate("domain", "acme") is not None
    assert validate("keyword", "ab") is not None
    assert validate("keyword", "Acme Corp") is None


# --------------------------------------------------------------------------- telegram parsing

_PREVIEW = """
<div class="tgme_channel_info_header_title"><span dir="auto">Leak Watch</span></div>
<div class="tgme_widget_message_wrap"><div class="tgme_widget_message js-widget_message" data-post="leakwatch/41">
 <div class="tgme_widget_message_text js-message_text" dir="auto">Selling <b>VPN access</b> to acme.com<br/>DM <a href="#">@x</a>
   <div class="nested">inner</div> tail</div>
 <a class="tgme_widget_message_date" href="https://t.me/leakwatch/41"><time datetime="2026-11-05T10:00:00+00:00"></time></a>
</div></div>
<div class="tgme_widget_message js-widget_message" data-post="leakwatch/42">
 <div class="tgme_widget_message_text js-message_text">nothing here &amp; there</div>
</div>
"""


def test_parse_preview():
    title, messages = telegram.parse_preview(_PREVIEW, "leakwatch")
    assert title == "Leak Watch"
    assert [m.message_id for m in messages] == [41, 42]
    assert "VPN access to acme.com\nDM @x" in messages[0].text and "inner" in messages[0].text and "tail" in messages[0].text
    assert messages[0].url == "https://t.me/leakwatch/41"
    assert messages[0].published_at == datetime(2026, 11, 5, 10, tzinfo=timezone.utc)
    assert messages[1].text == "nothing here & there"


@pytest.mark.parametrize("raw,expected", [("@leakwatch", "leakwatch"), ("https://t.me/s/leakwatch", "leakwatch"),
                                          ("t.me/leakwatch/41", "leakwatch")])
def test_normalise_username(raw, expected):
    assert telegram.normalise_username(raw) == expected


def test_fetch_public_rejects_bad_usernames():
    with pytest.raises(ValueError):
        telegram.fetch_public("../../evil")


# --------------------------------------------------------------------------- scan


def _post(victim, domain="", group="lockbit", description=""):
    return feeds.LeakPost(source="ransomware.live", group=group, victim=victim, domain=domain, description=description,
                          url="https://www.ransomware.live/id/x", published_at=datetime(2026, 11, 5, tzinfo=timezone.utc))


def test_scan_creates_deduplicated_mentions_and_alerts(db_session):
    from app.models.alert import Alert

    user, _ = _user(db_session)
    other, _ = _user(db_session)
    for kind, value in (("domain", "acme.com"), ("keyword", "Contoso")):
        db_session.add(MonitoredAsset(user_id=user.id, kind=kind, value=value))
    db_session.add(MonitoredAsset(user_id=other.id, kind="domain", value="unrelated.org"))
    db_session.add(TelegramChannel(user_id=user.id, username="leakwatch", mode="public"))
    db_session.commit()

    posts = [_post("ACME Corp", domain="acme.com"), _post("Contoso Ltd", group="akira"), _post("Other Inc")]
    breaches = [{"Name": "AcmeBreach", "Title": "Acme", "Domain": "acme.com", "PwnCount": 1000, "BreachDate": "2024-01-01",
                 "AddedDate": "2024-02-01T00:00:00Z", "DataClasses": ["Emails", "Passwords"]}]
    exposure = {"employees": 3, "users": 10, "third_parties": 0, "last_employee_compromised": "2026-10-01T00:00:00Z",
                "last_user_compromised": None, "stealer_families": {"Lumma": 5}}

    with patch.object(feeds, "infostealer_exposure", return_value=exposure), \
         patch.object(telegram, "fetch_public", return_value=telegram.parse_preview(_PREVIEW, "leakwatch")), \
         patch("app.services.notifier.notify_user_async"):
        result = DarkWebMonitor(db_session).scan_user(user.id, posts=posts, breaches=breaches)
        assert result["by_source"] == {"ransomware": 2, "breach": 1, "infostealer": 1, "telegram": 1}
        again = DarkWebMonitor(db_session).scan_user(user.id, posts=posts, breaches=breaches)
        assert again["new_mentions"] == 0  # fingerprints dedupe

    mentions = {m.source + ":" + m.matched_term: m for m in db_session.query(DarkWebMention).filter_by(user_id=user.id)}
    assert mentions["ransomware:acme.com"].severity == "critical"  # victim domain is the monitored domain
    assert mentions["ransomware:Contoso"].severity == "high"
    assert mentions["telegram:acme.com"].url == "https://t.me/leakwatch/41"
    assert db_session.query(DarkWebMention).filter_by(user_id=other.id).count() == 0  # per-user isolation
    assert db_session.query(Alert).filter_by(user_id=user.id).count() == 5
    channel = db_session.query(TelegramChannel).filter_by(user_id=user.id).one()
    assert channel.last_message_id == 42 and channel.title == "Leak Watch"


def test_channel_failure_is_recorded_not_fatal(db_session):
    user, _ = _user(db_session)
    db_session.add(MonitoredAsset(user_id=user.id, kind="keyword", value="Contoso"))
    db_session.add(TelegramChannel(user_id=user.id, username="gonechannel", mode="public"))
    db_session.commit()
    with patch.object(feeds, "infostealer_exposure", return_value=None), \
         patch.object(telegram, "fetch_public", side_effect=ValueError("Channel has no public preview")):
        result = DarkWebMonitor(db_session).scan_user(user.id, posts=[], breaches=[])
    assert result["status"] == "ok"
    assert "no public preview" in db_session.query(TelegramChannel).filter_by(user_id=user.id).one().last_error


# --------------------------------------------------------------------------- API


def test_asset_api_validation_and_isolation(client, db_session):
    _, alice = _user(db_session)
    _, bob = _user(db_session)
    r = client.post("/api/v1/darkweb/assets", json={"kind": "domain", "value": "https://www.Acme.com/"}, headers=alice)
    assert r.status_code == 201 and r.json()["value"] == "acme.com"
    assert client.post("/api/v1/darkweb/assets", json={"kind": "domain", "value": "acme.com"}, headers=alice).status_code == 409
    assert client.post("/api/v1/darkweb/assets", json={"kind": "keyword", "value": "ab"}, headers=alice).status_code == 400
    assert client.get("/api/v1/darkweb/assets", headers=bob).json() == []
    assert client.delete(f"/api/v1/darkweb/assets/{r.json()['id']}", headers=bob).status_code == 404


def test_channel_api(client, db_session):
    _, headers = _user(db_session, UserRole.VIEWER)
    with patch.object(telegram, "fetch_public", return_value=("Leak Watch", [])):
        r = client.post("/api/v1/darkweb/channels", json={"username": "https://t.me/leakwatch"}, headers=headers)
    assert r.status_code == 201 and r.json()["username"] == "leakwatch" and r.json()["title"] == "Leak Watch"
    with patch.object(telegram, "fetch_public", side_effect=ValueError("Channel has no public preview")):
        r = client.post("/api/v1/darkweb/channels", json={"username": "privatechan"}, headers=headers)
    assert r.status_code == 400
    r = client.post("/api/v1/darkweb/channels", json={"username": "secretgroup", "mode": "account"}, headers=headers)
    assert r.status_code == 400 and "Connect your Telegram account" in r.json()["detail"]


def test_telegram_account_login_flow_encrypts_secrets(client, db_session):
    user, headers = _user(db_session)
    with patch.object(telegram, "account_send_code", return_value=("partial-session", "code-hash")):
        r = client.post("/api/v1/darkweb/telegram-account/start",
                        json={"api_id": 12345, "api_hash": FAKE_API_HASH, "phone": "+90 555 123 4567"},
                        headers=headers)
    assert r.status_code == 200 and r.json()["phone"] == "+90•••••67"
    account = db_session.get(TelegramAccount, user.id)
    assert FAKE_API_HASH not in account.api_hash_enc and "partial-session" not in account.session_enc

    with patch.object(telegram, "account_sign_in", return_value=("full-session", "Analyst")) as sign_in:
        r = client.post("/api/v1/darkweb/telegram-account/verify", json={"code": "12345"}, headers=headers)
    assert r.status_code == 200 and r.json()["status"] == "connected"
    args = sign_in.call_args.args
    assert args[2] == "partial-session" and args[3] == "+905551234567" and args[5] == "code-hash"
    assert client.get("/api/v1/darkweb/telegram-account", headers=headers).json()["status"] == "connected"

    assert client.delete("/api/v1/darkweb/telegram-account", headers=headers).status_code == 204
    assert client.get("/api/v1/darkweb/telegram-account", headers=headers).json()["status"] == "not_connected"


def test_mentions_api(client, db_session):
    user, headers = _user(db_session)
    other, other_headers = _user(db_session)
    m = DarkWebMention(user_id=user.id, source="telegram", severity="high", matched_term="acme.com", title="t",
                       fingerprint="fp1")
    db_session.add(m)
    db_session.commit()
    body = client.get("/api/v1/darkweb/mentions?unread_only=true", headers=headers).json()
    assert body["total"] == 1
    assert client.get("/api/v1/darkweb/mentions", headers=other_headers).json()["total"] == 0
    assert client.put(f"/api/v1/darkweb/mentions/{m.id}", json={"is_read": True}, headers=other_headers).status_code == 404
    assert client.put(f"/api/v1/darkweb/mentions/{m.id}", json={"is_read": True}, headers=headers).json()["is_read"] is True
    assert client.get("/api/v1/darkweb/summary", headers=headers).json()["unread"] == 0


def test_mentions_sorted_unread_then_severity(client, db_session):
    user, headers = _user(db_session)
    for i, (sev, read) in enumerate([("medium", False), ("critical", False), ("high", True), ("high", False)]):
        db_session.add(DarkWebMention(user_id=user.id, source="telegram", severity=sev, matched_term="x", title=f"m{i}",
                                      fingerprint=f"s{i}", is_read=read))
    db_session.commit()
    order = [(m["severity"], m["is_read"]) for m in client.get("/api/v1/darkweb/mentions", headers=headers).json()["items"]]
    assert order == [("critical", False), ("high", False), ("medium", False), ("high", True)]
