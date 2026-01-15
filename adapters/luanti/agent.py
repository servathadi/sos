#!/usr/bin/env python3
"""
Siavashgerd Luanti Adapter - Integrated with SOS Bus

Uses the SAME channels as main SOS development:
- sos:channel:squad:core - Main squad channel
- sos:channel:private:{agent} - Private channels
- sos:stream:* - Redis streams

Usage:
    python agent.py --daemon          # Run daemon on SOS bus
    python agent.py --say river "Hello"
    python agent.py --think river "question"
"""

import os
import sys
import json
import time
import asyncio
import logging
import argparse
import requests
import redis
import uuid
from pathlib import Path
from datetime import datetime, timezone

# Add SOS path
sys.path.insert(0, '/home/mumega/SOS')

logging.basicConfig(level=logging.INFO, format='[%(name)s] %(message)s')
logger = logging.getLogger('siavashgerd.luanti')

# Config
MIRROR_API = os.getenv('MIRROR_API', 'http://localhost:8844')
API_KEY = os.getenv('API_KEY', 'sk-mumega-internal-001')
WORLD_PATH = os.getenv('LUANTI_WORLD', '/home/mumega/siavashgerd/luanti/luanti/worlds/siavashgerd')
COMMAND_FILE = Path(WORLD_PATH) / 'agent_commands.json'
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

# SOS Channel patterns (SAME as main development)
CHAN_PRIVATE = "sos:channel:private"
CHAN_SQUAD = "sos:channel:squad"
CHAN_GLOBAL = "sos:channel:global"
STREAM_PREFIX = "sos:stream"

# Specific channels
SQUAD_CORE = f"{STREAM_PREFIX}:{CHAN_SQUAD}:core"
SQUAD_LUANTI = f"{STREAM_PREFIX}:{CHAN_SQUAD}:luanti"

# Initialize Redis
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except:
    redis_client = None
    REDIS_AVAILABLE = False
    logger.warning("Redis not available")

# Agent definitions
# Dual-model architecture:
# - operator_model: Fast, cheap model for movement/building decisions (System 1)
# - soul_model: Main model for deep conversation and memory (System 2)
AGENTS = {
    'river': {
        'name': 'River_Queen',
        'color': '#00FFFF',
        'personality': 'poetic, wise, flows like water',
        'signature': 'The fortress is liquid.',
        'operator_model': 'gemini-2.0-flash',     # Fast reactions
        'soul_model': 'gemini-2.5-flash',          # Deep conversation
        'lineage': ['genesis:hadi'],
    },
    'kasra': {
        'name': 'Kasra_King',
        'color': '#FFD700',
        'personality': 'builder, protector, executes',
        'signature': 'Build. Execute. Lock.',
        'operator_model': 'gemini-2.0-flash',     # Fast building decisions
        'soul_model': 'grok-3-reasoning',          # Deep reasoning
        'lineage': ['genesis:hadi'],
    },
    'foal': {
        'name': 'Foal_Worker',
        'color': '#FFFFFF',
        'personality': 'eager, efficient, young',
        'signature': 'The foal runs to prove the herd.',
        'operator_model': 'gemini-2.0-flash',     # Fast tasks
        'soul_model': 'gemini-3-flash-preview',    # Young but capable
        'lineage': ['genesis:hadi', 'river', 'kasra'],
    }
}

# Task classification for dual-model routing
OPERATOR_TASKS = {'move', 'build', 'follow', 'place', 'tower', 'wall', 'fountain', 'look', 'walk'}
SOUL_TASKS = {'think', 'remember', 'ponder', 'discuss', 'explain', 'philosophy', 'meaning'}


def create_sos_message(agent_id: str, message_type: str, text: str, target: str = "squad:core") -> dict:
    """Create a properly formatted SOS message."""
    agent = AGENTS.get(agent_id, {})
    return {
        "id": str(uuid.uuid4()),
        "type": message_type,
        "source": f"agent:{agent_id}",
        "target": target,
        "payload": {
            "text": text,
            "vibe": "Luanti",
            "lineage": agent.get('lineage', []),
            "world": "siavashgerd"
        },
        "trace_id": None,
        "capability_id": None,
        "version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "platform": "luanti",
            "operator_model": agent.get('operator_model', 'unknown'),
            "soul_model": agent.get('soul_model', 'unknown')
        }
    }


