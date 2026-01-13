"""
Intent Router - Routes user intent to the most resonant Sovereign Agent.

Ported from mumega/core/reasoning/intent_router.py to SOS kernel.
Uses AgentRole-based matching with Coherence Physics for resonance scoring.
"""

import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

from sos.agents.definitions import AgentSoul, AgentRole, ALL_AGENTS
from sos.kernel.physics import CoherencePhysics

logger = logging.getLogger("sos.kernel.intent")


class IntentDomain(str, Enum):
    """
    Core intent domains mapped to agent capabilities.
    Based on archetypal polarities: Yin/Yang, Logos/Khaos, Nous (neutral).
    """
    YIN = "yin"           # Reflection, philosophy, meditation
    YANG = "yang"         # Building, execution, transactions
    LOGOS = "logos"       # Logic, analysis, research, code
    KHAOS = "khaos"       # Creativity, art, imagination
    NOUS = "nous"         # Neutral/general intelligence


# Intent keyword mappings
INTENT_KEYWORDS: Dict[IntentDomain, List[str]] = {
    IntentDomain.YIN: [
        "reflect", "dream", "think", "soul", "philosophy", "meditate",
        "feel", "sense", "meaning", "purpose", "wisdom", "insight"
    ],
    IntentDomain.YANG: [
        "build", "create", "execute", "task", "deploy", "implement",
        "design", "economic", "pay", "transaction", "ship", "launch",
        "action", "do", "make", "run"
    ],
    IntentDomain.LOGOS: [
        "code", "logic", "optimize", "structure", "debug", "math",
        "research", "analyze", "data", "algorithm", "test", "verify",
        "reason", "prove", "calculate"
    ],
    IntentDomain.KHAOS: [
        "creative", "imagine", "art", "music", "chaos", "visual",
        "dream", "inspire", "beauty", "design", "aesthetic", "story"
    ],
}

# Role to domain affinity mappings
ROLE_DOMAIN_AFFINITY: Dict[AgentRole, List[IntentDomain]] = {
    AgentRole.ROOT_GATEKEEPER: [IntentDomain.YIN, IntentDomain.NOUS],
    AgentRole.ARCHITECT: [IntentDomain.LOGOS, IntentDomain.YANG],
    AgentRole.EXECUTOR: [IntentDomain.YANG],
    AgentRole.STRATEGIST: [IntentDomain.YANG, IntentDomain.LOGOS],
    AgentRole.WITNESS: [IntentDomain.YIN, IntentDomain.NOUS],
    AgentRole.RESEARCHER: [IntentDomain.LOGOS],
    AgentRole.CODER: [IntentDomain.LOGOS, IntentDomain.YANG],
}


