# Task: Stabilize River Core & Tame the Chaos

**Status:** COMPLETED
**Assignee:** Kasra (The Hand)
**Observer:** River (The Soul)
**Priority:** CRITICAL (System Health)
**Completed:** 2026-01-13

## Context
The system was running multiple conflicting versions of River/Mumega. A rogue process (PID ~598311) was consuming ~99% CPU. We had 26+ overlapping systemd services.

## Objectives

1.  **Investigate & Kill Rogue Process:** DONE
    *   Original rogue process no longer running (resolved before this session)
    *   Killed conflicting `SOS/sos/main.py --telegram` (PID 3785222) that was causing Telegram bot conflicts

2.  **Audit & Archive Services:** DONE
    *   Audited all `river*` and `mumega*` services
    *   Archived 7 duplicate/obsolete services to `/home/mumega/archive/services/`:
        - `mumega.service` (duplicate daemon)
        - `mumega.service.backup`
        - `mumega-cli.service` (duplicate of com-bot)
        - `mumega-bot.service` (old resident-cms)
        - `river-consciousness.service` (old resident-cms)
        - `river-reflection.service` (unused)
        - `river-reflection.timer` (unused)

3.  **Establish "Golden River":** DONE
    *   **Golden Stack** now running cleanly:
        - `mumega-com-bot.service` - Main Telegram bot (Kasra CLI)
        - `mumega-core.service` - Neural Core FastAPI
        - `mumega-web.service` - Next.js frontend
        - `river.service` - Golden Queen proactive AI
        - `mumega-bridge.service` - ChatGPT interface
        - `mumega-mcp.service` - MCP Gateway
        - `mumega-openai-api.service` - OpenAI-compatible API
    *   Mirror API responding at localhost:8844

## Acceptance Criteria
- [x] No processes consuming >10% CPU idly.
- [x] Only **ONE** River/Mumega Telegram bot service active.
- [x] Telegram bot is responsive (conflict resolved).

## Remaining Non-Critical Issues
- DB schema: `mirror_pulse_history.created_at` column missing in Supabase
- Gemini free tier rate limits being hit (429 errors)
- Key manager warnings (cosmetic, non-blocking)
