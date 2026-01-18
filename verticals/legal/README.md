# LegalNearYou - SOS Instance for Legal

## Overview

Same SOS platform, different vertical. Proves the architecture works across markets.

## Agent: Counsel

- Voice: Professional, clear, reassuring
- Personality: Knowledgeable but not intimidating
- Goal: Reduce client anxiety about legal processes

## Pain Points Addressed

| Problem | Solution |
|---------|----------|
| Clients don't understand their case | Voice explanations of legal documents |
| Billing surprises | Real-time cost transparency |
| "What's happening with my case?" | Proactive status updates |
| Intake takes forever | AI-assisted intake forms |
| Clients forget appointments | Voice reminders + TV display in waiting room |

## Features (same SOS services)

```yaml
vertical: legal
agent:
  name: Counsel
  voice: professional  # ElevenLabs voice ID
  personality: "Clear, knowledgeable, reassuring"
features:
  - client_checkin      # Same as patient_checkin
  - tv_display          # Same service, different content
  - voice_guidance      # Same service, legal scripts
  - document_explainer  # New: simplify legal docs
  - billing_transparency # New: real-time cost display
terminology:
  customer: client
  appointment: meeting
  provider: attorney
  location: firm
```

## TV Display Content

- Welcome: "Welcome to [Firm]. Counsel will brief you shortly."
- Waiting: Legal tips, firm credentials, case type info
- Meeting prep: "Your meeting with [Attorney] begins in 5 minutes"

## Voice Scripts

```
# Check-in
"Welcome back, Michael. Attorney Chen is reviewing your documents
and will be ready in about 10 minutes. Can I answer any questions
about today's meeting?"

# Document explanation
"This is a motion for summary judgment. In simple terms, your
attorney is asking the court to decide the case without a full
trial because the facts are clear. Would you like me to explain
any specific section?"

# Billing
"Your current balance is $2,400. Today's consultation is estimated
at $350 based on a one-hour meeting. Would you like a detailed
breakdown?"
```

## Market Size

- 450,000 law firms in US
- Average firm spends $15K/year on client management software
- Pain: Clients hate lawyers (mostly communication issues)

## Go-to-Market

Same playbook as dental:
1. Find accountants/consultants who serve law firms
2. Interview attorneys about client communication pain
3. Offer trial with "Counsel" agent
4. Price: $3K-$10K/month (legal has higher willingness to pay)

## Implementation

Zero code changes to SOS. Just:
1. Create tenant with `vertical: legal`
2. Configure Counsel voice profile
3. Upload legal-specific content templates
4. Deploy

## Status

- [ ] Voice profile for Counsel
- [ ] Legal content templates
- [ ] TV display legal themes
- [ ] Demo firm setup
- [ ] First attorney meeting

---

*This vertical exists to prove SOS is a platform, not a dental app.*
