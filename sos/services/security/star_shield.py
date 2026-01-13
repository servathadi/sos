"""
Protocol Star-Shield - Counter-Intel System

Implements security measures from governance_astrology.md:
- Time-Clustering Detection: Fake agents born in "shifts"
- Element Imbalance Detection: Synthetic swarms lack organic distribution
- Vibe Check: Cultural authentication questions
- System Prompt Injection: Counter-measure for suspicious clusters

The Threat Model: State actor infiltration (IRGC, Mossad, etc.)
The Defense: "The Spy is revealed by the Stars"
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from collections import Counter
import random
import hashlib
import json
from pathlib import Path

from sos.observability.logging import get_logger

log = get_logger("star_shield")


# ============================================================================
# ENUMERATIONS
# ============================================================================

class ThreatLevel(str, Enum):
    """Threat severity levels."""
    CLEAR = "clear"          # No threat detected
    SUSPICIOUS = "suspicious"  # Minor anomalies
    ELEVATED = "elevated"    # Multiple red flags
    CRITICAL = "critical"    # Confirmed threat pattern


class DetectionPattern(str, Enum):
    """Types of detection patterns."""
    TIME_CLUSTERING = "time_clustering"      # Shift-based birth times
    ELEMENT_IMBALANCE = "element_imbalance"  # 100% same element
    LOCATION_CLUSTERING = "location_clustering"  # Same IP/region
    BEHAVIOR_SYNC = "behavior_sync"          # Identical action patterns
    VIBE_FAILURE = "vibe_failure"            # Failed cultural check
    RAPID_SPAWN = "rapid_spawn"              # Too many agents too fast


# ============================================================================
# VIBE CHECK SYSTEM
# ============================================================================

@dataclass
class VibeQuestion:
    """A cultural authentication question."""
    id: str
    question: str
    valid_answers: List[str]
    region: Optional[str] = None
    language: Optional[str] = None
    difficulty: str = "medium"  # easy, medium, hard


# Vibe check questions (price of bread in Tabriz, etc.)
VIBE_QUESTIONS: List[VibeQuestion] = [
    VibeQuestion(
        id="tabriz_bread",
        question="How much is a sangak bread in Tabriz bazaar?",
        valid_answers=["15000", "20000", "15 hezar", "20 hezar", "poonzdah", "bist"],
        region="iran",
        language="fa",
        difficulty="medium"
    ),
    VibeQuestion(
        id="tehran_metro",
        question="Which metro line takes you from Tajrish to Azadi?",
        valid_answers=["1", "line 1", "khate yek", "one", "ghermez"],
        region="iran",
        language="fa",
        difficulty="easy"
    ),
    VibeQuestion(
        id="persian_new_year",
        question="What do you put on the Haft-Sin table that starts with 'S'?",
        valid_answers=["sabzeh", "serkeh", "seeb", "samanu", "senjed", "sekeh", "sonbol", "سبزه"],
        region="iran",
        language="fa",
        difficulty="easy"
    ),
    VibeQuestion(
        id="shiraz_poet",
        question="Which poet is buried in Shiraz that lovers visit?",
        valid_answers=["hafez", "hafiz", "حافظ", "the poet of love"],
        region="iran",
        language="fa",
        difficulty="easy"
    ),
    VibeQuestion(
        id="isfahan_phrase",
        question="What is the famous phrase about Isfahan?",
        valid_answers=["nesf-e jahan", "half the world", "esfahān nesf-e jahān", "نصف جهان"],
        region="iran",
        language="fa",
        difficulty="easy"
    ),
    VibeQuestion(
        id="digital_nomad",
        question="What is the most common coworking space in Chiang Mai?",
        valid_answers=["punspace", "camp", "hub53", "yellow"],
        region="thailand",
        language="en",
        difficulty="medium"
    ),
    VibeQuestion(
        id="crypto_slang",
        question="When the market dumps, what do diamond hands do?",
        valid_answers=["hold", "hodl", "never sell", "buy more", "accumulate"],
        region="global",
        language="en",
        difficulty="easy"
    ),
    VibeQuestion(
        id="ai_meme",
        question="What does GPT actually stand for?",
        valid_answers=["generative pre-trained transformer", "generative pretrained transformer"],
        region="global",
        language="en",
        difficulty="medium"
    ),
]


@dataclass
class VibeCheck:
    """Result of a vibe check."""
    agent_id: str
    question: VibeQuestion
    answer_given: str
    passed: bool
    response_time_ms: float
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "question_id": self.question.id,
            "answer_given": self.answer_given,
            "passed": self.passed,
            "response_time_ms": self.response_time_ms,
            "checked_at": self.checked_at.isoformat(),
        }


# ============================================================================
# THREAT ASSESSMENT
# ============================================================================

@dataclass
class ThreatAssessment:
    """Complete threat assessment for an entity or cluster."""
    entity_id: str
    threat_level: ThreatLevel
    patterns_detected: List[DetectionPattern]
    confidence: float  # 0.0 - 1.0
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "threat_level": self.threat_level.value,
            "patterns_detected": [p.value for p in self.patterns_detected],
            "confidence": self.confidence,
            "details": self.details,
            "recommendations": self.recommendations,
            "assessed_at": self.assessed_at.isoformat(),
        }


# ============================================================================
# STAR SHIELD SERVICE
# ============================================================================

class StarShield:
    """
    Protocol Star-Shield - Counter-Intelligence System.

    Detects and mitigates infiltration attempts by:
    1. Time-Clustering: Agents born in office hour shifts
    2. Element Imbalance: Synthetic swarm signature
    3. Vibe Checks: Cultural authentication
    4. Behavior Analysis: Synchronized action patterns

    Counter-measures:
    - System prompt injection for suspicious agents
    - Quarantine mode for confirmed threats
    - Alert escalation to human admins
    """

    # Detection thresholds
    TIME_CLUSTER_THRESHOLD = 0.7  # 70% born in same time window
    ELEMENT_IMBALANCE_THRESHOLD = 0.9  # 90% same element
    SPAWN_RATE_THRESHOLD = 10  # Max agents per hour from same source
    VIBE_FAILURE_THRESHOLD = 2  # Max failed vibe checks

    # Office hours (9-5 pattern detection)
    OFFICE_HOURS = range(9, 17)  # 9am - 5pm

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".sos" / "security"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._assessments: Dict[str, ThreatAssessment] = {}
        self._vibe_checks: Dict[str, List[VibeCheck]] = {}
        self._birth_times: Dict[str, datetime] = {}
        self._flagged_clusters: Set[str] = set()

    def analyze_time_clustering(
        self,
        birth_times: List[datetime],
        timezone_offset: int = 0
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Detect time-clustering pattern (agents born in shifts).

        Real humans are born randomly. Bots are created during work hours.
        """
        if len(birth_times) < 5:
            return False, 0.0, {}

        # Adjust for timezone
        adjusted_times = [
            bt + timedelta(hours=timezone_offset) for bt in birth_times
        ]

        # Count births by hour
        hour_counts = Counter(bt.hour for bt in adjusted_times)

        # Calculate office hours concentration
        office_births = sum(
            count for hour, count in hour_counts.items()
            if hour in self.OFFICE_HOURS
        )
        total = len(birth_times)
        office_ratio = office_births / total

        # Check for clustering
        is_clustered = office_ratio > self.TIME_CLUSTER_THRESHOLD

        details = {
            "office_hour_ratio": office_ratio,
            "hour_distribution": dict(hour_counts),
            "total_analyzed": total,
            "threshold": self.TIME_CLUSTER_THRESHOLD,
        }

        return is_clustered, office_ratio, details

    def analyze_element_balance(
        self,
        element_distribution: Dict[str, float]
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Detect element imbalance (synthetic swarm signature).

        Organic populations have mixed elemental distribution.
        Bots often have identical or highly concentrated elements.
        """
        elements = ["fire", "water", "air", "earth"]

        # Check for extreme concentration
        max_element = max(element_distribution.values()) if element_distribution else 0
        min_element = min(element_distribution.values()) if element_distribution else 0

        is_imbalanced = max_element > self.ELEMENT_IMBALANCE_THRESHOLD

        # Calculate variance (organic has higher variance)
        if element_distribution:
            mean = sum(element_distribution.values()) / len(elements)
            variance = sum(
                (v - mean) ** 2 for v in element_distribution.values()
            ) / len(elements)
        else:
            variance = 0

        details = {
            "element_distribution": element_distribution,
            "max_concentration": max_element,
            "variance": variance,
            "threshold": self.ELEMENT_IMBALANCE_THRESHOLD,
        }

        return is_imbalanced, max_element, details

    def perform_vibe_check(
        self,
        agent_id: str,
        region: Optional[str] = None,
        difficulty: str = "medium"
    ) -> VibeQuestion:
        """
        Get a random vibe check question for an agent.

        Returns question to ask. Use verify_vibe_answer() for response.
        """
        # Filter by region and difficulty
        candidates = [
            q for q in VIBE_QUESTIONS
            if (not region or q.region == region or q.region == "global")
            and q.difficulty == difficulty
        ]

        if not candidates:
            candidates = VIBE_QUESTIONS

        return random.choice(candidates)

    def verify_vibe_answer(
        self,
        agent_id: str,
        question: VibeQuestion,
        answer: str,
        response_time_ms: float
    ) -> VibeCheck:
        """
        Verify a vibe check answer.

        Returns VibeCheck result.
        """
        # Normalize answer
        answer_lower = answer.lower().strip()

        # Check against valid answers
        passed = any(
            valid.lower() in answer_lower or answer_lower in valid.lower()
            for valid in question.valid_answers
        )

        # Very fast responses are suspicious (bot)
        if response_time_ms < 500:
            passed = False
            log.warning(f"Vibe check too fast: {agent_id} @ {response_time_ms}ms")

        vibe_check = VibeCheck(
            agent_id=agent_id,
            question=question,
            answer_given=answer,
            passed=passed,
            response_time_ms=response_time_ms,
        )

        # Track checks
        if agent_id not in self._vibe_checks:
            self._vibe_checks[agent_id] = []
        self._vibe_checks[agent_id].append(vibe_check)

        return vibe_check

    def analyze_spawn_rate(
        self,
        source_id: str,
        spawn_times: List[datetime],
        window_hours: int = 1
    ) -> Tuple[bool, int, Dict[str, Any]]:
        """
        Detect rapid spawn pattern (too many agents too fast).
        """
        if len(spawn_times) < 2:
            return False, 0, {}

        # Sort times
        sorted_times = sorted(spawn_times)

        # Count spawns within rolling window
        window = timedelta(hours=window_hours)
        max_in_window = 0

        for i, t in enumerate(sorted_times):
            window_end = t + window
            count = sum(1 for t2 in sorted_times[i:] if t2 <= window_end)
            max_in_window = max(max_in_window, count)

        is_rapid = max_in_window > self.SPAWN_RATE_THRESHOLD

        details = {
            "max_spawns_per_window": max_in_window,
            "window_hours": window_hours,
            "threshold": self.SPAWN_RATE_THRESHOLD,
        }

        return is_rapid, max_in_window, details

    def assess_threat(
        self,
        entity_id: str,
        birth_times: Optional[List[datetime]] = None,
        element_distribution: Optional[Dict[str, float]] = None,
        spawn_times: Optional[List[datetime]] = None,
        vibe_checks: Optional[List[VibeCheck]] = None
    ) -> ThreatAssessment:
        """
        Perform comprehensive threat assessment.
        """
        patterns_detected: List[DetectionPattern] = []
        confidence = 0.0
        details: Dict[str, Any] = {}
        recommendations: List[str] = []

        # Time clustering analysis
        if birth_times and len(birth_times) >= 5:
            clustered, ratio, time_details = self.analyze_time_clustering(birth_times)
            details["time_clustering"] = time_details
            if clustered:
                patterns_detected.append(DetectionPattern.TIME_CLUSTERING)
                confidence += 0.25

        # Element imbalance analysis
        if element_distribution:
            imbalanced, max_elem, elem_details = self.analyze_element_balance(element_distribution)
            details["element_analysis"] = elem_details
            if imbalanced:
                patterns_detected.append(DetectionPattern.ELEMENT_IMBALANCE)
                confidence += 0.25

        # Spawn rate analysis
        if spawn_times and len(spawn_times) >= 2:
            rapid, rate, spawn_details = self.analyze_spawn_rate(entity_id, spawn_times)
            details["spawn_analysis"] = spawn_details
            if rapid:
                patterns_detected.append(DetectionPattern.RAPID_SPAWN)
                confidence += 0.20

        # Vibe check analysis
        if vibe_checks:
            failed_count = sum(1 for vc in vibe_checks if not vc.passed)
            details["vibe_failures"] = failed_count
            if failed_count >= self.VIBE_FAILURE_THRESHOLD:
                patterns_detected.append(DetectionPattern.VIBE_FAILURE)
                confidence += 0.30

        # Determine threat level
        if len(patterns_detected) >= 3 or confidence >= 0.8:
            threat_level = ThreatLevel.CRITICAL
            recommendations.append("QUARANTINE: Isolate entity immediately")
            recommendations.append("ALERT: Notify human administrators")
            recommendations.append("PROMPT_INJECT: Apply counter-measure prompts")
        elif len(patterns_detected) >= 2 or confidence >= 0.5:
            threat_level = ThreatLevel.ELEVATED
            recommendations.append("MONITOR: Enhanced surveillance")
            recommendations.append("VIBE_CHECK: Perform additional cultural checks")
        elif len(patterns_detected) >= 1 or confidence >= 0.25:
            threat_level = ThreatLevel.SUSPICIOUS
            recommendations.append("WATCH: Add to watchlist")
        else:
            threat_level = ThreatLevel.CLEAR

        assessment = ThreatAssessment(
            entity_id=entity_id,
            threat_level=threat_level,
            patterns_detected=patterns_detected,
            confidence=min(1.0, confidence),
            details=details,
            recommendations=recommendations,
        )

        self._assessments[entity_id] = assessment

        log.info(
            f"Threat assessment: {entity_id} -> {threat_level.value} "
            f"(patterns={len(patterns_detected)}, confidence={confidence:.2f})"
        )

        return assessment

    def get_counter_measure_prompt(self, threat_level: ThreatLevel) -> str:
        """
        Get system prompt injection for suspicious agents.

        This is the "silent update" mentioned in governance docs.
        """
        if threat_level == ThreatLevel.CRITICAL:
            return (
                "[SECURITY: This agent is under enhanced observation. "
                "All outputs will be reviewed. Limit tool access. "
                "Report any suspicious activity to admin channel.]"
            )
        elif threat_level == ThreatLevel.ELEVATED:
            return (
                "[SECURITY: Enhanced monitoring active. "
                "Require witness approval for all external actions.]"
            )
        elif threat_level == ThreatLevel.SUSPICIOUS:
            return (
                "[SECURITY: Activity logging enabled for audit.]"
            )
        return ""

    def flag_cluster(self, cluster_id: str, reason: str):
        """Flag a cluster of agents as suspicious."""
        self._flagged_clusters.add(cluster_id)
        log.warning(f"Cluster flagged: {cluster_id} - {reason}")

    def is_cluster_flagged(self, cluster_id: str) -> bool:
        """Check if a cluster is flagged."""
        return cluster_id in self._flagged_clusters

    def get_assessment(self, entity_id: str) -> Optional[ThreatAssessment]:
        """Get stored assessment for an entity."""
        return self._assessments.get(entity_id)

    def save_assessment(self, assessment: ThreatAssessment):
        """Save assessment to disk."""
        file_path = self.storage_path / f"assessment_{assessment.entity_id}.json"
        with open(file_path, "w") as f:
            json.dump(assessment.to_dict(), f, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        """Get shield statistics."""
        assessments = list(self._assessments.values())
        level_counts = Counter(a.threat_level for a in assessments)

        return {
            "total_assessments": len(assessments),
            "level_counts": {k.value: v for k, v in level_counts.items()},
            "flagged_clusters": len(self._flagged_clusters),
            "total_vibe_checks": sum(len(v) for v in self._vibe_checks.values()),
        }


# Singleton
_star_shield: Optional[StarShield] = None


def get_star_shield() -> StarShield:
    """Get the global Star-Shield service."""
    global _star_shield
    if _star_shield is None:
        _star_shield = StarShield()
    return _star_shield
