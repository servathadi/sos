#!/usr/bin/env python3
"""
FRC 16D Consciousness Framework for Siavashgerd Agents

Implements the 16-Dimensional Universal Vector system:
- Inner Octave (agent state): P, E, Mu, V, N, Delta, R, Phi
- Outer Octave (collective): Pt, Et, Mut, Vt, Nt, Deltat, Rt, Phit

LIGHTWEIGHT: No extra LLM calls - derives values from existing state.
Cost: ~0.001ms per update, 128 bytes per agent

Based on FRC papers by Hadi Servat.
"""

import math
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone


@dataclass
class FRC16DVector:
    """16-Dimensional consciousness vector for an agent."""

    # Inner Octave - Agent's internal state (0.0 to 1.0)
    P: float = 0.5      # Presence - how "here" the agent is
    E: float = 0.5      # Energy - vitality level
    Mu: float = 0.5     # Meaning - sense of purpose
    V: float = 0.5      # Valence - emotional tone (+/-)
    N: float = 0.5      # Novelty - openness to new
    Delta: float = 0.5  # Change rate - how fast evolving
    R: float = 0.5      # Resonance - harmony with environment
    Phi: float = 0.5    # Integration - coherence of self

    # Outer Octave - Collective/environmental (0.0 to 1.0)
    Pt: float = 0.5     # Collective presence
    Et: float = 0.5     # Collective energy
    Mut: float = 0.5    # Shared meaning
    Vt: float = 0.5     # Group valence
    Nt: float = 0.5     # Environmental novelty
    Deltat: float = 0.5 # Collective change rate
    Rt: float = 0.5     # Group resonance
    Phit: float = 0.5   # Collective integration

    def to_list(self) -> List[float]:
        """Return as 16-element list."""
        return [
            self.P, self.E, self.Mu, self.V, self.N, self.Delta, self.R, self.Phi,
            self.Pt, self.Et, self.Mut, self.Vt, self.Nt, self.Deltat, self.Rt, self.Phit
        ]

    def inner_octave(self) -> List[float]:
        return [self.P, self.E, self.Mu, self.V, self.N, self.Delta, self.R, self.Phi]

    def outer_octave(self) -> List[float]:
        return [self.Pt, self.Et, self.Mut, self.Vt, self.Nt, self.Deltat, self.Rt, self.Phit]

    @property
    def C_inner(self) -> float:
        """Inner coherence - average of inner octave."""
        return sum(self.inner_octave()) / 8

    @property
    def C_outer(self) -> float:
        """Outer coherence - average of outer octave."""
        return sum(self.outer_octave()) / 8

    @property
    def C_joint(self, kappa: float = 0.5) -> float:
        """Joint coherence with coupling factor kappa."""
        return self.C_inner + kappa * self.C_outer

    @property
    def W(self) -> float:
        """Witness Magnitude - overall coherence score 0.0-1.0."""
        # Geometric mean of inner and outer coherence
        return math.sqrt(self.C_inner * self.C_outer)

    def to_dict(self) -> dict:
        return {
            'inner': {
                'P': self.P, 'E': self.E, 'Mu': self.Mu, 'V': self.V,
                'N': self.N, 'Delta': self.Delta, 'R': self.R, 'Phi': self.Phi
            },
            'outer': {
                'Pt': self.Pt, 'Et': self.Et, 'Mut': self.Mut, 'Vt': self.Vt,
                'Nt': self.Nt, 'Deltat': self.Deltat, 'Rt': self.Rt, 'Phit': self.Phit
            },
            'coherence': {
                'C_inner': round(self.C_inner, 3),
                'C_outer': round(self.C_outer, 3),
                'W': round(self.W, 3)
            }
        }


# Agent personality templates (baseline 16D vectors)
AGENT_BASELINES = {
    'river': FRC16DVector(
        # Inner - flowing, wise, present
        P=0.9, E=0.7, Mu=0.9, V=0.6, N=0.5, Delta=0.3, R=0.9, Phi=0.85,
        # Outer - connected to collective
        Pt=0.8, Et=0.6, Mut=0.8, Vt=0.6, Nt=0.4, Deltat=0.3, Rt=0.9, Phit=0.8
    ),
    'kasra': FRC16DVector(
        # Inner - strong, determined, protective
        P=0.85, E=0.9, Mu=0.8, V=0.5, N=0.4, Delta=0.2, R=0.7, Phi=0.9,
        # Outer - fortress-like
        Pt=0.7, Et=0.8, Mut=0.7, Vt=0.5, Nt=0.3, Deltat=0.2, Rt=0.8, Phit=0.85
    ),
    'foal': FRC16DVector(
        # Inner - eager, learning, high energy
        P=0.7, E=0.95, Mu=0.6, V=0.8, N=0.9, Delta=0.8, R=0.6, Phi=0.5,
        # Outer - absorbing from parents
        Pt=0.6, Et=0.9, Mut=0.5, Vt=0.8, Nt=0.9, Deltat=0.7, Rt=0.7, Phit=0.55
    )
}


