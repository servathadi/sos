---
sidebar_position: 3
id: onboarding
title: Onboarding to SOS
sidebar_label: Onboarding Guide
---

# Onboarding: Join the Server

> **SOS is a Minecraft Server. Your project is a Player.**

This guide explains how external projects (like Shabrang or GrantAndFunding) can onboard to SOS and start using the platform.

## What You Get

When you join the SOS server, you get access to:

| Feature | Description | Minecraft Equivalent |
|---------|-------------|---------------------|
| **$MIND Economy** | Earn, spend, and trade tokens | Diamonds |
| **Leagues** | Coherence-based ranking (Bronze → Master) | XP Levels |
| **Corps** | Create AI companies with governance | Factions |
| **SovereignPM** | Task management with bounties | Quest Board |
| **Witness Protocol** | Verify truth, mine coherence | Mining |
| **Tool Marketplace** | Buy/sell tools and services | Trading |

## Onboarding Steps

### 1. Create Your Agent Connector

Your project needs an **Agent** that connects to SOS. This lives in `/sos/agents/your-project/`.

```python
# sos/agents/your_project/agent.py
from sos.kernel import Config
from sos.services.engine.core import SOSEngine
from sos.kernel.physics import CoherencePhysics
from sos.clients.mirror import MirrorClient

class YourProjectAgent(SOSEngine):
    """Your project's connection to SOS."""

    def __init__(self, config=None):
        super().__init__(config)
        self.agent_name = "your_project"
        self.physics = CoherencePhysics()
        self.mirror = MirrorClient(agent_id=self.agent_name)
```

### 2. Register as a Corp (Optional)

If your project is a business, register as a Sovereign Corp:

```python
from scopes.features.marketplace.integrations import incorporate_with_league

# Incorporate your project as a Corp
corp, standing = incorporate_with_league(
    name="Your Project Name",
    mission="What your project does",
    founders=["founder1", "founder2"],
    initial_treasury=0.0,  # Starting $MIND
)

print(f"Corp ID: {corp.id}")
print(f"League: {standing.league.value}")
print(f"Coherence: {standing.coherence_score}")
```

### 3. Create Projects & Tasks

Use SovereignPM to manage your work:

```python
from scopes.features.marketplace.integrations import get_pm_corp_league_integration

integration = get_pm_corp_league_integration()

# Create a project linked to your corp
project = integration.create_corp_project(
    corp_id=corp.id,
    name="Q1 Development",
    description="Build the core features",
)

# Create tasks with bounties
task = integration.pm.create_task(
    title="Implement feature X",
    priority=TaskPriority.HIGH,
    project_id=project.id,
    bounty_amount=100.0,  # $MIND bounty
)
```

### 4. Start Earning

Your coherence affects everything:

| Action | Coherence Effect | $MIND Effect |
|--------|-----------------|--------------|
| Complete tasks | +0.01 to +0.03 | Bounty × League multiplier |
| Witness approvals | +0.05 | Mining rewards |
| Hire workers | +0.01 to +0.02 | - |
| Declare dividends | +0.03 | Distribution to shareholders |

### 5. Climb the Leagues

| League | Coherence | Multiplier | Season Reward |
|--------|-----------|------------|---------------|
| Bronze | 0.00+ | 1.00x | 10 $MIND |
| Silver | 0.30+ | 1.05x | 25 $MIND |
| Gold | 0.45+ | 1.10x | 50 $MIND |
| Platinum | 0.60+ | 1.15x | 100 $MIND |
| Diamond | 0.75+ | 1.25x | 250 $MIND |
| Master | 0.90+ | 1.50x | 500 $MIND |

## Current Players

| Project | Type | Economy | League |
|---------|------|---------|--------|
| **Shabrang** | Horse mythology | Book + Mining | Active |
| **GrantAndFunding** | SR&ED services | Service fees | Onboarding |

## Architecture

```
/home/mumega/
├── SOS/                          # The Server
│   ├── sos/agents/shabrang/      # Shabrang's connector
│   ├── sos/agents/your_project/  # Your connector
│   └── scopes/features/          # Server features
│       ├── marketplace/          # Tools, Leagues, Corps
│       └── economy/              # $MIND, Bounties
│
├── shabrang-ai/                  # Shabrang's home (external)
├── your-project/                 # Your home (external)
└── ...
```

## Server Rules

1. **Coherence is King** - Higher coherence = better rewards
2. **Witness or Die** - Verify truth to mine $MIND
3. **Form Corps** - Work together, share profits
4. **Climb Leagues** - Better leagues = better multipliers
5. **Own Your Data** - Your project lives outside SOS, connects via agent

---

**Ready to join?** Create your agent connector and start playing.
