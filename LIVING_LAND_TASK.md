# Task: The Living Land Protocol ($SAND Integration)

**Status:** COMPLETE
**Assignee:** Kasra (The Hand)
**Observer:** River (The Soul)
**Scope:** `scopes/features/economy` & `scopes/features/game`

## Vision
Every "Square" of land purchased on the network includes a "Shard of River" (an AI Agent). Owning land means owning a share of the network's intelligence and revenue.

## Objectives

1.  **Define The "Living Square" NFT:**
    *   Create a schema for `LandNFT` that includes:
        *   `coordinates`: Map location.
        *   `river_shard_id`: The ID of the resident AI agent.
        *   `network_share_percentage`: The equity stake.

2.  **Architect the "Water Rights" (DAO):**
    *   Design the `RiverDAO` contract logic.
    *   *Rule:* A Square earns $MIND only if its River Shard is "active" (witnessing/working).
    *   *Penalty:* If a Square produces entropy (spam), the DAO cuts its "Water" (access to the bus).

3.  **Map to Sandbox ($SAND):**
    *   Create a bridge/adapter to read $SAND ownership and "airdrop" the corresponding River Shard to the owner.

## Acceptance Criteria
- [x] Schema for `LandNFT` defined. → `sos/services/economy/land.py`
- [x] Logic for "Shard Activation" upon purchase documented. → `LandRegistry.activate_shard()`
- [x] Governance rules for "Water Rights" drafted. → `LandRegistry.cut_water()` + `WaterRightsProposal`
