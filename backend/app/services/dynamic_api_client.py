"""Dynamic API client for template-configured threat intelligence sources.

Two source modes are supported (``request_config["mode"]``):

* ``api`` (default) - one HTTP request per IOC, response parsed with JSONPath.
* ``feed`` - a downloadable blocklist (plain lines, CSV or JSON lines). The feed is
  cached in memory and the IOC is checked for membership (exact match, CIDR match
  for IPs, host match for domains against URL feeds).

Risk normalisation (``response_config``):

* ``risk_score_path``   JSONPath of the raw risk value.
* ``risk_score_map``    mapping for string/bool values, e.g. {"malicious": 0.9}.
                        A mapped value of ``null`` means "no signal" (not counted).
* ``risk_score_max``    divide numeric values (or list/dict lengths) by this number.
* ``risk_score_weight`` multiply the final score (0..1) by this factor.
* ``not_found_ok``      treat HTTP 404 as a successful "not found" answer.

Request templating (``request_config``): ``{ioc_type}``, ``{ioc_value}``, ``{hash_type}``
(md5/sha1/sha256 by length), ``{api_key}``, ``{username}``, ``{password}``;
``ioc_type_map`` renames IOC types for the API and ``ioc_value_transform`` can
encode values per type (``base64url``).
"""

from __future__ import annotations

import base64
import ipaddress
import json
import threading
import time
from typing import Any, Optional
from urllib.parse import quote, urlencode, urljoin, urlsplit

import requests
from jsonpath_ng import parse
from loguru import logger

from app.core.url_guard import UnsafeURLError, validate_outbound_url
from app.models.api_source import APISource, AuthenticationType

_MAX_REDIRECTS = 3
_MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MiB
_USER_AGENT = "ThreatIntelPlatform/2.1"
_FEED_TTL_SECONDS = 3600
_FREE_PLACEHOLDER = "FREE_SOURCE_NO_KEY_REQUIRED"

# url -> (fetched_at, exact_entries, networks)
_feed_cache: dict[str, tuple[float, set[str], list[ipaddress._BaseNetwork]]] = {}
_feed_lock = threading.Lock()


def _hash_type(value: str) -> str:
    return {32: "md5", 40: "sha1", 64: "sha256", 128: "sha512"}.get(len(value.strip()), "sha256")


def _host_of(value: str) -> str:
    candidate = value if "://" in value else f"http://{value}"
    return (urlsplit(candidate).hostname or "").lower()


