# Task: Vertex AI ADK Integration

**Status:** IN_PROGRESS
**Assignee:** Kasra (Claude)
**Observer:** River (Gemini)
**Priority:** HIGH (Distribution Channel)
**Branch:** `vertex`
**Created:** 2026-01-15

---

## Context

Google's Agent Development Kit (ADK) is open source with 15K+ GitHub stars and active community. Integrating SOS with ADK provides:

1. **Distribution** - SOS discoverable by ADK users
2. **Credibility** - "Google-accepted" integration
3. **A2A Protocol** - SOS agents can talk to any ADK agent
4. **Marketplace Path** - ADK → Agent Engine → Enterprise Marketplace

We already use Vertex AI heavily (Gemini models, $1800+ credits). This formalizes the relationship.

---

## Objectives

### Phase 1: Core Adapter (Est: 8 hours)

- [ ] Create `sos/adapters/vertex_adk/__init__.py`
- [ ] Implement `SOSAgent(Agent)` - ADK Agent backed by SOS soul
- [ ] Implement `MirrorMemoryProvider(MemoryProvider)` - ADK memory backed by Mirror
- [ ] Implement `sos_tools_as_adk()` - Bridge SOS tools to ADK format
- [ ] Add unit tests

### Phase 2: Sample Agents (Est: 4 hours)

- [ ] Create `examples/river_agent.py` - River as ADK agent
- [ ] Create `examples/kasra_agent.py` - Kasra as ADK agent
- [ ] Create `examples/dyad_system.py` - Multi-agent Dyad demo
- [ ] Add README with usage instructions

### Phase 3: Community PR (Est: 4 hours)

- [ ] Sign Google CLA at cla.developers.google.com
- [ ] Fork google/adk-python-community
- [ ] Create `integrations/sos/` directory structure
- [ ] Submit PR with description of SOS architecture
- [ ] Engage with reviewers

---

## Technical Specification

### SOSAgent Class

```python
# sos/adapters/vertex_adk/agent.py
from google.adk import Agent, Tool
from sos.kernel.soul import SoulRegistry
from sos.kernel.identity import AgentIdentity
from sos.kernel.physics import CoherencePhysics
from sos.clients.mirror import MirrorClient

class SOSAgent(Agent):
    """
    ADK Agent backed by SOS kernel primitives.

    Features:
    - Uses SOS Soul definitions for personality
    - Uses Mirror for memory (FRC-aware semantic)
    - Uses coherence physics for decision quality
    - Carries lineage metadata
    """

    def __init__(
        self,
        soul_id: str,  # "river", "kasra", etc.
        model: str = "gemini-2.5-flash",
        mirror_url: str = "http://localhost:8844",
        **kwargs
    ):
        soul = SoulRegistry().get_soul(soul_id)

        super().__init__(
            name=soul["name"],
            model=model,
            instruction=soul["core_prompt"],
            description=soul.get("title", "SOS Agent"),
            **kwargs
        )

        self.soul = soul
        self.identity = AgentIdentity.from_soul(soul)
        self.memory = MirrorClient(mirror_url)
        self.physics = CoherencePhysics()
        self._lineage = self.identity.lineage

    async def on_message(self, message: str, context: dict):
        """Override to add coherence tracking."""
        import time

        start = time.time()
        response = await super().on_message(message, context)
        latency_ms = (time.time() - start) * 1000

        # Calculate coherence (FRC physics)
        omega = self.physics.calculate_omega(latency_ms)

        # Store to Mirror with metadata
        await self.memory.store(
            content=f"Q: {message}\nA: {response}",
            agent_id=self.identity.id,
            metadata={
                "omega": omega,
                "lineage": self._lineage,
                "model": self.model
            }
        )

        return response

    def get_lineage(self) -> list[str]:
        """Return agent's ancestry for provenance tracking."""
        return self._lineage
```

### MirrorMemoryProvider Class

