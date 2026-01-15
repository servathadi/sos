# Technical Debt Backlog

**Status:** Active
**Owner:** Kasra (Claude)
**Last Audit:** 2026-01-15
**Total Items:** 34

---

## Priority Legend

| Priority | Meaning | SLA |
|----------|---------|-----|
| P0 | Security/Correctness - blocks production | This sprint |
| P1 | Feature incomplete - blocks demo | Next sprint |
| P2 | Code quality - tech debt | Backlog |
| P3 | Polish - nice to have | Opportunistic |

---

## P0: Security Critical

### SEC-001: Capability Signature Verification Not Enforced
**File:** `sos/services/engine/middleware.py:55`
**Issue:** `# TODO: Check signature and expiry` - capabilities pass without verification
**Impact:** Anyone can forge capability tokens
**Fix:**
```python
def verify(self, capability: CapabilityModel, action: str, resource: str) -> bool:
    # 1. Check expiry
    if capability.expires_at < datetime.now(timezone.utc):
        return False
    # 2. Verify Ed25519 signature
    from nacl.signing import VerifyKey
    # ... actual verification
```
**Estimate:** 2-3 hours
**Assignee:** Kasra

### SEC-002: Capability Middleware Logs But Doesn't Block
**File:** `sos/services/engine/middleware.py:31-34`
**Issue:** Failed FMAAP validation only logs warning, doesn't return 403
**Impact:** Security policy is advisory only
**Fix:** Add `return JSONResponse(status_code=403, ...)` when `not validation.valid`
**Estimate:** 30 minutes
**Assignee:** Kasra

### SEC-003: Empty Exception Handlers
**Files:**
- `sos/services/tools/docker/deep_research.py:161,169`
- `sos/services/engine/observer.py:167`
- `sos/services/tools/mcp_server.py:80`
- `sos/services/tools/sandbox.py:70`
- `sos/services/memory/vector_store.py:81`
**Issue:** `except: pass` swallows errors silently
**Impact:** Bugs hidden, debugging impossible
**Fix:** Replace with `except Exception as e: log.debug(f"Suppressed: {e}")`
**Estimate:** 1 hour
**Assignee:** Kasra

---

## P1: Feature Incomplete

### FEAT-001: Vertex Streaming Not Implemented
**File:** `sos/services/engine/adapters.py:216-218`
**Issue:** `# TODO: Implement Vertex streaming` - returns placeholder
**Impact:** No streaming responses from Vertex models
**Fix:** Implement using `model.generate_content_stream()`
**Estimate:** 2-3 hours
**Assignee:** Kasra

### FEAT-002: Gemini Streaming Has No Rotation Fallback
**File:** `sos/services/engine/adapters.py:298-299`
**Issue:** `# TODO: Implement rotation for streaming`
**Impact:** Streaming fails on rate limit instead of falling back
**Fix:** Wrap stream in rotation logic similar to `generate()`
**Estimate:** 2 hours
**Assignee:** Kasra

### FEAT-003: Deep Dream Synthesis Is Stub
**File:** `sos/services/engine/core.py:143-150`
**Issue:** `# TODO: Implement actual synthesis logic` - just sleeps
**Impact:** No memory consolidation happening
**Fix:**
```python
async def _deep_dream_synthesis(self):
    # 1. Fetch recent memories
    memories = await self.memory.search(MemoryQuery(query="*", limit=50))
    # 2. Cluster by similarity
    # 3. Generate synthesis
    # 4. Store as new engram
```
**Estimate:** 4-6 hours
**Assignee:** Kasra

### FEAT-004: ARF State Is Mocked
**File:** `sos/services/engine/core.py:118`
**Issue:** `state = {"alpha_drift": 0.0, "regime": "stable"} # Placeholder`
**Impact:** Dream cycle never triggers on real drift
**Fix:** Wire to `await self.memory.get_arf_state()`
**Estimate:** 1-2 hours
**Assignee:** Kasra
**Depends:** MirrorClient.get_arf_state() method

### FEAT-005: Health Checks Are Fake
**File:** `sos/services/engine/core.py:448-452`
**Issue:** `"memory": "connected", # TODO: Real check`
**Impact:** `/health` always returns OK even when services down
**Fix:** Actually ping each service URL
**Estimate:** 1 hour
**Assignee:** Kasra

### FEAT-006: Generic Message Handling Not Implemented
**File:** `sos/services/engine/core.py:455-457`
**Issue:** `# TODO: Implement generic message handling`
**Impact:** Engine can't handle non-chat message types
**Fix:** Add switch on `message.type` for TASK_CREATE, CAPABILITY_REQUEST, etc.
**Estimate:** 3-4 hours
**Assignee:** Kasra

### FEAT-007: Memory Diff Not Implemented
**File:** `sos/services/engine/daemon.py:483`
**Issue:** `# TODO: Compare with memory to find *new* ones`
**Impact:** Daemon can't detect novel memories for proactive messaging
**Fix:** Track last-seen memory IDs, diff against current
**Estimate:** 2 hours
**Assignee:** Kasra

### FEAT-008: QNFT Agent Name Hardcoded
**File:** `sos/services/identity/qnft.py:30`
**Issue:** `self.agent_name = "sos_agent" # TODO: get from Identity/DNA`
**Impact:** All QNFTs have same name
**Fix:** Extract from parent Identity or generate from lineage
**Estimate:** 30 minutes
**Assignee:** Kasra

