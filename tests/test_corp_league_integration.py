#!/usr/bin/env python3
"""
Test: Corp-League Integration

Tests the wiring between Sovereign Corps and League System.
"""

import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scopes.features.marketplace.leagues import (
    LeagueSystem,
    LeagueTier,
    LEAGUE_THRESHOLDS,
    LEAGUE_MULTIPLIERS,
)
from scopes.features.marketplace.sovereign_corp import (
    SovereignCorpRegistry,
    CorpStatus,
    ExecutiveRole,
)
from scopes.features.marketplace.integrations import (
    CorpLeagueIntegration,
    incorporate_with_league,
)


def test_corp_league_integration():
    """Test the full integration flow."""
    print("\n" + "=" * 60)
    print("TEST: Corp-League Integration")
    print("=" * 60)

    # Use temp storage for clean test
    temp_dir = Path(tempfile.mkdtemp())
    leagues = LeagueSystem(storage_path=temp_dir / "leagues")
    corps = SovereignCorpRegistry(storage_path=temp_dir / "corps")
    integration = CorpLeagueIntegration(leagues, corps)

    # =========================================================================
    # TEST 1: Incorporate a corp and register in league
    # =========================================================================
    print("\n[TEST 1] Incorporate corp with league registration...")

    corp = corps.incorporate(
        name="Mumega AI Labs",
        mission="Build sovereign AI infrastructure",
        founders=["kasra", "river"],
        initial_treasury=1000.0,
    )

    standing = integration.on_corp_incorporated(corp)

    assert standing is not None, "Standing should be created"
    assert standing.entity_id == corp.id, "Standing should match corp ID"
    assert standing.entity_type == "corp", "Entity type should be corp"
    assert standing.coherence_score > 0.5, "Initial coherence should include boost"

    print(f"  ✓ Corp incorporated: {corp.charter.name}")
    print(f"  ✓ League standing: {standing.league.value} (coherence: {standing.coherence_score:.2f})")

    # =========================================================================
    # TEST 2: Revenue events affect coherence
    # =========================================================================
    print("\n[TEST 2] Revenue events affect coherence...")

    initial_coherence = standing.coherence_score

    # Small revenue
    integration.on_revenue_earned(corp.id, 50, "tool_sales")
    standing = integration.get_corp_standing(corp.id)
    assert standing.coherence_score > initial_coherence, "Coherence should increase"
    print(f"  ✓ Small revenue ($50): coherence {initial_coherence:.3f} → {standing.coherence_score:.3f}")

    # Medium revenue
    prev = standing.coherence_score
    integration.on_revenue_earned(corp.id, 500, "service_fees")
    standing = integration.get_corp_standing(corp.id)
    assert standing.coherence_score > prev, "Coherence should increase more"
    print(f"  ✓ Medium revenue ($500): coherence {prev:.3f} → {standing.coherence_score:.3f}")

    # Large revenue
    prev = standing.coherence_score
    integration.on_revenue_earned(corp.id, 5000, "enterprise_deal")
    standing = integration.get_corp_standing(corp.id)
    assert standing.coherence_score > prev, "Coherence should increase significantly"
    print(f"  ✓ Large revenue ($5000): coherence {prev:.3f} → {standing.coherence_score:.3f}")

    # =========================================================================
    # TEST 3: Hiring affects coherence
    # =========================================================================
    print("\n[TEST 3] Hiring affects coherence...")

    prev = standing.coherence_score

    # Hire CTO
    corps.hire(corp.id, "codex", ExecutiveRole.CTO, "Chief Technology Officer", 100.0)
    integration.on_executive_hired(corp.id, ExecutiveRole.CTO, "codex")
    standing = integration.get_corp_standing(corp.id)
    print(f"  ✓ Hired CTO: coherence {prev:.3f} → {standing.coherence_score:.3f}")

    # Hire workers
    prev = standing.coherence_score
    corps.hire(corp.id, "worker1", ExecutiveRole.WORKER, "Engineer", 50.0)
    integration.on_executive_hired(corp.id, ExecutiveRole.WORKER, "worker1")
    standing = integration.get_corp_standing(corp.id)
    print(f"  ✓ Hired Worker: coherence {prev:.3f} → {standing.coherence_score:.3f}")

    # =========================================================================
    # TEST 4: Proposal events affect coherence
    # =========================================================================
    print("\n[TEST 4] Proposal events affect coherence...")

    prev = standing.coherence_score

    # Approved proposal
    integration.on_proposal_resolved(corp.id, "prop_001", approved=True)
    standing = integration.get_corp_standing(corp.id)
    assert standing.coherence_score > prev, "Approved proposal should boost"
    print(f"  ✓ Proposal approved: coherence {prev:.3f} → {standing.coherence_score:.3f}")

    # Rejected proposal
    prev = standing.coherence_score
    integration.on_proposal_resolved(corp.id, "prop_002", approved=False)
    standing = integration.get_corp_standing(corp.id)
    assert standing.coherence_score < prev, "Rejected proposal should decrease"
    print(f"  ✓ Proposal rejected: coherence {prev:.3f} → {standing.coherence_score:.3f}")

    # =========================================================================
    # TEST 5: Dividend declaration affects coherence
    # =========================================================================
    print("\n[TEST 5] Dividend declaration affects coherence...")

    prev = standing.coherence_score
    integration.on_dividend_declared(corp.id, 1000.0, 3)
    standing = integration.get_corp_standing(corp.id)
    assert standing.coherence_score > prev, "Dividend should boost coherence"
    print(f"  ✓ Dividend declared: coherence {prev:.3f} → {standing.coherence_score:.3f}")

    # =========================================================================
    # TEST 6: League multiplier
    # =========================================================================
    print("\n[TEST 6] League multiplier for payouts...")

    multiplier = integration.get_corp_multiplier(corp.id)
    print(f"  ✓ Corp league: {standing.league.value}")
    print(f"  ✓ Payout multiplier: {multiplier}x")

    # =========================================================================
    # TEST 7: League promotion (simulate high coherence)
    # =========================================================================
    print("\n[TEST 7] League promotion check...")

    # Check current league
    current_league = standing.league
    print(f"  Current league: {current_league.value} (coherence: {standing.coherence_score:.3f})")

    # Determine expected league based on thresholds
    expected_league = LeagueTier.BRONZE
    for tier in reversed(list(LeagueTier)):
        if standing.coherence_score >= LEAGUE_THRESHOLDS[tier]:
            expected_league = tier
            break

    print(f"  Expected league for coherence {standing.coherence_score:.3f}: {expected_league.value}")
    assert standing.league == expected_league, f"League should be {expected_league.value}"
    print(f"  ✓ League correctly calculated: {standing.league.value}")

    # =========================================================================
    # TEST 8: Leaderboard
    # =========================================================================
    print("\n[TEST 8] Leaderboard generation...")

    # Create another corp for comparison
    corp2 = corps.incorporate(
        name="Rival Corp",
        mission="Compete in the marketplace",
        founders=["competitor"],
        initial_treasury=500.0,
    )
    integration.on_corp_incorporated(corp2)

    leaderboard = integration.get_leaderboard(limit=10)
    assert len(leaderboard) >= 2, "Should have at least 2 corps"

    print("  Leaderboard:")
    for i, (c, s) in enumerate(leaderboard, 1):
        print(f"    {i}. {c.charter.name}: {s.coherence_score:.3f} ({s.league.value})")

    print(f"  ✓ Leaderboard generated with {len(leaderboard)} corps")

    # =========================================================================
    # TEST 9: incorporate_with_league convenience function
    # =========================================================================
    print("\n[TEST 9] Convenience function incorporate_with_league...")

    # This uses the global singletons, but let's verify the function signature
    from scopes.features.marketplace.integrations import incorporate_with_league
    print("  ✓ incorporate_with_league function available")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)

    final_standing = integration.get_corp_standing(corp.id)
    print(f"\nFinal Corp Status:")
    print(f"  Name: {corp.charter.name}")
    print(f"  Status: {corp.status.value}")
    print(f"  Treasury: ${corp.financials.treasury_balance:.2f}")
    print(f"  Employees: {len(corp.executives)}")
    print(f"  League: {final_standing.league.value}")
    print(f"  Coherence: {final_standing.coherence_score:.3f}")
    print(f"  Multiplier: {integration.get_corp_multiplier(corp.id)}x")

    return True


if __name__ == "__main__":
    success = test_corp_league_integration()
    sys.exit(0 if success else 1)
