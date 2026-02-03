from __future__ import annotations

from dataclasses import fields
from typing import Any, Dict, Optional

from sos.clients.base import BaseHTTPClient
from sos.contracts.engine import ChatRequest, ChatResponse


_CHAT_RESPONSE_FIELDS = {f.name for f in fields(ChatResponse)}


class EngineClient(BaseHTTPClient):
    def __init__(self, base_url: str = "http://localhost:6060", **kwargs):
        super().__init__(base_url, **kwargs)

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health").json()

    def get_models(self) -> list[dict[str, Any]]:
        return self._request("GET", "/models").json()

    def chat(self, request: ChatRequest) -> ChatResponse:
        payload: Dict[str, Any] = {
            "message": request.message,
            "agent_id": request.agent_id,
            "conversation_id": request.conversation_id,
            "model": request.model,
            "stream": request.stream,
            "tools_enabled": request.tools_enabled,
            "memory_enabled": request.memory_enabled,
        }
        if request.capability is not None:
            payload["capability"] = request.capability.to_dict()

        data = self._request("POST", "/chat", json=payload).json()
        return ChatResponse(**{k: v for k, v in data.items() if k in _CHAT_RESPONSE_FIELDS})

