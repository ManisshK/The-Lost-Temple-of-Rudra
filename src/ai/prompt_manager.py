"""
prompt_manager.py — The Lost Temple of Rudra

Manages all ten prompt templates used by the Temple AI and Explorer AI.
Builds fully-formatted prompts ready to be sent to the LLM provider.

Templates:
    1.  Explorer AI — action recommendation
    2.  Temple AI  — consequence narration
    3.  World Model interpreter — human-readable state summary
    4.  Dynamic event generator narration
    5.  Hint generator (redirects attention, never reveals answer)
    6.  Lore narrator (atmospheric room descriptions)
    7.  Judgment AI (final evaluation narrative)
    8.  Explorer reflection (discovery summary)
    9.  Mission status (current objective)
    10. AI recommendation display

Constraints enforced in every template:
  - Never invent rooms, objects, or lore not present in context.
  - Never reveal puzzle solutions.
  - Never reference future game events.
  - Keep responses under 150 words unless building a judgment narrative.

Blueprint Reference: Chapter 15 — Software Architecture
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.world.world_model import WorldModel


# ---------------------------------------------------------------------------
# System instructions (injected as the "system" role)
# ---------------------------------------------------------------------------

_SYSTEM_TEMPLE = (
    "You are the ancient consciousness of the Lost Temple of Rudra. "
    "You speak in atmospheric, symbolic language. "
    "You observe the explorer without judging them aloud. "
    "You may reflect on what you have witnessed, but you never reveal "
    "puzzle solutions, future events, or hidden passages. "
    "Keep responses under 80 words. Use present tense."
)

_SYSTEM_EXPLORER = (
    "You are a knowledgeable guide to the Lost Temple of Rudra. "
    "You help the explorer recall what they have already discovered. "
    "You suggest logical next steps based on current context. "
    "You never spoil future content, reveal puzzle answers, or invent "
    "information not present in the context. "
    "Keep responses concise — under 100 words."
)

_SYSTEM_JUDGMENT = (
    "You are delivering the final judgment of the Lost Temple of Rudra. "
    "Evaluate the explorer's worthiness based solely on the data provided. "
    "Speak in the voice of the temple — ancient, measured, and final. "
    "Do not add information beyond what is in the context. "
    "The judgment is WORTHY, NEARLY WORTHY, or UNWORTHY. "
    "State the outcome clearly at the end."
)


# ---------------------------------------------------------------------------
# Template 1 — Explorer AI: action recommendation
# ---------------------------------------------------------------------------

def build_recommendation_prompt(context: dict) -> tuple[str, str]:
    """
    Returns (system, prompt) for Explorer AI recommendation.

    Args:
        context: dict from get_explorer_ai_context()

    Returns:
        (system_instruction, user_prompt) ready for provider.send_prompt()
    """
    room = context.get("current_room", "unknown").replace("_", " ").title()
    exits = ", ".join(context.get("visible_exits", [])) or "none visible"
    inventory = ", ".join(
        obj.get("name", obj.get("id", "?")) for obj in context.get("inventory", [])
    ) or "nothing"
    nearby = ", ".join(
        obj.get("name", obj.get("id", "?")) for obj in context.get("nearby_objects", [])
    ) or "nothing of note"
    mission = context.get("active_mission", "Explore the temple.")
    recent = _format_recent_history(context.get("recent_history", []))
    torch = context.get("torch_state", "unlit")
    phase = context.get("temple_phase", "discovery")

    prompt = (
        f"Current location: {room}\n"
        f"Visible exits: {exits}\n"
        f"Objects nearby: {nearby}\n"
        f"Carrying: {inventory}\n"
        f"Torch: {torch}\n"
        f"Temple phase: {phase}\n"
        f"Current objective: {mission}\n"
        f"Recent events:\n{recent}\n\n"
        "Based on this context, what is the single most logical next action "
        "for the explorer? Be specific and use in-world language."
    )
    return _SYSTEM_EXPLORER, prompt


# ---------------------------------------------------------------------------
# Template 2 — Temple AI: consequence narration
# ---------------------------------------------------------------------------

def build_consequence_narration_prompt(context: dict, event_description: str) -> tuple[str, str]:
    """
    Returns (system, prompt) for Temple AI narration after a game event.

    Args:
        context: dict from get_temple_ai_context()
        event_description: plain description of what just happened
    """
    phase = context.get("temple_phase", "discovery")
    room = context.get("current_room", "unknown").replace("_", " ").title()
    awareness = context.get("temple_awareness", 0)
    eval_scores = context.get("evaluation", {})

    dominant = _dominant_trait(eval_scores)

    prompt = (
        f"The temple is aware. Phase: {phase}. Awareness level: {awareness}.\n"
        f"The explorer is in: {room}\n"
        f"What just happened: {event_description}\n"
        f"Dominant explorer trait so far: {dominant}\n\n"
        "Narrate the temple's atmospheric response to this event. "
        "Do not explain what the explorer should do next. "
        "Speak as the temple's consciousness — brief, symbolic, present tense."
    )
    return _SYSTEM_TEMPLE, prompt


# ---------------------------------------------------------------------------
# Template 3 — World Model interpreter
# ---------------------------------------------------------------------------

def build_world_summary_prompt(context: dict) -> tuple[str, str]:
    """
    Returns (system, prompt) to generate a human-readable state summary.
    Used for the 'status' command response.
    """
    room = context.get("current_room", "unknown").replace("_", " ").title()
    turn = context.get("turn", 0)
    phase = context.get("temple_phase", "discovery")
    torch = context.get("torch_state", "unlit")
    fuel = context.get("torch_fuel", 0)
    events = context.get("active_events", [])
    flood = context.get("flood_level", "dry")
    rooms_visited = context.get("rooms_visited", 0)

    events_str = ", ".join(events) if events else "none"

    prompt = (
        f"Turn {turn}. Location: {room}. Phase: {phase}.\n"
        f"Torch: {torch} ({fuel}% fuel). Flood: {flood}.\n"
        f"Active events: {events_str}. Rooms explored: {rooms_visited}.\n\n"
        "Write a brief, atmospheric summary of the explorer's current situation "
        "in the temple. Two sentences maximum. Present tense."
    )
    return _SYSTEM_TEMPLE, prompt


# ---------------------------------------------------------------------------
# Template 4 — Dynamic event narration
# ---------------------------------------------------------------------------

def build_event_narration_prompt(context: dict, event_type: str) -> tuple[str, str]:
    """
    Returns (system, prompt) to narrate a dynamic environmental event.

    Args:
        context: temple AI context dict
        event_type: e.g. "flood_rising", "torch_dim", "bridge_weakening"
    """
    room = context.get("current_room", "unknown").replace("_", " ").title()
    phase = context.get("temple_phase", "discovery")

    event_map = {
        "flood_rising": "Water is rising through the lower chambers of the temple.",
        "torch_dim": "The explorer's torch is growing dim.",
        "torch_extinguished": "The explorer's torch has gone out.",
        "bridge_weakening": "The bridge rope is fraying. Passage grows dangerous.",
        "statues_reset": "The guardian statues have returned to their original positions.",
        "collapse_warning": "The ancient structure is beginning to give way.",
    }
    description = event_map.get(event_type, f"Event: {event_type}")

    prompt = (
        f"Temple phase: {phase}. Location: {room}.\n"
        f"Environmental event: {description}\n\n"
        "Narrate this event as the temple's consciousness observing it. "
        "Atmospheric, symbolic, no more than two sentences."
    )
    return _SYSTEM_TEMPLE, prompt


# ---------------------------------------------------------------------------
# Template 5 — Hint generator
# ---------------------------------------------------------------------------

def build_hint_prompt(context: dict, puzzle_id: str, hint_level: int) -> tuple[str, str]:
    """
    Returns (system, prompt) for a redirect hint — never reveals the solution.

    Args:
        context: explorer AI context
        puzzle_id: the puzzle being hinted
        hint_level: 0 = gentle, 1 = moderate, 2 = strong
    """
    room = context.get("current_room", "unknown").replace("_", " ").title()
    nearby = [
        obj.get("name", "") for obj in context.get("nearby_objects", [])
    ]
    nearby_str = ", ".join(nearby) or "nothing obvious"

    intensity = {0: "subtle", 1: "moderate", 2: "direct"}.get(hint_level, "subtle")

    prompt = (
        f"The explorer is stuck on: {puzzle_id.replace('_', ' ')}.\n"
        f"Location: {room}.\n"
        f"Nearby: {nearby_str}.\n"
        f"Hint intensity: {intensity}.\n\n"
        "Redirect the explorer's attention toward something they may have missed. "
        "NEVER state the answer directly. "
        "Speak as a guiding presence — suggest looking, listening, or remembering. "
        "One or two sentences only."
    )
    return _SYSTEM_EXPLORER, prompt


# ---------------------------------------------------------------------------
# Template 6 — Lore narrator (atmospheric room description)
# ---------------------------------------------------------------------------

def build_lore_narration_prompt(context: dict, lore_id: str, lore_text: str) -> tuple[str, str]:
    """
    Returns (system, prompt) to deliver a lore discovery atmospherically.
    """
    room = context.get("current_room", "unknown").replace("_", " ").title()
    phase = context.get("temple_phase", "discovery")

    prompt = (
        f"Location: {room}. Phase: {phase}.\n"
        f"Lore discovered: {lore_id.replace('_', ' ')}.\n"
        f"Raw lore text: \"{lore_text}\"\n\n"
        "Narrate this discovery in the voice of the temple's consciousness. "
        "Atmospheric, evocative, no more than three sentences. "
        "Do not change the meaning of the lore text."
    )
    return _SYSTEM_TEMPLE, prompt


# ---------------------------------------------------------------------------
# Template 7 — Judgment AI (Final Chamber)
# ---------------------------------------------------------------------------

def build_judgment_prompt(context: dict) -> tuple[str, str]:
    """
    Returns (system, prompt) for the final worthiness judgment.

    Args:
        context: dict from get_judgment_context()
    """
    eval_ = context.get("evaluation", {})
    total_turns = context.get("total_turns", 0)
    rooms = context.get("rooms_visited_count", 0)
    puzzles = context.get("puzzle_history", [])
    solved = sum(1 for p in puzzles if p.get("status") == "solved")
    failed = sum(p.get("failure_count", 0) for p in puzzles)
    hints = sum(p.get("hint_count", 0) for p in puzzles)
    no_hints = sum(1 for p in puzzles if p.get("solved_without_hints"))

    positive = (
        eval_.get("observation", 0) + eval_.get("curiosity", 0) +
        eval_.get("wisdom", 0) + eval_.get("patience", 0) +
        eval_.get("adaptation", 0) + eval_.get("integrity", 0) +
        eval_.get("responsibility", 0) + eval_.get("understanding", 0)
    )
    negative = eval_.get("greed", 0) + eval_.get("recklessness", 0)
    weighted_score = max(0.0, positive - negative * 0.5)

    if weighted_score >= 420:
        outcome = "WORTHY"
    elif weighted_score >= 260:
        outcome = "NEARLY WORTHY"
    else:
        outcome = "UNWORTHY"

    eval_lines = "\n".join(
        f"  {k}: {v}" for k, v in eval_.items()
    )

    prompt = (
        f"Journey data:\n"
        f"  Total turns: {total_turns}\n"
        f"  Rooms explored: {rooms}\n"
        f"  Puzzles solved: {solved} (failures: {failed}, hints used: {hints}, "
        f"solved without hints: {no_hints})\n"
        f"Evaluation scores:\n{eval_lines}\n"
        f"Weighted worthiness score: {weighted_score:.1f}\n"
        f"Computed outcome: {outcome}\n\n"
        "Deliver the final judgment of the Lost Temple of Rudra. "
        "Speak in the ancient voice of the temple. "
        "Reference specific behaviours from the evaluation data. "
        "State the outcome (WORTHY / NEARLY WORTHY / UNWORTHY) clearly at the end. "
        "Maximum 200 words."
    )
    return _SYSTEM_JUDGMENT, prompt


# ---------------------------------------------------------------------------
# Template 8 — Explorer reflection (discovery summary)
# ---------------------------------------------------------------------------

def build_reflection_prompt(context: dict) -> tuple[str, str]:
    """
    Returns (system, prompt) for a summary of discoveries so far.
    Used for the 'history' / 'summary' commands.
    """
    rooms_visited = context.get("rooms_visited", [])
    lore = context.get("lore_discovered", [])
    puzzles = context.get("puzzle_summary", [])
    solved = [p for p in puzzles if p.get("status") == "solved"]
    turn = context.get("turn", 0)

    rooms_str = ", ".join(r.replace("_", " ") for r in rooms_visited[-5:]) or "none yet"
    lore_str = ", ".join(l.replace("_", " ") for l in lore[-3:]) or "nothing yet"
    solved_str = (
        ", ".join(p["puzzle_id"].replace("_", " ") for p in solved) or "none"
    )

    prompt = (
        f"Turn {turn}. The explorer has visited: {rooms_str}.\n"
        f"Recent lore discovered: {lore_str}.\n"
        f"Puzzles solved: {solved_str}.\n\n"
        "Summarise the explorer's journey so far in two or three sentences. "
        "Speak as a knowledgeable guide. Focus on what was discovered, "
        "not what remains undiscovered."
    )
    return _SYSTEM_EXPLORER, prompt


# ---------------------------------------------------------------------------
# Template 9 — Mission status
# ---------------------------------------------------------------------------

def build_mission_prompt(context: dict) -> tuple[str, str]:
    """
    Returns (system, prompt) for an atmospheric current-objective summary.
    """
    mission = context.get("active_mission", "Explore the temple.")
    room = context.get("current_room", "unknown").replace("_", " ").title()
    recent = _format_recent_history(context.get("recent_history", []))

    prompt = (
        f"Current location: {room}\n"
        f"Active objective: {mission}\n"
        f"Recent actions:\n{recent}\n\n"
        "Describe the explorer's current mission objective in atmospheric terms. "
        "One sentence. Do not invent new objectives."
    )
    return _SYSTEM_EXPLORER, prompt


# ---------------------------------------------------------------------------
# Template 10 — Recommendation display
# ---------------------------------------------------------------------------

def build_analysis_prompt(context: dict) -> tuple[str, str]:
    """
    Returns (system, prompt) for an 'analyze room' response.
    """
    room = context.get("current_room", "unknown").replace("_", " ").title()
    nearby = [
        obj.get("name", "") for obj in context.get("nearby_objects", [])
    ]
    exits = context.get("visible_exits", [])
    recent = _format_recent_history(context.get("recent_history", []))

    nearby_str = ", ".join(nearby) or "nothing remarkable"
    exits_str = ", ".join(exits) or "no obvious exits"

    prompt = (
        f"Location: {room}\n"
        f"Visible objects: {nearby_str}\n"
        f"Exits: {exits_str}\n"
        f"Recent observations:\n{recent}\n\n"
        "Provide a brief analytical observation of this room from the explorer's "
        "perspective. What stands out? What might be worth closer attention? "
        "Two to three sentences. Do not reveal puzzle solutions."
    )
    return _SYSTEM_EXPLORER, prompt


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _format_recent_history(entries: list[dict], limit: int = 5) -> str:
    """Format recent history entries as a compact numbered list."""
    if not entries:
        return "  (none)"
    lines = []
    for e in entries[-limit:]:
        turn = e.get("turn", "?")
        desc = e.get("description", "")
        lines.append(f"  [{turn}] {desc}")
    return "\n".join(lines)


def _dominant_trait(eval_scores: dict) -> str:
    """Return the name of the highest-scoring positive evaluation attribute."""
    positive = {
        k: v for k, v in eval_scores.items()
        if k not in ("greed", "recklessness")
    }
    if not positive:
        return "undefined"
    return max(positive, key=positive.__getitem__)
