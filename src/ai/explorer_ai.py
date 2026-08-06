"""
explorer_ai.py — The Lost Temple of Rudra

Optional advisor to the player.

Reads the World Model (read-only via sanitised context snapshots) and
recommends the most logical next action based on current room, inventory,
mission state, known clues, and active dynamic events.

The Explorer AI never commands — it suggests.
The player may always ignore its recommendations.
It never spoils future content or reveals puzzle solutions.

Blueprint Reference:
    Chapter 12 — Explorer AI
    Chapter 15 — Software Architecture
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from .ai_memory import AIMemory, MemoryEntry
from .context_builder import get_explorer_ai_context
from .prompt_manager import (
    build_recommendation_prompt,
    build_reflection_prompt,
    build_analysis_prompt,
    build_mission_prompt,
)

if TYPE_CHECKING:
    from src.world.world_model import WorldModel
    from .provider import BaseProvider


# ---------------------------------------------------------------------------
# Recommendation result
# ---------------------------------------------------------------------------

@dataclass
class Recommendation:
    """
    A single suggestion returned by the Explorer AI.

    Fields:
        text        — Human-readable suggestion text.
        confidence  — 0.0–1.0 confidence score.
        source      — "rule_based" | "llm"
        action_hint — Optional canonical action string for UI display.
    """
    text: str = ""
    confidence: float = 0.0
    source: str = "rule_based"
    action_hint: str = ""


# ---------------------------------------------------------------------------
# Explorer AI
# ---------------------------------------------------------------------------

class ExplorerAI:
    """
    Contextual guide for the player.

    Uses a rule-based reasoning pipeline for Version 1.
    Falls back gracefully when the LLM provider is unavailable.

    Blueprint Reference: Chapter 12 — Explorer AI.
    """

    _CONFIDENCE_THRESHOLD = 0.6

    def __init__(
        self,
        provider: Optional["BaseProvider"] = None,
        memory: Optional[AIMemory] = None,
    ) -> None:
        self._provider = provider
        self.memory: AIMemory = memory or AIMemory()

    # ------------------------------------------------------------------
    # Primary recommendation pipeline
    # ------------------------------------------------------------------

    def recommend(self, wm: "WorldModel") -> Recommendation:
        """
        Return the single best next-action recommendation.

        Pipeline:
            1. Build sanitised context snapshot.
            2. Apply rule-based reasoning to produce a candidate.
            3. If LLM available and rule confidence < threshold, try LLM.
            4. Return highest-confidence result.
        """
        ctx = get_explorer_ai_context(wm)
        rule_rec = self._rule_based_recommendation(ctx)

        if (
            self._provider
            and self._provider.is_available()
            and rule_rec.confidence < self._CONFIDENCE_THRESHOLD
        ):
            sys_msg, prompt = build_recommendation_prompt(ctx)
            response = self._provider.send_prompt(prompt, system=sys_msg)
            if response.success and response.text:
                return Recommendation(
                    text=response.text,
                    confidence=0.8,
                    source="llm",
                )

        return rule_rec

    # ------------------------------------------------------------------
    # History recall
    # ------------------------------------------------------------------

    def recall_discoveries(self, wm: "WorldModel") -> str:
        """
        Summarise what the explorer has discovered so far.
        Used for the 'history' and 'summary' commands.
        """
        ctx = get_explorer_ai_context(wm)

        if self._provider and self._provider.is_available():
            sys_msg, prompt = build_reflection_prompt(ctx)
            response = self._provider.send_prompt(prompt, system=sys_msg)
            if response.success and response.text:
                return response.text

        return self._rule_based_reflection(ctx)

    # ------------------------------------------------------------------
    # Room analysis
    # ------------------------------------------------------------------

    def analyze_room(self, wm: "WorldModel") -> str:
        """
        Provide an analytical observation of the current room.
        Used for the 'analyze' command.
        """
        ctx = get_explorer_ai_context(wm)

        if self._provider and self._provider.is_available():
            sys_msg, prompt = build_analysis_prompt(ctx)
            response = self._provider.send_prompt(prompt, system=sys_msg)
            if response.success and response.text:
                return response.text

        return self._rule_based_analysis(ctx)

    # ------------------------------------------------------------------
    # Answer lore question
    # ------------------------------------------------------------------

    def answer_lore_question(self, wm: "WorldModel", question: str) -> str:
        """
        Answer a lore question based only on what has been discovered.
        Never invents information not present in the World Model.
        """
        ctx = get_explorer_ai_context(wm)
        lore = ctx.get("lore_discovered", [])
        symbols = ctx.get("symbols_known", [])

        self.memory.record(MemoryEntry(
            turn=wm.world.current_turn,
            event_type="decision",
            subject="lore_question",
            detail=question[:80],
            source="explorer_ai",
        ))

        if not lore and not symbols:
            return (
                "You have not yet discovered enough lore to answer that. "
                "Keep exploring and reading inscriptions."
            )

        if self._provider and self._provider.is_available():
            from .prompt_manager import _SYSTEM_EXPLORER
            prompt = (
                f"Explorer question: \"{question}\"\n"
                f"Discovered lore: {', '.join(lore) or 'none'}\n"
                f"Known symbols: {', '.join(str(s) for s in symbols) or 'none'}\n\n"
                "Answer based ONLY on the discovered lore above. "
                "If the answer isn't known from context, say so honestly."
            )
            response = self._provider.send_prompt(prompt, system=_SYSTEM_EXPLORER)
            if response.success and response.text:
                return response.text

        return self._rule_based_lore_answer(lore, symbols, question)

    # ------------------------------------------------------------------
    # Mission summary
    # ------------------------------------------------------------------

    def summarise_mission(self, wm: "WorldModel") -> str:
        """Return a brief atmospheric mission objective summary."""
        ctx = get_explorer_ai_context(wm)

        if self._provider and self._provider.is_available():
            sys_msg, prompt = build_mission_prompt(ctx)
            response = self._provider.send_prompt(prompt, system=sys_msg)
            if response.success and response.text:
                return response.text

        return ctx.get("active_mission", "Explore the temple.")

    # ------------------------------------------------------------------
    # Rule-based reasoning
    # ------------------------------------------------------------------

    def _rule_based_recommendation(self, ctx: dict) -> Recommendation:
        """
        Deterministic recommendation pipeline based on game state.

        Priority order:
            1. Unlit torch — light it
            2. Active flood — move to higher ground
            3. Unexamined objects in room — inspect them
            4. Active puzzle — attempt it
            5. Unvisited exit — explore it
            6. Generic exploration
        """
        torch_state = ctx.get("torch_state", "unlit")
        inventory = ctx.get("inventory", [])
        nearby = ctx.get("nearby_objects", [])
        exits = ctx.get("visible_exits", [])
        active_events = ctx.get("active_events", [])
        puzzle_id = ctx.get("current_puzzle_id")
        room = ctx.get("current_room", "").replace("_", " ")
        rooms_visited = ctx.get("rooms_visited", [])

        inv_ids = {obj.get("id", "") for obj in inventory}

        # 1. Unlit torch — highest priority
        if torch_state in ("unlit", "extinguished"):
            torch_in_inv = any(
                "torch" in obj.get("id", "").lower()
                or "torch" in obj.get("name", "").lower()
                for obj in inventory
            )
            if torch_in_inv:
                return Recommendation(
                    text="Your torch is unlit. Light it before venturing deeper.",
                    confidence=0.95,
                    source="rule_based",
                    action_hint="light torch",
                )

        # 2. Flood active — urgent warning
        if "flood" in active_events:
            return Recommendation(
                text=(
                    "Water is rising. Move away from the lower chambers — "
                    "the flood control room may offer a solution."
                ),
                confidence=0.9,
                source="rule_based",
                action_hint="go",
            )

        # 3. Unexamined nearby objects
        if nearby:
            unexamined = [
                obj for obj in nearby
                if obj.get("state", "") not in ("read", "studied", "discovered", "used")
            ]
            if unexamined:
                name = unexamined[0].get("name", "the object here")
                return Recommendation(
                    text=f"There is {name} here you haven't examined closely. Inspect it.",
                    confidence=0.8,
                    source="rule_based",
                    action_hint=f"inspect {name.lower()}",
                )

        # 4. Active puzzle
        if puzzle_id:
            puzzle_name = puzzle_id.replace("puzzle_", "").replace("_", " ")
            return Recommendation(
                text=f"The {puzzle_name} mechanism is here. Consider examining it before acting.",
                confidence=0.75,
                source="rule_based",
                action_hint=f"inspect {puzzle_name}",
            )

        # 5. Unexplored exits
        unvisited_exits = [
            d for d in exits
            if d not in rooms_visited
        ]
        if unvisited_exits:
            direction = unvisited_exits[0]
            return Recommendation(
                text=f"You haven't explored to the {direction} yet. That passage awaits.",
                confidence=0.7,
                source="rule_based",
                action_hint=f"go {direction}",
            )

        # 6. Generic
        if exits:
            direction = exits[0]
            return Recommendation(
                text=f"Continue your exploration. The passage to the {direction} remains.",
                confidence=0.5,
                source="rule_based",
                action_hint=f"go {direction}",
            )

        return Recommendation(
            text=(
                "Look carefully around the room. "
                "There may be details that warrant closer attention."
            ),
            confidence=0.4,
            source="rule_based",
            action_hint="look",
        )

    def _rule_based_reflection(self, ctx: dict) -> str:
        """Return a simple discovery summary without LLM."""
        rooms = ctx.get("rooms_visited", [])
        lore = ctx.get("lore_discovered", [])
        puzzles = ctx.get("puzzle_summary", [])
        solved = [p for p in puzzles if p.get("status") == "solved"]
        turn = ctx.get("turn", 0)

        parts = [f"By turn {turn} you have explored {len(rooms)} room(s)."]
        if solved:
            names = ", ".join(
                p["puzzle_id"].replace("_", " ") for p in solved
            )
            parts.append(f"Mechanisms resolved: {names}.")
        if lore:
            parts.append(f"Lore discovered: {len(lore)} entry(ies).")
        else:
            parts.append("No lore has been discovered yet.")

        return " ".join(parts)

    def _rule_based_analysis(self, ctx: dict) -> str:
        """Return a brief room analysis without LLM."""
        room = ctx.get("current_room", "unknown").replace("_", " ").title()
        nearby = ctx.get("nearby_objects", [])
        exits = ctx.get("visible_exits", [])
        puzzle_id = ctx.get("current_puzzle_id")

        parts = [f"You are in {room}."]
        if nearby:
            names = ", ".join(obj.get("name", "?") for obj in nearby)
            parts.append(f"Objects of interest: {names}.")
        if puzzle_id:
            pname = puzzle_id.replace("puzzle_", "").replace("_", " ")
            parts.append(f"A {pname} mechanism is present — it has not been resolved.")
        if exits:
            parts.append(f"Visible exits: {', '.join(exits)}.")
        return " ".join(parts)

    def _rule_based_lore_answer(
        self, lore: list, symbols: list, question: str
    ) -> str:
        """Minimal lore answer based on known entries."""
        q = question.lower()
        if "symbol" in q and symbols:
            return (
                f"You have encountered these symbols: "
                f"{', '.join(str(s) for s in symbols)}."
            )
        if lore:
            return (
                f"From what you have read, {len(lore)} lore entry(ies) are known. "
                "Inspect inscriptions and scrolls to learn more."
            )
        return (
            "That knowledge has not yet been uncovered. "
            "Explore further and read what you find."
        )
