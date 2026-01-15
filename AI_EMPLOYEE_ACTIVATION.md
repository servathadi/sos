# AI Employee Activation Guide

**Status:** 60% Ready
**Last Audit:** 2026-01-15
**Owner:** Kasra (Claude)

---

## Overview

SOS is designed to function as an **AI Employee** - an autonomous agent that:
- Runs 24/7 without prompting
- Picks up tasks from a queue
- Executes work using LLM models
- Reports results back to the user
- Tracks reputation and earns $MIND

This document tracks the activation status of each component.

---

## Component Readiness

### Fully Implemented (100%)

| Component | File | Description |
|-----------|------|-------------|
| **SOSDaemon** | `sos/services/engine/daemon.py` | 5 concurrent loops (heartbeat, pulse, dream, maintenance, telegram) |
| **Task Auto-Spawn** | `sos/services/engine/task_manager.py` | Creates tasks from complex chat requests |
| **Task Storage** | `~/.sos/tasks/` | JSON file-based task repository |
| **AsyncWorker** | `sos/services/execution/worker.py` | Redis queue consumer framework |
| **Foal Agent** | `sos/agents/foal/agent.py` | Free model executor (Gemini Flash, Grok, OpenRouter) |
| **Worker Registry** | `scopes/features/swarm/workers.py` | Reputation tracking with tier system |
| **Model Adapters** | `sos/services/engine/adapters.py` | 17+ models with automatic failover |
| **Bounty System** | `scopes/features/economy/bounties.py` | Task marketplace with lifecycle |
| **Telegram Adapter** | `sos/adapters/telegram.py` | Chat interface for task assignment |

### Missing Components (0%)

| Component | Status | Required Work |
|-----------|--------|---------------|
| **Task Claiming Loop** | Missing | Periodic poll of pending tasks, submit to worker queue |
| **Auto-Start Worker** | Missing | Launch AsyncWorker on engine startup |
| **Result Submission** | Missing | `/tasks/{task_id}/submit` endpoint |
| **Reporting Loop** | Missing | Notify user via Telegram on task completion |

---

## Architecture Gap

```
USER
  | (Telegram/REST)
  v
ADAPTER -----------------------> TASK STORAGE
  |                                   |
  v                                   |
ENGINE (SOSEngine)                    |
  |                                   |
  v                                   v
DAEMON (SOSDaemon)              ~/.sos/tasks/
  |                                   |
  | [MISSING: task_claiming_loop]     |
  |                                   |
  v                                   v
REDIS QUEUE <-------- [GAP] -------- PENDING TASKS
  |
  v
WORKER (AsyncWorker)
  |
  | [MISSING: auto-start]
  v
FOAL AGENT (execution)
  |
  | [MISSING: result submission]
  v
USER NOTIFICATION
```

---

## Daemon Loops (Running)

The SOSDaemon runs 5 concurrent loops:

| Loop | Interval | Purpose |
|------|----------|---------|
| Heartbeat | 5 min | Broadcast status to Redis nervous system |
| Pulse | 1 min | Witness Redis activity via SwarmObserver |
| Dream | 30 min | Synthesize insights during idle time |
| Maintenance | 24 hr | Prune soul, scan projects, track memories |
| Telegram | Real-time | Handle chat commands |

---

## Activation Checklist

### Phase 1: Task Claiming Loop (30 min)

Add to `sos/services/engine/daemon.py`:

```python
async def _task_claiming_loop(self):
    """Poll pending tasks and submit to worker queue."""
    while self.running:
        try:
            tasks = await self.swarm.list_pending_tasks()
            for task in tasks:
                if task.get("status") == "pending":
                    # Submit to Redis queue
                    await self.bus._redis.xadd(
                        "sos:queue:global",
                        {
                            "task_id": task["id"],
                            "payload": json.dumps(task)
                        }
                    )
                    # Mark as claimed
                    await self.swarm.claim_task(task["id"])
        except Exception as e:
            log.error(f"Task claiming error: {e}")
        await asyncio.sleep(60)
```

### Phase 2: Worker Auto-Start (10 min)

Add to `sos/services/engine/app.py` startup:

```python
from sos.services.execution.worker import get_worker

async def startup_event():
    await engine.initialize_soul()
    await start_daemon()

    # NEW: Start worker
    worker = get_worker()
    asyncio.create_task(worker.start())
```

### Phase 3: Task Executor Handler (30 min)

Register in AsyncWorker:

