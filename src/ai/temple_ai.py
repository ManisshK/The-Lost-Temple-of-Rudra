"""
temple_ai.py — The Lost Temple of Rudra

The Guardian Consciousness of the temple.

Observes the explorer through the World Model (read-only via AIContext),
evaluates behaviour across the ten Guardian attributes, generates atmospheric
narration, and performs the final judgment when the explorer reaches the
Final Chamber.

The Temple AI NEVER writes to the World Model directly.
All evaluation updates pass through the Game Engine's write interface.

Blueprint Reference:
    Chapter 11 — Temple AI & Guardian Evaluation
    Chapter 11.3 — Silent Evaluation
    Chapter 11.4 — Judgment System
    Chapter 11.6 — Evaluation Engine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from .ai_memory import AIMemory, MemoryEntry
from .context_builder import get_temple_ai_context
from .prompt_manager import (
    build_consequence_narration_prompt,
    build_hint_prompt,
    build_judgment_prompt,
    build_event_narration_prompt,
)

if TYPE_CHECKING:
    from src.world.world_model import WorldModel
    from .provider import BaseProvider


# ---------------------------------------------------------------------------
# Observation result (returned by Temple AI, consumed by Game Engine)
# ---------------------------------------------------------------------------

@dataclass
class TempleObservation:
    """
    The Temple AI's response to a player action.

    Carries:
      - eval_deltas: {attribute: delta} — passed to Game Engine for writing
      - narration: atmospheric text shown to the player (if any)
      - hint: optional redirect hint text
      - is_significant: True when the event merits a history entry
    """
    eval_deltas: dict[str, float] = field(default_factory=dict)
    narration: str = ""
    hint: str = ""
    is_significant: bool = False
    event_type: str = ""


# ---------------------------------------------------------------------------
# Behaviour pattern detection thresholds
# ---------------------------------------------------------------------------

_REPEAT_FAIL_THRESHOLD = 3   # Failures on same puzzle before offering hint
_RUSH_THRESHOLD = 5          # Consecutive moves without observing = reckless
_CURIOSITY_BONUS_ROOMS = 3   # Extra rooms beyond required path


# ---------------------------------------------------------------------------
# Temple AI
# ---------------------------------------------------------------------------

class TempleAI:
    """
    The temple's observing consciousness.

    Reads the World Model through context snapshots (never directly).
    Records behavioural patterns in AIMemory.
    Returns TempleObservation objects — the Game Engine applies any eval deltas.

    Blueprint Reference: Chapter 11 — Temple AI.
    """

    def __init__(
        self,
        provider: Optional["BaseProvider"] = None,
        memory: Optional[AIMemory] = None,
    ) -> None:
        self._provider = provider
        self.memory: AIMemory = memory or AIMemory()
        self._last_room: Optional[str] = None
        self._moves_without_observe: int = 0

    # ------------------------------------------------------------------
    # Primary observation entry point
    # ------------------------------------------------------------------

    def observe_action(
        self,
        wm: "WorldModel",
        action_str: str,
        target: Optional[str] = None,
        result_success: bool = True,
    ) -> TempleObservation:
        """
        Called by the Game Engine after every player action.
        Evaluates the action and returns deltas + optional narration.

        This method is purely analytical — it never writes to wm.
        """
        obs = TempleObservation()
        ctx = get_temple_ai_context(wm)
        current_room = wm.player.current_room

        # --- Room visit tracking ---
        if current_room != self._last_room:
            self._last_room = current_room
            self.memory.record(MemoryEntry(
                turn=ctx["turn"],
                event_type="room_visited",
                subject=current_room,
                source="temple_ai",
            ))

        # --- Observation behaviour ---
        if action_str in ("look", "inspect", "examine", "read", "listen", "touch"):
            self._moves_without_observe = 0
            # Reward observation
            obs.eval_deltas["observation"] = 1.0
            self.memory.record(MemoryEntry(
                turn=ctx["turn"],
                event_type="recurring_action",
                subject="observe",
                source="temple_ai",
            ))

        # --- Movement without observing ---
        elif action_str in ("go", "enter", "leave", "cross", "climb", "descend"):
            self._moves_without_observe += 1
            if self._moves_without_observe >= _RUSH_THRESHOLD:
                obs.eval_deltas["recklessness"] = 0.5
                obs.eval_deltas["patience"] = -0.5
                self.memory.record(MemoryEntry(
                    turn=ctx["turn"],
                    event_type="recurring_action",
                    subject="rushing",
                    source="temple_ai",
                ))

        # --- Puzzle actions ---
        elif action_str in ("rotate", "push", "pull", "insert", "align", "activate"):
            self._moves_without_observe = 0
            if not result_success:
                puzzle_id = ctx.get("current_puzzle_id") or "unknown_puzzle"
                self.memory.record(MemoryEntry(
                    turn=ctx["turn"],
                    event_type="puzzle_failed",
                    subject=puzzle_id,
                    source="temple_ai",
                ))
                fail_count = self.memory.failure_count_for(puzzle_id)
                if fail_count >= _REPEAT_FAIL_THRESHOLD:
                    obs.eval_deltas["patience"] = -0.5
                    # Patience degradation for repeated failure

        # --- Hidden / ritual actions ---
        elif action_str in ("pray", "meditate", "kneel", "wait", "silence"):
            self._moves_without_observe = 0
            obs.eval_deltas["wisdom"] = 1.0
            obs.eval_deltas["understanding"] = 0.5
            obs.is_significant = True
            self.memory.record(MemoryEntry(
                turn=ctx["turn"],
                event_type="decision",
                subject=action_str,
                detail=f"Performed ritual action: {action_str}",
                source="temple_ai",
            ))

        # --- Greed detection (taking objects rapidly without inspecting) ---
        elif action_str == "take":
            obs_count = self.memory.get_behaviour_count("observe")
            take_count = self.memory.get_behaviour_count("take_action")
            self.memory.record(MemoryEntry(
                turn=ctx["turn"],
                event_type="recurring_action",
                subject="take_action",
                source="temple_ai",
            ))
            # If takes >> observations, flag greed
            if take_count > 0 and obs_count < take_count:
                obs.eval_deltas["greed"] = 0.5

        # --- Narration (rule-based fallback) ---
        obs.narration = self._rule_based_narration(ctx, action_str, result_success)

        # --- LLM narration if provider available ---
        if self._provider and self._provider.is_available() and obs.is_significant:
            event_desc = f"Player performed '{action_str}'" + (
                f" on '{target}'" if target else ""
            )
            sys_msg, prompt = build_consequence_narration_prompt(ctx, event_desc)
            response = self._provider.send_prompt(prompt, system=sys_msg)
            if response.success and response.text:
                obs.narration = response.text

        return obs

    # ------------------------------------------------------------------
    # Puzzle solved callback
    # ------------------------------------------------------------------

    def on_puzzle_solved(self, wm: "WorldModel", puzzle_id: str) -> TempleObservation:
        """Called by Game Engine when a puzzle is solved."""
        obs = TempleObservation(is_significant=True, event_type="puzzle_solved")
        ctx = get_temple_ai_context(wm)
        puzzle = wm.puzzles.get(puzzle_id)

        if puzzle:
            if puzzle.hint_count == 0:
                obs.eval_deltas["wisdom"] = 3.0
                obs.eval_deltas["patience"] = 2.0
            else:
                obs.eval_deltas["wisdom"] = 1.0

            if puzzle.observation_before_action:
                obs.eval_deltas["observation"] = 2.0

            if puzzle.time_to_solve_turns and puzzle.time_to_solve_turns <= 5:
                obs.eval_deltas["adaptation"] = 1.0

        self.memory.record(MemoryEntry(
            turn=ctx["turn"],
            event_type="puzzle_solved",
            subject=puzzle_id,
            detail=f"Solved in {puzzle.attempt_count if puzzle else '?'} attempts",
            source="temple_ai",
        ))

        obs.narration = self._solve_narration(puzzle_id)
        return obs

    # ------------------------------------------------------------------
    # Lore discovered callback
    # ------------------------------------------------------------------

    def on_lore_discovered(self, wm: "WorldModel", lore_id: str) -> TempleObservation:
        """Called by Game Engine when a lore entry is discovered."""
        obs = TempleObservation(is_significant=True, event_type="lore_discovered")
        ctx = get_temple_ai_context(wm)
        obs.eval_deltas["understanding"] = 1.5
        obs.eval_deltas["curiosity"] = 0.5

        self.memory.record(MemoryEntry(
            turn=ctx["turn"],
            event_type="lore_discovered",
            subject=lore_id,
            source="temple_ai",
        ))
        return obs

    # ------------------------------------------------------------------
    # Hint generation
    # ------------------------------------------------------------------

    def generate_hint(self, wm: "WorldModel") -> str:
        """
        Generate a redirect hint for the current puzzle.
        Returns empty string if no puzzle is active.
        Never reveals the solution — only redirects attention.
        """
        from .context_builder import get_explorer_ai_context
        ctx = get_explorer_ai_context(wm)
        puzzle_id = ctx.get("current_puzzle_id") or ""
        if not puzzle_id:
            return (
                "The temple offers no guidance here. "
                "Perhaps look more carefully at your surroundings."
            )

        puzzle = wm.puzzles.get(puzzle_id)
        hint_level = puzzle.hint_level if puzzle else 0
        self.memory.record(MemoryEntry(
            turn=wm.world.current_turn,
            event_type="hint_given",
            subject=puzzle_id,
            source="temple_ai",
        ))

        # LLM hint
        if self._provider and self._provider.is_available():
            sys_msg, prompt = build_hint_prompt(ctx, puzzle_id, hint_level)
            response = self._provider.send_prompt(prompt, system=sys_msg)
            if response.success and response.text:
                return response.text

        # Rule-based hint fallback
        return self._rule_based_hint(puzzle_id, hint_level)

    # ------------------------------------------------------------------
    # Final judgment
    # ------------------------------------------------------------------

    def compute_judgment(self, wm: "WorldModel") -> tuple[str, str]:
        """
        Compute the final worthiness judgment.

        Returns:
            (outcome_str, narrative_str)
            outcome_str: "worthy" | "nearly_worthy" | "unworthy"
        """
        from .context_builder import get_judgment_context
        ctx = get_judgment_context(wm)
        eval_ = ctx.get("evaluation", {})

        positive = (
            eval_.get("observation", 0) + eval_.get("curiosity", 0) +
            eval_.get("wisdom", 0) + eval_.get("patience", 0) +
            eval_.get("adaptation", 0) + eval_.get("integrity", 0) +
            eval_.get("responsibility", 0) + eval_.get("understanding", 0)
        )
        negative = eval_.get("greed", 0) + eval_.get("recklessness", 0)
        weighted = max(0.0, positive - negative * 0.5)

        if weighted >= 420:
            outcome = "worthy"
        elif weighted >= 260:
            outcome = "nearly_worthy"
        else:
            outcome = "unworthy"

        # LLM judgment
        if self._provider and self._provider.is_available():
            sys_msg, prompt = build_judgment_prompt(ctx)
            response = self._provider.send_prompt(prompt, system=sys_msg)
            if response.success and response.text:
                return outcome, response.text

        # Rule-based fallback
        narrative = self._rule_based_judgment(outcome, eval_, ctx)
        return outcome, narrative

    # ------------------------------------------------------------------
    # Event narration (called by Game Engine on dynamic events)
    # ------------------------------------------------------------------

    def narrate_event(self, wm: "WorldModel", event_type: str) -> str:
        """
        Generate atmospheric narration for a dynamic event.
        Returns empty string if narration is not warranted.
        """
        ctx = get_temple_ai_context(wm)
        if self._provider and self._provider.is_available():
            sys_msg, prompt = build_event_narration_prompt(ctx, event_type)
            response = self._provider.send_prompt(prompt, system=sys_msg)
            if response.success and response.text:
                return response.text
        return self._rule_based_event_narration(event_type)

    # ------------------------------------------------------------------
    # Rule-based fallbacks
    # ------------------------------------------------------------------

    def _rule_based_narration(
        self, ctx: dict, action: str, success: bool
    ) -> str:
        """Minimal atmospheric response without LLM."""
        phase = ctx.get("temple_phase", "discovery")
        awareness = ctx.get("temple_awareness", 0)

        if action in ("pray", "meditate", "kneel"):
            return "The stones remember those who show reverence."
        if action in ("look", "inspect") and success:
            if awareness > 50:
                return "The temple senses your careful attention."
            return ""
        if not success and action in ("rotate", "push", "pull"):
            fail_key = ctx.get("current_puzzle_id", "")
            fails = self.memory.failure_count_for(fail_key) if fail_key else 0
            if fails >= _REPEAT_FAIL_THRESHOLD:
                return "Patience. The mechanism remembers all that has been tried."
        return ""

    def _rule_based_hint(self, puzzle_id: str, hint_level: int) -> str:
        """Return a generic redirect hint by puzzle type."""
        generic = {
            0: "Perhaps there is something here you have not yet examined closely.",
            1: "Consider what you already know. The answer lies in what you have observed.",
            2: "Look at the objects in this room with fresh eyes. Something faces the wrong way.",
        }
        puzzle_hints = {
            "puzzle_guardian_statues": {
                0: "The guardians watch. But what are they watching?",
                1: "Four guardians. Four directions. Consider the geometry.",
                2: "Each guardian should face inward — toward the centre.",
            },
            "puzzle_flood_control": {
                0: "Water flows where you allow it. Control requires the right tool.",
                1: "The mechanism has more than one gate. Order matters.",
                2: "Secondary gate first. The bypass protects what follows.",
            },
        }
        p_hints = puzzle_hints.get(puzzle_id, generic)
        return p_hints.get(hint_level, p_hints.get(max(p_hints.keys()), ""))

    def _solve_narration(self, puzzle_id: str) -> str:
        """Return a brief atmospheric solve acknowledgement."""
        narrations = {
            "puzzle_guardian_statues": (
                "The guardians recognise the configuration. A path opens."
            ),
            "puzzle_flood_control": (
                "The waters relent. The temple acknowledges your understanding."
            ),
            "puzzle_bridge_integrity": (
                "The bridge holds. Your knowledge of its nature made it so."
            ),
        }
        return narrations.get(
            puzzle_id, "The temple acknowledges what has been accomplished."
        )

    def _rule_based_event_narration(self, event_type: str) -> str:
        """Return atmospheric text for a dynamic event."""
        narrations = {
            "flood_rising": (
                "Water remembers every crack. It is patient. It will rise."
            ),
            "torch_dim": (
                "The light grows uncertain. What will you do when darkness comes?"
            ),
            "torch_extinguished": (
                "Darkness. The temple has seen this before. It is not the end — "
                "but it changes everything."
            ),
            "bridge_weakening": (
                "The rope has carried many. It cannot carry patience indefinitely."
            ),
            "statues_reset": (
                "A tremor passes. The guardians return to the beginning."
            ),
            "collapse_warning": (
                "The walls remember all that has been built here. "
                "They are beginning to forget."
            ),
        }
        return narrations.get(event_type, "")

    def _rule_based_judgment(
        self, outcome: str, eval_: dict, ctx: dict
    ) -> str:
        """Generate a rule-based judgment narrative."""
        rooms = ctx.get("rooms_visited_count", 0)
        puzzles_solved = sum(
            1 for p in ctx.get("puzzle_history", []) if p.get("status") == "solved"
        )
        obs = eval_.get("observation", 0)
        curiosity = eval_.get("curiosity", 0)
        reck = eval_.get("recklessness", 0)

        if outcome == "worthy":
            return (
                f"You entered this temple with {rooms} rooms explored and "
                f"{puzzles_solved} mechanisms understood. "
                f"Your observation score of {obs:.0f} and curiosity of {curiosity:.0f} "
                "speak to a mind that looked before it acted. "
                "The temple has watched in silence. It finds you WORTHY."
            )
        elif outcome == "nearly_worthy":
            return (
                f"You explored {rooms} rooms and resolved {puzzles_solved} mechanisms. "
                "There is understanding here — imperfect, but genuine. "
                f"Recklessness ({reck:.0f}) tempered your wisdom. "
                "The temple finds you NEARLY WORTHY. Return wiser."
            )
        else:
            return (
                f"You moved through {rooms} rooms. "
                f"Recklessness ({reck:.0f}) outpaced observation ({obs:.0f}). "
                "The temple has seen you. It has measured you. "
                "It finds you UNWORTHY. The doors remain closed."
            )
