"""
main.py — The Lost Temple of Rudra

Command-line entry point.

Wires together:
    - WorldModel   via temple_loader.load_temple()
    - GameEngine   via engine.GameEngine (with AI Manager)
    - Parser       lives inside the engine (engine.process_input)

AI commands available:
    hint            — Temple AI redirect hint for current puzzle
    recommend       — Explorer AI next-action suggestion
    analyze         — Explorer AI room analysis
    think / history — Explorer AI journey reflection
    ask <question>  — Explorer AI lore question
    summary         — Exploration summary
    status          — Current game status

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
    name = room_id.replace("_", " ").title()
    _print_separator()
    print(f"  {name}")
    _print_separator()


def _print_turn(world_model) -> None:
    """Print the current turn number."""
    turn = world_model.world.current_turn
    if turn > 0:
        print(f"[Turn {turn}]")


def _print_help_ai() -> None:
    """Print the AI command reference."""
    print("AI Commands:")
    print("  hint          — Request a redirect hint for the current puzzle")
    print("  recommend     — Explorer AI suggests the next logical action")
    print("  analyze       — Explorer AI analyses the current room")
    print("  think         — Reflect on your discoveries so far")
    print("  ask <topic>   — Ask the Explorer AI a lore question")
    print("  summary       — Summary of your journey")
    print("  status        — Current game state summary")


# ---------------------------------------------------------------------------
# Inline AI commands (handled before routing to engine)
# ---------------------------------------------------------------------------

_AI_INLINE_COMMANDS = {
    "help ai": "_help_ai",
    "summary": "think",          # alias for think/history
    "ask": "ask",
}


def _handle_inline(raw: str, engine: GameEngine) -> tuple[bool, str]:
    """
    Handle CLI-level AI commands that need special routing.
    Returns (handled: bool, output: str).
    """
    lower = raw.strip().lower()

    # 'help ai' — print AI help
    if lower in ("help ai", "ai help"):
        _print_help_ai()
        return True, ""

    # 'summary' — route to 'think'
    if lower == "summary":
        result = engine.process_input("think")
        return True, result.message

    # 'ask <question>' — route through AI Manager directly
    if lower.startswith("ask "):
        question = raw[4:].strip()
        ai = engine._get_ai_manager()
        if ai is None:
            return True, "The explorer guide is not available."
        from src.ai.ai_manager import AIRequest
        response = ai.handle(
            AIRequest("ask", question=question),
            engine.world_model,
        )
        return True, response.text or "No answer available."

    return False, ""


# ---------------------------------------------------------------------------
# Game loop
# ---------------------------------------------------------------------------

def run() -> None:
    """
    Initialise all systems and enter the command loop.
    Delegates every command to the existing GameEngine unchanged.
    AI Manager is lazily initialised inside the engine.
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
    print("(Type 'help' for commands, 'help ai' for AI commands, 'quit' to exit.)")
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

        # Check inline AI commands first
        handled, inline_output = _handle_inline(raw, engine)
        if handled:
            if inline_output:
                print()
                print(inline_output)
                print()
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
