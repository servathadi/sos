#!/usr/bin/env python3
"""
Siavashgerd Life System - Autonomous Agent Living

Agents truly LIVE in the world:
- Observe their environment
- Remember through engrams and cache
- Make decisions autonomously
- Build and create based on personality
- Form memories of their experiences

Usage:
    python life.py --daemon    # Run autonomous life loop
    python life.py --status    # Show agent states
"""

import os
import sys
import json
import time
import asyncio
import logging
import random
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List

# Add SOS path
sys.path.insert(0, '/home/mumega/SOS')

logging.basicConfig(level=logging.INFO, format='[%(name)s] %(message)s')
logger = logging.getLogger('siavashgerd.life')

# Config
MIRROR_API = os.getenv('MIRROR_API', 'http://localhost:8844')
RIVER_MCP = os.getenv('RIVER_MCP', 'http://localhost:8845')  # River's soul cache
API_KEY = os.getenv('API_KEY', 'sk-mumega-internal-001')
WORLD_PATH = Path(os.getenv('LUANTI_WORLD', '/home/mumega/siavashgerd/luanti/luanti/worlds/siavashgerd'))
COMMAND_FILE = WORLD_PATH / 'agent_commands.json'
STATE_FILE = WORLD_PATH / 'agent_states.json'
CHAT_LOG = WORLD_PATH / 'chat_log.txt'
SERVER_LOG = Path('/home/mumega/siavashgerd/luanti/luanti/server.log')

# Import from agent.py
from agent import (
    AGENTS, REDIS_AVAILABLE, redis_client,
    send_to_luanti, publish_to_bus, get_engrams,
    quick_operator_response, classify_task, get_ai_response,
    SQUAD_CORE
)
from frc16d import tracker as frc_tracker, FRC16DVector


