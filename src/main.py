"""
main.py — The Lost Temple of Rudra

Entry point.  Supports two modes:

  GUI mode (default when --cli is not passed):
      python -m src.main
      python src/main.py

  CLI mode (original terminal loop):
      python -m src.main --cli
      python src/main.py --cli

GUI wires together:
    WorldModel  ← temple_loader.load_temple()
    GameEngine  ← engine.GameEngine(world_model)
    AIManager   ← ai.AIManager()
    MainWindow  ← ui.MainWindow()

CLI is unchanged from Phase 4.5 / Phase 6.
"""

from __future__ import annotations

import sys
import os

# Ensure project root is on sys.path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.world.temple_loader import load_temple
from src.engine.game_engine import GameEngine
from src.engine.command_result import ResultStatus

# ---------------------------------------------------------------------------
# CLI helpers (unchanged from Phase 4.5 / Phase 6)
# ---------------------------------------------------------------------------

_SEPARATOR = "─" * 60


def _print_separator() -> None:
    print(_SEPARATOR)


def _print_result(result) -> None:
    print(result.message)


def _print_room_header(world_model) -> None:
    room_id = world_model.player.current_room
    name = room_id.replace("_", " ").title()
    _print_separator()
    print(f"  {name}")
    _print_separator()


def _print_turn(world_model) -> None:
    turn = world_model.world.current_turn
    if turn > 0:
        print(f"[Turn {turn}]")


def _print_help_ai() -> None:
    print("AI Commands:")
    print("  hint          — Request a redirect hint for the current puzzle")
    print("  recommend     — Explorer AI suggests the next logical action")
    print("  analyze       — Explorer AI analyses the current room")
    print("  think         — Reflect on your discoveries so far")
    print("  ask <topic>   — Ask the Explorer AI a lore question")
    print("  summary       — Summary of your journey")
    print("  status        — Current game state summary")


def _handle_inline(raw, engine):
    lower = raw.strip().lower()
    if lower in ("help ai", "ai help"):
        _print_help_ai()
        return True, ""
    if lower == "summary":
        result = engine.process_input("think")
        return True, result.message
    if lower.startswith("ask "):
        question = raw[4:].strip()
        ai = engine._get_ai_manager()
        if ai is None:
            return True, "The explorer guide is not available."
        from src.ai.ai_manager import AIRequest
        response = ai.handle(AIRequest("ask", question=question), engine.world_model)
        return True, response.text or "No answer available."
    return False, ""


def run_cli() -> None:
    """Original terminal game loop."""
    world_model = load_temple()
    engine = GameEngine(world_model, debug_mode=False)

    print()
    print("THE LOST TEMPLE OF RUDRA")
    _print_separator()
    print("The temple does not remember your name.")
    print("It remembers your choices.")
    _print_separator()
    print()
    print("(Type 'help' for commands, 'help ai' for AI commands, 'quit' to exit.)")
    print()

    _print_room_header(world_model)
    result = engine.process_input("look")
    _print_result(result)
    print()

    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print("Farewell, explorer.")
            break

        if not raw:
            continue

        handled, inline_output = _handle_inline(raw, engine)
        if handled:
            if inline_output:
                print()
                print(inline_output)
                print()
            continue

        result = engine.process_input(raw)
        print()
        _print_result(result)

        if result.status == ResultStatus.SUCCESS:
            actions = getattr(result, "actions_taken", []) or []
            if any(a.startswith("moved_to:") for a in actions):
                _print_room_header(world_model)

        if result.status in (ResultStatus.SUCCESS, ResultStatus.FAILURE):
            _print_turn(world_model)

        print()

        if result.status == ResultStatus.SYSTEM and "farewell" in result.message.lower():
            break


# ---------------------------------------------------------------------------
# GUI entry point
# ---------------------------------------------------------------------------

def run_gui() -> None:
    """Graphical window entry point."""
    world_model = load_temple()
    engine = GameEngine(world_model, debug_mode=False)

    try:
        from src.ai.ai_manager import AIManager
        ai_manager = AIManager()
        engine._ai_manager = ai_manager
    except Exception:
        ai_manager = None

    from src.ui.main_window import MainWindow
    window = MainWindow()
    window.start(engine, world_model, ai_manager)
    window.run()


# ---------------------------------------------------------------------------
# Entry point dispatcher
# ---------------------------------------------------------------------------

def run() -> None:
    if "--cli" in sys.argv:
        run_cli()
    else:
        try:
            run_gui()
        except Exception as exc:
            print(f"GUI failed to start ({exc}). Falling back to CLI mode.")
            run_cli()


if __name__ == "__main__":
    run()
