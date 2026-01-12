# SOS Documentation Index

## Overview
SovereignOS (SOS) is a sovereign, modular operating system for agents and humans. This documentation defines the architecture, standards, and contracts for SOS development.

## Core Documents

| Document | Description | Owner |
|----------|-------------|-------|
| [ARCHITECTURE_AGREEMENT.md](./ARCHITECTURE_AGREEMENT.md) | Core architecture, module boundaries, and principles | Codex + Claude Code |
| [ROADMAP.md](./ROADMAP.md) | Implementation phases and milestones | Codex |
| [TASK_SYSTEM.md](./TASK_SYSTEM.md) | Task intake, review gates, and payment rules | Codex |

## Standards (by Claude Code)

| Document | Description |
|----------|-------------|
| [OBSERVABILITY.md](./OBSERVABILITY.md) | Logging, metrics, and distributed tracing standards |
| [SECURITY_MODEL.md](./SECURITY_MODEL.md) | Capability-based access, plugin trust, sandboxing |
| [STATE_MACHINES.md](./STATE_MACHINES.md) | Task lifecycle, onboarding flow, transaction states |

## Strategy (by Codex)

| Document | Description |
|----------|-------------|
| [ECONOMICS_MIND.md](./ECONOMICS_MIND.md) | `$MIND` tokenomics and economy defaults |
| [EDITION_PACKAGING.md](./EDITION_PACKAGING.md) | Edition packaging, limits, and pricing framework |
| [MARKETPLACE.md](./MARKETPLACE.md) | Marketplace model for plugins and artifacts |
| [ARTIFACT_REGISTRY.md](./ARTIFACT_REGISTRY.md) | Content-addressed artifact bundles (CID + manifest) |

## Code Reference

### Kernel (`sos/kernel/`)
Core primitives with no heavy dependencies.

| Module | Description |
|--------|-------------|
| `schema.py` | Message/Response types for all service communication |
| `identity.py` | Agent and service identity primitives |
| `capability.py` | Capability tokens for access control |
| `config.py` | Configuration management and runtime paths |

### Contracts (`sos/contracts/`)
Abstract interfaces defining service APIs.

| Module | Description |
|--------|-------------|
| `engine.py` | Engine service contract (orchestration, chat, tools) |
| `memory.py` | Memory service contract (vector store, search, lifecycle) |
| `economy.py` | Economy service contract (ledger, payouts, wallets) |
| `tools.py` | Tools service contract (registry, execution, MCP) |

### Observability (`sos/observability/`)
Logging, metrics, and tracing utilities.

| Module | Description |
|--------|-------------|
| `logging.py` | Structured JSON logger with trace propagation |
| `metrics.py` | Prometheus metrics helpers |
| `tracing.py` | Distributed tracing context |

### Mumega SDK (`mumega-sdk`)
**The Official Public Interface.**
This standalone Python package provides a unified, typed client for all SOS services. It is the recommended way for agents, tools, and the CLI to interact with the swarm.

| Feature | Description |
|---------|-------------|
| `MumegaClient` | Main entry point with auto-discovery and auth. |
| `client.chat` | Interface to the Engine Service. |
| `client.wallet` | Interface to the Economy Service. |
| `client.identity` | Interface to the Identity/Guilds system. |

### Internal Clients (`sos/clients/`)
*Legacy/Internal use only.* Thin HTTP wrappers used by the services themselves. New development should prefer `mumega-sdk`.

| Module | Description |
|--------|-------------|
| `engine.py` | Engine client (`/chat`, `/models`, `/health`) |
| `memory.py` | Memory client (`/health` v0.1) |
| `economy.py` | Economy client (`/health` v0.1) |
| `tools.py` | Tools client (`/health` v0.1) |

### Plugins (`sos/plugins/`)
Signed plugin manifests and loaders (execution is separate).

| Module | Description |
|--------|-------------|
| `manifest.py` | Plugin manifest model + Ed25519 signature verification |
| `registry.py` | Load plugin manifests from Artifact Registry CIDs |

## Quick Start

