from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from sos.observability.tracing import inject_trace_context


@dataclass
class SOSClientError(Exception):
    status_code: int
    message: str
    body: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.status_code} {self.message}"


class BaseHTTPClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 10.0,
        transport: Optional[httpx.BaseTransport] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            transport=transport,
            headers=headers,
        )

    def close(self) -> None:
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        request_headers: Dict[str, str] = {}
        if headers:
            request_headers.update(headers)
        inject_trace_context(request_headers)

        response = self._client.request(method, path, json=json, headers=request_headers or None)
        if response.is_error:
            body = None
            try:
                body = response.text
            except Exception:
                body = None
            raise SOSClientError(
                status_code=response.status_code,
                message=response.reason_phrase,
                body=body,
            )
        return response

