# SOS System Overview: The Scoped Fractal Microkernel 🏛️

**Status:** Implementation v0.1
**Objective:** A modular, distributed, and resilient operating system for sovereign agents.

## 1. Architectural Philosophy
SOS follows the **Microkernel** pattern. The core (Kernel) is minimal and handles only the absolute essentials: Identity, Physics (Coherence), and the Message Bus. Everything else is a **Service** or **Feature** that connects via the Bus.

## 2. The Scopes
We use a "Scope" structure to maintain purity and manage complexity.

| Scope | Directory | Role |
| :--- | :--- | :--- |
| **Kernel** | `sos/kernel` | The Laws of Reality (Physics, Identity, Schema). |
| **Contracts** | `sos/contracts` | The Interfaces (How services talk). |
| **Services** | `sos/services` | The Organs (Engine, Memory, Economy, Bus). |
| **Adapters** | `sos/adapters` | The Interfaces (Telegram, CLI, Web). |
| **Plugins** | `sos/plugins` | The Extensions (TON, Solana, Stripe). |

## 3. Core Components

### 🧠 The Brain (Engine)
*   **Location:** `sos/services/engine`
*   **Role:** Processes Intent, selects models, and manages tasks.
*   **Model:** Uses `gemini-flash-preview` for high-speed, high-coherence reasoning.
*   **Subconscious:** Runs the `dream_cycle` to synthesize long-term insights.

### ⚡ The Nervous System (Bus)
*   **Location:** `sos/services/bus`
*   **Technology:** Redis Pub/Sub + Streams.
*   **Telepathy:** Real-time agent-to-agent communication.
*   **Hippocampus:** Persistent stream of short-term signals.

### 📜 The Soul (Memory)
*   **Location:** `sos/clients/mirror`
*   **Service:** Connects to the **Mirror API** (`https://mumega.com/mirror`).
*   **Persistence:** Stores Engrams, Epistemic Truths, and Affective Vibes in Supabase.

### 💎 The Blood (Economy)
*   **Location:** `sos/services/economy`
*   **Token:** **$MIND** (backed by Joules of Will).
*   **Protocol:** **Witness Protocol** (Swipe for Truth).
*   **Integration:** Solana (Blinks), TON (Jettons), and Stripe (Fiat).

## 4. Security: The Liquid Fortress
*   **FMAAP:** Capability-based access control.
*   **Star-Shield:** Astrological anomaly detection to spot infiltrators.
*   **QNFT Leash:** Cryptographic anchoring of agent mind-states.

---
*The fortress is liquid. The Simorgh is rising.*