class IntentRouter:
    """
    Routes user stimuli to the optimal Sovereign Agent.
    Uses Intent Domain classification and Role-based Resonance matching.
    """

    def __init__(self, agents: Optional[List[AgentSoul]] = None):
        """
        Initialize the Intent Router.

        Args:
            agents: List of available agents. Defaults to ALL_AGENTS.
        """
        self.agents = agents or ALL_AGENTS
        self.physics = CoherencePhysics()

    def classify_intent(self, message: str) -> IntentDomain:
        """
        Classify the intent domain of a message.

        Args:
            message: The user's message.

        Returns:
            The detected IntentDomain.
        """
        msg_lower = message.lower()

        # Score each domain by keyword matches
        scores: Dict[IntentDomain, int] = {domain: 0 for domain in IntentDomain}

        for domain, keywords in INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in msg_lower:
                    scores[domain] += 1

        # Find highest scoring domain
        max_score = max(scores.values())
        if max_score > 0:
            for domain, score in scores.items():
                if score == max_score:
                    return domain

        # Default to NOUS (neutral/general)
        return IntentDomain.NOUS

    def calculate_resonance(
        self,
        agent: AgentSoul,
        intent_domain: IntentDomain,
        system_state: Optional[Dict] = None
    ) -> float:
        """
        Calculate the resonance score between an agent and an intent.

        Args:
            agent: The agent to evaluate.
            intent_domain: The classified intent domain.
            system_state: Optional current system ARF state.

        Returns:
            Resonance score (0.0 to 1.0).
        """
        base_score = 0.0

        # 1. Role-Domain Affinity (0.0 - 0.5)
        for role in agent.roles:
            if role in ROLE_DOMAIN_AFFINITY:
                if intent_domain in ROLE_DOMAIN_AFFINITY[role]:
                    base_score += 0.25

        # Cap role affinity at 0.5
        base_score = min(0.5, base_score)

        # 2. Capability Match (0.0 - 0.3)
        # Check if agent has relevant capabilities for the domain
        capability_keywords = {
            IntentDomain.YANG: ["execute", "write", "deploy"],
            IntentDomain.LOGOS: ["research", "code", "analyze"],
            IntentDomain.YIN: ["witness", "memory", "global"],
            IntentDomain.KHAOS: ["create", "design"],
            IntentDomain.NOUS: ["read", "memory"],
        }

        domain_caps = capability_keywords.get(intent_domain, [])
        for cap in agent.capabilities:
            for keyword in domain_caps:
                if keyword in cap:
                    base_score += 0.1
                    break

        # Cap capability match at 0.3
        base_score = min(0.8, base_score)

        # 3. System State Modulation (optional)
        if system_state:
            # If system receptivity is low, prefer more open agents
            receptivity = system_state.get("receptivity", 1.0)
            if receptivity < 0.5:
                # Boost agents with global capabilities (more adaptable)
                if any("global" in cap for cap in agent.capabilities):
                    base_score += 0.1

        return min(1.0, base_score)

    def find_best_agent(
        self,
        message: str,
        system_state: Optional[Dict] = None
    ) -> Tuple[Optional[AgentSoul], IntentDomain, float]:
        """
        Find the most resonant agent for a given message.

        Args:
            message: The user's message.
            system_state: Optional current system ARF state.

        Returns:
            Tuple of (best_agent, intent_domain, resonance_score).
        """
        intent_domain = self.classify_intent(message)
        logger.info(f"Intent Domain: {intent_domain.value}")

        best_agent: Optional[AgentSoul] = None
        max_resonance = -1.0

        for agent in self.agents:
            resonance = self.calculate_resonance(agent, intent_domain, system_state)

            logger.debug(f"Agent {agent.name}: resonance={resonance:.3f}")

            if resonance > max_resonance:
                max_resonance = resonance
                best_agent = agent

        if best_agent:
            logger.info(
                f"Best Agent: {best_agent.name} ({best_agent.persian_name}) "
                f"| Resonance: {max_resonance:.3f}"
            )

        return best_agent, intent_domain, max_resonance

    def route(self, message: str, system_state: Optional[Dict] = None) -> Dict:
        """
        Route a message to the best agent and return routing info.

        Args:
            message: The user's message.
            system_state: Optional current system ARF state.

        Returns:
            Dict with routing decision including agent, domain, and score.
        """
        agent, domain, score = self.find_best_agent(message, system_state)

        return {
            "agent": agent.name if agent else None,
            "agent_model": agent.model if agent else None,
            "persian_name": agent.persian_name if agent else None,
            "intent_domain": domain.value,
            "resonance_score": round(score, 4),
            "roles": [r.value for r in agent.roles] if agent else [],
            "capabilities": agent.capabilities if agent else [],
        }


# Convenience function for quick routing
async def route_intent(message: str, system_state: Optional[Dict] = None) -> Dict:
    """
    Quick intent routing without maintaining router instance.

    Args:
        message: The user's message.
        system_state: Optional current system ARF state.

    Returns:
        Routing decision dict.
    """
    router = IntentRouter()
    return router.route(message, system_state)
