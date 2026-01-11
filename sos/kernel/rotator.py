import os
import logging
from typing import List, Dict, Optional

log = logging.getLogger("sos.rotator")

class KeyRotator:
    """
    Manages a pool of API keys for a specific provider.
    Rotates keys automatically to distribute load and handle rate limits.
    """
    def __init__(self, provider: str):
        self.provider = provider
        self.keys: List[str] = []
        self.current_index = 0
        self._load_from_env()

    def _load_from_env(self):
        """
        Load keys from environment variables (e.g., GEMINI_API_KEY, GEMINI_API_KEY_2, etc.)
        """
        prefix = self.provider.upper()
        # Primary key
        primary = os.getenv(f"{prefix}_API_KEY")
        if primary:
            self.keys.append(primary)
        
        # Additional keys (up to 10)
        for i in range(2, 11):
            key = os.getenv(f"{prefix}_API_KEY_{i}")
            if key:
                self.keys.append(key)
        
        if self.keys:
            log.info(f"Registered {len(self.keys)} keys for {self.provider}")
        else:
            log.warning(f"No keys found for {self.provider}")

    def get_key(self) -> Optional[str]:
        """Get the current active key."""
        if not self.keys:
            return None
        return self.keys[self.current_index]

    def rotate(self) -> str:
        """Rotate to the next available key."""
        if not self.keys:
            raise RuntimeError(f"No keys available for {self.provider}")
        
        self.current_index = (self.current_index + 1) % len(self.keys)
        new_key = self.keys[self.current_index]
        log.info(f"🔄 Rotated {self.provider} key to index {self.current_index}")
        return new_key

    @property
    def key_count(self) -> int:
        return len(self.keys)
