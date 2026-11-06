"""Offline tests for DynamicAPIClient risk normalisation, request building and feed mode."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.models.api_source import AuthenticationType
from app.services import dynamic_api_client as dac
from app.services.dynamic_api_client import DynamicAPIClient


def _source(request_config=None, response_config=None, base_url="https://api.example.com", name="src"):
    return SimpleNamespace(
        name=name,
        display_name=name,
        base_url=base_url,
        request_config=request_config or {},
        response_config=response_config or {},
        authentication_type=AuthenticationType.NONE,
    )


def _response(status=200, text="", json_data=None):
    r = MagicMock()
    r.status_code = status
    r.text = text
    r.is_redirect = False
    r.json.side_effect = (lambda: json_data) if json_data is not None else ValueError("no json")
    r.raise_for_status = MagicMock() if status < 400 else MagicMock(side_effect=dac.requests.HTTPError(str(status)))
    return r


@pytest.mark.parametrize(
    "cfg,value,expected",
    [
        ({"risk_score_max": 100}, 25, 0.25),
        ({"risk_score_max": 10}, 15, 1.0),
        ({}, 0.4, 0.4),
        ({}, 40, 0.4),  # legacy percentage fallback
        ({"risk_score_map": {"malicious": 0.9, "unknown": None}}, "Malicious", 0.9),
        ({"risk_score_map": {"malicious": 0.9, "unknown": None}}, "unknown", None),
        ({"risk_score_map": {"true": 0.7, "false": 0.0}}, False, 0.0),
        ({"risk_score_max": 10, "risk_score_weight": 0.5}, ["CVE-1", "CVE-2"], 0.1),
        ({}, "not-a-number", None),
        ({}, None, None),
    ],
)
def test_normalize_risk(cfg, value, expected):
    assert DynamicAPIClient(_source(response_config=cfg), "")._normalize_risk(value) == expected


def test_form_body_is_url_encoded_and_api_key_header():
    client = DynamicAPIClient(
        _source(
            {
                "method": "POST",
                "headers": {"Content-Type": "application/x-www-form-urlencoded", "Auth-Key": "{api_key}"},
                "body": "query=get_info&hash={ioc_value}",
            }
        ),
        "secret-key",
    )
    headers = client._build_headers()
    assert headers["Auth-Key"] == "secret-key"
    assert client._build_body("hash", "a&b=c", headers) == {"data": "query=get_info&hash=a%26b%3Dc"}


def test_json_body_template_escapes_values():
    client = DynamicAPIClient(
        _source({"method": "POST", "body": {"query": "search_ioc", "search_term": "{ioc_value}"}}), "k"
    )
    body = client._build_body("domain", 'evil"}.com', {})
    assert body == {"json": {"query": "search_ioc", "search_term": 'evil"}.com'}}


def test_hash_type_placeholder():
    client = DynamicAPIClient(_source({"endpoint_template": "/lookup/{hash_type}/{ioc_value}"}), "")
    assert client._build_url("hash", "a" * 32).endswith("/lookup/md5/" + "a" * 32)
    assert client._build_url("hash", "a" * 64).endswith("/lookup/sha256/" + "a" * 64)


def test_free_placeholder_is_not_sent_as_key():
    client = DynamicAPIClient(_source({"headers": {"X-Key": "{api_key}"}}), "FREE_SOURCE_NO_KEY_REQUIRED")
    assert client._build_headers()["X-Key"] == ""


@patch("app.services.dynamic_api_client.validate_outbound_url", lambda u: u)
def test_not_found_ok_returns_success_without_signal():
    client = DynamicAPIClient(_source(response_config={"not_found_ok": True, "risk_score_path": "x"}), "")
    with patch.object(client, "_send", return_value=_response(404)):
        result = client.query("ip", "8.8.8.8")
    assert result["status"] == "success"
    assert result["risk_score"] is None


@patch("app.services.dynamic_api_client.validate_outbound_url", lambda u: u)
def test_feed_membership_exact_cidr_and_url_host():
    dac._feed_cache.clear()
    feed = "# comment\n1.2.3.4\n10.20.0.0/16\nhttps://bad.example.org/login.php\n"
    client = DynamicAPIClient(
        _source(
            {"mode": "feed", "endpoint_template": "/feed.txt", "match_url_host": True},
            {"listed_risk": 0.9, "feed_label": "Test feed"},
        ),
        "",
    )
    with patch.object(client, "_send", return_value=_response(text=feed)) as send:
        assert client.query("ip", "1.2.3.4")["risk_score"] == 0.9
        assert client.query("ip", "10.20.5.6")["raw"]["matched"] == "10.20.0.0/16"
        assert client.query("domain", "bad.example.org")["risk_score"] == 0.9
        clean = client.query("ip", "8.8.8.8")
        assert clean["status"] == "success" and clean["risk_score"] is None
        assert send.call_count == 1  # feed downloaded once, then cached


@patch("app.services.dynamic_api_client.validate_outbound_url", lambda u: u)
def test_feed_csv_column():
    dac._feed_cache.clear()
    feed = "# Listingdate,SHA1,Reason\n2026-11-05 16:25:51,788DE1386A4226D0993C1434A2D820BC1259B88E,C&C\n"
    client = DynamicAPIClient(
        _source({"mode": "feed", "endpoint_template": "/x.csv", "feed_format": "csv", "csv_column": 1}), ""
    )
    with patch.object(client, "_send", return_value=_response(text=feed)):
        assert client.query("hash", "788de1386a4226d0993c1434a2d820bc1259b88e")["raw"]["listed"] is True


def test_catalog_has_no_duplicates_and_deprecations_removed():
    import ast  # noqa: F401
    from app.db.source_catalog import DEPRECATED_SOURCES, NEW_SOURCES, apply_catalog

    legacy = [{"name": "phishtank"}, {"name": "phishtank"}, {"name": "threatminer"}, {"name": "virustotal"}]
    result, deprecated = apply_catalog(legacy)
    names = [a["name"] for a in result]
    assert len(names) == len(set(names))
    assert "threatminer" not in names and "threatminer" in deprecated
    assert all(s["name"] in names for s in NEW_SOURCES)
    assert set(DEPRECATED_SOURCES).isdisjoint(names)


def test_virustotal_style_type_map_and_url_id():
    client = DynamicAPIClient(
        _source(
            {
                "endpoint_template": "/{ioc_type}/{ioc_value}",
                "ioc_type_map": {"ip": "ip_addresses", "url": "urls"},
                "ioc_value_transform": {"url": "base64url"},
            },
            base_url="https://www.virustotal.com/api/v3",
        ),
        "k",
    )
    assert client._build_url("ip", "8.8.8.8") == "https://www.virustotal.com/api/v3/ip_addresses/8.8.8.8"
    assert client._build_url("url", "http://example.com/") == (
        "https://www.virustotal.com/api/v3/urls/aHR0cDovL2V4YW1wbGUuY29tLw"
    )


def test_ioc_query_runs_sources_concurrently_and_keeps_order(db_session):
    import threading
    import time as _time
    from unittest.mock import patch as _patch

    from app.schemas.ioc import IOCQueryRequest, IOCSourceResult
    from app.services.ioc_service import IOCService

    sources = [SimpleNamespace(id=f"s{i}", name=f"s{i}", display_name=f"s{i}") for i in range(6)]
    threads = set()

    def slow(api_source, ioc_type, ioc_value):
        threads.add(threading.current_thread().name)
        _time.sleep(0.3)
        return IOCSourceResult(source=api_source.name, status="success", risk_score=None, description="", raw=None)

    service = IOCService(db_session)
    with _patch.object(service, "_get_active_api_keys", return_value=[]), \
         _patch.object(service, "_get_sources_without_auth", return_value=sources), \
         _patch.object(service, "_query_single_source_without_key", side_effect=slow), \
         _patch.object(service, "_save_query_to_db"), \
         _patch("app.services.ioc_service.redis_cache") as rc:
        rc.get.return_value = None
        started = _time.monotonic()
        response = service.query_ioc("u-par", IOCQueryRequest(ioc_type="ip", ioc_value="9.9.9.9"))
        elapsed = _time.monotonic() - started
    assert [r.source for r in response.queried_sources] == [s.name for s in sources]
    assert elapsed < 1.0  # sequential would take ~1.8 s
    assert len(threads) > 1


def test_seed_removes_placeholder_keys_of_deprecated_sources(db_session, monkeypatch):
    from uuid import uuid4 as _uuid

    from app.db import seed_predefined_apis as seed
    from app.models.api_source import APIKey, APISource, APIType, AuthenticationType
    from app.models.user import User, UserRole

    user = User(id=str(_uuid()), username="seeduser", email="seed@example.com", password_hash="x",
                role=UserRole.ANALYST, is_active=True)
    dead = APISource(id="predefined-threatminer", name="threatminer", display_name="ThreatMiner",
                     api_type=APIType.PREDEFINED, base_url="https://api.threatminer.org/v2",
                     supported_ioc_types=["ip"], authentication_type=AuthenticationType.NONE,
                     request_config={}, is_active=True)
    db_session.add_all([user, dead])
    db_session.flush()
    placeholder = APIKey(id="k-placeholder", user_id=user.id, api_source_id=dead.id,
                         api_key="FREE_SOURCE_NO_KEY_REQUIRED")
    real = APIKey(id="k-real", user_id=user.id, api_source_id=dead.id, api_key="encrypted-real-key")
    db_session.add_all([placeholder, real])
    db_session.commit()

    class _NoClose:
        def __getattr__(self, name):
            return getattr(db_session, name)

        def close(self):
            pass

    monkeypatch.setattr(seed, "SessionLocal", lambda: _NoClose())
    seed.seed_predefined_apis()

    remaining = {k.id for k in db_session.query(APIKey).filter(APIKey.api_source_id == dead.id).all()}
    assert remaining == {"k-real"}
    assert db_session.query(APISource).filter_by(name="threatminer").one().is_active is False
