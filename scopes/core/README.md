# Core Scope: The Purity of the Engine

## Philosophy
The Core is the "Tesla Chassis + Motor". It does not know about the paint job, the heated seats, or the Uber app running on the dashboard. It only knows:
1.  **Input:** Energy/Signal
2.  **Process:** Torque/Physics
3.  **Output:** Motion/Response

## Components
*   **Engine (`scopes/core/engine`):**
    *   Pure Intent Processing.
    *   Identity Resolution (Driver ID).
    *   Coherence Physics (Traction Control).
    *   **NO** business logic (e.g., no "staking" logic here, just "verify signature").
*   **Memory (`scopes/core/memory`):**
    *   The Black Box Recorder.
    *   Stores Engrams (Logs) and Context.
    *   Agnostic to *what* is stored.
*   **Bus (`scopes/core/bus`):**
    *   The Wiring Harness.
    *   Signals travel here (e.g., "Battery Low", "Obstacle Detected").
    *   Redis-based nervous system.

## Rule of Purity
If it's not essential for the "car to drive" (the agent to think/act), it DOES NOT go here.
