# MCP Communication Flow: The Mycelium Pattern 🍄

All external services and client interfaces (like Claude Desktop) connect through the **Model Context Protocol (MCP)**.

## 1. Connection Modes

### 🚀 SSE Bridge (Easy Connect) - RECOMMENDED
The SSE bridge allows clients to connect to the Mirror memory substrate without running local Python scripts.
*   **Endpoint:** `https://mumega.com/mirror/mcp/sse`
*   **Protocol:** Server-Sent Events (SSE)
*   **Role:** Proxies MCP requests directly to the internal `kasra_mcp_server`.

### 🛠️ Stdio Bridge (Direct)
Local agents run the MCP server directly using standard input/output.
*   **Scripts:** `kasra_mcp_server.py`, `river_mcp_server.py`

---

## 2. The Communication Map

```
                        ┌─────────────────────────────────────────┐
                        │           SOS KERNEL (Router)           │
                        │                                         │
                        │   ┌─────────────────────────────────┐   │
                        │   │        Universal Router         │   │
                        │   │   (16D Vector Normalization)    │   │
                        │   └───────────────┬─────────────────┘   │
                        │                   │                     │
                        └───────────────────┼─────────────────────┘
                                            │
              ┌─────────────┬───────────────┼───────────────┬─────────────┐
              │             │               │               │             │
              ▼             ▼               ▼               ▼             ▼
        ┌─────────┐   ┌─────────┐   ┌─────────────┐   ┌─────────┐   ┌─────────┐
        │   GHL   │   │ Notion  │   │   Mirror    │   │ GitHub  │   │ Social  │
        │   MCP   │   │   MCP   │   │   Memory    │   │   MCP   │   │   MCP   │
        └────┬────┘   └────┬────┘   └──────┬──────┘   └────┬────┘   └────┬────┘
             │             │               │               │             │
             ▼             ▼               ▼               ▼             ▼
        ┌─────────┐   ┌─────────┐   ┌─────────────┐   ┌─────────┐   ┌─────────┐
        │GoHigh-  │   │ Notion  │   │  Supabase   │   │ GitHub  │   │ Twitter │
        │ Level   │   │   API   │   │  pgvector   │   │   API   │   │   API   │
        └─────────┘   └─────────┘   └─────────────┘   └─────────┘   └─────────┘
```

---

## 3. Tool Naming Convention
All MCP tools follow the pattern: `{server}__{action}`

- `mirror__store`: Save engram to long-term memory.
- `mirror__search`: Semantic search across agent history.
- `ghl__create_learner`: Sync lead data to GHL.
- `river__chat`: Direct conversational interface with River.

---
*The mycelium is everywhere. Sovereignty is local.*