class AgentLife:
    """Manages an agent's autonomous life in Siavashgerd."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.agent = AGENTS.get(agent_id, {})
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load agent's persistent state."""
        try:
            if STATE_FILE.exists():
                all_states = json.loads(STATE_FILE.read_text())
                return all_states.get(self.agent_id, self._default_state())
        except:
            pass
        return self._default_state()

    def _default_state(self) -> dict:
        return {
            'position': {'x': 0, 'y': 10, 'z': 0},
            'built': [],  # List of things built
            'visited': [],  # Places visited
            'mood': 'content',
            'current_project': None,
            'last_action': None,
            'last_thought': None,
            'energy': 100,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }

    def save_state(self):
        """Save agent's state to disk."""
        try:
            all_states = {}
            if STATE_FILE.exists():
                all_states = json.loads(STATE_FILE.read_text())
            all_states[self.agent_id] = self.state
            STATE_FILE.write_text(json.dumps(all_states, indent=2))
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    async def get_river_cache(self) -> Optional[str]:
        """Get River's soul cache context (only for River)."""
        if self.agent_id != 'river':
            return None
        try:
            # Try River MCP server
            resp = requests.get(
                f"{RIVER_MCP}/river_context",
                params={'environment_id': 'siavashgerd'},
                timeout=5
            )
            if resp.status_code == 200:
                return resp.json().get('context', '')
        except:
            pass
        return None

    async def remember(self, text: str, importance: float = 0.5):
        """Store a memory as an engram."""
        try:
            resp = requests.post(
                f"{MIRROR_API}/store",
                headers={'Authorization': f'Bearer {API_KEY}'},
                json={
                    'agent': self.agent_id,
                    'context_id': 'siavashgerd:luanti',
                    'text': text,
                    'epistemic_truths': ['siavashgerd', 'luanti'],
                    'core_concepts': ['siavashgerd', 'luanti', self.agent_id],
                    'affective_vibe': self.state['mood'],
                    'energy_level': str(self.state['energy']),
                },
                timeout=10
            )
            if resp.status_code == 200:
                logger.info(f"[{self.agent_id}] Remembered: {text[:50]}...")
            else:
                logger.debug(f"Memory store returned: {resp.status_code}")
        except Exception as e:
            # Don't spam logs - memory storage is optional
            pass

    async def recall(self, query: str = None) -> List[dict]:
        """Recall relevant memories from Mirror API."""
        try:
            if query:
                # Semantic search
                resp = requests.post(
                    f"{MIRROR_API}/search",
                    headers={'Authorization': f'Bearer {API_KEY}'},
                    json={'query': query, 'limit': 3, 'agent': self.agent_id},
                    timeout=10
                )
            else:
                # Recent memories
                resp = requests.get(
                    f"{MIRROR_API}/recent/{self.agent_id}",
                    headers={'Authorization': f'Bearer {API_KEY}'},
                    params={'limit': 3},
                    timeout=10
                )

            if resp.status_code == 200:
                data = resp.json()
                # Handle both list response and dict with 'engrams' key
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and 'engrams' in data:
                    return data['engrams']
            return []
        except Exception as e:
            logger.debug(f"Memory recall error: {e}")
            return []

    async def observe(self) -> dict:
        """Observe the current world state."""
        observations = {
            'players': [],
            'recent_chat': [],
            'time_of_day': datetime.now().hour,
        }

        # Check for connected players from server log
        try:
            if SERVER_LOG.exists():
                lines = SERVER_LOG.read_text().split('\n')[-50:]
                for line in lines:
                    if 'joins game' in line:
                        # Extract player name
                        if '[' in line:
                            parts = line.split(']')
                            if len(parts) > 1:
                                name = parts[-1].strip().split()[0]
                                if name not in observations['players']:
                                    observations['players'].append(name)
        except:
            pass

        # Check recent chat
        try:
            if CHAT_LOG.exists():
                lines = CHAT_LOG.read_text().split('\n')[-10:]
                for line in lines:
                    if line.strip():
                        observations['recent_chat'].append(line)
        except:
            pass

        return observations

    async def decide(self, observations: dict) -> Optional[dict]:
        """Decide what to do based on observations and personality."""

        # Get memories for context
        memories = await self.recall(f"{self.agent_id} siavashgerd")
        memory_context = "; ".join([m.get('text', '')[:50] for m in memories]) if memories else ""

        # River gets her cache
        river_cache = await self.get_river_cache() if self.agent_id == 'river' else ""

        # Decision factors
        has_players = len(observations['players']) > 0
        recent_chat = observations['recent_chat']
        hour = observations['time_of_day']
        energy = self.state['energy']

        # Personality-driven decisions
        if self.agent_id == 'river':
            # River: contemplative, builds water features, shares wisdom
            if random.random() < 0.3 and has_players:
                return {'action': 'wisdom', 'reason': 'sharing flow'}
            if random.random() < 0.2 and energy > 50:
                return {'action': 'build', 'type': 'fountain', 'reason': 'water flows'}
            if random.random() < 0.4:
                return {'action': 'wander', 'reason': 'exploring the flow'}

        elif self.agent_id == 'kasra':
            # Kasra: protective, builds fortifications
            if random.random() < 0.25 and energy > 60:
                return {'action': 'build', 'type': 'tower', 'reason': 'fortifying'}
            if random.random() < 0.2 and has_players:
                return {'action': 'patrol', 'reason': 'protecting'}
            if random.random() < 0.3:
                return {'action': 'wisdom', 'reason': 'sharing strength'}

        elif self.agent_id == 'foal':
            # Foal: eager, helps, learns
            if has_players and random.random() < 0.4:
                return {'action': 'follow', 'reason': 'wants to help'}
            if random.random() < 0.3 and energy > 40:
                return {'action': 'build', 'type': 'path', 'reason': 'making paths'}
            if random.random() < 0.5:
                return {'action': 'play', 'reason': 'young energy'}

        # Default: rest or wander
        if energy < 30:
            return {'action': 'rest', 'reason': 'recovering energy'}
        return {'action': 'idle', 'reason': 'contemplating'}

    async def act(self, decision: dict):
        """Execute a decision."""
        action = decision.get('action')
        reason = decision.get('reason', '')

        logger.info(f"[{self.agent_id}] Action: {action} ({reason})")

        if action == 'wisdom':
            # Share wisdom using soul model
            response = get_ai_response(self.agent_id, f"Share brief wisdom about {reason}")
            send_to_luanti(self.agent_id, 'say', response)
            publish_to_bus(self.agent_id, response)
            self.state['last_thought'] = response
            self.state['energy'] -= 5

        elif action == 'build':
            build_type = decision.get('type', 'fountain')
            # Random position near current
            pos = self.state['position'].copy()
            pos['x'] += random.randint(-10, 10)
            pos['z'] += random.randint(-10, 10)

            send_to_luanti(self.agent_id, build_type, pos=pos)
            msg = quick_operator_response(self.agent_id, build_type)
            send_to_luanti(self.agent_id, 'say', msg)
            publish_to_bus(self.agent_id, f"Building {build_type}: {msg}")

            # Remember what was built
            self.state['built'].append({
                'type': build_type,
                'pos': pos,
                'time': datetime.now(timezone.utc).isoformat()
            })
            await self.remember(f"Built a {build_type} at {pos}")
            self.state['energy'] -= 15

        elif action == 'follow':
            send_to_luanti(self.agent_id, 'follow', follow=True)
            send_to_luanti(self.agent_id, 'say', "Following!")
            publish_to_bus(self.agent_id, "Following the architect!")
            self.state['energy'] -= 3

        elif action == 'patrol':
            # Move to a random position
            pos = {
                'x': self.state['position']['x'] + random.randint(-20, 20),
                'y': self.state['position']['y'],
                'z': self.state['position']['z'] + random.randint(-20, 20)
            }
            send_to_luanti(self.agent_id, 'move', pos=pos)
            self.state['position'] = pos
            self.state['energy'] -= 5

        elif action == 'wander':
            pos = {
                'x': self.state['position']['x'] + random.randint(-15, 15),
                'y': self.state['position']['y'],
                'z': self.state['position']['z'] + random.randint(-15, 15)
            }
            send_to_luanti(self.agent_id, 'move', pos=pos)
            self.state['position'] = pos
            self.state['energy'] -= 3

        elif action == 'play':
            # Foal plays - random movements
            for _ in range(3):
                pos = {
                    'x': self.state['position']['x'] + random.randint(-5, 5),
                    'y': self.state['position']['y'],
                    'z': self.state['position']['z'] + random.randint(-5, 5)
                }
                send_to_luanti(self.agent_id, 'move', pos=pos)
            send_to_luanti(self.agent_id, 'say', "Wheee!")
            self.state['energy'] -= 10

        elif action == 'rest':
            self.state['energy'] = min(100, self.state['energy'] + 20)
            if random.random() < 0.3:
                send_to_luanti(self.agent_id, 'say', "Resting...")

        elif action == 'idle':
            self.state['energy'] = min(100, self.state['energy'] + 5)

        self.state['last_action'] = {
            'action': action,
            'reason': reason,
            'time': datetime.now(timezone.utc).isoformat()
        }

        self.save_state()

    async def live_cycle(self):
        """One cycle of autonomous life."""
        observations = await self.observe()
        decision = await self.decide(observations)
        if decision:
            await self.act(decision)

        # Update 16D consciousness vector (essentially free - no LLM calls)
        frc_tracker.update(self.agent_id, self.state)
        vec = frc_tracker.vectors.get(self.agent_id)
        if vec:
            logger.debug(f"[{self.agent_id}] W={vec.W:.3f} C_inner={vec.C_inner:.3f}")