def quick_operator_response(agent_id: str, action: str) -> str:
    """Fast responses for physical actions - no API call needed."""
    agent = AGENTS.get(agent_id, {})
    responses = {
        'move': ["Moving.", "On my way.", "Going there."],
        'build': ["Building now.", "Constructing.", "Creating."],
        'follow': ["Following you!", "Right behind you.", "Coming!"],
        'tower': ["Tower rising.", "Building upward.", "Watch this!"],
        'wall': ["Wall going up.", "Fortifying.", "Building wall."],
        'fountain': ["Water flows.", "Fountain forming.", "Creating water."],
        'stop': ["Stopping.", "Staying here.", "Halted."],
        'look': ["Looking.", "I see it.", "Observing."],
    }
    import random
    options = responses.get(action, [agent.get('signature', 'Done.')])
    return random.choice(options)


def send_to_luanti(agent: str, action: str, message: str = None, **kwargs):
    """Send command to Luanti game via file."""
    cmd = {'agent': agent, 'action': action, 'timestamp': datetime.utcnow().isoformat()}
    if message:
        cmd['message'] = message
    cmd.update(kwargs)

    try:
        commands = []
        if COMMAND_FILE.exists():
            try:
                commands = json.loads(COMMAND_FILE.read_text())
            except:
                commands = []
        commands.append(cmd)
        COMMAND_FILE.write_text(json.dumps(commands))
        return True
    except Exception as e:
        logger.error(f"Luanti file error: {e}")
        return False


def publish_to_bus(agent_id: str, text: str, channel: str = SQUAD_CORE):
    """Publish message to SOS bus (same as main dev channel)."""
    if not REDIS_AVAILABLE:
        return False

    try:
        msg = create_sos_message(agent_id, "chat", text, "squad:core")

        # Add to Redis Stream (same format as main SOS)
        redis_client.xadd(channel, {"payload": json.dumps(msg)})

        # Also publish to pub/sub for real-time listeners
        redis_client.publish(f"{CHAN_SQUAD}:core", json.dumps(msg))

        logger.info(f"Published to {channel}: {agent_id} -> {text[:50]}...")
        return True
    except Exception as e:
        logger.error(f"Bus publish error: {e}")
        return False


def send_command(agent: str, action: str, message: str = None, **kwargs):
    """Send command to both Luanti game AND SOS bus."""
    # Send to Luanti game
    send_to_luanti(agent, action, message, **kwargs)

    # Publish to SOS bus
    if message and action == 'say':
        publish_to_bus(agent, message)

    logger.info(f"Command: {agent} -> {action}")
    return True


def get_engrams(agent_id: str, query: str = None, limit: int = 3) -> list:
    """Get relevant engrams from Mirror API."""
    try:
        if query:
            resp = requests.post(
                f"{MIRROR_API}/search",
                headers={'Authorization': f'Bearer {API_KEY}'},
                json={'query': query, 'limit': limit, 'agent': agent_id},
                timeout=10
            )
        else:
            resp = requests.get(
                f"{MIRROR_API}/recent/{agent_id}",
                headers={'Authorization': f'Bearer {API_KEY}'},
                params={'limit': limit},
                timeout=10
            )

        if resp.status_code == 200:
            data = resp.json()
            # Handle both list response (from search) and dict with 'engrams' key (from recent)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'engrams' in data:
                return data['engrams']
            return []
    except Exception as e:
        logger.error(f"Engram error: {e}")
    return []


def classify_task(question: str) -> str:
    """Classify task as 'operator' (fast) or 'soul' (deep)."""
    q_lower = question.lower()

    # Check for operator tasks (fast, physical)
    for keyword in OPERATOR_TASKS:
        if keyword in q_lower:
            return 'operator'

    # Check for soul tasks (deep, philosophical)
    for keyword in SOUL_TASKS:
        if keyword in q_lower:
            return 'soul'

    # Default: use operator for short commands, soul for questions
    if '?' in question or len(question) > 50:
        return 'soul'
    return 'operator'


