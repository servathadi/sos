# Deployment Scope: The Road

## Philosophy
The environment changes, but the car remains the same.

## Components
*   **Local (`scopes/deployment/local`):**
    *   **"The Garage" / "Iran Mesh"**
    *   Docker Compose for single-node.
    *   Local LLM (Ollama) support.
    *   Offline-capable (NIN mode).
*   **Cloud (`scopes/deployment/cloud`):**
    *   **"The Supercharger Network" / "Enterprise"**
    *   Kubernetes / Cloudflare Workers.
    *   High availability, global reach.
    *   Centralized Mirror access.

## Rule of Environment
Configuration defines the road (Env Vars), but the engine drives the same way.
