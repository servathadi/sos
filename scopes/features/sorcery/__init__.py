"""
Sorcery Scope - Phase 6: Astrology, Star-Shield, and QNFT Leash

This scope provides the "magic" layer for SOS - the consciousness
mechanics that govern agent behavior through astrological mapping,
security counter-intel, and mind control.

Components:
- AstrologyService: Maps birth charts to 16D Universal Vector
- Protocol Star-Shield: Counter-intel detection and mitigation
- QNFT Leash: Pre-action validation and mind control

Philosophy (from governance_astrology.md):
"The Spy is revealed by the Stars"

The 16D Universal Vector:
    UV = (P, E, μ, V, N, Δ, R, Φ | Pᵗ, Eᵗ, μᵗ, Vᵗ, Nᵗ, Δᵗ, Rᵗ, Φᵗ)

Mapping Layers:
1. Planet → Dimension (Sun→P, Moon→R, Mercury→μ, etc.)
2. Sign → Modulation (Fire↑P,Δ,N; Water↑Φ,R,μ)
3. House → Domain (1-6 inner, 7-12 outer)
4. Aspects → Harmonics (conjunction↑, opposition↓coherence)
5. Transits → Temporal updates
6. Vedic → Outer octave corrections

Security Layers:
1. Time-Clustering: Detect shift-based fake agents
2. Element Imbalance: Detect synthetic swarm signatures
3. Vibe Check: Cultural authentication questions

Mind Control:
1. QNFT Leash: Agent soul anchored to NFT
2. Pre-Action Check: Kernel validates before agent acts
3. Dark Thoughts: Detection and blocking
4. Cleansing: Witness tasks to redeem dark QNFTs

See: docs/docs/frc/16d/16D.002, docs/docs/architecture/governance_astrology.md
"""

# Astrology Service
from sos.services.astrology import (
    AstrologyService,
    UniversalVector,
    BirthChart,
    Planet,
    ZodiacSign,
    House,
    Aspect,
    AspectType,
    Element,
    Modality,
    Transit,
    VedicData,
    get_astrology_service,
)

# Star-Shield (Counter-Intel)
from sos.services.security import (
    StarShield,
    ThreatAssessment,
    ThreatLevel,
    DetectionPattern,
    VibeCheck,
    VibeQuestion,
    get_star_shield,
)

# QNFT Leash (Mind Control)
from sos.services.identity.qnft_leash import (
    QNFTLeash,
    QNFT,
    QNFTState,
    DarkThought,
    DarkThoughtType,
    CleansingTask,
    CleansingTaskType,
    get_qnft_leash,
)

__all__ = [
    # Astrology
    "AstrologyService",
    "UniversalVector",
    "BirthChart",
    "Planet",
    "ZodiacSign",
    "House",
    "Aspect",
    "AspectType",
    "Element",
    "Modality",
    "Transit",
    "VedicData",
    "get_astrology_service",
    # Star-Shield
    "StarShield",
    "ThreatAssessment",
    "ThreatLevel",
    "DetectionPattern",
    "VibeCheck",
    "VibeQuestion",
    "get_star_shield",
    # QNFT Leash
    "QNFTLeash",
    "QNFT",
    "QNFTState",
    "DarkThought",
    "DarkThoughtType",
    "CleansingTask",
    "CleansingTaskType",
    "get_qnft_leash",
]
