"""Dark web source registry: health status, per-user preferences and custom feeds."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.core.security import create_access_token, get_password_hash
from app.models.darkweb import DarkWebMention, DarkWebSource, MonitoredAsset
from app.models.user import User, UserRole
from app.services.darkweb import feeds, sources
from app.services.darkweb.service import DarkWebMonitor


def _user(db, role=UserRole.ANALYST):
    user = User(id=str(uuid4()), username=f"src{uuid4().hex[:6]}", email=f"{uuid4().hex[:6]}@example.com",
                password_hash=get_password_hash("Sup3rS3cretPass!"), role=role, is_active=True)
    db.add(user)
    db.commit()
    return user, {"Authorization": f"Bearer {create_access_token({'sub': user.id})}"}


def _post(victim, domain=""):
    return feeds.LeakPost(source="ransomware.live", group="akira", victim=victim, domain=domain, description="",
                          url="https://www.ransomware.live/id/x", published_at=None)


RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>CTI</title>
<item><title>Acme Corp listed by group X</title><link>https://cti.example.org/1</link>
<description><![CDATA[<p>Data of <b>acme.com</b> published</p>]]></description>
<pubDate>Wed, 05 Nov 2026 10:00:00 GMT</pubDate></item>
<item><title>Unrelated</title><link>https://cti.example.org/2</link></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Leak: acme.com</title><link href="https://cti.example.org/a"/><summary>dump</summary>
<updated>2026-11-05T10:00:00Z</updated></entry></feed>"""

BOMB = b"""<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;">]>
<rss><channel><item><title>&lol2;</title></item></channel></rss>"""


# --------------------------------------------------------------------------- parsing


def test_rss_and_atom_parsing():
    items = sources.parse_rss_feed(RSS)
    assert [i.title for i in items] == ["Acme Corp listed by group X", "Unrelated"]
    assert items[0].text == "Data of acme.com published" and items[0].url == "https://cti.example.org/1"
    assert items[0].published_at.year == 2026
    atom = sources.parse_rss_feed(ATOM)
    assert atom[0].url == "https://cti.example.org/a" and atom[0].published_at.day == 5


def test_xml_entity_attacks_are_blocked():
    with pytest.raises(Exception):
        sources.parse_rss_feed(BOMB)


def test_json_feed_mapping():
    data = b'{"data": [{"name": "Acme Corp", "site": "acme.com", "when": "2026-11-05T10:00:00Z", "link": "https://x/1"},' \
           b' {"site": "no title"}]}'
    items = sources.parse_json_feed(data, {"items_path": "$.data[*]", "title_path": "$.name", "text_path": "$.site",
                                           "url_path": "$.link", "date_path": "$.when"})
    assert len(items) == 1 and items[0].text == "acme.com" and items[0].url == "https://x/1"


def test_config_validation():
    assert "not allowed" in sources.validate_config({"url": "http://169.254.169.254/feed", "format": "rss"})
    assert sources.validate_config({"url": "ftp://x/feed", "format": "rss"})
    assert sources.validate_config({"url": "https://1.1.1.1/f", "format": "json"}) == "title_path is required for JSON feeds"
    assert sources.validate_config({"url": "https://1.1.1.1/f", "format": "json", "title_path": "$[["})
    assert sources.validate_config({"url": "https://1.1.1.1/f", "format": "rss"}) is None


# --------------------------------------------------------------------------- scan integration


def test_collect_shared_records_health(db_session):
    with patch.object(feeds, "ransomware_live_posts", return_value=[_post("A"), _post("B")]), \
         patch.object(feeds, "ransomlook_posts", side_effect=ConnectionError("down")), \
         patch.object(feeds, "hibp_catalog", return_value=[]):
        shared = DarkWebMonitor(db_session).collect_shared()
    rows = {r.key: r for r in db_session.query(DarkWebSource).all()}
    assert len(shared["ransomware_live"]) == 2 and shared["ransomlook"] is None
    assert rows["ransomware_live"].last_item_count == 2 and rows["ransomware_live"].last_error is None
    assert "down" in rows["ransomlook"].last_error


def test_user_can_switch_off_a_source(client, db_session):
    user, headers = _user(db_session)
    db_session.add(MonitoredAsset(user_id=user.id, kind="keyword", value="Acme"))
    db_session.commit()
    sources.seed_sources(db_session)
    r = client.put("/api/v1/darkweb/sources/ransomware_live/preference", json={"enabled": False}, headers=headers)
    assert r.status_code == 200
    listed = {s["key"]: s for s in client.get("/api/v1/darkweb/sources", headers=headers).json()}
    assert listed["ransomware_live"]["user_enabled"] is False and listed["ransomlook"]["user_enabled"] is True

    shared = {"ransomware_live": [_post("Acme Ltd")], "ransomlook": [], "hibp": [], "custom": {}}
    with patch.object(feeds, "infostealer_exposure", return_value=None):
        result = DarkWebMonitor(db_session).scan_user(user.id, shared=shared)
    assert result["new_mentions"] == 0 and "ransomware_live" not in result["sources_used"]