```python
async def execute_task(payload: dict) -> dict:
    task = json.loads(payload["payload"])

    # Use Foal Agent for execution
    foal = FoalAgent()
    result = await foal.execute(
        task["description"],
        context=task.get("context")
    )

    return {
        "task_id": task["id"],
        "output": result["output"],
        "model": result["model"],
        "status": "completed"
    }

worker.register("task", execute_task)
```

### Phase 4: Result Submission Endpoint (30 min)

Add to `sos/services/engine/app.py`:

```python
@app.post("/tasks/{task_id}/submit")
async def submit_task_result(task_id: str, result: dict):
    # Store result
    task_path = Path.home() / ".sos" / "tasks" / f"{task_id}.json"
    if task_path.exists():
        task = json.loads(task_path.read_text())
        task["status"] = "completed"
        task["result"] = result
        task["completed_at"] = datetime.now(timezone.utc).isoformat()
        task_path.write_text(json.dumps(task, indent=2))

    return {"status": "ok", "task_id": task_id}
```

### Phase 5: Reporting Loop (30 min)

Add to `sos/services/engine/daemon.py`:

```python
async def _report_results_loop(self):
    """Notify user of completed tasks."""
    while self.running:
        try:
            tasks_dir = Path.home() / ".sos" / "tasks"
            for task_file in tasks_dir.glob("*.json"):
                task = json.loads(task_file.read_text())
                if task.get("status") == "completed" and not task.get("reported"):
                    # Send Telegram notification
                    await self.telegram.send_message(
                        f"Task completed: {task['title']}\n"
                        f"Result: {task.get('result', {}).get('output', 'N/A')[:500]}"
                    )
                    task["reported"] = True
                    task_file.write_text(json.dumps(task, indent=2))
        except Exception as e:
            log.error(f"Reporting error: {e}")
        await asyncio.sleep(300)
```

---

## Environment Variables

```bash
# Task System
SOS_TASK_POLLING_INTERVAL=60        # Seconds between task polls
SOS_AUTO_CLAIM_ENABLED=true         # Enable automatic task claiming
SOS_AUTO_EXECUTE_ENABLED=true       # Enable automatic execution
SOS_AUTO_REPORT_ENABLED=true        # Enable automatic reporting

# Worker
SOS_WORKER_QUEUE=sos:queue:global   # Redis queue name
SOS_WORKER_TIMEOUT=300              # Task timeout in seconds

# Models (for Foal Agent)
SOS_PREFERRED_MODEL=gemini-flash    # Default execution model
GEMINI_API_KEY=                     # Required
XAI_API_KEY=                        # Optional (Grok fallback)
OPENROUTER_API_KEY=                 # Optional (free fallback)
```

---

## Testing

### Manual Test Flow

1. Start services:
   ```bash
   docker-compose up -d redis
   python -m sos.services.engine.app
   ```

2. Create a task via chat:
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Build a Python script that lists files"}'
   ```

3. Check pending tasks:
   ```bash
   curl http://localhost:8000/tasks
   ```

4. Verify task claimed and executed (check logs)

5. Check task result:
   ```bash
   cat ~/.sos/tasks/<task_id>.json
   ```

### E2E Test

```bash
PYTHONPATH=. python tests/test_ai_employee_e2e.py
```

---

## Estimated Activation Time

| Phase | Task | Time |
|-------|------|------|
| 1 | Task claiming loop | 30 min |
| 2 | Worker auto-start | 10 min |
| 3 | Task executor handler | 30 min |
| 4 | Result submission endpoint | 30 min |
| 5 | Reporting loop | 30 min |
| 6 | Telegram notifications | 20 min |
| 7 | Environment config | 10 min |
| 8 | Testing | 1-2 hr |
| **Total** | | **4-6 hours** |

---

## Success Criteria

The AI Employee is activated when:

- [ ] Daemon runs 24/7 with task claiming loop
- [ ] Tasks auto-spawn from complex requests
- [ ] Pending tasks are claimed within 60 seconds
- [ ] Worker executes tasks using Foal Agent
- [ ] Results are stored in task JSON
- [ ] User receives Telegram notification on completion
- [ ] Worker reputation updates after task completion

---

## References

- [MIGRATION_TASKS.md](./MIGRATION_TASKS.md) - Phase history
- [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md) - Issue tracking
- [Daemon Code](./sos/services/engine/daemon.py) - SOSDaemon implementation
- [Worker Code](./sos/services/execution/worker.py) - AsyncWorker implementation
- [Foal Agent](./sos/agents/foal/agent.py) - Free model executor
