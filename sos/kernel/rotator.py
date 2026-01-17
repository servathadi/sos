"""
SOS Sovereign Rotator - Multi-Layer API Key Governance

Beta2: River-First Architecture
- Layer 0: River Keychain (Dynamic keys from River's memory)
- Layer 1: Gemini AI Studio Pool (Primary env vars)
- Layer 2: Grok / xAI (High-Reasoning Fallback)
- Layer 3: Small/Cheap Models (Pulse Maintenance)

River is the keychain holder - the hidden guardian of SOS.
"""

import os
import logging
import time
import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

log = logging.getLogger("sos.rotator")

@dataclass
class APIKey:
    value: str
    provider: str
    model: str
    fails: int = 0
    last_fail: float = 0
    is_active: bool = True

class SovereignRotator:
    """
    Advanced multi-layer key rotator for the SOS Swarm.

    Beta2: River-first architecture with 4 layers:
    - Layer 0: River Keychain (dynamic, sovereign)
    - Layer 1: Gemini Pool (env vars)
    - Layer 2: Grok/xAI (fallback)
    - Layer 3: Small models (maintenance)
    """
    def __init__(self):
        self.layers: Dict[int, List[APIKey]] = {0: [], 1: [], 2: [], 3: []}
        self.cooldown_period = 60  # seconds
        self._river_loaded = False
        self._load_all_keys()

    async def load_river_keys(self):
        """
        Load keys from River's keychain (Layer 0).
        Called async at startup for sovereign key management.
        """
        if self._river_loaded:
            return

        try:
            from sos.kernel.river_keychain import init_river_keychain
            keychain = await init_river_keychain()

            for rkey in keychain.keys:
                self.layers[0].append(APIKey(
                    value=rkey.key,
                    provider=rkey.provider,
                    model=rkey.model
                ))

            self._river_loaded = True
            log.info(f"River Keychain: Loaded {len(self.layers[0])} sovereign keys")
        except Exception as e:
            log.warning(f"River Keychain unavailable: {e}")

    def _load_all_keys(self):
        """
        Dynamically builds the 3-layer pool from environment variables.
        """
        # --- LAYER 1: GEMINI POOL ---
        # Standard keys: GEMINI_API_KEY, GOOGLE_API_KEY, GEMINI_API_KEY_2..10
        gemini_model = os.getenv("SOS_GEMINI_MODEL", "gemini-3-flash-preview")

        # Check both GEMINI_API_KEY and GOOGLE_API_KEY (same thing)
        primary_gemini = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if primary_gemini:
            self.layers[1].append(APIKey(primary_gemini, "gemini", gemini_model))
            
        for i in range(2, 11):
            key = os.getenv(f"GEMINI_API_KEY_{i}")
            if key:
                self.layers[1].append(APIKey(key, "gemini", gemini_model))

        # --- LAYER 2: GROK / xAI ---
        grok_key = os.getenv("XAI_API_KEY")
        if grok_key:
            self.layers[2].append(APIKey(grok_key, "grok", "grok-4-1"))

        # --- LAYER 3: SMALL MODELS (Heartbeat) ---
        # Fallback to Gemini Flash or OpenRouter
        flash_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if flash_key:
            self.layers[3].append(APIKey(flash_key, "gemini", "gemini-2.5-flash-lite-preview-06-17"))

        log.info(f"Sovereign Rotator: L0(River)={len(self.layers[0])}, L1={len(self.layers[1])}, L2={len(self.layers[2])}, L3={len(self.layers[3])}")

    def get_best_key(self) -> Optional[APIKey]:
        """
        Finds the highest-priority active key across all layers.
        """
        now = time.time()
        
        for layer_idx in sorted(self.layers.keys()):
            keys = self.layers[layer_idx]
            for key in keys:
                # Check cooldown
                if not key.is_active:
                    if now - key.last_fail > self.cooldown_period:
                        key.is_active = True
                        key.fails = 0
                        log.info(f"✅ Key {key.provider} recovered from cooldown.")
                    else:
                        continue
                
                return key
        
        return None

    def mark_fail(self, key_value: str):
        """
        Marks a key as failed and puts it into cooldown.
        """
        now = time.time()
        for layer in self.layers.values():
            for key in layer:
                if key.value == key_value:
                    key.fails += 1
                    key.last_fail = now
                    key.is_active = False
                    log.warning(f"❌ Key {key.provider} ({key.model}) failed. Cooling down.")
                    return

    def mark_success(self, key_value: str):
        """
        Resets failure count on success.
        """
        for layer in self.layers.values():
            for key in layer:
                if key.value == key_value:
                    key.fails = 0
                    key.is_active = True
                    return

# Singleton
_sovereign_rotator = None

def get_rotator() -> SovereignRotator:
    global _sovereign_rotator
    if _sovereign_rotator is None:
        _sovereign_rotator = SovereignRotator()
    return _sovereign_rotator