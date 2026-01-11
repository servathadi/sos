# SOS Roadmap (Draft)

Status: Living Document
Owner: Codex
Last Updated: 2026-01-10

## Goal
Create a clean SovereignOS workspace in `/home/mumega/SOS` with modular services and thin adapters, while keeping the current repo stable.

## Branching Strategy
- Keep `Beta2` stable in `/home/mumega/cli`.
- Create a dedicated branch for modularization work (e.g., `sos-modularization`).
- SOS workspace is built in parallel; adapters can switch over via feature flags.

## Phases

### Phase 0: Agreement (Active)
- Finalize `ARCHITECTURE_AGREEMENT.md` with agent feedback.
- Lock module boundaries and contracts.
- **Owner:** Codex / Mumega

### Phase 1: Kernel + Engine Surface (Active)
- Extract kernel schema and capability model.
- Build Engine Service API surface (HTTP+JSON v0.1).
- **Owner:** Kasra (Engine) / Mumega (Orchestration)

### Phase 2: Memory + Economy Services (Complete)
- Move vector memory behind Memory Service. ✅
- Make Economy Service optional; wallet adapters become plugins. ✅
- **Owner:** Kasra (Implementation) / Mizan (Economics)

### Phase 3: Adapters & Thin Clients (Active)
- CLI/Telegram/Discord adapters become thin clients.
- Remove heavy imports from adapter entrypoints.
- **Owner:** Codex (Web/Telegram) / Mumega (Migration)

### Phase 4: Onboarding + Guild Hall Protocol
- River-led onboarding flow as a service.
- Edition policy sets (business, education, kids, art/music).
- **Owner:** River (Policy) / Mumega (Social Layer)

### Phase 5: Task Economy
- Task system uses SOS services.
- Witness, payout, and slashing rules enforced by Economy Service.
- **Owner:** Mizan / Kasra

## Success Criteria
- Adapters boot in <100ms with no heavy deps.
- Engine runs without memory/economy services when disabled.
- New agent can onboard with a single adapter and join a squad safely.
- **Guild Hall:** Users receive a QNFT Pass and can visualize their agent's subconscious.

---
*Updated by Mumega (Steward) - 2026-01-10*