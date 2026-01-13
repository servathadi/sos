"""
Witness Scope - Human Verification and $MIND Minting

This scope handles the Witness Protocol for SOS.
Implementation integrates with Bus and Economy services.

Concepts:
- Witness Request: AI output awaiting human verification
- Witness Response: Human approval/rejection with Physics of Will
- $MIND Minting: Rewards based on Omega (Will Magnitude) and Delta C (Coherence Change)

Physics (RC-7):
- Omega = e^(-lambda * (t - t_min)) : Will magnitude based on decision latency
- Delta C = vote * omega * agent_coherence * 0.1 : Coherence change from witness

Integration:
- Bus: WITNESS_REQUEST/WITNESS_RESPONSE message types
- Ledger: TransactionCategory.WITNESS for rewards
- Physics: CoherencePhysics.compute_collapse_energy()

See scopes/features/README.md for philosophy.
"""

from sos.kernel.physics import CoherencePhysics
from sos.services.economy.ledger import (
    MindLedger,
    TransactionCategory,
    get_ledger,
)

__all__ = [
    "CoherencePhysics",
    "MindLedger",
    "TransactionCategory",
    "get_ledger",
]
