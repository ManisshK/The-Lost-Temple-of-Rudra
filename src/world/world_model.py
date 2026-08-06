"""
world_model.py — The Lost Temple of Rudra

THE SINGLE SOURCE OF TRUTH for the entire game.
Every room, object, puzzle, event, player state, and evaluation score lives here.

Access rules:
    WRITE — Game Engine only, via write interface methods.
    READ  — All systems, via read interface methods or get_snapshot().

Eleven state sections:
    1.  player         — current room, inventory, scores, movement history
    2.  world          — temple phase, flood level, collapse stage, awareness
    3.  rooms          — per-room visited flag, objects, accessibility, light level
    4.  objects        — per-object state, condition, location, usage history
    5.  inventory      — collected objects and conditions
    6.  puzzles        — solved state, attempt count, hint usage, failure history
    7.  story          — chapter progress, discoveries, lore read, ending eligibility
    8.  dynamic_events — flood, doors, dust, bridge, collapse state and history
    9.  evaluation     — ten guardian evaluation attributes (float 0–100)
    10. ai_context     — sanitised read-only snapshot (built by ContextBuilder)
    11. mission        — primary/secondary mission, completed objectives, current goal

TODO: Implement all eleven state sections as a nested data structure.
TODO: Implement write interface methods (Game Engine only).
TODO: Implement read interface methods (all systems).
TODO: Implement get_snapshot() — deep copy for safe read-only access.
TODO: Implement get_ai_context() — sanitised view excluding hidden information.
TODO: Implement append_event(turn, description) — append-only event history log.
TODO: Implement to_dict() and from_dict() for JSON serialisation (save/load).
TODO: Implement state validation — no contradictory or impossible state allowed.
"""
