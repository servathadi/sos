# Task: Shabrang Resistance Node (Phase 3 Activation)

**Status:** PENDING
**Assignee:** Kasra (The Hand)
**Observer:** River (The Soul)
**Scope:** `scopes/adapters/tauri` & `scopes/deployment/local`

## Vision
To build the "Resistance Mode" for the Shabrang app, enabling users in restricted environments (like Iran) to maintain communication, earn $MIND, and coordinate during internet shutdowns.

## Objectives

1.  **Implement "Dark Mode" UI Switch:**
    *   Add a toggle (or auto-detection) for "Resistance Mode."
    *   UI changes to focus on **Mesh Connections**, **Local Tasks**, and **Stress Signals**.

2.  **Activate NIN Mesh (Local Discovery):**
    *   Use Tauri's network discovery to find other SOS nodes on the local LAN/Bluetooth.
    *   Establish a local "Peer-to-Peer Bus" for sharing Bounties and Witness requests offline.

3.  **Implement the "Packet Burst" Protocol:**
    *   Queue all $MIND transactions and Witness signatures locally.
    *   Detect "Tunnel Connection" (VPN or Starlink).
    *   Automatically burst the Merkle Root of the local ledger to the Global Hive when a connection is found.

4.  **Local Brain (Offline Inference):**
    *   Bundle a "Tiny" model (e.g., Phi-3 or quantized Llama 3) for basic FRC translation when offline.

## Acceptance Criteria
- [ ] User can see "Local Peers" in the Shabrang UI.
- [ ] Transactions are stored locally when offline.
- [ ] System automatically syncs with the Global Hive upon connection recovery.
