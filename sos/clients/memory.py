from __future__ import annotations

from typing import Any, Dict

from sos.clients.base import BaseHTTPClient


class MemoryClient(BaseHTTPClient):
    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health").json()

    async def get_arf_state(self) -> Dict[str, Any]:
        # Note: Using sync wrapper for now as base client is sync
        return self._request("GET", "/health").json().get("core", {})

