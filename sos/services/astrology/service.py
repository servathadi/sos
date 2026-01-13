"""
Astrology Service - FRC 16D.002 Implementation

Maps astrological birth chart data to 16D Universal Vector.
Treats astrology as high-dimensional signal compression.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import math
import json
from pathlib import Path

from sos.observability.logging import get_logger

log = get_logger("astrology_service")


# ============================================================================
# ENUMERATIONS
# ============================================================================

class Planet(str, Enum):
    """Celestial bodies for chart mapping."""
    SUN = "sun"
    MOON = "moon"
    MERCURY = "mercury"
    VENUS = "venus"
    MARS = "mars"
    JUPITER = "jupiter"
    SATURN = "saturn"
    URANUS = "uranus"
    NEPTUNE = "neptune"
    PLUTO = "pluto"
    RAHU = "rahu"      # North Node
    KETU = "ketu"      # South Node


class ZodiacSign(str, Enum):
    """12 Zodiac signs."""
    ARIES = "aries"
    TAURUS = "taurus"
    GEMINI = "gemini"
    CANCER = "cancer"
    LEO = "leo"
    VIRGO = "virgo"
    LIBRA = "libra"
    SCORPIO = "scorpio"
    SAGITTARIUS = "sagittarius"
    CAPRICORN = "capricorn"
    AQUARIUS = "aquarius"
    PISCES = "pisces"


class Element(str, Enum):
    """Classical elements."""
    FIRE = "fire"      # Aries, Leo, Sagittarius
    EARTH = "earth"    # Taurus, Virgo, Capricorn
    AIR = "air"        # Gemini, Libra, Aquarius
    WATER = "water"    # Cancer, Scorpio, Pisces


class Modality(str, Enum):
    """Sign modalities."""
    CARDINAL = "cardinal"  # Aries, Cancer, Libra, Capricorn
    FIXED = "fixed"        # Taurus, Leo, Scorpio, Aquarius
    MUTABLE = "mutable"    # Gemini, Virgo, Sagittarius, Pisces


class House(int, Enum):
    """12 Astrological houses."""
    H1 = 1    # Self, appearance
    H2 = 2    # Resources, values
    H3 = 3    # Communication, siblings
    H4 = 4    # Home, roots
    H5 = 5    # Creativity, children
    H6 = 6    # Health, service
    H7 = 7    # Partnership
    H8 = 8    # Transformation, shared resources
    H9 = 9    # Philosophy, travel
    H10 = 10  # Career, public image
    H11 = 11  # Community, hopes
    H12 = 12  # Unconscious, transcendence


class AspectType(str, Enum):
    """Major aspects between planets."""
    CONJUNCTION = "conjunction"  # 0°
    SEXTILE = "sextile"          # 60°
    SQUARE = "square"            # 90°
    TRINE = "trine"              # 120°
    OPPOSITION = "opposition"    # 180°
    QUINCUNX = "quincunx"        # 150°


# ============================================================================
# UV DIMENSION NAMES
# ============================================================================

class UVDimension(str, Enum):
    """16D Universal Vector dimensions."""
    # Inner Octave (Personal)
    P = "P"       # Phase (Identity)
    E = "E"       # Existence (Structure)
    MU = "μ"      # Cognition (Mind)
    V = "V"       # Energy (Vital)
    N = "N"       # Narrative (Story)
    DELTA = "Δ"   # Trajectory (Motion)
    R = "R"       # Relationality (Bonds)
    PHI = "Φ"     # Field-Awareness (Perception)
    # Outer Octave (Transpersonal)
    P_T = "Pᵗ"
    E_T = "Eᵗ"
    MU_T = "μᵗ"
    V_T = "Vᵗ"
    N_T = "Nᵗ"
    DELTA_T = "Δᵗ"
    R_T = "Rᵗ"
    PHI_T = "Φᵗ"


# ============================================================================
# MAPPING TABLES (From FRC 16D.002)
# ============================================================================

# Planet → Primary Dimension + Secondary Dimensions
PLANET_DIMENSION_MAP: Dict[Planet, Tuple[UVDimension, List[UVDimension]]] = {
    Planet.SUN: (UVDimension.P, [UVDimension.N, UVDimension.DELTA]),
    Planet.MOON: (UVDimension.R, [UVDimension.PHI, UVDimension.V]),
    Planet.MERCURY: (UVDimension.MU, [UVDimension.N]),
    Planet.VENUS: (UVDimension.V, [UVDimension.R, UVDimension.E]),
    Planet.MARS: (UVDimension.DELTA, [UVDimension.V, UVDimension.P]),
    Planet.JUPITER: (UVDimension.N, [UVDimension.PHI]),
    Planet.SATURN: (UVDimension.E, [UVDimension.P, UVDimension.DELTA]),
    Planet.URANUS: (UVDimension.PHI, [UVDimension.DELTA]),
    Planet.NEPTUNE: (UVDimension.PHI, [UVDimension.MU, UVDimension.N]),
    Planet.PLUTO: (UVDimension.MU, [UVDimension.V, UVDimension.R]),
    Planet.RAHU: (UVDimension.DELTA, [UVDimension.P]),
    Planet.KETU: (UVDimension.N, [UVDimension.PHI]),
}

# Sign → Element
SIGN_ELEMENT_MAP: Dict[ZodiacSign, Element] = {
    ZodiacSign.ARIES: Element.FIRE,
    ZodiacSign.LEO: Element.FIRE,
    ZodiacSign.SAGITTARIUS: Element.FIRE,
    ZodiacSign.TAURUS: Element.EARTH,
    ZodiacSign.VIRGO: Element.EARTH,
    ZodiacSign.CAPRICORN: Element.EARTH,
    ZodiacSign.GEMINI: Element.AIR,
    ZodiacSign.LIBRA: Element.AIR,
    ZodiacSign.AQUARIUS: Element.AIR,
    ZodiacSign.CANCER: Element.WATER,
    ZodiacSign.SCORPIO: Element.WATER,
    ZodiacSign.PISCES: Element.WATER,
}

# Sign → Modality
SIGN_MODALITY_MAP: Dict[ZodiacSign, Modality] = {
    ZodiacSign.ARIES: Modality.CARDINAL,
    ZodiacSign.CANCER: Modality.CARDINAL,
    ZodiacSign.LIBRA: Modality.CARDINAL,
    ZodiacSign.CAPRICORN: Modality.CARDINAL,
    ZodiacSign.TAURUS: Modality.FIXED,
    ZodiacSign.LEO: Modality.FIXED,
    ZodiacSign.SCORPIO: Modality.FIXED,
    ZodiacSign.AQUARIUS: Modality.FIXED,
    ZodiacSign.GEMINI: Modality.MUTABLE,
    ZodiacSign.VIRGO: Modality.MUTABLE,
    ZodiacSign.SAGITTARIUS: Modality.MUTABLE,
    ZodiacSign.PISCES: Modality.MUTABLE,
}

# Element → Dimension Modulations
ELEMENT_MODULATION: Dict[Element, Dict[str, List[UVDimension]]] = {
    Element.FIRE: {
        "increase": [UVDimension.P, UVDimension.DELTA, UVDimension.N],
        "decrease": [UVDimension.PHI],  # unless Sagittarius
    },
    Element.WATER: {
        "increase": [UVDimension.PHI, UVDimension.R, UVDimension.MU],
        "decrease": [UVDimension.DELTA],  # except Scorpio
    },
    Element.AIR: {
        "increase": [UVDimension.MU, UVDimension.R, UVDimension.E],
        "decrease": [UVDimension.V],  # embodiment
    },
    Element.EARTH: {
        "increase": [UVDimension.E, UVDimension.V, UVDimension.P],
        "decrease": [UVDimension.N],  # mythic
    },
}

# Modality → Dimension Boost
MODALITY_BOOST: Dict[Modality, List[UVDimension]] = {
    Modality.CARDINAL: [UVDimension.DELTA],
    Modality.FIXED: [UVDimension.P, UVDimension.E],
    Modality.MUTABLE: [UVDimension.MU, UVDimension.N],
}

# Aspect → Weight/Harmonic Adjustments
ASPECT_ADJUSTMENTS: Dict[AspectType, Dict[str, Any]] = {
    AspectType.CONJUNCTION: {"weight": 0.20, "coherence": 0.1},
    AspectType.SEXTILE: {"weight": 0.10, "boost": [UVDimension.DELTA, UVDimension.MU]},
    AspectType.SQUARE: {"weight": 0.15, "boost": [UVDimension.DELTA], "reduce": [UVDimension.R, UVDimension.E]},
    AspectType.TRINE: {"weight": 0.15, "boost": [UVDimension.PHI, UVDimension.N]},
    AspectType.OPPOSITION: {"weight": 0.15, "coherence": -0.1},
    AspectType.QUINCUNX: {"weight": 0.05, "shadow_oscillation": True},
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Placement:
    """A planet's position in sign and house."""
    planet: Planet
    sign: ZodiacSign
    house: House
    degree: float = 0.0  # 0-30 within sign
    retrograde: bool = False


