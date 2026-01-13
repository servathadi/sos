"""
Tauri Adapter Scope - Desktop Shell for SOS (Shabrang)

This scope implements the Tauri desktop application.
Wraps the web dashboard with native desktop capabilities.

Architecture: Sidecar Pattern
┌─────────────────────────────┐
│  Tauri App (Desktop Shell)  │
│  ├─ React Dashboard UI      │
│  └─ Rust Backend (IPC)      │
└─────────────────────────────┘
         ↓ HTTP + WebSocket
┌─────────────────────────────┐
│  SOS Sidecar (Docker)       │
│  ├─ Engine :8000            │
│  ├─ Memory :8001            │
│  ├─ Economy :8002           │
│  └─ Redis :6379             │
└─────────────────────────────┘

Features:
- Native desktop application (Windows, macOS, Linux)
- System tray presence
- Auto-launch SOS services
- Local file system access
- Offline-first operation

Tauri Commands (Rust → TypeScript):
- start_sos: Launch Docker compose
- stop_sos: Stop all services
- get_status: Health check
- open_logs: View service logs

Build:
    cd scopes/adapters/tauri
    npm install
    npm run tauri build

See /web/dashboard for the React UI source.
"""

__all__ = []
