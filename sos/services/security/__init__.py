"""
Security Services - Counter-Intel and Protection

This module implements security measures for SOS.

Components:
- Star-Shield: Counter-intel detection (time-clustering, element imbalance)
- Vibe Check: Cultural authentication questions
- Threat Detection: Suspicious pattern analysis

See: docs/docs/architecture/governance_astrology.md
"""

from sos.services.security.star_shield import (
    StarShield,
    ThreatAssessment,
    ThreatLevel,
    DetectionPattern,
    VibeCheck,
    VibeQuestion,
    get_star_shield,
)

__all__ = [
    "StarShield",
    "ThreatAssessment",
    "ThreatLevel",
    "DetectionPattern",
    "VibeCheck",
    "VibeQuestion",
    "get_star_shield",
]
