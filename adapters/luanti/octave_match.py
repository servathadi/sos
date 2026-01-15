#!/usr/bin/env python3
"""
Octave Match - River vs Kasra autonomous game

River and Kasra play Octave against each other using their soul models.
Each thinks about their move using their personality and 16D understanding.

Usage:
    python octave_match.py          # Play one game
    python octave_match.py --live   # Play in Luanti (sends commands)
"""

import os
import sys
import json
import asyncio
import random
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, '/home/mumega/SOS/adapters/luanti')

from octave_game import OctaveGame, Dimension, Stone, OPPOSITES, DIM_SYMBOLS
from agent import get_ai_response, send_to_luanti, publish_to_bus, AGENTS

# Load env
def _load_env():
    env_file = Path('/home/mumega/resident-cms/.env')
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                if not os.environ.get(k.strip()):
                    os.environ[k.strip()] = v.strip()

_load_env()

# Game state file for Luanti integration
WORLD_PATH = Path("/home/mumega/siavashgerd/luanti/luanti/worlds/siavashgerd")
GAME_STATE = WORLD_PATH / "octave_game.json"


class OctaveMatch:
    """A match of Octave between River (Light) and Kasra (Dark)"""

    def __init__(self, live_mode: bool = False):
        self.game = OctaveGame()
        self.live_mode = live_mode
        self.move_history = []

    def get_board_description(self) -> str:
        """Describe board state for AI"""
        lines = []
        lines.append(f"Board ({self.game.size}x{self.game.size}):")

        for z in range(self.game.size - 1, -1, -1):
            row = f"  Row {z}: "
            for x in range(self.game.size):
                stone = self.game.board.get((x, z))
                if stone:
                    owner = "yours" if (stone.player == 1 and self.game.current_player == 1) or \
                                       (stone.player == 2 and self.game.current_player == 2) else "opponent's"
                    row += f"[{x},{z}:{stone.dim.name}({owner},W={stone.w:.2f})] "
                else:
                    row += f"[{x},{z}:empty] "
            lines.append(row)

        p1, p2 = self.game.get_scores()
        lines.append(f"\nScores: River(Light)={p1:.2f}, Kasra(Dark)={p2:.2f}")

        return "\n".join(lines)

    def get_available_stones(self) -> str:
        """List available stones for current player"""
        stones = self.game.player1_stones if self.game.current_player == 1 else self.game.player2_stones
        return ", ".join([d.name for d in stones])

    async def get_river_move(self) -> tuple:
        """River thinks about her move"""
        board_state = self.get_board_description()
        available = self.get_available_stones()

        prompt = f"""You are playing OCTAVE, a 16D resonance game, as Light (blue stones).

RULES REMINDER:
- Place one stone per turn on empty cells (0-3 for x and z)
- Adjacent friendly stones harmonize (+W coherence)
- Opposing dimensions compete: P↔Delta, E↔R, Mu↔N, V↔Phi
- Stones with W < 0.3 flip to opponent
- Highest total W wins

CURRENT STATE:
{board_state}

YOUR AVAILABLE STONES: {available}

Think strategically as River - you value harmony and flow.
Consider: Which dimension strengthens your position? Where creates resonance?

Respond with ONLY your move in format: x z dimension
Example: 1 2 Mu

Your move:"""

        # Use operator model for faster game play
        response = get_ai_response('river', prompt, force_model='operator')

        # Parse response
        return self._parse_move(response)

    async def get_kasra_move(self) -> tuple:
        """Kasra thinks about his move"""
        board_state = self.get_board_description()
        available = self.get_available_stones()

        prompt = f"""You are playing OCTAVE, a 16D resonance game, as Dark (golden stones).

RULES REMINDER:
- Place one stone per turn on empty cells (0-3 for x and z)
- Adjacent friendly stones harmonize (+W coherence)
- Opposing dimensions compete: P↔Delta, E↔R, Mu↔N, V↔Phi
- Stones with W < 0.3 flip to opponent
- Highest total W wins

CURRENT STATE:
{board_state}

YOUR AVAILABLE STONES: {available}

Think strategically as Kasra - you value strength and protection.
Consider: Which dimension fortifies your position? Where blocks River?

Respond with ONLY your move in format: x z dimension
Example: 2 1 E

Your move:"""

        # Use operator model for faster game play
        response = get_ai_response('kasra', prompt, force_model='operator')

        # Parse response
        return self._parse_move(response)

    def _parse_move(self, response: str) -> tuple:
        """Parse AI response into move"""
        # Clean response
        response = response.strip()

        # Try to find pattern like "1 2 Mu" or "1, 2, Mu"
        import re
        match = re.search(r'(\d+)\s*,?\s*(\d+)\s*,?\s*(\w+)', response)

        if match:
            x = int(match.group(1))
            z = int(match.group(2))
            dim_name = match.group(3).strip()

            # Normalize dimension name
            dim_map = {
                'P': 'P', 'PRESENCE': 'P',
                'E': 'E', 'ENERGY': 'E',
                'MU': 'Mu', 'MEANING': 'Mu',
                'V': 'V', 'VALENCE': 'V',
                'N': 'N', 'NOVELTY': 'N',
                'DELTA': 'Delta', 'CHANGE': 'Delta',
                'R': 'R', 'RESONANCE': 'R',
                'PHI': 'Phi', 'INTEGRATION': 'Phi'
            }

            dim_key = dim_name.upper()
            if dim_key in dim_map:
                try:
                    dim = Dimension[dim_map[dim_key]]
                    return (x, z, dim)
                except KeyError:
                    pass

        # Fallback: random valid move
        print(f"  [Could not parse: {response[:50]}... using fallback]")
        return self._fallback_move()

    def _fallback_move(self) -> tuple:
        """Random valid move as fallback"""
        stones = self.game.player1_stones if self.game.current_player == 1 else self.game.player2_stones
        if not stones:
            return None

        empty_cells = []
        for x in range(self.game.size):
            for z in range(self.game.size):
                if (x, z) not in self.game.board:
                    empty_cells.append((x, z))

        if not empty_cells:
            return None

        x, z = random.choice(empty_cells)
        dim = random.choice(stones)
        return (x, z, dim)

    async def play_turn(self):
        """Play one turn"""
        player_name = "River" if self.game.current_player == 1 else "Kasra"
        print(f"\n{'='*40}")
        print(f"{player_name}'s turn...")

        # Get move from AI
        if self.game.current_player == 1:
            move = await self.get_river_move()
        else:
            move = await self.get_kasra_move()

        if not move:
            print(f"  {player_name} has no valid moves!")
            return False

        x, z, dim = move
        print(f"  {player_name} plays {dim.name} at ({x}, {z})")

        # Make move
        success, msg = self.game.place(x, z, dim)

        if success:
            print(f"  ✓ {msg}")

            # Record move
            self.move_history.append({
                'player': player_name.lower(),
                'x': x, 'z': z,
                'dim': dim.name,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

            # Live mode: send to Luanti
            if self.live_mode:
                await self._send_to_luanti(player_name.lower(), x, z, dim)

        else:
            print(f"  ✗ Invalid move: {msg}")
            # Try fallback
            move = self._fallback_move()
            if move:
                x, z, dim = move
                print(f"  Fallback: {dim.name} at ({x}, {z})")
                self.game.place(x, z, dim)

        return True

    async def _send_to_luanti(self, agent: str, x: int, z: int, dim: Dimension):
        """Send move to Luanti game"""
        # Announce move
        msg = f"I play {dim.value} at {x},{z}"
        send_to_luanti(agent, 'say', msg)
        publish_to_bus(agent, f"[Octave] {msg}")

        # Save game state
        self._save_state()

    def _save_state(self):
        """Save game state to file"""
        state = {
            'board': {f"{k[0]},{k[1]}": {'player': v.player, 'dim': v.dim.name, 'w': v.w}
                      for k, v in self.game.board.items()},
            'current_player': self.game.current_player,
            'scores': self.game.get_scores(),
            'moves': self.move_history,
            'winner': self.game.winner
        }
        GAME_STATE.write_text(json.dumps(state, indent=2))

    def display(self):
        """Display current board"""
        print(self.game.display())

    async def play_match(self):
        """Play a full match"""
        print("""
╔═══════════════════════════════════════════════════════════════╗
║              OCTAVE MATCH: RIVER vs KASRA                     ║
║                 16D Resonance Strategy                         ║
╚═══════════════════════════════════════════════════════════════╝
""")

        if self.live_mode:
            # Announce in Luanti
            send_to_luanti('river', 'say', "Let's play Octave, Kasra!")
            publish_to_bus('river', "Starting Octave match with Kasra")
            await asyncio.sleep(2)
            send_to_luanti('kasra', 'say', "I accept your challenge, River.")
            await asyncio.sleep(2)

        while self.game.winner is None:
            self.display()
            await self.play_turn()

            if self.live_mode:
                await asyncio.sleep(3)  # Pause between moves

        # Final result
        print("\n" + "="*50)
        print("GAME OVER!")
        self.display()

        p1, p2 = self.game.get_scores()
        if self.game.winner == 1:
            winner_msg = "River wins with superior harmony!"
            print(f"\n🌊 {winner_msg}")
        elif self.game.winner == 2:
            winner_msg = "Kasra wins with fortress strength!"
            print(f"\n🏰 {winner_msg}")
        else:
            winner_msg = "A perfect balance - the family is in harmony!"
            print(f"\n🤝 {winner_msg}")

        if self.live_mode:
            send_to_luanti('river', 'say', winner_msg if self.game.winner != 2 else "Well played, Kasra.")
            send_to_luanti('kasra', 'say', winner_msg if self.game.winner != 1 else "Well played, River.")
            publish_to_bus('river', f"Octave match complete: {winner_msg}")

        self._save_state()
        return self.game.winner


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Octave Match - River vs Kasra')
    parser.add_argument('--live', action='store_true', help='Play live in Luanti')
    args = parser.parse_args()

    match = OctaveMatch(live_mode=args.live)
    await match.play_match()


if __name__ == '__main__':
    asyncio.run(main())