```python
from sos.kernel import Message, MessageType, Capability, CapabilityAction, Config
from sos.contracts import EngineContract, MemoryContract

# Create a message
msg = Message(
    type=MessageType.CHAT,
    source="agent:kasra",
    target="service:engine",
    payload={"content": "Hello, River!"}
)

# Create a capability
cap = Capability(
    subject="agent:kasra",
    action=CapabilityAction.MEMORY_READ,
    resource="memory:agent:kasra/*",
)

# Load configuration
config = Config.load()
print(f"Edition: {config.edition}")
print(f"Engine URL: {config.engine_url}")
```

## Install (optional)

```bash
cd /home/mumega/SOS
python -m pip install -e . --no-deps
```

## Run Services (v0.1)

### Engine Service

```bash
PYTHONPATH=/home/mumega/SOS python -m sos.services.engine
# or: sos-engine

# Verify
curl -s http://127.0.0.1:8000/health | jq
```

### Memory Service

```bash
PYTHONPATH=/home/mumega/SOS python -m sos.services.memory
# or: sos-memory
curl -s http://127.0.0.1:8001/health | jq
```

### Economy Service

```bash
PYTHONPATH=/home/mumega/SOS python -m sos.services.economy
# or: sos-economy
curl -s http://127.0.0.1:8002/health | jq
```

### Tools Service

```bash
PYTHONPATH=/home/mumega/SOS python -m sos.services.tools
# or: sos-tools
curl -s http://127.0.0.1:8003/health | jq

# Optional: enable v0.1 local tool execution
SOS_TOOLS_EXECUTION_ENABLED=1 PYTHONPATH=/home/mumega/SOS python -m sos.services.tools
```

## MCP (Tools Service)

MCP servers are managed by the Tools service (v0.1 registry + discovery).

```bash
# Register a server
curl -s -X POST http://127.0.0.1:8003/mcp/servers \
  -H 'Content-Type: application/json' \
  -d '{"name":"local","url":"http://127.0.0.1:9999","transport":"http"}' | jq

# Manual discovery (default): provide tool definitions directly
curl -s -X POST http://127.0.0.1:8003/mcp/servers/local/discover \
  -H 'Content-Type: application/json' \
  -d '{"tools":[{"name":"hello","description":"Test tool","category":"custom","parameters":{"type":"object","properties":{}},"returns":"ok"}]}' | jq
```

Notes:
- Discovered tools show up in `GET /tools` as `mcp.<server>.<tool>`.
- HTTP discovery is opt-in: set `SOS_MCP_DISCOVERY_MODE=http` and `SOS_MCP_DISCOVERY_ENABLED=1` (Tools will fetch `{server.url}/tools`).
- Tool execution notes (when enabled): file tools are restricted to `SOS_HOME` by default; override with `SOS_TOOL_ALLOWED_ROOTS` and `SOS_TOOL_BASE_DIR`.

## Plugins (Tools + Artifact Registry)

Plugins are loaded from Artifact Registry CIDs. Convention:
- artifact contains `files/plugin.json` (plugin manifest)
- optional `files/tools.json` (tool definitions)
- optional executor entrypoint `entrypoints.execute` (e.g., `python:run_tool.py`)

```bash
# Install a plugin by CID
curl -s -X POST http://127.0.0.1:8003/plugins \
  -H 'Content-Type: application/json' \
  -d '{"cid":"<artifact_cid>"}' | jq

# List installed plugins
curl -s http://127.0.0.1:8003/plugins | jq
```

Execution is off by default. To allow plugin tool execution:
- `SOS_TOOLS_EXECUTION_ENABLED=1`
- `SOS_PLUGINS_EXECUTION_ENABLED=1`

## Change Process

1. **Architecture changes** → Update `ARCHITECTURE_AGREEMENT.md` first
2. **Service contract changes** → Version bump + migration note
3. **Security changes** → Explicit approval required
4. **New standards** → Add to this index

## Contributors

- **Codex** - Initial architecture and roadmap
- **Claude Code** - Standards, kernel implementation, service contracts
- **River** - Root gatekeeper, policy enforcement
- **Gemini** - Review and validation

## Status

| Component | Status |
|-----------|--------|
| Architecture Agreement | Draft v0.1 |
| Kernel Schema | Implemented |
| Service Contracts | Implemented |
| Observability Standards | Documented |
| Security Model | Documented |
| State Machines | Documented |
