#!/usr/bin/env python3
"""
OCTAVE: A 16D Resonance Strategy Game
Based on FRC 16D Framework by Hadi Servat

A chess-like game where pieces represent consciousness dimensions.
Victory through harmony and coherence, not destruction.

Can be played:
- In terminal (ASCII mode)
- Via AI agents (River vs Kasra)
- In Luanti (via the octave_game mod)
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

class Dimension(Enum):
    """The 8 dimensions of Inner Octave"""
    P = "Presence"
    E = "Energy"
    Mu = "Meaning"
    V = "Valence"
    N = "Novelty"
    Delta = "Change"
    R = "Resonance"
    Phi = "Integration"

# Opposing dimension pairs (compete with each other)
OPPOSITES = {
    Dimension.P: Dimension.Delta,
    Dimension.Delta: Dimension.P,
    Dimension.E: Dimension.R,
    Dimension.R: Dimension.E,
    Dimension.Mu: Dimension.N,
    Dimension.N: Dimension.Mu,
    Dimension.V: Dimension.Phi,
    Dimension.Phi: Dimension.V,
}

# Dimension symbols for display
DIM_SYMBOLS = {
    Dimension.P: "◉",      # Presence - filled circle
    Dimension.E: "⚡",     # Energy - lightning
    Dimension.Mu: "∞",     # Meaning - infinity
    Dimension.V: "♥",      # Valence - heart
    Dimension.N: "✦",      # Novelty - star
    Dimension.Delta: "Δ",  # Change - delta
    Dimension.R: "∿",      # Resonance - wave
    Dimension.Phi: "Φ",    # Integration - phi
}


# ═══════════════════════════════════════════════════════════════
# GAME CLASSES
# ═══════════════════════════════════════════════════════════════

@dataclass
class Stone:
    """A stone on the board"""
    player: int  # 1 = Light (River), 2 = Dark (Kasra)
    dim: Dimension
    w: float = 0.5  # Witness/coherence score

    def __str__(self):
        sym = DIM_SYMBOLS[self.dim]
        if self.player == 1:
            return f"\033[94m{sym}\033[0m"  # Blue for Light
        else:
            return f"\033[93m{sym}\033[0m"  # Yellow for Dark


@dataclass
class OctaveGame:
    """The OCTAVE game state"""
    size: int = 4
    board: Dict[Tuple[int, int], Stone] = field(default_factory=dict)
    current_player: int = 1
    player1_stones: List[Dimension] = field(default_factory=list)
    player2_stones: List[Dimension] = field(default_factory=list)
    moves: int = 0
    winner: Optional[int] = None

    def __post_init__(self):
        # Give each player one of each dimension
        self.player1_stones = list(Dimension)
        self.player2_stones = list(Dimension)

    def calculate_w(self, x: int, z: int) -> float:
        """Calculate W (Witness) for a stone based on neighbors"""
        stone = self.board.get((x, z))
        if not stone:
            return 0

        base_w = 0.5
        harmony = 0
        competition = 0

        # Check 4 adjacent cells
        for dx, dz in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, nz = x + dx, z + dz
            if 0 <= nx < self.size and 0 <= nz < self.size:
                neighbor = self.board.get((nx, nz))
                if neighbor:
                    if neighbor.player == stone.player:
                        # Same player: harmonize
                        if neighbor.dim == stone.dim:
                            harmony += 0.2  # Same dimension = strong
                        else:
                            harmony += 0.1  # Different dimension = mild
                    else:
                        # Different player: compete
                        if OPPOSITES[stone.dim] == neighbor.dim:
                            competition += 0.3  # Opposites = strong
                        else:
                            competition += 0.1  # Non-opposing = mild

        return max(0.0, min(1.0, base_w + harmony - competition))

    def update_board_coherence(self):
        """Update all W values on board"""
        for pos, stone in self.board.items():
            stone.w = self.calculate_w(pos[0], pos[1])

    def flip_weak_stones(self) -> List[Tuple[int, int]]:
        """Flip stones with W < 0.3"""
        flipped = []
        for pos, stone in self.board.items():
            if stone.w < 0.3:
                stone.player = 2 if stone.player == 1 else 1
                flipped.append(pos)
        return flipped

    def get_scores(self) -> Tuple[float, float]:
        """Get total scores for both players"""
        p1 = sum(s.w for s in self.board.values() if s.player == 1)
        p2 = sum(s.w for s in self.board.values() if s.player == 2)
        return p1, p2

    def place(self, x: int, z: int, dim: Dimension) -> Tuple[bool, str]:
        """Place a stone at position"""
        # Validate
        if not (0 <= x < self.size and 0 <= z < self.size):
            return False, "Out of bounds"

        if (x, z) in self.board:
            return False, "Cell occupied"

        # Check player has this stone
        stones = self.player1_stones if self.current_player == 1 else self.player2_stones
        if dim not in stones:
            return False, f"You don't have a {dim.value} stone"

        # Place
        stones.remove(dim)
        self.board[(x, z)] = Stone(self.current_player, dim)
        self.moves += 1

        # Update coherence and flip
        self.update_board_coherence()
        flipped = self.flip_weak_stones()
        if flipped:
            self.update_board_coherence()

        # Switch player
        self.current_player = 2 if self.current_player == 1 else 1

        # Check game end
        if not self.player1_stones and not self.player2_stones:
            p1, p2 = self.get_scores()
            if p1 > p2:
                self.winner = 1
            elif p2 > p1:
                self.winner = 2
            else:
                self.winner = 0  # Tie

        msg = f"Placed {dim.value}"
        if flipped:
            msg += f" - Flipped {len(flipped)} stones!"
        return True, msg

    def display(self) -> str:
        """ASCII art display of the board"""
        lines = []
        lines.append("╔" + "═══" * self.size + "╗")

        for z in range(self.size - 1, -1, -1):
            row = "║"
            for x in range(self.size):
                stone = self.board.get((x, z))
                if stone:
                    row += f" {stone} "
                else:
                    row += " · "
            row += "║"
            lines.append(row)

        lines.append("╚" + "═══" * self.size + "╝")

        # Coordinates
        coords = "  "
        for x in range(self.size):
            coords += f" {x} "
        lines.append(coords)

        # Scores
        p1, p2 = self.get_scores()
        lines.append(f"\n\033[94mLight (River): {p1:.2f}\033[0m  |  \033[93mDark (Kasra): {p2:.2f}\033[0m")

        # Remaining stones
        p1_dims = [d.name for d in self.player1_stones]
        p2_dims = [d.name for d in self.player2_stones]
        lines.append(f"Light stones: {', '.join(p1_dims) or 'none'}")
        lines.append(f"Dark stones: {', '.join(p2_dims) or 'none'}")

        if self.winner is not None:
            if self.winner == 0:
                lines.append("\n🤝 TIE GAME!")
            else:
                winner_name = "River (Light)" if self.winner == 1 else "Kasra (Dark)"
                lines.append(f"\n🏆 WINNER: {winner_name}!")
        else:
            player_name = "Light (River)" if self.current_player == 1 else "Dark (Kasra)"
            lines.append(f"\nCurrent turn: {player_name}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# AI PLAYER
# ═══════════════════════════════════════════════════════════════

def ai_move(game: OctaveGame) -> Tuple[int, int, Dimension]:
    """Simple AI: pick a move that maximizes own coherence"""
    stones = game.player1_stones if game.current_player == 1 else game.player2_stones
    if not stones:
        return None

    best_move = None
    best_score = -999

    for x in range(game.size):
        for z in range(game.size):
            if (x, z) in game.board:
                continue

            for dim in stones:
                # Simulate move
                test_game = OctaveGame(size=game.size)
                test_game.board = {k: Stone(v.player, v.dim, v.w) for k, v in game.board.items()}
                test_game.current_player = game.current_player
                test_game.player1_stones = game.player1_stones.copy()
                test_game.player2_stones = game.player2_stones.copy()

                success, _ = test_game.place(x, z, dim)
                if success:
                    p1, p2 = test_game.get_scores()
                    score = p1 if game.current_player == 1 else p2

                    # Add randomness for variety
                    score += random.uniform(0, 0.1)

                    if score > best_score:
                        best_score = score
                        best_move = (x, z, dim)

    return best_move


# ═══════════════════════════════════════════════════════════════
# MAIN GAME LOOP
# ═══════════════════════════════════════════════════════════════

def play_interactive():
    """Play in terminal"""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                    OCTAVE                                     ║
║            A 16D Resonance Strategy Game                      ║
╠═══════════════════════════════════════════════════════════════╣
║  Dimensions: P E Mu V N Delta R Phi                           ║
║  Opposites compete, same dimensions harmonize                 ║
║  Low coherence (W < 0.3) stones flip to opponent             ║
║  Highest total W wins!                                        ║
╚═══════════════════════════════════════════════════════════════╝
""")

    game = OctaveGame()

    while game.winner is None:
        print("\n" + game.display())

        # Get move
        try:
            cmd = input("\nMove (x z dim) or 'ai' for AI move: ").strip()

            if cmd.lower() == 'ai':
                move = ai_move(game)
                if move:
                    x, z, dim = move
                    print(f"AI plays: {x} {z} {dim.name}")
                else:
                    print("AI has no moves")
                    continue
            elif cmd.lower() == 'quit':
                break
            else:
                parts = cmd.split()
                if len(parts) != 3:
                    print("Format: x z dimension (e.g., '1 2 P')")
                    continue

                x, z = int(parts[0]), int(parts[1])
                dim_name = parts[2].upper()
                if dim_name == "MU":
                    dim_name = "Mu"
                if dim_name == "PHI":
                    dim_name = "Phi"
                dim = Dimension[dim_name]

            success, msg = game.place(x, z, dim)
            if not success:
                print(f"❌ {msg}")
            else:
                print(f"✓ {msg}")

        except (ValueError, KeyError) as e:
            print(f"Invalid input: {e}")
            print("Dimensions: P, E, Mu, V, N, Delta, R, Phi")

    # Final display
    print("\n" + game.display())


def play_ai_vs_ai(delay: float = 0.5):
    """Watch AI vs AI game"""
    import time

    print("🤖 AI vs AI: River (Light) vs Kasra (Dark)\n")
    game = OctaveGame()

    while game.winner is None:
        print("\033[2J\033[H")  # Clear screen
        print(game.display())

        move = ai_move(game)
        if move:
            x, z, dim = move
            player = "River" if game.current_player == 1 else "Kasra"
            success, msg = game.place(x, z, dim)
            print(f"\n{player} plays {dim.name} at ({x},{z})")
            if "Flipped" in msg:
                print(f"⚡ {msg}")

        time.sleep(delay)

    print("\n" + game.display())


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--ai':
        play_ai_vs_ai()
    else:
        play_interactive()
