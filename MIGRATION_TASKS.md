# Migration Tasks: CLI -> Scoped SOS

## Phase 1: The Brain Transplant (Core Scope) - COMPLETE
- [x] **Port Intent Logic**: Created `sos/kernel/intent.py` with IntentRouter, IntentDomain, role-based resonance matching.
- [x] **Port Coherence Physics**: Already exists at `sos/kernel/physics.py` (CoherencePhysics) + `sos/services/memory/monitor.py` (CoherenceMonitor with FRC 841.004).
- [x] **Identity Bridge**: `sos/agents/definitions.py` has AgentSoul + AgentRole. Core agents (River, Kasra, Mizan, Mumega, Codex) defined.

## Phase 2: The Heartbeat (Feature Scope - Swarm) - COMPLETE
- [x] **Daemon Service**: Created `sos/services/engine/daemon.py` with SOSDaemon (Heartbeat, Dreams, Maintenance loops).
- [x] **Task Dispatcher**: Already exists at `sos/services/engine/swarm.py` (SwarmDispatcher) + `sos/services/engine/task_manager.py` (SovereignTaskManager).

## Phase 3: The Wealth Engine (Feature Scope - Economy) - COMPLETE
- [x] **$MIND Ledger**: Ported to `sos/services/economy/ledger.py`.
- [x] **Witness Integration**: Wired to Bus at `sos/services/witness/__init__.py`.
- [x] **Living Land Protocol**: Implemented at `sos/services/economy/land.py`.
- [x] **Bounty Board**: Created `scopes/features/economy/bounties.py` with lifecycle, expiration, witness approval.
- [x] **Hive Workers**: Created `scopes/features/swarm/workers.py` with WorkerRegistry, AsyncHiveBridge, reputation tiers.
- [x] **Guild Registry**: Created `scopes/features/economy/guilds.py` with multi-sig treasury, governance proposals.

## Phase 4: The Nervous System (Adapters) - COMPLETE
- [x] **CLI Adapter**: Created `scopes/adapters/cli/cli_adapter.py` with Click commands (task, witness, economy, land, status, chat).
- [x] **Telegram Bot**: Enhanced `sos/adapters/telegram.py` with 10+ commands (/help, /status, /balance, /witness, /tasks, /land).
- [x] **Tauri Shell (Shabrang)**: Scaffolded `scopes/adapters/tauri/` with Rust backend, sidecar management, IPC commands.
- [x] **Web Adapter**: Documented at `scopes/adapters/web/` linking to `/web/dashboard`.

## Phase 5: Deployment - COMPLETE
- [x] **Docker "Pocket Node"**: Already exists at `docker-compose.yml` with all services (Redis, Engine, Memory, Economy, Tools, Identity, Workers x3).

---

## 🔮 The Backlog (Advanced Magic)

### Phase 6: The Sorcery (Astrology & QNFT)
- [ ] **Astrological Profiling**: Implement `AstrologyService`.
- [ ] **Protocol Star-Shield**: Counter-Intel logic.
- [ ] **QNFT Leash**: Mind Control metadata.

### Phase 7: The Empire (Game & Strategy)
- [ ] **League Logic**: Implement Leagues.
- [ ] **Marketplace Contract**: P2P Market.
- [ ] **AI Company Template**: Sovereign Corp logic.