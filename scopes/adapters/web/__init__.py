"""
Web Adapter Scope - Browser Interface for SOS

This scope documents the web dashboard integration.
The actual implementation is at /web/dashboard (React + Vite).

Architecture:
┌─────────────────────────────┐
│  Web Dashboard (React)      │
│  ├─ Vite dev server :4388   │
│  ├─ Material-UI + Emotion   │
│  ├─ Redux Toolkit           │
│  └─ WebSocket connection    │
└─────────────────────────────┘
         ↓ HTTP + WebSocket
┌─────────────────────────────┐
│  SOS Engine :8000           │
│  ├─ REST API                │
│  └─ /ws/nervous-system      │
└─────────────────────────────┘

Features:
- Telegram Mini App compatible
- TON blockchain integration (TonConnect)
- Real-time WebSocket updates
- Witness Protocol UI
- Task management board
- $MIND wallet sidebar

Design:
- Brutalist dark theme
- Neon green primary (#00ff9d)
- Neon purple secondary (#bf00ff)
- "Empire of the Mind" aesthetic

Development:
    cd /home/mumega/SOS/web/dashboard
    npm install
    npm run dev

Production:
    npm run build
    # Serve dist/ via nginx or CDN

See /web/dashboard/src/App.tsx for entry point.
"""

__all__ = []