class DynamicAPIClient:
    """Dynamic API client that uses template-based configuration."""

    def __init__(
        self,
        api_source: APISource,
        api_key: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_url_override: Optional[str] = None,
    ) -> None:
        self.api_source = api_source
        self.api_key = "" if api_key == _FREE_PLACEHOLDER else (api_key or "")
        self.username = username
        self.password = password
        self.base_url = api_url_override or api_source.base_url
        self.request_config = api_source.request_config or {}
        self.response_config = api_source.response_config or {}

    # ------------------------------------------------------------------ templating

    def _api_values(self, ioc_type: str, ioc_value: str) -> tuple[str, str]:
        """Apply per-source IOC type names / value encodings (e.g. VirusTotal URL ids)."""
        type_map = self.request_config.get("ioc_type_map") or {}
        transforms = self.request_config.get("ioc_value_transform") or {}
        if transforms.get(ioc_type) == "base64url":
            ioc_value = base64.urlsafe_b64encode(ioc_value.encode()).decode().rstrip("=")
        return type_map.get(ioc_type, ioc_type), ioc_value

    def _substitute(self, template: str, ioc_type: str, ioc_value: str, encode=lambda v: v) -> str:
        hash_type = _hash_type(ioc_value)
        ioc_type, ioc_value = self._api_values(ioc_type, ioc_value)
        out = (
            template.replace("{ioc_type}", encode(ioc_type))
            .replace("{ioc_value}", encode(ioc_value))
            .replace("{hash_type}", hash_type)
            .replace("{api_key}", self.api_key)
        )
        if self.username:
            out = out.replace("{username}", self.username)
        if self.password:
            out = out.replace("{password}", self.password)
        return out

    def _build_url(self, ioc_type: str, ioc_value: str) -> str:
        """Build the full URL from template.

        User supplied values are path-encoded so an IOC cannot traverse to other
        endpoints (e.g. "../../admin") while carrying the user's API key.
        """
        endpoint_template = self.request_config.get("endpoint_template", "/{ioc_type}/{ioc_value}")
        endpoint = self._substitute(endpoint_template, ioc_type, ioc_value, encode=lambda v: quote(v, safe=""))
        return f"{self.base_url.rstrip('/')}{endpoint}"

    def _build_headers(self) -> dict[str, str]:
        processed = {}
        for key, value_template in (self.request_config.get("headers") or {}).items():
            processed[key] = self._substitute(str(value_template), "", "")
        return processed

    def _build_params(self, ioc_type: str, ioc_value: str) -> dict[str, str]:
        return {
            key: self._substitute(str(tpl), ioc_type, ioc_value)
            for key, tpl in (self.request_config.get("query_params") or {}).items()
        }

    def _build_body(self, ioc_type: str, ioc_value: str, headers: dict[str, str]) -> dict[str, Any]:
        """Return requests kwargs (``json=`` or ``data=``) for the request body."""
        body_template = self.request_config.get("body_template", self.request_config.get("body"))
        if body_template is None:
            return {}
        content_type = next((v for k, v in headers.items() if k.lower() == "content-type"), "")

        if isinstance(body_template, (dict, list)):
            rendered = json.loads(
                self._substitute(
                    json.dumps(body_template),
                    ioc_type,
                    ioc_value,
                    encode=lambda v: json.dumps(v)[1:-1],
                )
            )
            if "x-www-form-urlencoded" in content_type and isinstance(rendered, dict):
                return {"data": rendered}
            return {"json": rendered}

        body_str = str(body_template)
        if "x-www-form-urlencoded" in content_type:
            # "query=get_info&hash={ioc_value}" -> url-encode each substituted value
            pairs = []
            for part in body_str.split("&"):
                key, _, value = part.partition("=")
                pairs.append((key, self._substitute(value, ioc_type, ioc_value)))
            return {"data": urlencode(pairs)}
        rendered = self._substitute(body_str, ioc_type, ioc_value, encode=lambda v: json.dumps(v)[1:-1])
        try:
            return {"json": json.loads(rendered)}
        except json.JSONDecodeError:
            return {"data": rendered}

    # ------------------------------------------------------------------ parsing

    def _extract_value(self, data: Any, json_path: str) -> Any:
        if not json_path:
            return None
        try:
            matches = [match.value for match in parse(json_path).find(data)]
            return matches[0] if matches else None
        except Exception as e:
            logger.warning(f"Failed to extract value from path {json_path}: {e}")
            return None

    def _normalize_risk(self, value: Any) -> Optional[float]:
        """Convert a source specific value into a 0..1 risk score (None = no signal)."""
        if value is None:
            return None
        cfg = self.response_config
        mapping = cfg.get("risk_score_map")
        if mapping is not None:
            key = str(value).lower() if not isinstance(value, bool) else str(value).lower()
            lowered = {str(k).lower(): v for k, v in mapping.items()}
            if key in lowered:
                mapped = lowered[key]
                return None if mapped is None else max(0.0, min(1.0, float(mapped)))
            if isinstance(value, str):
                return None
        if isinstance(value, bool):
            score = 1.0 if value else 0.0
        elif isinstance(value, (list, dict)):
            score = float(len(value))
        elif isinstance(value, (int, float)):
            score = float(value)
        else:
            try:
                score = float(str(value))
            except ValueError:
                return None
        max_value = cfg.get("risk_score_max")
        if max_value:
            score = score / float(max_value)
        elif score > 1:
            score = score / 100.0  # legacy: assume percentage
        score = max(0.0, min(1.0, score))
        return round(score * float(cfg.get("risk_score_weight", 1.0)), 4)

    def _parse_response(self, response_data: Any) -> dict[str, Any]:
        parsed: dict[str, Any] = {"raw": response_data}
        risk_score_path = self.response_config.get("risk_score_path")
        if risk_score_path:
            parsed["risk_score"] = self._normalize_risk(self._extract_value(response_data, risk_score_path))
        status_path = self.response_config.get("status_path")
        if status_path:
            parsed["source_status"] = self._extract_value(response_data, status_path)
        data_path = self.response_config.get("data_path", "$")
        if data_path:
            parsed["data"] = self._extract_value(response_data, data_path) or response_data
        return parsed

    # ------------------------------------------------------------------ transport

    def _redact(self, text: str) -> str:
        """Remove secrets from error messages (URLs may carry API keys in query strings)."""
        for secret in (self.api_key, self.password):
            if secret and len(secret) >= 4:
                text = text.replace(secret, "***").replace(quote(secret, safe=""), "***")
        return text

    def _send(self, method: str, url: str, headers, params, auth, timeout, body_kwargs) -> requests.Response:
        """Send the request, validating the destination of every hop (no blind redirects)."""
        for _ in range(_MAX_REDIRECTS + 1):
            validate_outbound_url(url)
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                auth=auth,
                timeout=timeout,
                allow_redirects=False,
                stream=True,
                **body_kwargs,
            )
            if response.is_redirect and response.headers.get("Location"):
                next_url = urljoin(url, response.headers["Location"])
                response.close()
                # Never forward credentials to a different host.
                if urlsplit(next_url).netloc != urlsplit(url).netloc:
                    raise UnsafeURLError("Cross-host redirect refused")
                url, params = next_url, None
                if response.status_code in (301, 302, 303):
                    method, body_kwargs = "GET", {}
                continue
            declared = int(response.headers.get("Content-Length") or 0)
            if declared > _MAX_RESPONSE_BYTES:
                response.close()
                raise requests.exceptions.RequestException("Response too large")
            content = response.raw.read(_MAX_RESPONSE_BYTES + 1, decode_content=True)
            if len(content) > _MAX_RESPONSE_BYTES:
                raise requests.exceptions.RequestException("Response too large")
            response._content = content
            return response
        raise requests.exceptions.TooManyRedirects("Too many redirects")

    def _result(self, ioc_type: str, ioc_value: str, status: str, **extra) -> dict[str, Any]:
        return {
            "source": self.api_source.name,
            "ioc_type": ioc_type,
            "ioc_value": ioc_value,
            "status": status,
            **extra,
        }

    # ------------------------------------------------------------------ feed mode

    def _load_feed(self, url: str, timeout: int) -> tuple[set[str], list]:
        now = time.time()
        with _feed_lock:
            cached = _feed_cache.get(url)
            if cached and now - cached[0] < _FEED_TTL_SECONDS:
                return cached[1], cached[2]

        response = self._send("GET", url, {"User-Agent": _USER_AGENT}, None, None, timeout, {})
        response.raise_for_status()
        fmt = self.request_config.get("feed_format", "lines")
        column = int(self.request_config.get("csv_column", 0))
        field = self.request_config.get("json_field")
        comments = tuple(self.request_config.get("comment_prefixes", ["#", ";", "//"]))

        entries: set[str] = set()
        networks: list = []
        for raw_line in response.text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith(comments):
                continue
            if fmt == "csv":
                cells = [c.strip().strip('"') for c in line.split(",")]
                if column >= len(cells):
                    continue
                value = cells[column]
            elif fmt == "jsonl":
                try:
                    value = str(json.loads(line).get(field, ""))
                except (ValueError, AttributeError):
                    continue
            else:
                value = line.split()[0]
            value = value.strip().lower()
            if not value:
                continue
            if "/" in value and "://" not in value:
                try:
                    networks.append(ipaddress.ip_network(value, strict=False))
                    continue
                except ValueError:
                    pass
            entries.add(value)

        with _feed_lock:
            _feed_cache[url] = (now, entries, networks)
        return entries, networks

    def _query_feed(self, ioc_type: str, ioc_value: str, timeout: int) -> dict[str, Any]:
        url = self._build_url(ioc_type, ioc_value)
        entries, networks = self._load_feed(url, timeout)
        needle = ioc_value.strip().lower()
        matched: Optional[str] = None

        if needle in entries:
            matched = needle
        elif ioc_type == "ip" and networks:
            try:
                ip = ipaddress.ip_address(needle)
                matched = next((str(n) for n in networks if ip in n), None)
            except ValueError:
                pass
        if matched is None and ioc_type == "domain" and self.request_config.get("match_url_host"):
            matched = next((e for e in entries if "://" in e and _host_of(e) == needle), None)

        listed = matched is not None
        label = self.response_config.get("feed_label", self.api_source.name)
        raw = {"listed": listed, "matched": matched, "feed": label, "feed_entries": len(entries) + len(networks)}
        return self._result(
            ioc_type,
            ioc_value,
            "success",
            risk_score=float(self.response_config.get("listed_risk", 0.8)) if listed else None,
            raw=raw,
            data={"description": f"{'Listed' if listed else 'Not listed'} in {label}"},
            http_status=200,
        )

    # ------------------------------------------------------------------ public

    def query(self, ioc_type: str, ioc_value: str, timeout: int = 30) -> dict[str, Any]:
        """Query the source for the given IOC."""
        try:
            if self.request_config.get("mode") == "feed":
                return self._query_feed(ioc_type, ioc_value, timeout)

            method = self.request_config.get("method", "GET").upper()
            url = self._build_url(ioc_type, ioc_value)
            headers = self._build_headers()
            headers.setdefault("User-Agent", _USER_AGENT)
            headers.setdefault("Accept", "application/json")
            params = self._build_params(ioc_type, ioc_value) or None
            body_kwargs = (
                self._build_body(ioc_type, ioc_value, headers) if method in ("POST", "PUT", "PATCH") else {}
            )

            auth = None
            if self.api_source.authentication_type == AuthenticationType.BASIC_AUTH:
                if self.username and self.password:
                    auth = requests.auth.HTTPBasicAuth(self.username, self.password)
            elif self.api_source.authentication_type == AuthenticationType.BEARER_TOKEN and self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = self._send(method, url, headers, params, auth, timeout, body_kwargs)

            if response.status_code == 404 and self.response_config.get("not_found_ok"):
                return self._result(
                    ioc_type,
                    ioc_value,
                    "success",
                    risk_score=None,
                    raw={"not_found": True},
                    data={"description": "Not found in source"},
                    http_status=404,
                )
            response.raise_for_status()

            try:
                response_data = response.json()
            except ValueError:
                response_data = {"text": response.text[:5000]}
            if not isinstance(response_data, dict):
                response_data = {"data": response_data}

            parsed = self._parse_response(response_data)
            parsed.update(source=self.api_source.name, ioc_type=ioc_type, ioc_value=ioc_value)
            parsed["status"] = "success"
            parsed["http_status"] = response.status_code
            return parsed

        except UnsafeURLError as e:
            logger.warning(f"Blocked outbound request for {self.api_source.name}: {e}")
            return self._result(ioc_type, ioc_value, "error", error=f"Blocked unsafe destination: {e}")
        except requests.exceptions.Timeout:
            return self._result(ioc_type, ioc_value, "timeout", error="Request timeout")
        except requests.exceptions.RequestException as e:
            msg = self._redact(str(e))
            logger.error(f"API request failed for {self.api_source.name}: {msg}")
            return self._result(ioc_type, ioc_value, "error", error=msg)
        except Exception as e:
            msg = self._redact(str(e))
            logger.error(f"Unexpected error in API client for {self.api_source.name}: {msg}")
            return self._result(ioc_type, ioc_value, "error", error=msg)
