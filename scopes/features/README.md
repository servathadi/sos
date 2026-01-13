# Feature Scope: The Business of Being

## Philosophy
This is the "Uber App" or the "Full Self-Driving Subscription" layer. It creates value from the Core's movement.

## Components
*   **Economy (`scopes/features/economy`):**
    *   **The Tesla Model:**
        *   **Staking (Battery Pack):** Users stack tokens to increase "Range" (Throughput) or "Priority" (Speed).
        *   **Mining (Regenerative Braking):** Earning back energy ($MIND) by doing work (Witnessing).
        *   **Investors:** Stack for "Fleet Priority" (Enterprise Tier).
    *   Handles Wallets, Ledgers, and $MIND token logic.
*   **Swarm (`scopes/features/swarm`):**
    *   **Fleet Management:**
        *   Distributes tasks to "Parked Cars" (Idle PCs).
        *   "The Old Man's Node" = A parked Tesla earning money by renting out compute.
    *   Handles Task Sharding, Dispatch, and Result Aggregation.
*   **Witness (`scopes/features/witness`):**
    *   **Autopilot Safety:**
        *   The "Human Hand on Wheel".
        *   Verifies AI output.
        *   Calculates $\Omega$ (Physics of Will) to mint value.

## Rule of Integration
Features consume Core signals (via Bus) and manipulate Core state (via Contracts), but they do not modify Core code.