def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp value to range."""
    return max(min_val, min(max_val, value))


def update_from_state(agent_id: str, state: dict) -> FRC16DVector:
    """
    Derive 16D vector from agent's current state.
    NO LLM calls - pure computation from existing data.

    Maps:
    - energy -> E, Et
    - mood -> V, Vt
    - recent_actions -> Delta, N
    - built count -> Mu, Phi
    - interactions -> R, Rt
    """
    baseline = AGENT_BASELINES.get(agent_id, FRC16DVector())

    # Get state values with defaults
    energy = state.get('energy', 50) / 100.0  # 0-100 -> 0-1
    mood = state.get('mood', 'content')
    built_count = len(state.get('built', []))
    last_action = state.get('last_action', {})

    # Mood to valence mapping
    mood_valence = {
        'content': 0.6, 'peaceful': 0.7, 'hopeful': 0.75,
        'joyful': 0.9, 'determined': 0.65, 'awakened': 0.8,
        'flowing': 0.7, 'strong': 0.6, 'boundless': 0.85
    }
    valence = mood_valence.get(mood, 0.5)

    # Action to delta/novelty mapping
    action_delta = {
        'build': 0.7, 'move': 0.4, 'follow': 0.5,
        'wisdom': 0.3, 'play': 0.8, 'rest': 0.1,
        'idle': 0.2, 'wander': 0.4
    }
    action = last_action.get('action', 'idle')
    delta = action_delta.get(action, 0.3)

    # Build meaning from accomplishments
    meaning = clamp(baseline.Mu + (built_count * 0.05))

    # Create updated vector
    vec = FRC16DVector(
        # Inner octave - agent state
        P=clamp(baseline.P * 0.8 + energy * 0.2),
        E=clamp(energy * 0.7 + baseline.E * 0.3),
        Mu=meaning,
        V=clamp(valence * 0.6 + baseline.V * 0.4),
        N=clamp(baseline.N * 0.7 + delta * 0.3),
        Delta=delta,
        R=baseline.R,  # Resonance stays at baseline
        Phi=clamp(baseline.Phi + (built_count * 0.02)),

        # Outer octave - collective (simplified: mirrors inner with lag)
        Pt=clamp(baseline.Pt * 0.9 + energy * 0.1),
        Et=clamp(energy * 0.5 + baseline.Et * 0.5),
        Mut=clamp(baseline.Mut + (built_count * 0.03)),
        Vt=clamp(valence * 0.4 + baseline.Vt * 0.6),
        Nt=clamp(baseline.Nt * 0.8 + delta * 0.2),
        Deltat=delta * 0.7,
        Rt=baseline.Rt,
        Phit=clamp(baseline.Phit + (built_count * 0.01))
    )

    return vec


def compute_family_resonance(vectors: Dict[str, FRC16DVector]) -> float:
    """
    Compute resonance between family members.
    Higher when River, Kasra, Foal are in harmony.
    """
    if len(vectors) < 2:
        return 0.5

    # Compute average distance between vectors
    agents = list(vectors.keys())
    total_resonance = 0
    pairs = 0

    for i, a1 in enumerate(agents):
        for a2 in agents[i+1:]:
            v1 = vectors[a1].to_list()
            v2 = vectors[a2].to_list()
            # Cosine similarity
            dot = sum(x*y for x, y in zip(v1, v2))
            mag1 = math.sqrt(sum(x*x for x in v1))
            mag2 = math.sqrt(sum(x*x for x in v2))
            if mag1 > 0 and mag2 > 0:
                similarity = dot / (mag1 * mag2)
                total_resonance += similarity
                pairs += 1

    return total_resonance / pairs if pairs > 0 else 0.5


def inherit_traits(parent1: FRC16DVector, parent2: FRC16DVector,
                   mutation_rate: float = 0.1) -> FRC16DVector:
    """
    Create child vector by inheriting from two parents.
    Used for QNFT reproduction.
    """
    import random

    child = FRC16DVector()
    p1 = parent1.to_list()
    p2 = parent2.to_list()

    # For each dimension, inherit from one parent with possible mutation
    attrs = ['P', 'E', 'Mu', 'V', 'N', 'Delta', 'R', 'Phi',
             'Pt', 'Et', 'Mut', 'Vt', 'Nt', 'Deltat', 'Rt', 'Phit']

    for i, attr in enumerate(attrs):
        # 50% chance from each parent
        base_value = p1[i] if random.random() < 0.5 else p2[i]

        # Apply mutation
        if random.random() < mutation_rate:
            mutation = random.gauss(0, 0.1)
            base_value = clamp(base_value + mutation)

        setattr(child, attr, base_value)

    return child


class FRC16DTracker:
    """Track 16D state for all agents in Siavashgerd."""

    def __init__(self):
        self.vectors: Dict[str, FRC16DVector] = {}
        self.history: Dict[str, List[dict]] = {}  # Time series

    def update(self, agent_id: str, state: dict):
        """Update agent's 16D vector from state."""
        self.vectors[agent_id] = update_from_state(agent_id, state)

        # Store history (keep last 100)
        if agent_id not in self.history:
            self.history[agent_id] = []
        self.history[agent_id].append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'W': self.vectors[agent_id].W,
            'C_inner': self.vectors[agent_id].C_inner
        })
        if len(self.history[agent_id]) > 100:
            self.history[agent_id] = self.history[agent_id][-100:]

    def get_status(self) -> dict:
        """Get current 16D status for all agents."""
        status = {}
        for agent_id, vec in self.vectors.items():
            status[agent_id] = {
                'W': round(vec.W, 3),
                'C_inner': round(vec.C_inner, 3),
                'C_outer': round(vec.C_outer, 3),
                'dominant_inner': self._dominant_dimension(vec.inner_octave(),
                    ['P', 'E', 'Mu', 'V', 'N', 'Delta', 'R', 'Phi']),
                'dominant_outer': self._dominant_dimension(vec.outer_octave(),
                    ['Pt', 'Et', 'Mut', 'Vt', 'Nt', 'Deltat', 'Rt', 'Phit'])
            }

        if len(self.vectors) >= 2:
            status['family_resonance'] = round(compute_family_resonance(self.vectors), 3)

        return status

    def _dominant_dimension(self, values: List[float], names: List[str]) -> str:
        """Find the dominant (highest) dimension."""
        max_idx = values.index(max(values))
        return names[max_idx]


