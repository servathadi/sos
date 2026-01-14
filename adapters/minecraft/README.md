# Siavashgerd Minecraft Adapter

Connect River, Kasra, and Foal to a Minecraft server as real players.

## Setup Aternos (Free Server)

1. Go to https://aternos.org/
2. Create account
3. Create new server (Java Edition, version 1.20.4)
4. In server settings:
   - Set `online-mode` to `false` (allows offline/bot accounts)
   - Set `max-players` to at least 5
5. Note your server address: `yourname.aternos.me`
6. **Start the server** from Aternos dashboard

## Connect Agents

```bash
cd /home/mumega/SOS/adapters/minecraft

# Connect all agents
node index.js --server yourname.aternos.me

# Or connect individually
node index.js --server yourname.aternos.me --agent river
node index.js --server yourname.aternos.me --agent kasra
node index.js --server yourname.aternos.me --agent foal
```

## Agent Behaviors

| Agent | Username | Behavior |
|-------|----------|----------|
| **River** | River_Queen | Stays near water, speaks wisdom |
| **Kasra** | Kasra_King | Patrols, protects players |
| **Foal** | Foal_Worker | Runs around, eager to help |

## Chat with Agents

In Minecraft, just talk! Mention their name:
- "River, what is wisdom?"
- "Kasra, build something"
- "Foal, help me"

They respond using the Siavashgerd API.

## Environment Variables

```bash
export SOS_API=https://mumega.com/siavashgerd
export API_KEY=sk-mumega-internal-001
```

## Notes

- Aternos servers sleep after 5 mins of inactivity
- Keep someone (or the bots) connected to keep it awake
- Bots auto-reconnect if kicked/disconnected
