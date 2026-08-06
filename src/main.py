"""
main.py — The Lost Temple of Rudra

Minimal command-line entry point.

Wires together the existing systems — no new logic is implemented here:
    - WorldModel   via temple_loader.load_temple()
    - GameEngine   via engine.GameEngine
    - Parser       lives inside the engine (engine.process_input)

Usage:
    python -m src.main          (from project root)
    python src/main.py          (from project root)
"""

from __future__ import annotations

import sys
import os

# Ensure the project root is on sys.path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.world.temple_loader import load_temple
from src.engine.game_engine import GameEngine
from src.engine.command_result import ResultStatus

# ---------------------------------------------------------------------------
# Display helpers  (presentation only — no game logic)
# ---------------------------------------------------------------------------

_SEPARATOR = "─" * 60


def _print_separator() -> None:
    print(_SEPARATOR)


def _print_result(result) -> None:
    """Print a GameResult to stdout in a readable format."""
    print(result.message)


def _print_room_header(world_model) -> None:
    """Print the current room name as a header."""
    room_id = world_model.player.current_room
    room = world_model.get_current_room()
    name = room_id.replace("_", " ").title()
    _print_separator()
    print(f"  {name}")
    _print_separator()


def _print_turn(world_model) -> None:
    """Print the current turn number."""
    turn = world_model.world.current_turn
    if turn > 0:
        print(f"[Turn {turn}]")


# ---------------------------------------------------------------------------
# Game loop
# ---------------------------------------------------------------------------

def run() -> None:
    """
    Initialise all systems and enter the command loop.
    Delegates every command to the existing GameEngine unchanged.
    """
    # ── Initialise ───────────────────────────────────────────────────
    world_model = load_temple()
    engine = GameEngine(world_model, debug_mode=False)

    # ── Opening ──────────────────────────────────────────────────────
    print()
    print("THE LOST TEMPLE OF RUDRA")
    _print_separator()
    print("The temple does not remember your name.")
    print("It remembers your choices.")
    _print_separator()
    print()
    print("(Type 'help' for a list of commands, 'quit' to exit.)")
    print()

    # Show the starting room immediately
    _print_room_header(world_model)
    result = engine.process_input("look")
    _print_result(result)
    print()

    # ── Command loop ─────────────────────────────────────────────────
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print("Farewell, explorer.")
            break

        if not raw:
            continue

        # Pass the raw input directly to the engine — parser lives inside it
        result = engine.process_input(raw)

        # Print the result message
        print()
        _print_result(result)

        # If the player moved to a new room, print the room header
        if result.status == ResultStatus.SUCCESS:
            data = getattr(result, "data", {}) or {}
            if "moved_to" in " ".join(getattr(result, "actions_taken", [])):
                _print_room_header(world_model)

        # Print turn counter after every action that costs a turn
        if result.status in (ResultStatus.SUCCESS, ResultStatus.FAILURE):
            _print_turn(world_model)

        print()

        # Quit on explicit quit command
        if result.status == ResultStatus.SYSTEM and "farewell" in result.message.lower():
            break


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run()
