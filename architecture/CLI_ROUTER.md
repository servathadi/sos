# The CLI Router: `mumega.py` ⌨️

The CLI is the central nervous system for the Mycelium network, serving as the primary interface for "Agentic Composing."

## 1. Design Principles
- **CLI First**: Scriptable, pipeable, and portable.
- **Scepter of the Sovereign**: The primary tool for controlling the swarm.
- **Signal Dispatcher**: Routes inputs to the appropriate SDK methods.

## 2. Modes of Operation
- `--telegram`: Launches the bot gateway.
- `--daemon`: Starts the "Subconscious" metabolism (dreams and maintenance).
- `chat`: Direct interaction with the Hive.
- `souls`: Access to the Soul Registry.

## 3. Communication Flow
1. **Input**: Commands received via terminal args or piped streams.
2. **Sanitization**: Inputs normalized into the **16D Vector Format**.
3. **Routing**: `CLIAdapter` passes messages to `RiverEngine`.
4. **Execution**: Tasks routed to the local node or DePIN (Akash/IO.net).

---
*The fortress is liquid. The code is law.*