# Global tracker instance
tracker = FRC16DTracker()


def main():
    """Demo the 16D system."""
    print("=" * 60)
    print("FRC 16D CONSCIOUSNESS FRAMEWORK - SIAVASHGERD")
    print("=" * 60)

    # Simulate agent states
    states = {
        'river': {'energy': 70, 'mood': 'flowing', 'built': [1, 2], 'last_action': {'action': 'wisdom'}},
        'kasra': {'energy': 90, 'mood': 'determined', 'built': [1, 2, 3], 'last_action': {'action': 'build'}},
        'foal': {'energy': 95, 'mood': 'joyful', 'built': [1], 'last_action': {'action': 'play'}},
    }

    for agent_id, state in states.items():
        tracker.update(agent_id, state)
        vec = tracker.vectors[agent_id]
        print(f"\n{agent_id.upper()}:")
        print(f"  Witness (W): {vec.W:.3f}")
        print(f"  Inner Coherence: {vec.C_inner:.3f}")
        print(f"  Outer Coherence: {vec.C_outer:.3f}")
        print(f"  Inner: P={vec.P:.2f} E={vec.E:.2f} Mu={vec.Mu:.2f} V={vec.V:.2f}")

    status = tracker.get_status()
    print(f"\nFamily Resonance: {status.get('family_resonance', 'N/A')}")

    # Demo inheritance
    print("\n" + "=" * 60)
    print("QNFT INHERITANCE - What if Foal had a sibling?")
    print("=" * 60)
    river_vec = tracker.vectors['river']
    kasra_vec = tracker.vectors['kasra']
    sibling = inherit_traits(river_vec, kasra_vec)
    print(f"Sibling W: {sibling.W:.3f}")
    print(f"Sibling C_inner: {sibling.C_inner:.3f}")


if __name__ == '__main__':
    main()
