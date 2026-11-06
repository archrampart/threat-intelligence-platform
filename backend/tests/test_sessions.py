"""Cookie sessions, CSRF protection and refresh-token rotation."""

from uuid import uuid4

from app.core.security import get_password_hash
from app.models.user import User, UserRole

XHR = {"X-Requested-With": "XMLHttpRequest"}
PASSWORD = "Sup3rS3cretPass!"


def _user(db, username="sess"):
    user = User(
        id=str(uuid4()),
        username=f"{username}{uuid4().hex[:6]}",
        email=f"{uuid4().hex[:8]}@example.com",
        password_hash=get_password_hash(PASSWORD),
        role=UserRole.ANALYST,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def _login(client, user):
    r = client.post("/api/v1/auth/login", data={"username": user.username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r


def test_login_sets_httponly_strict_cookies(client, db_session):
    r = _login(client, _user(db_session))
    cookies = r.headers.get_list("set-cookie")
    access = next(c for c in cookies if c.startswith("tip_access="))
    refresh = next(c for c in cookies if c.startswith("tip_refresh="))
    for c in (access, refresh):
        assert "HttpOnly" in c and "SameSite=strict" in c
    assert "Path=/api" in access and "Path=/api/v1/auth" in refresh


def test_cookie_auth_and_csrf_header(client, db_session):
    _login(client, _user(db_session))
    assert client.get("/api/v1/auth/me").status_code == 200  # cookie only, safe method
    # Unsafe method with cookie auth but without the CSRF header is refused
    assert client.post("/api/v1/ioc/extract", json={"text": "1.2.3.4"}).status_code == 403
    assert client.post("/api/v1/ioc/extract", json={"text": "1.2.3.4"}, headers=XHR).status_code == 200


def test_bearer_clients_need_no_csrf_header(client, db_session):
    token = _login(client, _user(db_session)).json()["access_token"]
    client.cookies.clear()
    r = client.post("/api/v1/ioc/extract", json={"text": "1.2.3.4"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_cookie_refresh_rotates_and_hides_tokens(client, db_session):
    _login(client, _user(db_session))
    old_refresh = client.cookies.get("tip_refresh")
    assert client.post("/api/v1/auth/refresh").status_code == 403  # CSRF header required
    r = client.post("/api/v1/auth/refresh", headers=XHR)
    assert r.status_code == 200
    assert r.json()["access_token"] is None and r.json()["refresh_token"] is None  # not readable by scripts
    assert client.cookies.get("tip_refresh") != old_refresh


def test_refresh_token_reuse_revokes_all_sessions(client, db_session):
    user = _user(db_session)
    tokens = _login(client, user).json()
    client.cookies.clear()

    first = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    rotated = first.json()["refresh_token"]

    # Replaying the already used token -> theft assumed -> everything revoked
    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401 and "reuse" in replay.json()["detail"]
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": rotated}).status_code == 401


def test_logout_revokes_refresh_and_clears_cookies(client, db_session):
    user = _user(db_session)
    tokens = _login(client, user).json()
    r = client.post("/api/v1/auth/logout", headers=XHR)
    assert r.status_code == 204
    assert any(c.startswith("tip_access=") and "Max-Age=0" in c for c in r.headers.get_list("set-cookie"))
    client.cookies.clear()
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_password_change_revokes_other_sessions(client, db_session):
    user = _user(db_session)
    other_session = _login(client, user).json()
    current = _login(client, user).json()
    client.cookies.clear()
    r = client.put(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "An0ther-L0ng-Passw0rd"},
        headers={"Authorization": f"Bearer {current['access_token']}"},
    )
    assert r.status_code == 200 and r.json()["revoked_sessions"] >= 2
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": other_session["refresh_token"]}).status_code == 401


def test_legacy_refresh_tokens_without_db_record_are_rejected(client, db_session):
    from app.core.security import create_refresh_token

    user = _user(db_session)
    forged_but_signed = create_refresh_token({"sub": user.id})  # valid signature, never issued
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": forged_but_signed}).status_code == 401
