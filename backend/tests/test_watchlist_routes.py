"""Watchlist create / update routes: manually added assets."""

import json


def _assets(*pairs):
    return json.dumps([{"ioc_type": t, "ioc_value": v, "risk_threshold": "medium", "is_active": True}
                       for t, v in pairs])


def test_create_keeps_manually_added_assets(client, auth_headers):
    r = client.post("/api/v1/watchlists/", headers=auth_headers, data={
        "name": "Manual", "check_interval": "60", "notification_enabled": "true",
        "assets_json": _assets(("email", " ceo@acme.com "), ("ip", "8.8.8.8")),
    })
    assert r.status_code == 201, r.text
    assets = {(a["ioc_type"], a["ioc_value"]) for a in r.json()["assets"]}
    assert assets == {("email", "ceo@acme.com"), ("ip", "8.8.8.8")}

    fetched = client.get(f"/api/v1/watchlists/{r.json()['id']}", headers=auth_headers).json()
    assert len(fetched["assets"]) == 2


def test_create_combines_manual_assets_and_file(client, auth_headers):
    r = client.post("/api/v1/watchlists/", headers=auth_headers,
                    data={"name": "Both", "assets_json": _assets(("email", "soc@acme.com"))},
                    files={"file": ("iocs.txt", b"1.1.1.1\nexample.org\n", "text/plain")})
    assert r.status_code == 201, r.text
    assert {a["ioc_value"] for a in r.json()["assets"]} == {"soc@acme.com", "1.1.1.1", "example.org"}


def test_invalid_assets_are_rejected(client, auth_headers):
    for bad in ('{"not": "a list"}', _assets(("phone", "123")), _assets(("email", "   ")), "not json"):
        r = client.post("/api/v1/watchlists/", headers=auth_headers, data={"name": "Bad", "assets_json": bad})
        assert r.status_code == 400, (bad, r.text)
        assert "Invalid assets JSON" in r.json()["detail"]


def test_update_adds_email_asset(client, auth_headers):
    created = client.post("/api/v1/watchlists/", headers=auth_headers, data={"name": "Edit me"}).json()
    r = client.put(f"/api/v1/watchlists/{created['id']}", headers=auth_headers,
                   data={"name": "Edit me", "assets_json": _assets(("email", "it@acme.com"))})
    assert r.status_code == 200, r.text
    assert [a["ioc_value"] for a in r.json()["assets"]] == ["it@acme.com"]


def test_delete_removes_items_and_history(client, auth_headers, db_session):
    from uuid import uuid4

    from app.models.watchlist import AssetCheckHistory, AssetWatchlistItem

    created = client.post("/api/v1/watchlists/", headers=auth_headers, data={
        "name": "Gone", "assets_json": _assets(("email", "a@acme.com"), ("ip", "1.1.1.1"))}).json()
    item = db_session.query(AssetWatchlistItem).filter_by(watchlist_id=created["id"]).first()
    db_session.add(AssetCheckHistory(id=str(uuid4()), watchlist_item_id=item.id))
    db_session.commit()

    # editing replaces the items without leaving history behind
    r = client.put(f"/api/v1/watchlists/{created['id']}", headers=auth_headers,
                   data={"name": "Gone", "assets_json": _assets(("email", "b@acme.com"))})
    assert r.status_code == 200
    assert db_session.query(AssetCheckHistory).count() == 0
    assert db_session.query(AssetWatchlistItem).filter_by(watchlist_id=created["id"]).count() == 1

    assert client.delete(f"/api/v1/watchlists/{created['id']}", headers=auth_headers).status_code == 204
    assert db_session.query(AssetWatchlistItem).filter_by(watchlist_id=created["id"]).count() == 0
