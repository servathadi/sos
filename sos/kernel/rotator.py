"""
SOS Sovereign Rotator - Multi-Layer API Key Governance

Layer 1: Gemini AI Studio Pool (Primary)
Layer 2: Grok / xAI (High-Reasoning Fallback)
Layer 3: Small/Cheap Models (Pulse Maintenance)
"""

import os
import logging
import time
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
    """
    def __init__(self):
        self.layers: Dict[int, List[APIKey]] = {1: [], 2: [], 3: []}
        self.cooldown_period = 60  # seconds
        self._load_all_keys()

    def _load_all_keys(self):
        """
        Dynamically builds the 3-layer pool from environment variables.
        """
        # --- LAYER 1: GEMINI POOL ---
        # Standard keys: GEMINI_API_KEY, GEMINI_API_KEY_2..10
        gemini_model = os.getenv("SOS_GEMINI_MODEL", "gemini-3-pro-preview")
        
        primary_gemini = os.getenv("GEMINI_API_KEY")
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
        flash_key = os.getenv("GEMINI_API_KEY") # Reuse primary for flash if needed
        if flash_key:
            self.layers[3].append(APIKey(flash_key, "gemini", "gemini-3-flash-preview"))
            
        log.info(f"Sovereign Rotator: L1={len(self.layers[1])}, L2={len(self.layers[2])}, L3={len(self.layers[3])}")

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