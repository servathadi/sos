from __future__ import annotations

from typing import Any, Dict

from sos.clients.base import BaseHTTPClient


class MemoryClient(BaseHTTPClient):
    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health").json()