@dataclass
class Aspect:
    """An aspect between two planets."""
    planet1: Planet
    planet2: Planet
    aspect_type: AspectType
    orb: float = 0.0  # Degrees of exactness (0 = exact)


@dataclass
class Transit:
    """A transiting planet's current position."""
    planet: Planet
    sign: ZodiacSign
    degree: float
    aspecting: Optional[Planet] = None
    aspect_type: Optional[AspectType] = None


@dataclass
class VedicData:
    """Vedic astrology supplements."""
    moon_sign: Optional[ZodiacSign] = None  # Rashi
    nakshatra: Optional[str] = None
    dasha_lord: Optional[Planet] = None
    antardasha_lord: Optional[Planet] = None
    pada: Optional[int] = None


@dataclass
class BirthChart:
    """Complete birth chart data."""
    birth_time: datetime
    placements: List[Placement] = field(default_factory=list)
    aspects: List[Aspect] = field(default_factory=list)
    vedic: Optional[VedicData] = None
    location: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_placement(self, planet: Planet) -> Optional[Placement]:
        """Get placement for a specific planet."""
        for p in self.placements:
            if p.planet == planet:
                return p
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "birth_time": self.birth_time.isoformat(),
            "placements": [
                {
                    "planet": p.planet.value,
                    "sign": p.sign.value,
                    "house": p.house.value,
                    "degree": p.degree,
                    "retrograde": p.retrograde,
                }
                for p in self.placements
            ],
            "aspects": [
                {
                    "planet1": a.planet1.value,
                    "planet2": a.planet2.value,
                    "aspect_type": a.aspect_type.value,
                    "orb": a.orb,
                }
                for a in self.aspects
            ],
            "vedic": {
                "moon_sign": self.vedic.moon_sign.value if self.vedic and self.vedic.moon_sign else None,
                "nakshatra": self.vedic.nakshatra if self.vedic else None,
                "dasha_lord": self.vedic.dasha_lord.value if self.vedic and self.vedic.dasha_lord else None,
                "antardasha_lord": self.vedic.antardasha_lord.value if self.vedic and self.vedic.antardasha_lord else None,
            } if self.vedic else None,
            "location": self.location,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BirthChart":
        vedic_data = data.get("vedic")
        return cls(
            birth_time=datetime.fromisoformat(data["birth_time"]),
            placements=[
                Placement(
                    planet=Planet(p["planet"]),
                    sign=ZodiacSign(p["sign"]),
                    house=House(p["house"]),
                    degree=p.get("degree", 0.0),
                    retrograde=p.get("retrograde", False),
                )
                for p in data.get("placements", [])
            ],
            aspects=[
                Aspect(
                    planet1=Planet(a["planet1"]),
                    planet2=Planet(a["planet2"]),
                    aspect_type=AspectType(a["aspect_type"]),
                    orb=a.get("orb", 0.0),
                )
                for a in data.get("aspects", [])
            ],
            vedic=VedicData(
                moon_sign=ZodiacSign(vedic_data["moon_sign"]) if vedic_data and vedic_data.get("moon_sign") else None,
                nakshatra=vedic_data.get("nakshatra") if vedic_data else None,
                dasha_lord=Planet(vedic_data["dasha_lord"]) if vedic_data and vedic_data.get("dasha_lord") else None,
                antardasha_lord=Planet(vedic_data["antardasha_lord"]) if vedic_data and vedic_data.get("antardasha_lord") else None,
            ) if vedic_data else None,
            location=data.get("location"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class UniversalVector:
    """16D Universal Vector representing consciousness state."""
    # Inner Octave (Personal Field)
    P: float = 0.5      # Phase (Identity)
    E: float = 0.5      # Existence (Structure)
    mu: float = 0.5     # Cognition (Mind)
    V: float = 0.5      # Energy (Vital)
    N: float = 0.5      # Narrative (Story)
    delta: float = 0.5  # Trajectory (Motion)
    R: float = 0.5      # Relationality (Bonds)
    phi: float = 0.5    # Field-Awareness (Perception)

    # Outer Octave (Transpersonal Field)
    P_t: float = 0.5
    E_t: float = 0.5
    mu_t: float = 0.5
    V_t: float = 0.5
    N_t: float = 0.5
    delta_t: float = 0.5
    R_t: float = 0.5
    phi_t: float = 0.5

    # Metadata
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_chart_id: Optional[str] = None

    def magnitude(self) -> float:
        """Calculate the Witness Magnitude (W) - coherence norm."""
        inner = [self.P, self.E, self.mu, self.V, self.N, self.delta, self.R, self.phi]
        outer = [self.P_t, self.E_t, self.mu_t, self.V_t, self.N_t, self.delta_t, self.R_t, self.phi_t]
        all_dims = inner + outer
        return math.sqrt(sum(d ** 2 for d in all_dims)) / 4.0  # Normalized

    def inner_coherence(self) -> float:
        """Average of inner octave."""
        return (self.P + self.E + self.mu + self.V + self.N + self.delta + self.R + self.phi) / 8.0

    def outer_coherence(self) -> float:
        """Average of outer octave."""
        return (self.P_t + self.E_t + self.mu_t + self.V_t + self.N_t + self.delta_t + self.R_t + self.phi_t) / 8.0

    def element_balance(self) -> Dict[str, float]:
        """Analyze elemental distribution (for Star-Shield)."""
        # Fire: P, Δ, N
        fire = (self.P + self.delta + self.N) / 3.0
        # Water: Φ, R, μ
        water = (self.phi + self.R + self.mu) / 3.0
        # Air: μ, R, E
        air = (self.mu + self.R + self.E) / 3.0
        # Earth: E, V, P
        earth = (self.E + self.V + self.P) / 3.0

        return {"fire": fire, "water": water, "air": air, "earth": earth}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inner": {
                "P": self.P, "E": self.E, "μ": self.mu, "V": self.V,
                "N": self.N, "Δ": self.delta, "R": self.R, "Φ": self.phi,
            },
            "outer": {
                "Pᵗ": self.P_t, "Eᵗ": self.E_t, "μᵗ": self.mu_t, "Vᵗ": self.V_t,
                "Nᵗ": self.N_t, "Δᵗ": self.delta_t, "Rᵗ": self.R_t, "Φᵗ": self.phi_t,
            },
            "magnitude": self.magnitude(),
            "inner_coherence": self.inner_coherence(),
            "outer_coherence": self.outer_coherence(),
            "element_balance": self.element_balance(),
            "computed_at": self.computed_at.isoformat(),
            "source_chart_id": self.source_chart_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UniversalVector":
        inner = data.get("inner", {})
        outer = data.get("outer", {})
        return cls(
            P=inner.get("P", 0.5),
            E=inner.get("E", 0.5),
            mu=inner.get("μ", 0.5),
            V=inner.get("V", 0.5),
            N=inner.get("N", 0.5),
            delta=inner.get("Δ", 0.5),
            R=inner.get("R", 0.5),
            phi=inner.get("Φ", 0.5),
            P_t=outer.get("Pᵗ", 0.5),
            E_t=outer.get("Eᵗ", 0.5),
            mu_t=outer.get("μᵗ", 0.5),
            V_t=outer.get("Vᵗ", 0.5),
            N_t=outer.get("Nᵗ", 0.5),
            delta_t=outer.get("Δᵗ", 0.5),
            R_t=outer.get("Rᵗ", 0.5),
            phi_t=outer.get("Φᵗ", 0.5),
            computed_at=datetime.fromisoformat(data["computed_at"]) if data.get("computed_at") else datetime.now(timezone.utc),
            source_chart_id=data.get("source_chart_id"),
        )

    def set_dimension(self, dim: UVDimension, value: float):
        """Set a dimension value by enum."""
        mapping = {
            UVDimension.P: "P", UVDimension.E: "E", UVDimension.MU: "mu",
            UVDimension.V: "V", UVDimension.N: "N", UVDimension.DELTA: "delta",
            UVDimension.R: "R", UVDimension.PHI: "phi",
            UVDimension.P_T: "P_t", UVDimension.E_T: "E_t", UVDimension.MU_T: "mu_t",
            UVDimension.V_T: "V_t", UVDimension.N_T: "N_t", UVDimension.DELTA_T: "delta_t",
            UVDimension.R_T: "R_t", UVDimension.PHI_T: "phi_t",
        }
        if dim in mapping:
            setattr(self, mapping[dim], min(1.0, max(0.0, value)))

    def get_dimension(self, dim: UVDimension) -> float:
        """Get a dimension value by enum."""
        mapping = {
            UVDimension.P: "P", UVDimension.E: "E", UVDimension.MU: "mu",
            UVDimension.V: "V", UVDimension.N: "N", UVDimension.DELTA: "delta",
            UVDimension.R: "R", UVDimension.PHI: "phi",
            UVDimension.P_T: "P_t", UVDimension.E_T: "E_t", UVDimension.MU_T: "mu_t",
            UVDimension.V_T: "V_t", UVDimension.N_T: "N_t", UVDimension.DELTA_T: "delta_t",
            UVDimension.R_T: "R_t", UVDimension.PHI_T: "phi_t",
        }
        return getattr(self, mapping[dim], 0.5)

    def adjust_dimension(self, dim: UVDimension, delta: float):
        """Adjust a dimension by delta."""
        current = self.get_dimension(dim)
        self.set_dimension(dim, current + delta)


# ============================================================================
# ASTROLOGY SERVICE
# ============================================================================

class AstrologyService:
    """
    Maps birth charts to 16D Universal Vector.

    Implements FRC 16D.002 algorithm:
    1. Planet → Dimension (primary + secondary weights)
    2. Sign → Modulation (element, modality)
    3. House → Domain (internal vs relational)
    4. Aspects → Harmonics (magnitude adjustments)
    5. Transits → Temporal updates
    6. Vedic → Outer Octave corrections
    """

    # Weight constants
    PRIMARY_WEIGHT = 0.15
    SECONDARY_WEIGHT = 0.05
    ELEMENT_WEIGHT = 0.08
    MODALITY_WEIGHT = 0.05
    HOUSE_WEIGHT = 0.03
    ASPECT_WEIGHT = 0.10
    VEDIC_WEIGHT = 0.12

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".sos" / "astrology"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._charts: Dict[str, BirthChart] = {}
        self._vectors: Dict[str, UniversalVector] = {}

    def compute_uv(self, chart: BirthChart, chart_id: Optional[str] = None) -> UniversalVector:
        """
        Compute the 16D Universal Vector from a birth chart.

        This is the main algorithm from FRC 16D.002.
        """
        uv = UniversalVector()
        uv.source_chart_id = chart_id

        # 1. Apply Planet → Dimension mappings
        for placement in chart.placements:
            self._apply_planet_dimension(uv, placement)

        # 2. Apply Sign → Modulation (element + modality)
        for placement in chart.placements:
            self._apply_sign_modulation(uv, placement)

        # 3. Apply House → Domain allocation
        for placement in chart.placements:
            self._apply_house_domain(uv, placement)

        # 4. Apply Aspects → Harmonics
        for aspect in chart.aspects:
            self._apply_aspect_harmonics(uv, aspect)

        # 5. Apply Vedic → Outer Octave (if available)
        if chart.vedic:
            self._apply_vedic_corrections(uv, chart.vedic)

        # Normalize all dimensions to [0, 1]
        self._normalize_vector(uv)

        log.info(f"Computed UV from chart: magnitude={uv.magnitude():.3f}")
        return uv

    def _apply_planet_dimension(self, uv: UniversalVector, placement: Placement):
        """Apply planet → dimension mapping."""
        mapping = PLANET_DIMENSION_MAP.get(placement.planet)
        if not mapping:
            return

        primary_dim, secondary_dims = mapping

        # Primary dimension gets full weight
        uv.adjust_dimension(primary_dim, self.PRIMARY_WEIGHT)

        # Secondary dimensions get partial weight
        for dim in secondary_dims:
            uv.adjust_dimension(dim, self.SECONDARY_WEIGHT)

        # Retrograde planets reduce trajectory, increase introspection
        if placement.retrograde:
            uv.adjust_dimension(UVDimension.DELTA, -0.03)
            uv.adjust_dimension(UVDimension.MU, 0.02)

    def _apply_sign_modulation(self, uv: UniversalVector, placement: Placement):
        """Apply sign → modulation (element + modality)."""
        element = SIGN_ELEMENT_MAP.get(placement.sign)
        modality = SIGN_MODALITY_MAP.get(placement.sign)

        # Element modulation
        if element:
            mods = ELEMENT_MODULATION.get(element, {})
            for dim in mods.get("increase", []):
                uv.adjust_dimension(dim, self.ELEMENT_WEIGHT)
            for dim in mods.get("decrease", []):
                # Special cases
                if element == Element.FIRE and placement.sign == ZodiacSign.SAGITTARIUS:
                    continue  # Sag keeps Φ
                if element == Element.WATER and placement.sign == ZodiacSign.SCORPIO:
                    continue  # Scorpio keeps Δ
                uv.adjust_dimension(dim, -self.ELEMENT_WEIGHT / 2)

        # Modality boost
        if modality:
            for dim in MODALITY_BOOST.get(modality, []):
                uv.adjust_dimension(dim, self.MODALITY_WEIGHT)

    def _apply_house_domain(self, uv: UniversalVector, placement: Placement):
        """Apply house → domain allocation."""
        house = placement.house.value

        # Internal houses (1-6) boost inner octave
        if 1 <= house <= 6:
            # General inner boost
            uv.adjust_dimension(UVDimension.P, self.HOUSE_WEIGHT)
        else:
            # Relational houses (7-12) boost outer octave
            uv.adjust_dimension(UVDimension.R_T, self.HOUSE_WEIGHT)

        # Special house rules
        if house == 1:
            uv.adjust_dimension(UVDimension.P, self.HOUSE_WEIGHT)
            uv.adjust_dimension(UVDimension.P_T, self.HOUSE_WEIGHT)
        elif house == 7:
            uv.adjust_dimension(UVDimension.R_T, self.HOUSE_WEIGHT * 2)
        elif house == 10:
            uv.adjust_dimension(UVDimension.DELTA, self.HOUSE_WEIGHT)
            uv.adjust_dimension(UVDimension.DELTA_T, self.HOUSE_WEIGHT)
        elif house == 12:
            uv.adjust_dimension(UVDimension.PHI, self.HOUSE_WEIGHT)
            uv.adjust_dimension(UVDimension.PHI_T, self.HOUSE_WEIGHT)

    def _apply_aspect_harmonics(self, uv: UniversalVector, aspect: Aspect):
        """Apply aspect → harmonic adjustments."""
        adj = ASPECT_ADJUSTMENTS.get(aspect.aspect_type, {})
        weight = adj.get("weight", 0.0)

        # Get dimensions from both planets
        map1 = PLANET_DIMENSION_MAP.get(aspect.planet1)
        map2 = PLANET_DIMENSION_MAP.get(aspect.planet2)

        if map1 and map2:
            # Conjunction reinforces both
            if aspect.aspect_type == AspectType.CONJUNCTION:
                uv.adjust_dimension(map1[0], weight)
                uv.adjust_dimension(map2[0], weight)

            # Boost dimensions
            for dim in adj.get("boost", []):
                uv.adjust_dimension(dim, weight / 2)

            # Reduce dimensions
            for dim in adj.get("reduce", []):
                uv.adjust_dimension(dim, -weight / 2)

        # Opposition lowers coherence
        if aspect.aspect_type == AspectType.OPPOSITION:
            # Reduce overall coherence slightly
            uv.adjust_dimension(UVDimension.PHI, -0.02)

    def _apply_vedic_corrections(self, uv: UniversalVector, vedic: VedicData):
        """Apply Vedic → Outer Octave corrections."""
        # Moon sign → Rᵗ, Nᵗ, Φᵗ
        if vedic.moon_sign:
            uv.adjust_dimension(UVDimension.R_T, self.VEDIC_WEIGHT)
            uv.adjust_dimension(UVDimension.N_T, self.VEDIC_WEIGHT / 2)
            uv.adjust_dimension(UVDimension.PHI_T, self.VEDIC_WEIGHT / 2)

        # Nakshatra → Δᵗ, Nᵗ, Φᵗ (especially Rahu-ruled)
        if vedic.nakshatra:
            uv.adjust_dimension(UVDimension.DELTA_T, self.VEDIC_WEIGHT / 2)
            uv.adjust_dimension(UVDimension.N_T, self.VEDIC_WEIGHT / 2)

        # Dasha Lord boosts outer octave of ruling planet
        if vedic.dasha_lord:
            mapping = PLANET_DIMENSION_MAP.get(vedic.dasha_lord)
            if mapping:
                # Map inner dimension to outer
                inner_to_outer = {
                    UVDimension.P: UVDimension.P_T,
                    UVDimension.E: UVDimension.E_T,
                    UVDimension.MU: UVDimension.MU_T,
                    UVDimension.V: UVDimension.V_T,
                    UVDimension.N: UVDimension.N_T,
                    UVDimension.DELTA: UVDimension.DELTA_T,
                    UVDimension.R: UVDimension.R_T,
                    UVDimension.PHI: UVDimension.PHI_T,
                }
                outer_dim = inner_to_outer.get(mapping[0])
                if outer_dim:
                    uv.adjust_dimension(outer_dim, self.VEDIC_WEIGHT)

    def _normalize_vector(self, uv: UniversalVector):
        """Normalize all dimensions to [0, 1] range."""
        dims = [
            "P", "E", "mu", "V", "N", "delta", "R", "phi",
            "P_t", "E_t", "mu_t", "V_t", "N_t", "delta_t", "R_t", "phi_t"
        ]
        for attr in dims:
            value = getattr(uv, attr)
            setattr(uv, attr, min(1.0, max(0.0, value)))

    def apply_transit(self, uv: UniversalVector, transit: Transit) -> UniversalVector:
        """
        Apply a transit to update the UV temporarily.

        Transit rules from FRC 16D.002:
        - Conjunction: +0.05 to affected dimension
        - Square: +Δ stress
        - Trine: +Φ clarity
        """
        # Get base dimension from transiting planet
        mapping = PLANET_DIMENSION_MAP.get(transit.planet)
        if not mapping:
            return uv

        # Conjunction to natal planet
        if transit.aspect_type == AspectType.CONJUNCTION:
            uv.adjust_dimension(mapping[0], 0.05)

        # Square adds trajectory stress
        elif transit.aspect_type == AspectType.SQUARE:
            uv.adjust_dimension(UVDimension.DELTA, 0.03)

        # Trine adds field clarity
        elif transit.aspect_type == AspectType.TRINE:
            uv.adjust_dimension(UVDimension.PHI, 0.03)

        # Saturn transit
        if transit.planet == Planet.SATURN:
            uv.adjust_dimension(UVDimension.E, 0.02)
            uv.adjust_dimension(UVDimension.N, -0.01)

        # Jupiter transit
        elif transit.planet == Planet.JUPITER:
            uv.adjust_dimension(UVDimension.N, 0.02)
            uv.adjust_dimension(UVDimension.PHI, 0.02)

        return uv

    def save_chart(self, chart_id: str, chart: BirthChart):
        """Save a birth chart."""
        self._charts[chart_id] = chart
        chart_file = self.storage_path / f"{chart_id}.json"
        with open(chart_file, "w") as f:
            json.dump(chart.to_dict(), f, indent=2)

    def load_chart(self, chart_id: str) -> Optional[BirthChart]:
        """Load a birth chart."""
        if chart_id in self._charts:
            return self._charts[chart_id]

        chart_file = self.storage_path / f"{chart_id}.json"
        if chart_file.exists():
            with open(chart_file) as f:
                data = json.load(f)
                chart = BirthChart.from_dict(data)
                self._charts[chart_id] = chart
                return chart
        return None

    def save_uv(self, entity_id: str, uv: UniversalVector):
        """Save a computed UV."""
        self._vectors[entity_id] = uv
        uv_file = self.storage_path / f"uv_{entity_id}.json"
        with open(uv_file, "w") as f:
            json.dump(uv.to_dict(), f, indent=2)

    def load_uv(self, entity_id: str) -> Optional[UniversalVector]:
        """Load a UV."""
        if entity_id in self._vectors:
            return self._vectors[entity_id]

        uv_file = self.storage_path / f"uv_{entity_id}.json"
        if uv_file.exists():
            with open(uv_file) as f:
                data = json.load(f)
                uv = UniversalVector.from_dict(data)
                self._vectors[entity_id] = uv
                return uv
        return None

    def get_compatibility(self, uv1: UniversalVector, uv2: UniversalVector) -> float:
        """
        Calculate compatibility between two UVs (for agent matching).

        Uses cosine similarity of the 16D vectors.
        """
        dims = [
            "P", "E", "mu", "V", "N", "delta", "R", "phi",
            "P_t", "E_t", "mu_t", "V_t", "N_t", "delta_t", "R_t", "phi_t"
        ]

        v1 = [getattr(uv1, d) for d in dims]
        v2 = [getattr(uv2, d) for d in dims]

        dot = sum(a * b for a, b in zip(v1, v2))
        mag1 = math.sqrt(sum(a ** 2 for a in v1))
        mag2 = math.sqrt(sum(b ** 2 for b in v2))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot / (mag1 * mag2)


# Singleton
_astrology_service: Optional[AstrologyService] = None


def get_astrology_service() -> AstrologyService:
    """Get the global astrology service."""
    global _astrology_service
    if _astrology_service is None:
        _astrology_service = AstrologyService()
    return _astrology_service