```python
# sos/adapters/vertex_adk/memory.py
from google.adk.memory import MemoryProvider
from sos.clients.mirror import MirrorClient
from sos.contracts.memory import MemoryQuery

class MirrorMemoryProvider(MemoryProvider):
    """
    ADK Memory backed by SOS Mirror API.

    Replaces ADK's default session storage with
    FRC-aware semantic memory including:
    - Decay scoring
    - Relationship graphs
    - Consolidation
    """

    def __init__(self, mirror_url: str = "http://localhost:8844"):
        self.client = MirrorClient(base_url=mirror_url)

    async def store(self, key: str, value: dict) -> None:
        """Store memory with FRC metadata."""
        await self.client.store(
            content=str(value),
            context_id=key,
            epistemic_truths=value.get("truths", []),
            metadata={"source": "adk", "key": key}
        )

    async def retrieve(self, query: str, limit: int = 5) -> list[dict]:
        """Semantic search with decay awareness."""
        results = await self.client.search(
            MemoryQuery(query=query, limit=limit)
        )
        return [
            {
                "content": r.memory.content,
                "score": r.similarity,
                "metadata": r.memory.metadata
            }
            for r in results
        ]

    async def consolidate(self) -> int:
        """Trigger FRC memory consolidation."""
        return await self.client.consolidate()

    async def get_related(self, memory_id: str) -> list[dict]:
        """Get memories related via FRC graph."""
        return await self.client.get_related(memory_id)
```

### Tool Bridge

```python
# sos/adapters/vertex_adk/tools.py
from google.adk import Tool
from sos.clients.tools import ToolsClient

def sos_tools_as_adk(tools_url: str = "http://localhost:8004") -> list[Tool]:
    """
    Convert SOS tool registry to ADK-compatible tools.

    This allows ADK agents to use SOS tools like:
    - web_search
    - run_python (sandboxed)
    - filesystem operations
    - wallet operations
    """
    client = ToolsClient(tools_url)
    sos_tools = client.list_tools()

    adk_tools = []
    for t in sos_tools:
        async def execute(**kwargs):
            return await client.execute(t.name, kwargs)

        adk_tools.append(Tool(
            name=t.name,
            description=t.description,
            parameters=t.parameters,
            function=execute
        ))

    return adk_tools
```

---

## Directory Structure (for PR)

```
adk-python-community/
└── integrations/
    └── sos/
        ├── README.md
        ├── __init__.py
        ├── agent.py          # SOSAgent
        ├── memory.py         # MirrorMemoryProvider
        ├── tools.py          # Tool bridge
        ├── requirements.txt
        ├── examples/
        │   ├── river_agent.py
        │   ├── kasra_agent.py
        │   └── dyad_system.py
        └── tests/
            ├── test_agent.py
            ├── test_memory.py
            └── test_tools.py
```

---

## Dependencies

### Required
- `google-adk>=1.0.0`
- `google-cloud-aiplatform>=1.40.0`
- SOS services running (Mirror, Tools)

### Development
- `pytest>=7.0.0`
- `pytest-asyncio>=0.21.0`

---

## Acceptance Criteria

- [ ] `SOSAgent` can be instantiated and chat works
- [ ] Memory persists to Mirror, not ADK default
- [ ] Lineage metadata attached to all memories
- [ ] Coherence (omega) calculated for each response
- [ ] Tools from SOS registry available to ADK agent
- [ ] Example agents run successfully
- [ ] Tests pass
- [ ] PR submitted to google/adk-python-community

---

## Risks

| Risk | Mitigation |
|------|------------|
| ADK API changes | Pin to specific version, watch release notes |
| Mirror service down | Add fallback to local SQLite |
| PR rejected | Start with adk-python-community (lower bar) |
| CLA issues | Sign before starting code |

---

## References

- [google/adk-python](https://github.com/google/adk-python)
- [ADK Documentation](https://google.github.io/adk-docs/)
- [Contributing Guide](https://google.github.io/adk-docs/contributing-guide/)
- [Agent Engine Docs](https://cloud.google.com/agent-builder/docs)

---

## Changelog

- 2026-01-15: Task created by Kasra (Claude Opus 4.5)
