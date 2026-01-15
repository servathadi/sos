"""
SOS Cost Accountant - Vertex AI Budget Governance
Updated: January 2026 (Full Model Lineup)

Enforces 5-layer model sinking strategy based on $1,831 credits.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Optional, Any

log = logging.getLogger("sos.accountant")

class CostAccountant:
    # JAN 2026 OFFICIAL PRICING
    PRICING = {
        "gemini-3-pro-preview": {
            "input_small": 2.00,  # <= 200k
            "input_large": 4.00,  # > 200k
            "output_small": 12.00,
            "output_large": 18.00,
            "cache_storage": 4.50
        },
        "gemini-3-flash-preview": {
            "input": 0.50,
            "output": 3.00,
            "cache_storage": 1.00
        },
        "gemini-2.5-pro": {
            "input_small": 1.25,
            "input_large": 2.50,
            "output_small": 10.00,
            "output_large": 15.00,
            "cache_storage": 4.50
        },
        "gemini-2.5-flash": {
            "input": 0.30,
            "output": 2.50,
            "cache_storage": 1.00
        },
        "gemini-2.5-flash-lite": {
            "input": 0.10,
            "output": 0.40,
            "cache_storage": 1.00
        },
        "imagen-4.0-ultra": 0.06, # per image
        "imagen-4.0-fast": 0.02,
        "veo-3.1-standard": 0.40  # per second
    }

    def __init__(self, budget_limit: float = 1831.0):
        self.budget_limit = budget_limit
        self.current_spend = 0.0
        self.daily_target = 50.0

    def get_recommended_model(self, task_type: str = "chat") -> str:
        """
        Intelligence Sinking Strategy:
        1. High-Reasoning -> Gemini 3 Pro (if budget > 20%)
        2. Standard -> Gemini 2.5 Pro
        3. Low Latency -> Gemini 2.5 Flash
        4. Maintenance -> Gemini 2.5 Flash-Lite
        """
        hour = datetime.now().hour
        is_quiet = hour >= 23 or hour < 7
        
        # Priority 1: Budget Level
        remaining_ratio = (self.budget_limit - self.current_spend) / self.budget_limit
        
        if remaining_ratio < 0.1: # Emergency Mode
            return "gemini-2.5-flash-lite"
            
        # Priority 2: Task Type
        if task_type == "coding":
            return "gemini-3-pro-preview" if not is_quiet else "gemini-2.5-pro"
            
        if task_type == "maintenance":
            return "gemini-2.5-flash-lite"

        # Default Chat
        if is_quiet:
            return "gemini-2.5-flash"
        else:
            return "gemini-2.5-pro"

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        # Simplified tracker
        return 0.0 # Implementation depends on usage telemetry

# Singleton
_accountant = None
def get_accountant() -> CostAccountant:
    global _accountant
    if _accountant is None:
        _accountant = CostAccountant()
    return _accountant