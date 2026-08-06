"""
ai_manager.py — The Lost Temple of Rudra

Central coordinator for all AI systems.

Owns the TempleAI, ExplorerAI, and provider instances.
Provides a unified, isolated interface for the Game Engine to request
narration, hints, recommendations, and evaluations.

The AI Manager is the ONLY layer the Game Engine interacts with —
it never touches TempleAI or ExplorerAI directly.

Architecture constraint:
    AI Manager → Temple AI / Explorer AI → Context Builder → World Model
    AI Manager is NEVER imported by World Model.
    AI Manager NEVER writes to the World Model.

Blueprint Reference:
    Chapter 15 — Software Architecture
    Chapter 15.4 — Core Software Modules
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from .ai_memory import AIMemory
from .temple_ai import TempleAI, TempleObservation
from .explorer_ai import ExplorerAI, Recommendation
from .ollama_client import OllamaProvider

if TYPE_CHECKING:
    from src.world.world_model import WorldModel
    from .provider import BaseProvider


# ---------------------------------------------------------------------------
# Default config path
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "ai_settings.json")
)


# ---------------------------------------------------------------------------
# AI Request / Response types
# ---------------------------------------------------------------------------

@dataclass
class AIRequest:
    """Describes a request to the AI Manager."""
    request_type: str          # "hint" | "recommend" | "analyze" | "reflect" |
                               # "narrate_event" | "observe_action" | "judgment"
    action_str: str = ""       # command action string (for observe_action)
    target: str = ""           # command target
    result_success: bool = True
    event_type: str = ""       # for narrate_event
    lore_id: str = ""          # for lore callbacks
    puzzle_id: str = ""        # for puzzle callbacks
    question: str = ""         # for lore questions


@dataclass
class AIResponse:
    """Typed response from the AI Manager."""
    text: str = ""
    eval_deltas: dict[str, float] = field(default_factory=dict)
    is_significant: bool = False
    source: str = "rule_based"   # "rule_based" | "llm"
    request_type: str = ""


# ---------------------------------------------------------------------------
# AI Manager
# ---------------------------------------------------------------------------

class AIManager:
    """
    Unified coordinator for all AI subsystems.

    Initialised once at game start (alongside the Game Engine).
    Remains isolated from the World Model — reads only through AIContext.

    Usage (from Game Engine):
        ai = AIManager()
        response = ai.handle(AIRequest("observe_action", action_str="look"), wm)
        # Apply response.eval_deltas via wm._update_evaluation(...)
    """

    def __init__(
        self,
        config_path: str = _DEFAULT_CONFIG,
        provider: Optional["BaseProvider"] = None,
    ) -> None:
        self._cfg = self._load_config(config_path)
        self._provider = provider or self._build_provider(config_path)

        # Shared memory — both AIs read and write to the same store
        self._memory = AIMemory()

        self._temple = TempleAI(
            provider=self._provider,
            memory=self._memory,
        )
        self._explorer = ExplorerAI(
            provider=self._provider,
            memory=self._memory,
        )

    # ------------------------------------------------------------------
    # Primary dispatch
    # ------------------------------------------------------------------

    def handle(self, request: AIRequest, wm: "WorldModel") -> AIResponse:
        """
        Dispatch an AI request and return a structured response.

        The Game Engine calls this after every player action for
        observe_action, and explicitly for hint/recommend/analyze.

        Never raises — returns an empty AIResponse on any error.
        """
        try:
            rtype = request.request_type

            if rtype == "observe_action":
                return self._handle_observe(request, wm)

            if rtype == "hint":
                return self._handle_hint(request, wm)

            if rtype == "recommend":
                return self._handle_recommend(request, wm)

            if rtype == "analyze":
                return self._handle_analyze(request, wm)

            if rtype == "reflect":
                return self._handle_reflect(request, wm)

            if rtype == "narrate_event":
                return self._handle_narrate_event(request, wm)

            if rtype == "puzzle_solved":
                return self._handle_puzzle_solved(request, wm)

            if rtype == "lore_discovered":
                return self._handle_lore_discovered(request, wm)

            if rtype == "judgment":
                return self._handle_judgment(request, wm)

            if rtype == "ask":
                return self._handle_ask(request, wm)

            if rtype == "mission":
                return self._handle_mission(request, wm)

        except Exception:  # noqa: BLE001 — AI must never crash the game
            pass

        return AIResponse(request_type=request.request_type)

    # ------------------------------------------------------------------
    # Handler implementations
    # ------------------------------------------------------------------

    def _handle_observe(self, req: AIRequest, wm: "WorldModel") -> AIResponse:
        obs: TempleObservation = self._temple.observe_action(
            wm, req.action_str, req.target or None, req.result_success
        )
        return AIResponse(
            text=obs.narration,
            eval_deltas=obs.eval_deltas,
            is_significant=obs.is_significant,
            source="llm" if (self._provider and self._provider.is_available()) else "rule_based",
            request_type="observe_action",
        )

    def _handle_hint(self, req: AIRequest, wm: "WorldModel") -> AIResponse:
        if not self._cfg.get("temple_ai", {}).get("narration_enabled", True):
            return AIResponse(
                text="The temple offers no guidance here.",
                request_type="hint",
            )
        text = self._temple.generate_hint(wm)
        return AIResponse(text=text, request_type="hint")

    def _handle_recommend(self, req: AIRequest, wm: "WorldModel") -> AIResponse:
        if not self._cfg.get("explorer_ai", {}).get("recommendation_enabled", True):
            return AIResponse(
                text="The explorer AI is not active.",
                request_type="recommend",
            )
        rec: Recommendation = self._explorer.recommend(wm)
        return AIResponse(
            text=rec.text,
            source=rec.source,
            request_type="recommend",
        )

    def _handle_analyze(self, req: AIRequest, wm: "WorldModel") -> AIResponse:
        text = self._explorer.analyze_room(wm)
        return AIResponse(text=text, request_type="analyze")

    def _handle_reflect(self, req: AIRequest, wm: "WorldModel") -> AIResponse:
        text = self._explorer.recall_discoveries(wm)
        return AIResponse(text=text, request_type="reflect")

    def _handle_narrate_event(
        self, req: AIRequest, wm: "WorldModel"
    ) -> AIResponse:
        if not self._cfg.get("temple_ai", {}).get("narration_enabled", True):
            return AIResponse(request_type="narrate_event")
        text = self._temple.narrate_event(wm, req.event_type)
        return AIResponse(text=text, is_significant=True, request_type="narrate_event")

    def _handle_puzzle_solved(
        self, req: AIRequest, wm: "WorldModel"
    ) -> AIResponse:
        obs = self._temple.on_puzzle_solved(wm, req.puzzle_id)
        return AIResponse(
            text=obs.narration,
            eval_deltas=obs.eval_deltas,
            is_significant=True,
            request_type="puzzle_solved",
        )

    def _handle_lore_discovered(
        self, req: AIRequest, wm: "WorldModel"
    ) -> AIResponse:
        obs = self._temple.on_lore_discovered(wm, req.lore_id)
        return AIResponse(
            eval_deltas=obs.eval_deltas,
            is_significant=True,
            request_type="lore_discovered",
        )

    def _handle_judgment(self, req: AIRequest, wm: "WorldModel") -> AIResponse:
        outcome, narrative = self._temple.compute_judgment(wm)
        return AIResponse(
            text=narrative,
            is_significant=True,
            source="llm" if (self._provider and self._provider.is_available()) else "rule_based",
            request_type="judgment",
            eval_deltas={"judgment_outcome": 0.0},  # no eval delta — outcome is final
        )

    def _handle_ask(self, req: AIRequest, wm: "WorldModel") -> AIResponse:
        text = self._explorer.answer_lore_question(wm, req.question)
        return AIResponse(text=text, request_type="ask")

    def _handle_mission(self, req: AIRequest, wm: "WorldModel") -> AIResponse:
        text = self._explorer.summarise_mission(wm)
        return AIResponse(text=text, request_type="mission")

    # ------------------------------------------------------------------
    # Provider availability check (for UI display)
    # ------------------------------------------------------------------

    def is_llm_available(self) -> bool:
        """Returns True when the LLM provider is reachable."""
        return bool(self._provider and self._provider.is_available())

    @property
    def memory(self) -> AIMemory:
        """Read-only access to the shared AI memory."""
        return self._memory

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    @staticmethod
    def _load_config(config_path: str) -> dict:
        """Load ai_settings.json, return {} on failure."""
        try:
            with open(config_path, encoding="utf-8") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    @staticmethod
    def _build_provider(config_path: str) -> OllamaProvider:
        """Build the default Ollama provider from config."""
        return OllamaProvider(config_path=config_path)
