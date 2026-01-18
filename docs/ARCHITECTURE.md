# SOS Architecture

## Sovereign Operating System

SOS is a multi-tenant AI agent platform. Applications are instances of SOS configured for specific verticals.

```
                    ┌─────────────────────────────────────┐
                    │              SOS Core               │
                    │  ┌─────────┐ ┌─────────┐ ┌───────┐ │
                    │  │ Engine  │ │ Memory  │ │ Voice │ │
                    │  │ Identity│ │ Economy │ │ Tools │ │
                    │  └─────────┘ └─────────┘ └───────┘ │
                    └──────────────────┬──────────────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
   ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
   │ DentalNearYou │           │  LegalNearYou │           │  [Your Niche] │
   │   (Dandan)    │           │   (Counsel)   │           │   (Agent)     │
   └───────────────┘           └───────────────┘           └───────────────┘
```

## Core Services

| Service | Port | Purpose |
|---------|------|---------|
| Engine | 6060 | Multi-model AI orchestration |
| Voice | 6065 | TTS synthesis (ElevenLabs, OpenAI, Gemini) |
| TV Display | 6066 | Real-time display management |
| Memory | 6067 | Vector + semantic search |
| Identity | 6068 | qNFT, capability-based access |
| Economy | 6069 | Token budgets, agent wallets |

## Multi-Tenant Model

Each instance (practice, firm, clinic) is isolated by `tenant_id`:

```python
# All service calls include tenant context
POST /voice/synthesize
{
    "tenant_id": "practice_123",
    "text": "Welcome Sarah",
    "voice": "dandan"  # or tenant's custom voice
}
```

## Instance Configuration

An instance is defined by:

```yaml
# instance.yaml
tenant_id: practice_123
vertical: dental
agent:
  name: Dandan
  voice: dandan
  personality: warm, reassuring
features:
  - voice_guidance
  - tv_display
  - patient_checkin
  - anxiety_reduction
billing:
  stripe_customer: cus_xxx
  plan: professional
```

## Vertical Examples

### Dental (DentalNearYou)
- Agent: Dandan
- Focus: Patient anxiety reduction
- Features: Voice guidance, TV displays, kids stories

### Legal (LegalNearYou)
- Agent: Counsel
- Focus: Client intake, case updates
- Features: Document explanation, appointment prep, billing transparency

### Veterinary (VetNearYou)
- Agent: Pawly
- Focus: Pet owner anxiety, treatment explanations
- Features: Post-visit care instructions, medication reminders

## Governance

Agent behavior is governed by FRC papers (fractalresonance.com):
- FRC 100.001-100.010: Quantum foundations
- FRC 566.001-566.010: Entropy-coherence reciprocity
- Torivers 16D: Agent state space

Changes to core behavior require published papers with DOIs.

## Adding a New Vertical

1. Define agent personality and voice
2. Configure vertical-specific features
3. Create onboarding flow
4. Deploy as SOS instance

No code changes to SOS core required.