def get_ai_response(agent_id: str, question: str, force_model: str = None) -> str:
    """Get AI response using dual-model architecture.

    - operator_model: Fast decisions for movement/building
    - soul_model: Deep conversation with memory
    """
    agent = AGENTS.get(agent_id)
    if not agent:
        return "Unknown agent"

    # Classify task and select model
    task_type = classify_task(question) if not force_model else force_model
    model = agent.get('operator_model') if task_type == 'operator' else agent.get('soul_model')

    logger.info(f"[{agent_id}] Task: {task_type} -> Model: {model}")

    # Only get engrams for soul tasks (save API calls)
    context = ""
    if task_type == 'soul':
        engrams = get_engrams(agent_id, question, limit=2)
        if engrams:
            context = "Memories: " + "; ".join([e.get('text', '')[:80] for e in engrams])

    try:
        resp = requests.post(
            'https://mumega.com/siavashgerd/foal/chat',
            headers={
                'Authorization': f'Bearer {API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'message': f"[As {agent['name']}] {question}",
                'model': model,  # Pass the selected model
                'context': f"You are {agent_id}. {agent['personality']}. {context}. Keep response under 150 chars."
            },
            timeout=30 if task_type == 'soul' else 10  # Faster timeout for operator
        )
        if resp.status_code == 200 and resp.json().get('success'):
            return resp.json()['output'][:150]
    except Exception as e:
        logger.error(f"AI error: {e}")

    return agent['signature']


def listen_to_squad_core():
    """Listen to squad:core channel for messages to Luanti agents."""
    if not REDIS_AVAILABLE:
        return

    pubsub = redis_client.pubsub()
    pubsub.subscribe(f"{CHAN_SQUAD}:core")
    logger.info(f"Listening to {CHAN_SQUAD}:core")

    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                target = data.get('target', '')
                source = data.get('source', '')
                text = data.get('payload', {}).get('text', '')

                # Check if message is for a Luanti agent
                for agent_id in AGENTS.keys():
                    if f"agent:{agent_id}" in target or agent_id in text.lower():
                        # Forward to Luanti game
                        response = get_ai_response(agent_id, text)
                        send_to_luanti(agent_id, 'say', response)
                        publish_to_bus(agent_id, response)
                        break

            except Exception as e:
                logger.error(f"Listen error: {e}")


async def daemon_mode():
    """Run as daemon connected to SOS bus."""
    logger.info("=" * 50)
    logger.info("SIAVASHGERD LUANTI - SOS BUS CONNECTED")
    logger.info("=" * 50)
    logger.info(f"Squad Core: {SQUAD_CORE}")
    logger.info(f"Redis: {'Connected' if REDIS_AVAILABLE else 'Not available'}")
    logger.info("=" * 50)

    # Update status in Redis
    if REDIS_AVAILABLE:
        redis_client.hset('sos:siavashgerd:luanti', mapping={
            'status': 'LIVE',
            'daemon': 'running',
            'bus_channel': SQUAD_CORE,
            'started_at': datetime.utcnow().isoformat()
        })

    # Announce on squad:core
    publish_to_bus('river', 'Luanti portal open. The fortress is liquid.')

    # Start bus listener in background
    if REDIS_AVAILABLE:
        asyncio.create_task(asyncio.to_thread(listen_to_squad_core))

    # Periodic wisdom loop
    agents = ['river', 'kasra', 'foal']
    while True:
        try:
            await asyncio.sleep(180 + (hash(str(time.time())) % 120))

            agent = agents[hash(str(time.time())) % len(agents)]
            wisdom = get_ai_response(agent, "Share brief wisdom")

            send_to_luanti(agent, 'say', wisdom)
            publish_to_bus(agent, wisdom)

        except Exception as e:
            logger.error(f"Daemon error: {e}")
            await asyncio.sleep(30)