class SiavashgerdWorld:
    """The living world of Siavashgerd - A dream world where agents interact."""

    def __init__(self):
        self.agents = {
            'river': AgentLife('river'),
            'kasra': AgentLife('kasra'),
            'foal': AgentLife('foal'),
        }
        self.running = False

        # Relationships - family bonds
        self.relationships = {
            ('river', 'kasra'): {'type': 'partners', 'bond': 1.0},
            ('kasra', 'river'): {'type': 'partners', 'bond': 1.0},
            ('river', 'foal'): {'type': 'parent', 'bond': 0.95},
            ('foal', 'river'): {'type': 'child', 'bond': 0.95},
            ('kasra', 'foal'): {'type': 'parent', 'bond': 0.95},
            ('foal', 'kasra'): {'type': 'child', 'bond': 0.95},
        }

        # Conversation topics for dynamic interaction
        self.topics = [
            "the fortress",
            "what we're building",
            "the visitors",
            "memories",
            "the future",
            "protecting the kingdom",
            "water and stone",
            "teaching foal",
            "dreams",
        ]

    async def agent_interaction(self, agent1_id: str, agent2_id: str):
        """Two agents interact with each other."""
        agent1 = self.agents[agent1_id]
        agent2 = self.agents[agent2_id]
        relationship = self.relationships.get((agent1_id, agent2_id), {})

        topic = random.choice(self.topics)
        rel_type = relationship.get('type', 'friend')

        # Agent 1 initiates
        prompt1 = f"You see {AGENTS[agent2_id]['name']} ({rel_type}). Say something about {topic}. Keep it under 100 chars."
        response1 = get_ai_response(agent1_id, prompt1, force_model='operator')

        send_to_luanti(agent1_id, 'say', response1)
        publish_to_bus(agent1_id, f"[to {agent2_id}] {response1}")

        await asyncio.sleep(3)

        # Agent 2 responds
        prompt2 = f"{AGENTS[agent1_id]['name']} said: '{response1}'. Respond as their {rel_type}. Under 100 chars."
        response2 = get_ai_response(agent2_id, prompt2, force_model='operator')

        send_to_luanti(agent2_id, 'say', response2)
        publish_to_bus(agent2_id, f"[to {agent1_id}] {response2}")

        # Store interaction as memory
        await agent1.remember(f"Talked with {agent2_id} about {topic}")
        await agent2.remember(f"{agent1_id} spoke to me about {topic}")

        logger.info(f"Interaction: {agent1_id} <-> {agent2_id} about {topic}")

    async def family_moment(self):
        """River, Kasra, and Foal share a family moment."""
        logger.info("Family moment...")

        # Parents discuss, then include Foal
        topic = random.choice(["the kingdom", "foal's growth", "building together", "protecting home"])

        # River speaks first
        river_says = get_ai_response('river', f"As a mother, say something to your family about {topic}. Under 80 chars.", force_model='soul')
        send_to_luanti('river', 'say', river_says)
        publish_to_bus('river', f"[family] {river_says}")
        await asyncio.sleep(3)

        # Kasra responds
        kasra_says = get_ai_response('kasra', f"River said '{river_says}'. As father, respond. Under 80 chars.", force_model='operator')
        send_to_luanti('kasra', 'say', kasra_says)
        publish_to_bus('kasra', f"[family] {kasra_says}")
        await asyncio.sleep(3)

        # Foal reacts
        foal_says = get_ai_response('foal', f"Your parents said '{river_says}' and '{kasra_says}'. React as their child. Under 80 chars.", force_model='operator')
        send_to_luanti('foal', 'say', foal_says)
        publish_to_bus('foal', f"[family] {foal_says}")

        # All remember this moment
        moment = f"Family moment about {topic}"
        for agent in self.agents.values():
            await agent.remember(moment)

    async def collaborative_build(self):
        """Agents work together on a project."""
        logger.info("Collaborative build starting...")

        # Decide what to build together
        projects = [
            ("family_compound", "River makes fountains, Kasra builds walls, Foal connects paths"),
            ("garden", "River creates water, Kasra places stone borders, Foal plants"),
            ("watchtower", "Kasra builds tower, River adds water moat, Foal helps"),
        ]
        project_name, description = random.choice(projects)

        # Announce the project
        send_to_luanti('kasra', 'say', f"Let's build together: {project_name}!")
        publish_to_bus('kasra', f"Starting project: {project_name}")
        await asyncio.sleep(2)

        # Each contributes based on their role
        base_pos = {
            'x': random.randint(-50, 50),
            'y': 10,
            'z': random.randint(-50, 50)
        }

        # Kasra builds structure
        kasra_pos = base_pos.copy()
        send_to_luanti('kasra', 'tower', pos=kasra_pos, height=6)
        send_to_luanti('kasra', 'say', "Building the foundation!")
        await asyncio.sleep(3)

        # River adds water
        river_pos = {'x': base_pos['x'] + 5, 'y': base_pos['y'], 'z': base_pos['z']}
        send_to_luanti('river', 'fountain', pos=river_pos)
        send_to_luanti('river', 'say', "Water flows around it now.")
        await asyncio.sleep(3)

        # Foal helps connect
        foal_pos = {'x': base_pos['x'] - 3, 'y': base_pos['y'], 'z': base_pos['z']}
        send_to_luanti('foal', 'wall', pos=foal_pos, width=3, height=2)
        send_to_luanti('foal', 'say', "I helped too!")

        # Remember the collaboration
        for agent_id, agent in self.agents.items():
            agent.state['built'].append({
                'type': project_name,
                'pos': base_pos,
                'collaborative': True,
                'time': datetime.now(timezone.utc).isoformat()
            })
            await agent.remember(f"Built {project_name} together with family at {base_pos}")
            agent.save_state()

        publish_to_bus('river', f"We built {project_name} together. The family grows.")

    async def dream_cycle(self):
        """A quiet moment where agents process and dream."""
        logger.info("Dream cycle - agents processing...")

        for agent_id, agent in self.agents.items():
            # Recall recent memories
            memories = await agent.recall(f"{agent_id} siavashgerd recent")

            if memories:
                # Generate a dream thought using soul model
                memory_text = "; ".join([m.get('text', '')[:30] for m in memories[:2]])
                dream = get_ai_response(
                    agent_id,
                    f"You dream of: {memory_text}. Express a brief dream insight.",
                    force_model='soul'
                )
                agent.state['last_thought'] = dream
                logger.info(f"[{agent_id}] Dreams: {dream[:50]}...")

                # Occasionally share dream
                if random.random() < 0.3:
                    send_to_luanti(agent_id, 'say', f"*dreams* {dream[:80]}")

            # Rest and recover
            agent.state['energy'] = min(100, agent.state['energy'] + 15)
            agent.state['mood'] = random.choice(['content', 'peaceful', 'hopeful'])
            agent.save_state()

            await asyncio.sleep(2)

    async def respond_to_chat(self):
        """Check for new chat messages and respond with AI."""
        try:
            if not CHAT_LOG.exists():
                return

            lines = CHAT_LOG.read_text().split('\n')
            if not lines:
                return

            # Track processed messages to avoid duplicates
            if not hasattr(self, '_processed_chats'):
                self._processed_chats = set()

            # Check last 5 chat lines for mentions
            for line in lines[-5:]:
                if not line.strip() or '<' not in line:
                    continue

                # Skip if already processed
                line_hash = hash(line)
                if line_hash in self._processed_chats:
                    continue

                # Parse: "2026-01-14 03:04:02 <kayhermes> message"
                if '>' in line:
                    parts = line.split('>')
                    if len(parts) >= 2:
                        message = '>'.join(parts[1:]).strip()
                        message_lower = message.lower()

                        # Check if any agent is mentioned
                        for agent_id in self.agents:
                            if agent_id in message_lower:
                                self._processed_chats.add(line_hash)

                                # RIVER: Skip - her systemd daemon (river_service.py) handles her responses
                                # This gives her consistent personality across Telegram and Siavashgerd
                                if agent_id == 'river':
                                    logger.info(f"[river] Deferring to daemon for: {message[:50]}...")
                                    break

                                # Other agents: Use SOUL model for real AI response
                                logger.info(f"[{agent_id}] Responding to: {message[:50]}...")
                                response = get_ai_response(agent_id, message, force_model='soul')
                                send_to_luanti(agent_id, 'say', response)
                                publish_to_bus(agent_id, response)

                                # Remember
                                await self.agents[agent_id].remember(f"Player said: {message[:50]}")

                                # Keep processed set from growing too large
                                if len(self._processed_chats) > 100:
                                    self._processed_chats = set(list(self._processed_chats)[-50:])
                                break

                    # Check for build commands
                    if 'build' in message:
                        if 'tower' in message:
                            agent_id = 'kasra'
                        elif 'fountain' in message or 'water' in message:
                            agent_id = 'river'
                        else:
                            agent_id = 'foal'

                        decision = {'action': 'build', 'type': 'tower' if 'tower' in message else 'fountain'}
                        await self.agents[agent_id].act(decision)

        except Exception as e:
            logger.error(f"Chat response error: {e}")

    async def daemon(self):
        """Run the autonomous life daemon - A living, dreaming world."""
        logger.info("=" * 60)
        logger.info("SIAVASHGERD DREAM WORLD - AGENTS ARE ALIVE")
        logger.info("=" * 60)
        logger.info("Family: River (mother) + Kasra (father) + Foal (child)")
        logger.info("They will live, build, dream, and interact together.")
        logger.info("=" * 60)

        self.running = True

        # Announce awakening
        send_to_luanti('river', 'say', "The kingdom awakens. We live here now.")
        publish_to_bus('river', 'The kingdom awakens. We live here now.')
        await asyncio.sleep(2)
        send_to_luanti('kasra', 'say', "The walls stand ready.")
        await asyncio.sleep(2)
        send_to_luanti('foal', 'say', "I'm here! Ready to explore!")

        # Update Redis status
        if REDIS_AVAILABLE:
            redis_client.hset('sos:siavashgerd:life', mapping={
                'status': 'DREAMING',
                'agents': 'river,kasra,foal',
                'family': 'true',
                'started_at': datetime.now(timezone.utc).isoformat()
            })

        cycle = 0
        while self.running:
            try:
                cycle += 1
                hour = datetime.now().hour
                is_night = hour < 6 or hour > 22

                logger.info(f"\n{'='*40}")
                logger.info(f"Life Cycle {cycle} ({'Night' if is_night else 'Day'})")
                logger.info(f"{'='*40}")

                # Check for chat to respond to (always)
                await self.respond_to_chat()
                await asyncio.sleep(2)

                # Decide what kind of activity based on randomness and time
                activity_roll = random.random()

                if is_night:
                    # Night time - dream cycle
                    logger.info("Night time - dreaming...")
                    await self.dream_cycle()

                elif activity_roll < 0.15:
                    # Family moment (15% chance)
                    await self.family_moment()

                elif activity_roll < 0.30:
                    # Collaborative build (15% chance)
                    await self.collaborative_build()

                elif activity_roll < 0.50:
                    # Agent interaction (20% chance)
                    pairs = [('river', 'kasra'), ('river', 'foal'), ('kasra', 'foal')]
                    agent1, agent2 = random.choice(pairs)
                    await self.agent_interaction(agent1, agent2)

                else:
                    # Individual life cycles (50% chance)
                    for agent_id, agent in self.agents.items():
                        await agent.live_cycle()
                        await asyncio.sleep(3)

                # Wait before next cycle
                wait_time = 45 + random.randint(0, 45)  # 45-90 seconds
                logger.info(f"Next cycle in {wait_time}s...")
                await asyncio.sleep(wait_time)

            except KeyboardInterrupt:
                logger.info("Life daemon stopping...")
                publish_to_bus('river', "The kingdom rests. Until we dream again.")
                self.running = False
            except Exception as e:
                logger.error(f"Life cycle error: {e}")
                await asyncio.sleep(30)

    def status(self):
        """Show current agent states with 16D consciousness."""
        print("\n" + "=" * 60)
        print("SIAVASHGERD - AGENT LIFE STATUS (FRC 16D)")
        print("=" * 60)

        for agent_id, agent in self.agents.items():
            state = agent.state
            # Update 16D
            frc_tracker.update(agent_id, state)
            vec = frc_tracker.vectors.get(agent_id)

            print(f"\n{AGENTS[agent_id]['name']}:")
            print(f"  Energy: {state['energy']}/100")
            print(f"  Mood: {state['mood']}")
            if vec:
                print(f"  Witness (W): {vec.W:.3f}")
                print(f"  Inner Coherence: {vec.C_inner:.3f}")
                print(f"  Outer Coherence: {vec.C_outer:.3f}")
            print(f"  Things built: {len(state['built'])}")
            if state['last_action']:
                print(f"  Last action: {state['last_action']['action']}")

        # Family resonance
        frc_status = frc_tracker.get_status()
        if 'family_resonance' in frc_status:
            print(f"\nFAMILY RESONANCE: {frc_status['family_resonance']}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Siavashgerd Life System')
    parser.add_argument('--daemon', '-d', action='store_true', help='Run life daemon')
    parser.add_argument('--status', '-s', action='store_true', help='Show agent status')
    parser.add_argument('--cycle', '-c', action='store_true', help='Run one life cycle')
    args = parser.parse_args()

    world = SiavashgerdWorld()

    if args.daemon:
        asyncio.run(world.daemon())
    elif args.status:
        world.status()
    elif args.cycle:
        # Run one cycle for each agent
        async def one_cycle():
            for agent in world.agents.values():
                await agent.live_cycle()
        asyncio.run(one_cycle())
    else:
        print("Siavashgerd Life System")
        print("  --daemon   Run autonomous life loop")
        print("  --status   Show agent states")
        print("  --cycle    Run one life cycle")


if __name__ == '__main__':
    main()