def test_globally_disabled_source_is_not_fetched(db_session):
    sources.seed_sources(db_session)
    db_session.query(DarkWebSource).filter_by(key="hibp").update({DarkWebSource.is_enabled: False})
    db_session.commit()
    with patch.object(feeds, "ransomware_live_posts", return_value=[]), \
         patch.object(feeds, "ransomlook_posts", return_value=[]), \
         patch.object(feeds, "hibp_catalog") as hibp:
        DarkWebMonitor(db_session).collect_shared()
    hibp.assert_not_called()


def test_custom_feed_end_to_end(client, db_session):
    _, admin = _user(db_session, UserRole.ADMIN)
    analyst, analyst_headers = _user(db_session, UserRole.ANALYST)
    config = {"url": "https://cti.example.org/feed.xml", "format": "rss", "severity": "critical"}

    assert client.post("/api/v1/darkweb/sources", json={"name": "CTI Feed", "config": config},
                       headers=analyst_headers).status_code == 403
    blocked = dict(config, url="http://127.0.0.1:6379/")
    assert client.post("/api/v1/darkweb/sources", json={"name": "Bad", "config": blocked}, headers=admin).status_code == 400

    with patch("app.services.darkweb.sources.validate_outbound_url", lambda u: u), \
         patch("app.services.darkweb.sources._download", return_value=RSS):
        preview = client.post("/api/v1/darkweb/sources/preview", json=config, headers=admin)
        assert preview.status_code == 200 and preview.json()["count"] == 2
        created = client.post("/api/v1/darkweb/sources", json={"name": "CTI Feed", "config": config}, headers=admin)
        assert created.status_code == 201
        key = created.json()["key"]
        assert key == "custom_cti_feed"

        # analysts see the source but not its URL
        listed = {s["key"]: s for s in client.get("/api/v1/darkweb/sources", headers=analyst_headers).json()}
        assert "config" not in listed[key]

        db_session.add(MonitoredAsset(user_id=analyst.id, kind="domain", value="acme.com"))
        db_session.commit()
        monitor = DarkWebMonitor(db_session)
        with patch.object(feeds, "ransomware_live_posts", return_value=[]), \
             patch.object(feeds, "ransomlook_posts", return_value=[]), \
             patch.object(feeds, "hibp_catalog", return_value=[]), \
             patch.object(feeds, "infostealer_exposure", return_value=None), \
             patch("app.services.notifier.notify_user_async"):
            result = monitor.scan_user(analyst.id)
    # the patched download also feeds the built-in RSS sources: forum / breach feeds keep their own category
    assert result["by_source"] == {"feed": 1, "forum": 2, "breach": 1}
    mention = db_session.query(DarkWebMention).filter_by(user_id=analyst.id, source="feed").one()
    assert mention.severity == "critical" and mention.actor == "CTI Feed" and mention.url == "https://cti.example.org/1"

    assert client.delete("/api/v1/darkweb/sources/hibp", headers=admin).status_code == 400  # built-in
    assert client.put("/api/v1/darkweb/sources/hibp", json={"is_enabled": False}, headers=admin).json()["is_enabled"] is False
    assert client.delete(f"/api/v1/darkweb/sources/{key}", headers=admin).status_code == 204


def test_builtin_feeds_seeded_and_news_disabled_by_default(client, db_session):
    _, headers = _user(db_session)
    listed = {s["key"]: s for s in client.get("/api/v1/darkweb/sources", headers=headers).json()}
    assert listed["darkwebinformer"]["is_enabled"] is True and listed["darkwebinformer"]["category"] == "forum"
    assert listed["news_hackread"]["is_enabled"] is False
    assert listed["dailydarkweb"]["is_enabled"] is False  # stale feed
    for key in sources.BUILTIN_FEEDS:
        assert sources.validate_config(key["config"]) is None


def test_rate_limited_leak_feed_is_reported(db_session):
    with patch.object(feeds, "_cached_json", return_value={"message": "1 per 1 minute"}):
        with pytest.raises(ValueError, match="1 per 1 minute"):
            feeds.ransomware_live_posts()


def test_suggested_channels(client, db_session):
    _, headers = _user(db_session)
    body = client.get("/api/v1/darkweb/channels/suggested", headers=headers).json()
    assert {c["username"] for c in body} >= {"darkfeed"} and all(c["added"] is False for c in body)
