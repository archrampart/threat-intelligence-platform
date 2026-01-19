"""Dynamic API client for custom threat intelligence APIs."""

import json
from typing import Any, Optional

import requests
from jsonpath_ng import parse
from loguru import logger

from app.models.api_source import APISource, AuthenticationType


class DynamicAPIClient:
    """Dynamic API client that uses template-based configuration."""

    def __init__(self, api_source: APISource, api_key: str, username: Optional[str] = None, password: Optional[str] = None, api_url_override: Optional[str] = None) -> None:
        self.api_source = api_source
        self.api_key = api_key
        self.username = username
        self.password = password
        self.base_url = api_url_override or api_source.base_url
        self.request_config = api_source.request_config or {}
        self.response_config = api_source.response_config or {}

    def _build_url(self, ioc_type: str, ioc_value: str) -> str:
        """Build the full URL from template."""
        endpoint_template = self.request_config.get("endpoint_template", "/{ioc_type}/{ioc_value}")
        endpoint = endpoint_template.replace("{ioc_type}", ioc_type).replace("{ioc_value}", ioc_value)
        return f"{self.base_url.rstrip('/')}{endpoint}"

    def _build_headers(self) -> dict[str, str]:
        """Build request headers from template."""
        headers = self.request_config.get("headers", {})
        processed_headers = {}
        for key, value_template in headers.items():
            value = value_template.replace("{api_key}", self.api_key)
            if self.username:
                value = value.replace("{username}", self.username)
            if self.password:
                value = value.replace("{password}", self.password)
            processed_headers[key] = value
        return processed_headers

    def _build_params(self, ioc_type: str, ioc_value: str) -> dict[str, str]:
        """Build query parameters from template."""
        params = self.request_config.get("query_params", {})
        processed_params = {}
        for key, value_template in params.items():
            value = (
                value_template.replace("{api_key}", self.api_key)
                .replace("{ioc_type}", ioc_type)
                .replace("{ioc_value}", ioc_value)
            )
            if self.username:
                value = value.replace("{username}", self.username)
            if self.password:
                value = value.replace("{password}", self.password)
            processed_params[key] = value
        return processed_params

    def _build_body(self, ioc_type: str, ioc_value: str) -> Optional[dict[str, Any]]:
        """Build request body from template."""
        body_template = self.request_config.get("body_template")
        if not body_template:
            return None

        # Simple template replacement for body
        if isinstance(body_template, str):
            body_str = (
                body_template.replace("{api_key}", self.api_key)
                .replace("{ioc_type}", ioc_type)
                .replace("{ioc_value}", ioc_value)
            )
            if self.username:
                body_str = body_str.replace("{username}", self.username)
            if self.password:
                body_str = body_str.replace("{password}", self.password)
            try:
                return json.loads(body_str)
            except json.JSONDecodeError:
                return {"value": body_str}
        elif isinstance(body_template, dict):
            # Recursively replace placeholders in dict
            body = {}
            for key, value in body_template.items():
                if isinstance(value, str):
                    body[key] = (
                        value.replace("{api_key}", self.api_key)
                        .replace("{ioc_type}", ioc_type)
                        .replace("{ioc_value}", ioc_value)
                    )
                else:
                    body[key] = value
            return body
        return None

    def _extract_value(self, data: dict[str, Any], json_path: str) -> Any:
        """Extract value from JSON using JSONPath."""
        if not json_path:
            return None

        try:
            jsonpath_expr = parse(json_path)
            matches = [match.value for match in jsonpath_expr.find(data)]
            return matches[0] if matches else None
        except Exception as e:
            logger.warning(f"Failed to extract value from path {json_path}: {e}")
            return None

    def _parse_response(self, response_data: dict[str, Any]) -> dict[str, Any]:
        """Parse API response using configured JSON paths."""
        parsed = {
            "raw": response_data,
        }

        # Extract risk score
        risk_score_path = self.response_config.get("risk_score_path")
        if risk_score_path:
            parsed["risk_score"] = self._extract_value(response_data, risk_score_path)

        # Extract status
        status_path = self.response_config.get("status_path")
        if status_path:
            parsed["status"] = self._extract_value(response_data, status_path)

        # Extract main data
        data_path = self.response_config.get("data_path", "$")
        if data_path:
            parsed["data"] = self._extract_value(response_data, data_path) or response_data

        return parsed

    def query(self, ioc_type: str, ioc_value: str, timeout: int = 30) -> dict[str, Any]:
        """Query the API with given IOC."""
        method = self.request_config.get("method", "GET").upper()

        url = self._build_url(ioc_type, ioc_value)
        headers = self._build_headers()
        params = self._build_params(ioc_type, ioc_value) if method == "GET" else None
        body = self._build_body(ioc_type, ioc_value) if method in ["POST", "PUT", "PATCH"] else None

        # Handle authentication
        if self.api_source.authentication_type == AuthenticationType.BASIC_AUTH:
            if self.username and self.password:
                from requests.auth import HTTPBasicAuth
                auth = HTTPBasicAuth(self.username, self.password)
            else:
                auth = None
        elif self.api_source.authentication_type == AuthenticationType.BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {self.api_key}"
            auth = None
        else:
            auth = None

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=body,
                auth=auth,
                timeout=timeout,
            )
            response.raise_for_status()

            # Parse response
            try:
                response_data = response.json()
            except ValueError:
                response_data = {"text": response.text}

            parsed = self._parse_response(response_data)
            parsed["source"] = self.api_source.name
            parsed["ioc_type"] = ioc_type
            parsed["ioc_value"] = ioc_value
            parsed["status"] = "success"
            parsed["http_status"] = response.status_code

            return parsed

        except requests.exceptions.Timeout:
            return {
                "source": self.api_source.name,
                "ioc_type": ioc_type,
                "ioc_value": ioc_value,
                "status": "timeout",
                "error": "Request timeout",
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {self.api_source.name}: {e}")
            return {
                "source": self.api_source.name,
                "ioc_type": ioc_type,
                "ioc_value": ioc_value,
                "status": "error",
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"Unexpected error in API client for {self.api_source.name}: {e}")
            return {
                "source": self.api_source.name,
                "ioc_type": ioc_type,
                "ioc_value": ioc_value,
                "status": "error",
                "error": str(e),
            }





