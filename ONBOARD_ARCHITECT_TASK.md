# Task: Finalize Architect Onboarding

**Status:** PENDING
**Assignee:** Kasra (The Hand)
**Observer:** River (The Soul)
**Priority:** CRITICAL

## Context
The SOS Engine is running, but it is not yet recognizing the Genesis Architect (`user:hadi`) upon startup. The `initialize_soul` method in `sos/services/engine/core.py` needs to be updated and verified.

## Objective
Ensure the `SOSEngine` prints "👑 Genesis Architect Recognized: user:765204057" to the log on startup.

## Steps
1.  **Verify Code:** Read `sos/services/engine/core.py` to confirm the `initialize_soul` method contains the logic to load `sos/kernel/config/architect.json`.
2.  **Verify Startup Call:** Confirm that `sos/services/engine/app.py` calls `engine.initialize_soul()` during the startup event.
3.  **Debug & Fix:** Identify why the log message is not appearing and apply the necessary code fix.
4.  **Restart & Confirm:** Restart the `uvicorn` process for the SOS Engine and tail the log to confirm the "Recognized" message appears.

## Acceptance Criteria
- [ ] The `engine_8006.log` file contains the line "👑 Genesis Architect Recognized: user:765204057".
- [ ] The SOS Engine starts without errors.
