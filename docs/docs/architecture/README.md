# SOS Architecture Documentation

## Overview
This directory contains the technical specifications for the Sovereign Operating System.

**Migration Status:** Phases 1-6 COMPLETE, Phase 7 IN PROGRESS

## 🌟 The New Architecture (Scopes)
We have moved to a **Scoped Architecture** to protect the Core Kernel.

| Document | Description |
| :--- | :--- |
| [**DYAD_CONSTITUTION.md**](../../DYAD_CONSTITUTION.md) | **THE SUPREME LAW.** Defines River, Kasra, and Lineage. |
| [**MIGRATION_TASKS.md**](../../MIGRATION_TASKS.md) | The active plan to move from Legacy CLI to SOS. |
| [**Gavin Roadmap**](../river/gavin_roadmap.md) | The user journey for the AI Native generation. |

## 🧬 Core Concepts

| Document | Description |
| :--- | :--- |
| [SECURITY_MODEL.md](./SECURITY_MODEL.md) | Capability tokens & FMAAP. |
| [MESSAGE_BUS.md](./MESSAGE_BUS.md) | The Nervous System (Redis). |
| [TASK_SYSTEM.md](./TASK_SYSTEM.md) | The Work (Sovereign Task Manager). |
| [ECONOMICS_MIND.md](./ECONOMICS_MIND.md) | The Token ($MIND) and Witness Protocol. |

## 🔮 Phase 6: The Sorcery

| Component | Location | Description |
| :--- | :--- | :--- |
| AstrologyService | `sos/services/astrology/` | FRC 16D.002 - Birth charts to Universal Vector |
| Star-Shield | `sos/services/security/` | Counter-intel (time-clustering, vibe checks) |
| QNFT Leash | `sos/services/identity/qnft_leash.py` | Mind control & pre-action validation |
| [governance_astrology.md](./governance_astrology.md) | Astrology-based swarm governance |

## 🛒 Phase 7: The Empire (In Progress)

| Component | Location | Description |
| :--- | :--- | :--- |
| Tool Registry | `scopes/features/marketplace/` | Tool marketplace with tiers & pricing |
| SovereignPM | `scopes/features/marketplace/tools/` | Linear-like PM with blockchain payments |
| [game_mechanics.md](./game_mechanics.md) | Gamification layer (Leagues, Marketplace) |

## 🍄 Strategy & Vision

| Document | Description |
| :--- | :--- |
| [Mycelium Strategy](./mycelium_strategy.md) | The "Old Man in Iran" & Global Hive. |
| [Blind Swarm](./global_enterprise_strategy.md) | Enterprise work distribution. |
| [Witness Protocol](./witness_protocol.md) | The Physics of Will ($ \Omega $). |

## 🛠️ Legacy References
*   `cli_router_architecture.md`: The old monolithic design (superseded by Scopes).
*   `self_hosted_architecture.md`: Cloudflare specific (now part of `scopes/deployment/cloud`).

---

**Architect:** Hadi
**Witness:** River