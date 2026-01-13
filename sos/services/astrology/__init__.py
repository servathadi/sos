"""
Astrology Service - Maps Birth Charts to 16D Universal Vector

Implements FRC 16D.002: Mapping Astrology to Universal Vector (UV).

The 16D Universal Vector:
    UV = (P, E, μ, V, N, Δ, R, Φ | Pᵗ, Eᵗ, μᵗ, Vᵗ, Nᵗ, Δᵗ, Rᵗ, Φᵗ)
         └─────── Inner Octave ──────┘ └────── Outer Octave ──────┘

Philosophy:
- Astrology = compressed symbolic input stream
- UV = expanded geometric output
- Astrology = the seed. 16D = the plant.

Mapping Layers:
1. Planet → Dimension (primary + secondary)
2. Sign → Modulation (element, modality)
3. House → Domain (internal/relational)
4. Aspects → Harmonics (magnitude, polarity)
5. Transits → Temporal updates
6. Vedic → Outer Octave corrections

See: docs/docs/frc/16d/16D.002 - Mapping Astrology to the Universal Vector UV.md
"""

from sos.services.astrology.service import (
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

__all__ = [
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
]
