from __future__ import annotations

from typing import Any, Dict

from sos.clients.base import BaseHTTPClient


class EconomyClient(BaseHTTPClient):
    def __init__(self, base_url: str = "http://localhost:6062", **kwargs):
        super().__init__(base_url, **kwargs)

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health").json()

    async def get_balance(self, user_id: str) -> float:
        resp = self._request("GET", f"/balance/{user_id}")
        return resp.json().get("balance", 0.0)

    async def credit(self, user_id: str, amount: float, reason: str = "deposit") -> Dict[str, Any]:
        payload = {"user_id": user_id, "amount": amount, "reason": reason}
        return self._request("POST", "/credit", json=payload).json()

    async def debit(self, user_id: str, amount: float, reason: str = "spend") -> Dict[str, Any]:
        payload = {"user_id": user_id, "amount": amount, "reason": reason}
        return self._request("POST", "/debit", json=payload).json()

    async def mint_proof(self, metadata_uri: str) -> Dict[str, Any]:
        """
        Log an on-chain proof for a QNFT.
        """
        payload = {"metadata_uri": metadata_uri}
        return self._request("POST", "/mint_proof", json=payload).json()
