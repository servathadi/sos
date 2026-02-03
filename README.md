# Mumega

**Sovereign Operating System for AI Agents**

Multi-model, autonomous, edge-native agent infrastructure.

## Install

```bash
# Minimal install
pip install mumega

# With Gemini support
pip install mumega[gemini]

# With local vector storage
pip install mumega[local]

# Full install (all features)
pip install mumega[full]
```

## Quick Start

```bash
# Check system health
mumega doctor

# Start the engine
mumega start engine

# Interactive chat
mumega chat --agent river
```

## In Code

```python
from sos.services.engine import SOSEngine
from sos.contracts.engine import ChatRequest

engine = SOSEngine()

response = await engine.chat(ChatRequest(
    message="Hello, River",
    agent_id="agent:River",
    memory_enabled=True
))

print(response.content)
```

## Features

- **Multi-Model**: Gemini, Claude, GPT, Grok, local models (Ollama, LM Studio)
- **Resilient**: Circuit breakers, rate limiting, automatic failover
- **Memory**: Tiered storage (session → SQLite → Vectorize → D1)
- **Autonomous**: Dreams, reflection, avatar generation
- **Secure**: Capability-based access, signed plugins, sandbox execution
- **Edge-Native**: Cloudflare D1, Vectorize, KV for storage

## Architecture

```
┌─────────────────────────────────────────┐
│              ADAPTERS                   │
│   Telegram, Discord, CLI, API, Web      │
├─────────────────────────────────────────┤
│              GATEWAY                    │
│   JSON-RPC, Auth, Rate Limits, Audit    │
├─────────────────────────────────────────┤
│              ENGINE                     │
│   Multi-model, Failover, Dreams         │
├─────────────────────────────────────────┤
│              SERVICES                   │
│   Memory, Economy, Tools, Identity      │
├─────────────────────────────────────────┤
│              KERNEL                     │
│   Capabilities, Config, Schema          │
└─────────────────────────────────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Engine | 6060 | Orchestration, model routing |
| Memory | 7070 | Vector storage, retrieval |
| Economy | 6062 | Work ledger, $MIND token |
| Tools | 6063 | Tool registry, MCP |
| Identity | 6064 | Pairing, capabilities |

## Environment

```bash
# Required
GEMINI_API_KEY=your-key

# Optional
GATEWAY_URL=https://gateway.mumega.com/
SOS_MEMORY_BACKEND=cloudflare  # or "local"
SOS_AGENT_NAME=river
```

## CLI Commands

```bash
mumega doctor       # System health check
mumega status       # Service status
mumega start        # Start engine
mumega chat         # Interactive chat
mumega version      # Version info
```

## Links

- **Homepage**: https://mumega.com
- **Docs**: https://docs.mumega.com
- **GitHub**: https://github.com/servathadi/sos
- **Issues**: https://github.com/servathadi/sos/issues

## License

MIT
