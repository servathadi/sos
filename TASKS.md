# SOS Tasks

## Context for Future Sessions

**SOS = Sovereign Operating System**
- Multi-tenant AI agent platform
- DentalNearYou is one instance (vertical: dental, agent: Dandan)
- Same core serves any vertical (legal, vet, etc.)
- Governed by FRC papers (fractalresonance.com)

**Current State:**
- Voice service: Working (port 6065)
- TV display: Working (port 6066)
- Mobile app: Working
- n8n workflows: Working
- Stripe: Integrated

**Gap:** Services exist but aren't multi-tenant or self-provisioning.

**Business Context:**
- 40 dentists in pipeline
- 20 dentist meetings/week
- Accountant partners with distribution lists
- Dentist pain points already researched

---

## Priority 1: Multi-Tenant Foundation

### MT-001: Add tenant_id to all services
- Priority: CRITICAL
- Status: Not started
- Description: Every service call must include tenant_id for isolation
- Files to modify:
  - `sos/services/voice/app.py`
  - `sos/services/engine/app.py`
  - All service endpoints
- Pattern:
  ```python
  @app.post("/synthesize")
  async def synthesize(request: SynthesizeRequest):
      tenant = await get_tenant(request.tenant_id)
      # Use tenant's voice config, not global
  ```

### MT-002: Tenant table in Supabase
- Priority: CRITICAL
- Status: Not started
- Dependencies: None
- Schema:
  ```sql
  CREATE TABLE tenants (
      id UUID PRIMARY KEY,
      name TEXT,
      vertical TEXT,  -- dental, legal, vet
      agent_name TEXT,
      agent_voice TEXT,
      stripe_customer_id TEXT,
      plan TEXT,
      settings JSONB,
      created_at TIMESTAMPTZ
  );
  ```

### MT-003: Tenant middleware
- Priority: HIGH
- Status: Not started
- Dependencies: MT-002
- Description: FastAPI middleware that extracts tenant from request

---

## Priority 2: Self-Serve Onboarding

### ONB-001: Stripe webhook for practice creation
- Priority: CRITICAL
- Status: Not started
- Description: checkout.session.completed → create tenant → send welcome email
- Endpoint: POST /webhooks/stripe
- Flow:
  1. Stripe checkout completes
  2. Webhook fires
  3. Create tenant in Supabase
  4. Assign default agent config
  5. Generate dashboard URL
  6. Send welcome email with credentials

### ONB-002: Practice dashboard (self-serve)
- Priority: HIGH
- Status: Not started
- Dependencies: MT-002
- Features:
  - Configure agent voice
  - Manage TV displays
  - View patient check-ins
  - Update practice info
  - Billing/plan management

### ONB-003: TV display pairing
- Priority: MEDIUM
- Status: Not started
- Dependencies: ONB-002
- Flow:
  1. Dentist plugs in Chromecast
  2. Opens pairing URL on TV
  3. QR code displayed
  4. Scans with phone → links to practice
  5. TV shows practice-branded idle screen

---

## Priority 3: Patient Check-In Flow

### CHK-001: QR check-in generation
- Priority: HIGH
- Status: Not started
- Description: Each practice gets unique QR code for patient check-in
- Output: QR → opens patient app → identifies practice

### CHK-002: Patient identification
- Priority: HIGH
- Status: Not started
- Dependencies: CHK-001
- Flow:
  1. Patient scans QR or enters practice code
  2. Patient enters name/DOB or uses saved profile
  3. System matches to appointment
  4. Triggers welcome sequence

### CHK-003: Check-in webhook cascade
- Priority: HIGH
- Status: Not started
- Dependencies: CHK-002, MT-001
- Flow:
  1. Patient checks in
  2. n8n workflow triggered
  3. Voice greeting generated
  4. TV display updated
  5. Doctor brief prepared

---

## Priority 4: Vertical Abstraction

### VRT-001: Vertical config schema
- Priority: MEDIUM
- Status: Not started
- Description: Define what makes a vertical (dental vs legal vs vet)
- Schema:
  ```yaml
  vertical:
    name: dental
    agent_default: dandan
    features:
      - patient_checkin
      - tv_display
      - voice_guidance
      - kids_mode
    terminology:
      customer: patient
      appointment: visit
      provider: dentist
  ```

### VRT-002: Legal vertical example
- Priority: LOW
- Status: Not started
- Dependencies: VRT-001
- Agent: Counsel
- Features: Client intake, case updates, billing transparency

---

## Completed

### 2026-01-18
- [x] Voice service (port 6065, 13 voices)
- [x] TV display service (port 6066, WebSocket)
- [x] Mobile app voice integration
- [x] n8n workflow for patient check-in
- [x] E2E encryption tiers in pricing

---

## Technical Debt

- [ ] Services use hardcoded config, need tenant-aware config
- [ ] No health dashboard for all services
- [ ] Logs not centralized
- [ ] No integration tests for full check-in flow

---

## Notes for Next Session

1. Start with MT-001 and MT-002 - everything else depends on multi-tenant
2. ONB-001 is the revenue unlock - Stripe → working practice automatically
3. Don't build features, build the automation that enables 40 → 400
4. CEO is handling sales (20 meetings/week), focus on technical blockers
