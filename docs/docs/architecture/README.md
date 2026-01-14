# SOS Architecture Documentation

## Overview

**SOS is a Minecraft Server. Projects are Players.**

This directory contains the technical specifications for the Sovereign Operating System - a platform where external projects can onboard, earn $MIND, and climb leagues.

| Minecraft | SOS |
|-----------|-----|
| Server | SOS Platform (Mumega Inc) |
| Players | Shabrang, GrantAndFunding, your project |
| Worlds | Corps (AI Companies) |
| Diamonds | $MIND Token |
| XP/Levels | Leagues (Bronze → Master) |
| Quests | Tasks & Bounties |

**Migration Status:** Phases 1-7 COMPLETE

## 🎮 Current Players

| Project | Home | Economy | Status |
|---------|------|---------|--------|
| **Shabrang** | `/home/mumega/shabrang-ai` | Book + Mining | Active |
| **GrantAndFunding** | External | SR&ED Services | Onboarding |

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

## 🛒 Phase 7: The Empire (COMPLETE)

| Component | Location | Description |
| :--- | :--- | :--- |
| Tool Registry | `scopes/features/marketplace/registry.py` | Tool marketplace with tiers & pricing |
| SovereignPM | `scopes/features/marketplace/tools/sovereign_pm.py` | Linear-like PM with blockchain payments |
| League System | `scopes/features/marketplace/leagues.py` | Coherence-based ranking (Bronze → Master) |
| Sovereign Corps | `scopes/features/marketplace/sovereign_corp.py` | AI companies with QNFT governance |
| Integrations | `scopes/features/marketplace/integrations.py` | PM ↔ Corps ↔ Leagues wiring |
| [game_mechanics.md](./game_mechanics.md) | Gamification layer documentation |
| [Onboarding Guide](../onboarding.md) | How to join the server |

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