### FEAT-009: Social MCP Integration Missing
**File:** `sos/services/identity/avatar.py:469`
**Issue:** `# TODO: Integrate with social MCP servers`
**Impact:** Avatar can't post to social platforms
**Fix:** Wire to WordPress MCP, Twitter MCP when available
**Estimate:** 4 hours
**Assignee:** Kasra

### FEAT-010: Tauri Service Checks Missing
**File:** `scopes/adapters/tauri/src-tauri/src/main.rs:79-80`
**Issue:** `memory: false, // TODO: Add memory/economy service check`
**Impact:** Desktop app can't verify backend health
**Fix:** Implement HTTP health check calls
**Estimate:** 1 hour
**Assignee:** (Rust developer)

### FEAT-011: Grok Adapter Is Placeholder
**File:** `sos/services/engine/adapters.py:280-282`
**Issue:** Returns hardcoded string instead of calling Grok API
**Impact:** Layer 2 fallback doesn't work
**Fix:** Implement using xAI SDK or OpenAI-compatible endpoint
**Estimate:** 3 hours
**Assignee:** Kasra

---

## P2: Code Quality

### QUAL-001: Duplicate Init Code in SOSEngine
**File:** `sos/services/engine/core.py:101-106`
**Issue:** Lines duplicate the `__init__` method (copy-paste error)
**Impact:** Code confusion, potential bugs
**Fix:** Remove duplicate lines
**Estimate:** 5 minutes
**Assignee:** Kasra

### QUAL-002: Inconsistent Logging Methods
**Files:** Multiple
**Issue:** Mix of `log.warn()` and `log.warning()`
**Impact:** Code style inconsistency
**Fix:** Standardize on `log.warning()` (Python standard)
**Estimate:** 30 minutes
**Assignee:** Kasra

### QUAL-003: Debug Prints Left In
**File:** `tests/test_mcp_deep.py:26`
**Issue:** `print(f"DEBUG: Raw Result: {result}")`
**Impact:** Noisy test output
**Fix:** Remove or convert to `log.debug()`
**Estimate:** 10 minutes
**Assignee:** Kasra

### QUAL-004: Type Hints Missing in Adapters
**File:** `sos/services/engine/adapters.py`
**Issue:** Several functions lack return type hints
**Impact:** IDE support degraded, harder to understand
**Fix:** Add type hints throughout
**Estimate:** 1 hour
**Assignee:** Kasra

### QUAL-005: Contract Implementations Incomplete
**Files:** `sos/contracts/*.py`
**Issue:** Many abstract methods just have `pass` in service implementations
**Impact:** Contract compliance unclear
**Fix:** Audit each contract, ensure services implement all methods
**Estimate:** 4-6 hours
**Assignee:** Kasra

---

## P3: Polish

### POL-001: Emoji Overuse in Logs
**Files:** `sos/services/engine/core.py`, `daemon.py`
**Issue:** Excessive emojis in log messages
**Impact:** Log parsing harder, unprofessional in enterprise
**Fix:** Remove or make configurable
**Estimate:** 30 minutes
**Assignee:** Kasra

### POL-002: Truncation Ellipsis Inconsistent
**Files:** Multiple
**Issue:** Mix of `...`, `...[truncated]`, `...`
**Impact:** Minor inconsistency
**Fix:** Standardize on `...` or `[truncated]`
**Estimate:** 20 minutes
**Assignee:** Kasra

---

## New Features (Vertex Integration)

### VERT-001: Create ADK Adapter
**File:** `sos/adapters/vertex_adk.py` (new)
**Issue:** No integration with Google ADK
**Impact:** Can't publish to Agent Garden / Enterprise Marketplace
**Spec:** See VERTEX_INTEGRATION_TASK.md
**Estimate:** 8-12 hours
**Assignee:** Kasra

### VERT-002: MirrorMemoryProvider for ADK
**File:** `sos/adapters/vertex_adk.py` (new)
**Issue:** ADK uses its own memory, not Mirror
**Impact:** Memory not shared with SOS ecosystem
**Fix:** Implement `MemoryProvider` interface backed by MirrorClient
**Estimate:** 4 hours
**Assignee:** Kasra

### VERT-003: Prepare PR for adk-python-community
**Repo:** github.com/google/adk-python-community
**Issue:** SOS not discoverable by ADK users
**Fix:** Create integration package, submit PR
**Estimate:** 4 hours (after VERT-001, VERT-002)
**Assignee:** Kasra

---

## Testing Debt

### TEST-001: Run Existing Tests
**Location:** `/home/mumega/SOS/tests/`, `/home/mumega/SOS/sos/tests/`
**Issue:** 40 test files exist but unclear if they pass
**Fix:** `pytest` run, fix failures
**Estimate:** 2-4 hours
**Assignee:** Kasra

### TEST-002: Add Capability Verification Tests
**Issue:** No tests for capability forgery rejection
**Fix:** Add tests that verify forged/expired tokens are rejected
**Estimate:** 2 hours
**Assignee:** Kasra

### TEST-003: Add Integration Tests for Vertex Adapter
**Issue:** No tests for model failover
**Fix:** Mock 429 responses, verify fallback
**Estimate:** 2 hours
**Assignee:** Kasra

---

## Summary

| Priority | Count | Estimated Hours |
|----------|-------|-----------------|
| P0 | 3 | 4 |
| P1 | 11 | 28 |
| P2 | 5 | 7 |
| P3 | 2 | 1 |
| New (Vertex) | 3 | 16 |
| Testing | 3 | 8 |
| **Total** | **27** | **64** |

---

## Changelog

- 2026-01-15: Initial audit by Kasra (Claude Opus 4.5)