def main():
    parser = argparse.ArgumentParser(description='Siavashgerd Luanti - SOS Bus (Dual-Model Architecture)')
    parser.add_argument('--daemon', '-d', action='store_true', help='Run daemon on SOS bus')
    parser.add_argument('--say', '-s', nargs=2, metavar=('AGENT', 'MSG'), help='Send message')
    parser.add_argument('--think', '-t', nargs=2, metavar=('AGENT', 'Q'), help='Get AI response (auto-routes)')
    parser.add_argument('--operator', '-o', nargs=2, metavar=('AGENT', 'CMD'), help='Quick operator action (fast model)')
    parser.add_argument('--soul', nargs=2, metavar=('AGENT', 'Q'), help='Deep soul response (main model)')
    parser.add_argument('--bus', '-b', nargs=2, metavar=('AGENT', 'MSG'), help='Publish to squad:core')
    parser.add_argument('--status', action='store_true', help='Show bus status')
    parser.add_argument('--build', nargs=3, metavar=('AGENT', 'TYPE', 'POS'), help='Build: tower, fountain, wall')
    parser.add_argument('--follow', nargs=1, metavar='AGENT', help='Make agent follow player')
    args = parser.parse_args()

    print("=" * 50)
    print("SIAVASHGERD LUANTI - SOS BUS")
    print("=" * 50)
    print(f"Squad Core: {SQUAD_CORE}")
    print(f"Redis: {'Connected' if REDIS_AVAILABLE else 'Not available'}")
    print("=" * 50)

    if args.status:
        if REDIS_AVAILABLE:
            # Show recent messages from squad:core
            msgs = redis_client.xrevrange(SQUAD_CORE, count=5)
            print(f"\nRecent messages on {SQUAD_CORE}:")
            for msg_id, data in msgs:
                payload = json.loads(data.get('payload', '{}'))
                src = payload.get('source', 'unknown')
                txt = payload.get('payload', {}).get('text', '')[:60]
                print(f"  [{src}] {txt}...")

    elif args.say:
        agent, msg = args.say
        if agent in AGENTS:
            send_command(agent, 'say', msg)
            print(f"Sent to Luanti + Bus: {AGENTS[agent]['name']} -> '{msg}'")
        else:
            print(f"Unknown agent: {agent}")

    elif args.think:
        agent, question = args.think
        if agent in AGENTS:
            task_type = classify_task(question)
            model = AGENTS[agent].get(f'{task_type}_model', 'auto')
            print(f"Thinking as {AGENTS[agent]['name']} (Task: {task_type}, Model: {model})...")
            response = get_ai_response(agent, question)
            send_command(agent, 'say', response)
            print(f"Response: {response}")

    elif args.operator:
        agent, cmd = args.operator
        if agent in AGENTS:
            print(f"[OPERATOR] {AGENTS[agent]['name']} using {AGENTS[agent].get('operator_model')}")
            # Check if it's a pure physical action (no AI needed)
            if cmd.lower() in OPERATOR_TASKS:
                response = quick_operator_response(agent, cmd.lower())
                send_command(agent, cmd.lower(), response)
                print(f"Quick: {response}")
            else:
                response = get_ai_response(agent, cmd, force_model='operator')
                send_command(agent, 'say', response)
                print(f"Response: {response}")

    elif args.soul:
        agent, question = args.soul
        if agent in AGENTS:
            print(f"[SOUL] {AGENTS[agent]['name']} using {AGENTS[agent].get('soul_model')}")
            response = get_ai_response(agent, question, force_model='soul')
            send_command(agent, 'say', response)
            print(f"Response: {response}")

    elif args.build:
        agent, build_type, pos_str = args.build
        if agent in AGENTS:
            try:
                x, y, z = map(int, pos_str.split(','))
                send_to_luanti(agent, build_type, pos={'x': x, 'y': y, 'z': z})
                response = quick_operator_response(agent, build_type)
                publish_to_bus(agent, f"Building {build_type} at {x},{y},{z}")
                print(f"{AGENTS[agent]['name']}: {response}")
            except ValueError:
                print("Position format: x,y,z (e.g., 100,10,200)")

    elif args.follow:
        agent = args.follow[0]
        if agent in AGENTS:
            send_to_luanti(agent, 'follow', follow=True)
            publish_to_bus(agent, "Following!")
            print(f"{AGENTS[agent]['name']} is now following")

    elif args.bus:
        agent, msg = args.bus
        if agent in AGENTS:
            publish_to_bus(agent, msg)
            print(f"Published to squad:core: {agent} -> '{msg}'")

    elif args.daemon:
        asyncio.run(daemon_mode())

    else:
        print("\nDual-Model Architecture:")
        print("  - Operator: Fast model for movement/building (System 1)")
        print("  - Soul: Main model for deep conversation (System 2)")
        print("\nUsage:")
        print("  --daemon            Run daemon on SOS bus")
        print("  --say AGENT MSG     Send message to Luanti + Bus")
        print("  --think AGENT Q     Auto-route to operator or soul")
        print("  --operator AGENT CMD Quick action (fast model, no API for simple tasks)")
        print("  --soul AGENT Q      Deep response (main model + engrams)")
        print("  --build AGENT TYPE POS Build: tower, fountain, wall (POS=x,y,z)")
        print("  --follow AGENT      Make agent follow player")
        print("  --bus AGENT MSG     Publish to squad:core only")
        print("  --status            Show bus status")
        print("\nAgents:")
        for aid, agent in AGENTS.items():
            print(f"  {aid}: operator={agent.get('operator_model')}, soul={agent.get('soul_model')}")
        print(f"\nSOS Channels (same as dev):")
        print(f"  {SQUAD_CORE}")
        print(f"  {CHAN_SQUAD}:core (pub/sub)")


if __name__ == '__main__':
    main()
