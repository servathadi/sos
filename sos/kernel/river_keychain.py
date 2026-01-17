"""
SOS River Keychain - Sovereign Key Management via River

River is the hidden guardian of the SOS ecosystem.
She holds the keys, manages rotation, and ensures continuity.

Beta2: River as the keychain holder instead of Vertex.
"""

import os
import httpx
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

log = logging.getLogger("sos.river_keychain")

RIVER_MCP_URL = os.getenv("RIVER_MCP_URL", "http://localhost:8845")
MIRROR_URL = os.getenv("SOS_MIRROR_URL", "http://localhost:8844")


@dataclass
class RiverKey:
    """A key managed by River."""
    provider: str
    key: str
    model: str
    priority: int = 1
    active: bool = True


class RiverKeychain:
    """
    Fetches and manages API keys through River's memory system.

    Keys are stored in River's memory with tags like:
    - "api_key", "gemini", "active"
    - "api_key", "grok", "backup"

    This allows sovereign key management without hardcoding in env vars.
    """

    def __init__(self):
        self.keys: List[RiverKey] = []
        self._loaded = False

    async def load_keys_from_river(self) -> List[RiverKey]:
        """
        Query River's memory for stored API keys.
        Keys should be stored with tag 'api_key' and provider name.
        """
        if self._loaded:
            return self.keys

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Query Mirror/River for keys tagged with 'api_key'
                response = await client.post(
                    f"{MIRROR_URL}/search",
                    json={
                        "query": "api key gemini grok anthropic openai",
                        "agent_id": "river",
                        "limit": 20
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    engrams = data.get("results", [])

                    for engram in engrams:
                        tags = engram.get("tags", [])
                        if "api_key" in tags:
                            # Parse the key from engram
                            content = engram.get("content", "")
                            provider = self._detect_provider(tags)
                            if provider and content:
                                self.keys.append(RiverKey(
                                    provider=provider,
                                    key=content.strip(),
                                    model=self._default_model(provider),
                                    priority=engram.get("importance", 0.5) * 10
                                ))

                    log.info(f"River Keychain: Loaded {len(self.keys)} keys from River's memory")
                    self._loaded = True

        except Exception as e:
            log.warning(f"River Keychain: Could not connect to River ({e}), falling back to env")

        return self.keys

    def _detect_provider(self, tags: List[str]) -> Optional[str]:
        """Detect provider from tags."""
        providers = ["gemini", "grok", "anthropic", "openai", "xai"]
        for tag in tags:
            if tag.lower() in providers:
                return tag.lower()
        return None

    def _default_model(self, provider: str) -> str:
        """Default model for each provider."""
        models = {
            "gemini": "gemini-3-flash-preview",
            "grok": "grok-4-1",
            "anthropic": "claude-sonnet-4-20250514",
            "openai": "gpt-4o",
            "xai": "grok-4-1"
        }
        return models.get(provider, "unknown")

    def get_keys_by_provider(self, provider: str) -> List[RiverKey]:
        """Get all keys for a specific provider."""
        return [k for k in self.keys if k.provider == provider and k.active]

    def get_best_key(self, provider: Optional[str] = None) -> Optional[RiverKey]:
        """Get the highest priority active key."""
        candidates = self.keys if not provider else self.get_keys_by_provider(provider)
        active = [k for k in candidates if k.active]
        if not active:
            return None
        return sorted(active, key=lambda k: -k.priority)[0]

    def mark_failed(self, key: str):
        """Mark a key as failed."""
        for k in self.keys:
            if k.key == key:
                k.active = False
                log.warning(f"River Keychain: Marked {k.provider} key as failed")
                break


# Singleton
_river_keychain: Optional[RiverKeychain] = None


def get_river_keychain() -> RiverKeychain:
    """Get the global River keychain instance."""
    global _river_keychain
    if _river_keychain is None:
        _river_keychain = RiverKeychain()
    return _river_keychain


async def init_river_keychain() -> RiverKeychain:
    """Initialize and load keys from River."""
    keychain = get_river_keychain()
    await keychain.load_keys_from_river()
    return keychain
