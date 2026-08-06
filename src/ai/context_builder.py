"""
context_builder.py — The Lost Temple of Rudra

Builds sanitised, read-only AI context dictionaries from the World Model.

Rules:
  - NEVER expose puzzle solutions, judgment thresholds, or hidden passages
    the player has not yet discovered.
  - Always return plain dicts — not live WorldModel references.
  - Temple AI context includes evaluation scores (rounded integers).
  - Explorer AI context focuses on navigation, inventory, and recent events.
  - Judgment context is a comprehensive journey summary for the Final Chamber.

Blueprint Reference: Chapter 10, Section 10.4.9 — AI Context
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.world.world_model import WorldModel


# ---------------------------------------------------------------------------
# Temple AI context
# ---------------------------------------------------------------------------

def get_temple_ai_context(wm: "WorldModel") -> dict:
    """
    Build the Temple AI context snapshot.

    Includes:
      - Current room and phase
      - Evaluation attribute scores (rounded, no raw history)
      - Recent player behaviour (last 10 history entries)
      - Active dynamic events
      - Torch state and flood level
      - Turn number and temple awareness
      - Recent command pattern (last 5 commands)

    Never includes:
      - Puzzle solutions
      - Future room contents
      - Judgment thresholds
    """
    eval_ = wm.evaluation
    recent = wm.history.get_last_n_entries(10)

    return {
        "turn": wm.world.current_turn,
        "temple_phase": wm.world.temple_phase.value,
        "temple_awareness": round(wm.world.temple_awareness, 1),
        "current_room": wm.player.current_room,
        "torch_state": wm.player.torch.state,
        "torch_fuel": wm.player.torch.fuel,
        "flood_level": wm.world.flood_level.value,
        "world_stability": round(wm.world.world_stability, 1),
        "active_events": list(wm.dynamic_events.active_events),
        "evaluation": {
            "observation": round(eval_.observation.score),
            "curiosity": round(eval_.curiosity.score),
            "wisdom": round(eval_.wisdom.score),
            "patience": round(eval_.patience.score),
            "adaptation": round(eval_.adaptation.score),
            "integrity": round(eval_.integrity.score),
            "responsibility": round(eval_.responsibility.score),
            "understanding": round(eval_.understanding.score),
            "greed": round(eval_.greed.score),
            "recklessness": round(eval_.recklessness.score),
        },
        "recent_behaviour": [
            {
                "turn": e.turn,
                "category": e.category,
                "description": e.description,
                "room": e.room_id,
            }
            for e in recent
        ],
        "recent_commands": list(wm.player.command_history[-5:]),
        "rooms_visited": len(wm.player.visited_rooms),
        "current_puzzle_id": (
            wm.get_current_room().puzzle_id
            if wm.get_current_room() else None
        ),
        "solved_puzzles": [
            pid for pid, ps in wm.puzzles.items()
            if ps.status.value == "solved"
        ],
        "failed_puzzles": [
            pid for pid, ps in wm.puzzles.items()
            if ps.failure_count > 0
        ],
    }


# ---------------------------------------------------------------------------
# Explorer AI context
# ---------------------------------------------------------------------------

def get_explorer_ai_context(wm: "WorldModel") -> dict:
    """
    Build the Explorer AI context snapshot.

    Includes:
      - Current room, visible exits, visible objects
      - Player inventory (object IDs and names)
      - Active mission goal
      - Recent discoveries (lore, symbols)
      - Exploration history (rooms visited in order)
      - Completed and in-progress puzzles (no solutions)
      - Recent player commands
      - Dynamic events summary

    Never includes:
      - Future room contents
      - Puzzle solutions
      - Undiscovered hidden passages
    """
    room = wm.get_current_room()
    visible_exits = []
    nearby_objects = []

    if room:
        visible_exits = [
            d for d, dest in room.accessible_exits.items()
            if dest
        ]
        nearby_objects = [
            {
                "id": oid,
                "name": wm.objects[oid].name if oid in wm.objects else oid,
                "state": wm.objects[oid].state if oid in wm.objects else "",
            }
            for oid in room.object_ids_present
            if oid in wm.objects and wm.objects[oid].visible
        ]

    inventory_objects = [
        {
            "id": oid,
            "name": wm.objects[oid].name if oid in wm.objects else oid,
        }
        for oid in wm.player.inventory
    ]

    puzzle_summary = []
    for pid, ps in wm.puzzles.items():
        puzzle_summary.append({
            "puzzle_id": pid,
            "room_id": ps.room_id,
            "status": ps.status.value,
            "attempts": ps.attempt_count,
            "hints_used": ps.hint_count,
        })

    recent_history = [
        {
            "turn": e.turn,
            "category": e.category,
            "description": e.description,
        }
        for e in wm.history.get_last_n_entries(10)
    ]

    return {
        "turn": wm.world.current_turn,
        "current_room": wm.player.current_room,
        "room_description": (
            wm.get_current_room().room_id.replace("_", " ").title()
            if wm.get_current_room() else ""
        ),
        "visible_exits": visible_exits,
        "nearby_objects": nearby_objects,
        "inventory": inventory_objects,
        "torch_state": wm.player.torch.state,
        "torch_fuel": wm.player.torch.fuel,
        "active_mission": wm.mission.current_goal_description,
        "lore_discovered": list(wm.story.lore_ids_discovered),
        "symbols_known": list(wm.story.symbols_encountered),
        "rooms_visited": list(wm.player.visited_rooms),
        "movement_history": list(wm.player.movement_history[-10:]),
        "puzzle_summary": puzzle_summary,
        "recent_history": recent_history,
        "recent_commands": list(wm.player.command_history[-5:]),
        "active_events": list(wm.dynamic_events.active_events),
        "flood_level": wm.world.flood_level.value,
        "temple_phase": wm.world.temple_phase.value,
        "current_puzzle_id": (
            wm.get_current_room().puzzle_id
            if wm.get_current_room() else None
        ),
    }


# ---------------------------------------------------------------------------
# Judgment context (Final Chamber)
# ---------------------------------------------------------------------------

def get_judgment_context(wm: "WorldModel") -> dict:
    """
    Build the comprehensive journey summary for the final judgment.

    Used by the Judgment AI (Template 7) to construct the evaluation narrative.
    Includes the full evaluation scores, complete puzzle history, and
    complete exploration record.

    Never includes the judgment thresholds themselves.
    """
    eval_ = wm.evaluation

    puzzle_detail = []
    for pid, ps in wm.puzzles.items():
        puzzle_detail.append({
            "puzzle_id": pid,
            "room_id": ps.room_id,
            "category": ps.category.value,
            "status": ps.status.value,
            "attempt_count": ps.attempt_count,
            "failure_count": ps.failure_count,
            "hint_count": ps.hint_count,
            "solved_without_hints": ps.solved_without_hints,
            "time_to_solve_turns": ps.time_to_solve_turns,
            "observation_before_action": ps.observation_before_action,
        })

    history_entries = [
        {
            "turn": e.turn,
            "category": e.category,
            "description": e.description,
            "room_id": e.room_id,
        }
        for e in wm.history.entries
    ]

    return {
        "total_turns": wm.world.current_turn,
        "temple_phase": wm.world.temple_phase.value,
        "rooms_visited": list(wm.player.visited_rooms),
        "rooms_visited_count": len(wm.player.visited_rooms),
        "lore_discovered": list(wm.story.lore_ids_discovered),
        "symbols_known": list(wm.story.symbols_encountered),
        "chapters_reached": list(wm.story.chapters_reached),
        "entrance_inscription_read": wm.story.entrance_inscription_read,
        "inventory_final": list(wm.player.inventory),
        "evaluation": {
            "observation": round(eval_.observation.score, 1),
            "curiosity": round(eval_.curiosity.score, 1),
            "wisdom": round(eval_.wisdom.score, 1),
            "patience": round(eval_.patience.score, 1),
            "adaptation": round(eval_.adaptation.score, 1),
            "integrity": round(eval_.integrity.score, 1),
            "responsibility": round(eval_.responsibility.score, 1),
            "understanding": round(eval_.understanding.score, 1),
            "greed": round(eval_.greed.score, 1),
            "recklessness": round(eval_.recklessness.score, 1),
        },
        "puzzle_history": puzzle_detail,
        "full_history": history_entries,
        "steps_taken": wm.player.steps_taken,
        "commands_issued": len(wm.player.command_history),
    }
