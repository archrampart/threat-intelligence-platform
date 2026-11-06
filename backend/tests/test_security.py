"""Regression tests for security hardening."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    get_user_id_from_token,
    verify_password,
)
from app.core.url_guard import UnsafeURLError, validate_outbound_url
from app.models.user import User, UserRole


def _make_user(db, username: str, role: UserRole, password: str = "Sup3rS3cretPass!") -> User:
    user = User(
        id=str(uuid4()),
        username=username,
        email=f"{username}@example.com",
        password_hash=get_password_hash(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def _headers(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': user.id, 'username': user.username})}"}


# --------------------------------------------------------------------------- passwords / JWT


def test_password_hash_roundtrip_and_legacy_passlib_hash():
    h = get_password_hash("correct horse battery staple")
    assert verify_password("correct horse battery staple", h)
    assert not verify_password("wrong", h)
    # Hash produced by the previous passlib[bcrypt] implementation must keep working
    legacy = "$2b$12$F4C7wrVbrpvjSxzXvSvtrO/GXGDn89LR52OkOvHKWt0P.tgq2z0m."  # passlib 1.7.4 CryptContext(schemes=["bcrypt"]).hash("admin123")
    assert verify_password("admin123", legacy)
    assert not verify_password("admin124", legacy)
    assert not verify_password("x", "not-a-bcrypt-hash")


def test_long_password_does_not_raise():
    h = get_password_hash("a" * 200)
    assert verify_password("a" * 200, h)


def test_refresh_token_cannot_be_used_as_access_token():
    assert get_user_id_from_token(create_refresh_token({"sub": "u1"})) is None
    assert get_user_id_from_token(create_access_token({"sub": "u1"})) == "u1"


def test_unsigned_and_foreign_tokens_rejected():
    now = datetime.now(timezone.utc)
    claims = {"sub": "u1", "type": "access", "exp": now + timedelta(minutes=5), "iat": now}
    none_token = jwt.encode(claims, key=None, algorithm="none")
    assert get_user_id_from_token(none_token) is None
    forged = jwt.encode({**claims, "iss": get_settings().jwt_issuer}, "attacker-key-" + "x" * 32, algorithm="HS256")
    assert get_user_id_from_token(forged) is None


def test_expired_token_rejected():
    assert get_user_id_from_token(create_access_token({"sub": "u1"}, timedelta(seconds=-5))) is None


# --------------------------------------------------------------------------- SSRF guard


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:6379/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://0.0.0.0/",
        "file:///etc/passwd",
        "gopher://1.1.1.1/",
        "http://user:pass@1.1.1.1/",
        "http://localhost/",
    ],
)
def test_url_guard_blocks_internal_targets(url):
    with pytest.raises(UnsafeURLError):
        validate_outbound_url(url)


def test_url_guard_allows_public_ip():
    assert validate_outbound_url("https://1.1.1.1/path") == "https://1.1.1.1/path"


def test_dynamic_client_blocks_internal_override():
    from unittest.mock import Mock

    from app.models.api_source import AuthenticationType
    from app.services.dynamic_api_client import DynamicAPIClient

    source = Mock()
    source.name = "test"
    source.base_url = "https://example.com"
    source.request_config = {"endpoint_template": "/{ioc_value}"}
    source.response_config = {}
    source.authentication_type = AuthenticationType.NONE
    client = DynamicAPIClient(source, "k", api_url_override="http://169.254.169.254")
    result = client.query("ip", "1.2.3.4")
    assert result["status"] == "error"
    assert "Blocked" in result["error"]


def test_dynamic_client_encodes_path_traversal():
    from unittest.mock import Mock

    from app.services.dynamic_api_client import DynamicAPIClient

    source = Mock()
    source.base_url = "https://api.example.com/v1"
    source.request_config = {"endpoint_template": "/ip/{ioc_value}"}
    source.response_config = {}
    client = DynamicAPIClient(source, "k")
    assert client._build_url("ip", "../../admin") == "https://api.example.com/v1/ip/..%2F..%2Fadmin"


# --------------------------------------------------------------------------- authorization


def test_metrics_requires_admin(client, db_session):
    analyst = _make_user(db_session, "an1", UserRole.ANALYST)
    admin = _make_user(db_session, "ad1", UserRole.ADMIN)
    assert client.get("/api/v1/metrics").status_code == 401
    assert client.get("/api/v1/metrics", headers=_headers(analyst)).status_code == 403
    assert client.get("/api/v1/metrics", headers=_headers(admin)).status_code == 200


def test_analyst_cannot_modify_global_api_sources(client, db_session):
    analyst = _make_user(db_session, "an2", UserRole.ANALYST)
    payload = {
        "name": "evil",
        "display_name": "Evil",
        "base_url": "https://1.1.1.1",
        "authentication_type": "none",
    }
    r = client.post("/api/v1/api-sources/", json=payload, headers=_headers(analyst))
    assert r.status_code == 403


def test_admin_cannot_create_api_source_pointing_to_internal_host(client, db_session):
    admin = _make_user(db_session, "ad2", UserRole.ADMIN)
    payload = {
        "name": "internal",
        "display_name": "Internal",
        "api_type": "custom",
        "base_url": "http://169.254.169.254",
        "authentication_type": "none",
    }
    r = client.post("/api/v1/api-sources/", json=payload, headers=_headers(admin))
    assert r.status_code == 400


def test_viewer_with_shared_watchlist_cannot_modify_it(db_session):
    from app.models.watchlist import AssetWatchlist
    from app.services.watchlist_service import WatchlistService

    owner = _make_user(db_session, "owner", UserRole.ANALYST)
    viewer = _make_user(db_session, "viewer1", UserRole.VIEWER)
    wl = AssetWatchlist(
        id=str(uuid4()),
        user_id=owner.id,
        name="wl",
        shared_with_user_ids=[viewer.id],
    )
    db_session.add(wl)
    db_session.commit()

    service = WatchlistService(db_session)
    assert service.get_watchlist(wl.id, viewer.id) is not None  # read access
    assert service.delete_watchlist(wl.id, viewer.id) is False  # no write access
    with pytest.raises(ValueError):
        service.share_watchlist(wl.id, viewer.id, [viewer.id])
    assert service.delete_watchlist(wl.id, owner.id) is True


# --------------------------------------------------------------------------- rate limiting


def test_login_rate_limit_ignores_spoofed_forwarded_for():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.middleware.rate_limit import RateLimitMiddleware

    app = FastAPI()

    @app.post("/api/v1/auth/login")
    def login():
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, login_requests_per_minute=3)
    c = TestClient(app)
    codes = [
        c.post("/api/v1/auth/login", headers={"X-Forwarded-For": f"10.0.0.{i}"}).status_code for i in range(5)
    ]
    assert codes[:3] == [200, 200, 200]
    assert codes[3:] == [429, 429]


# --------------------------------------------------------------------------- report output encoding


def test_html_report_escapes_untrusted_values(db_session):
    from app.services.report_service import ReportService

    html = ReportService(db_session)._generate_html_content(
        {
            "title": "<script>alert(1)</script>",
            "description": "<img src=x onerror=alert(2)>",
            "generated_at": "2026-01-01T00:00:00",
            "total_queries": 1,
            "queries": [
                {
                    "ioc_type": "domain",
                    "ioc_value": "evil.com\"><svg onload=alert(3)>",
                    "risk_score": 0.9,
                    "threat_intelligence": [
                        {"source": "<b>otx</b>", "confidence_score": 0.9, "tags": ["<iframe src=//x>"]}
                    ],
                }
            ],
        }
    )
    for needle in ("<script>alert", "<img src=x", "<svg onload", "<iframe src", "<b>otx</b>"):
        assert needle not in html


def test_csv_formula_injection_neutralised():
    from app.services.report_service import _csv_safe

    assert _csv_safe("=HYPERLINK(\"http://x\")").startswith("'")
    assert _csv_safe("@SUM(1)").startswith("'")
    assert _csv_safe("1.2.3.4") == "1.2.3.4"


def test_production_rejects_default_secrets(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "your-secret-key-change-in-production")
    with pytest.raises(Exception):
        Settings(_env_file=None)
    monkeypatch.setenv("SECRET_KEY", "s" * 48)
    monkeypatch.setenv("ENCRYPTION_KEY", "e" * 48)
    assert Settings(_env_file=None).is_production


# --------------------------------------------------------------------------- personal API keys


def _add_key(db, user, source_id="predefined-virustotal"):
    from app.core.encryption import encrypt_value
    from app.models.api_source import APIKey, APISource, APIType, AuthenticationType

    if not db.query(APISource).filter(APISource.id == source_id).first():
        db.add(
            APISource(
                id=source_id,
                name=source_id.split("-", 1)[1],
                display_name="VirusTotal",
                api_type=APIType.PREDEFINED,
                base_url="https://www.virustotal.com/api/v3",
                supported_ioc_types=["ip"],
                authentication_type=AuthenticationType.API_KEY,
                request_config={},
                is_active=True,
            )
        )
    key = APIKey(id=str(uuid4()), user_id=user.id, api_source_id=source_id, api_key=encrypt_value("k-" + user.id))
    db.add(key)
    db.commit()
    return key


def test_ioc_query_uses_only_callers_own_keys(db_session):
    from app.services.ioc_service import IOCService

    alice = _make_user(db_session, "alice", UserRole.ANALYST)
    bob = _make_user(db_session, "bob", UserRole.ANALYST)
    viewer = _make_user(db_session, "viewer2", UserRole.VIEWER)
    _add_key(db_session, alice)
    _add_key(db_session, alice)  # duplicate for the same source -> queried once
    bob_key = _add_key(db_session, bob)

    service = IOCService(db_session)
    alice_keys = service._get_active_api_keys(alice.id)
    assert len(alice_keys) == 1 and alice_keys[0][0].user_id == alice.id
    assert alice_keys[0][0].id != bob_key.id
    assert [k.id for k, _ in service._get_active_api_keys(bob.id)] == [bob_key.id]
    assert service._get_active_api_keys(viewer.id) == []


def test_api_keys_are_private_even_for_admins(client, db_session):
    owner = _make_user(db_session, "keyowner", UserRole.ANALYST)
    admin = _make_user(db_session, "admin2", UserRole.ADMIN)
    key = _add_key(db_session, owner)

    assert [k["id"] for k in client.get("/api/v1/api-keys/", headers=_headers(owner)).json()] == [key.id]
    assert client.get("/api/v1/api-keys/", headers=_headers(admin)).json() == []
    assert client.get(f"/api/v1/api-keys/{key.id}", headers=_headers(admin)).status_code == 404
    assert client.delete(f"/api/v1/api-keys/{key.id}", headers=_headers(admin)).status_code == 404


def test_ioc_cache_is_per_user():
    from datetime import datetime, timezone

    from app.schemas.ioc import IOCQueryResponse
    from app.services.cache import IOCResponseCache

    cache = IOCResponseCache()
    resp = IOCQueryResponse(ioc_type="ip", ioc_value="1.2.3.4", overall_risk="high", queried_sources=[],
                            queried_at=datetime.now(timezone.utc))
    cache.set(resp, scope="alice")
    assert cache.get("ip", "1.2.3.4", scope="alice") is not None
    assert cache.get("ip", "1.2.3.4", scope="bob") is None


def test_viewer_can_manage_own_keys_and_read_catalog(client, db_session):
    from app.models.api_source import APISource, APIType, AuthenticationType

    viewer = _make_user(db_session, "viewer3", UserRole.VIEWER)
    db_session.add(
        APISource(id="predefined-otx", name="otx", display_name="OTX", api_type=APIType.PREDEFINED,
                  base_url="https://otx.alienvault.com/api/v1", supported_ioc_types=["ip"],
                  authentication_type=AuthenticationType.API_KEY, request_config={}, is_active=True)
    )
    db_session.commit()

    sources = client.get("/api/v1/api-sources", headers=_headers(viewer)).json()
    otx = next(s for s in sources if s["name"] == "otx")
    assert otx["access"] == "free_key" and otx["key_signup_url"].startswith("https://otx.alienvault.com")

    r = client.post("/api/v1/api-keys/", json={"api_source_id": "predefined-otx", "api_key": "viewer-own-key"},
                    headers=_headers(viewer))
    assert r.status_code == 201, r.text
    payload = {"name": "x", "display_name": "X", "base_url": "https://1.1.1.1", "authentication_type": "none"}
    assert client.post("/api/v1/api-sources/", json=payload, headers=_headers(viewer)).status_code == 403
