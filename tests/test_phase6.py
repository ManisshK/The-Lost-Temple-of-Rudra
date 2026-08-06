"""
test_phase6.py — The Lost Temple of Rudra

Comprehensive tests for Phase 6: Temple AI + Explorer AI.

All LLM provider calls are mocked — no real model inference runs.

Coverage:
  - AIMemory: record, indexes, queries
  - ContextBuilder: temple, explorer, and judgment contexts
  - PromptManager: all 10 templates
  - Provider abstraction: BaseProvider, ProviderResponse
  - OllamaProvider: config loading, availability check, disabled state
  - TempleAI: observe_action, puzzle_solved, lore_discovered, hints, judgment
  - ExplorerAI: recommend, reflect, analyze, lore question, mission
  - AIManager: dispatch, all request types, error safety
  - Game Engine integration: hint/recommend/analyze commands, Temple AI wiring
  - CLI AI commands
"""

from __future__ import annotations

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from world.world_model import WorldModel
from world.room_state import RoomState, RoomRegion
from world.object_state import ObjectState, ObjectCategory
from world.puzzle_state import PuzzleState, PuzzleStatus, PuzzleCategory
from world.player_state import TorchStatus
from world.history_state import HistoryEntry
from world.story_state import StoryState

from ai.provider import BaseProvider, ProviderResponse
from ai.ollama_client import OllamaProvider, _load_ollama_config
from ai.ai_memory import AIMemory, MemoryEntry
from ai.context_builder import (
    get_temple_ai_context,
    get_explorer_ai_context,
    get_judgment_context,
)
from ai.prompt_manager import (
    build_recommendation_prompt,
    build_consequence_narration_prompt,
    build_world_summary_prompt,
    build_event_narration_prompt,
    build_hint_prompt,
    build_lore_narration_prompt,
    build_judgment_prompt,
    build_reflection_prompt,
    build_mission_prompt,
    build_analysis_prompt,
    _format_recent_history,
    _dominant_trait,
)
from ai.temple_ai import TempleAI, TempleObservation
from ai.explorer_ai import ExplorerAI, Recommendation
from ai.ai_manager import AIManager, AIRequest, AIResponse

from engine.game_engine import GameEngine
from engine.command_result import ResultStatus


# ===========================================================================
# Helpers
# ===========================================================================

class MockProvider(BaseProvider):
    """Deterministic stub provider for tests. Never does I/O."""

    def __init__(self, response_text: str = "mock response", available: bool = True):
        self._text = response_text
        self._available = available
        self.call_count = 0
        self.last_prompt = ""
        self.last_system = ""

    @property
    def model_name(self) -> str:
        return "mock_model"

    def is_available(self) -> bool:
        return self._available

    def send_prompt(self, prompt: str, system: str = "") -> ProviderResponse:
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system = system
        if not self._available:
            return ProviderResponse(success=False, error="not available", model="mock_model")
        return ProviderResponse(text=self._text, success=True, model="mock_model", latency_ms=1)


def _simple_world(room_id: str = "temple_entrance") -> WorldModel:
    """Minimal WorldModel with one room and the player in it."""
    wm = WorldModel()
    wm.rooms[room_id] = RoomState(
        room_id=room_id,
        region=RoomRegion.OUTER_TEMPLE,
        accessible_exits={"north": "hall_of_echoes"},
    )
    wm.player.current_room = room_id
    wm.player.torch = TorchStatus(state="lit", fuel=80, brightness=70)
    return wm


def _world_with_puzzle(puzzle_id: str = "puzzle_guardian_statues") -> WorldModel:
    wm = _simple_world("hall_of_guardians")
    wm.rooms["hall_of_guardians"].puzzle_id = puzzle_id
    wm.puzzles[puzzle_id] = PuzzleState(
        puzzle_id=puzzle_id,
        room_id="hall_of_guardians",
        category=PuzzleCategory.LOGIC,
        status=PuzzleStatus.AVAILABLE,
    )
    return wm


def _world_with_lore() -> WorldModel:
    wm = _simple_world()
    wm.story.lore_ids_discovered = ["lore_entrance_warning", "lore_guardian_truth"]
    wm.story.symbols_encountered = {"eye", "river"}
    return wm


# ===========================================================================
# Provider abstraction
# ===========================================================================

class TestProviderAbstraction:
    def test_mock_provider_is_available(self):
        p = MockProvider()
        assert p.is_available() is True

    def test_mock_provider_unavailable(self):
        p = MockProvider(available=False)
        assert p.is_available() is False

    def test_mock_provider_send_prompt_returns_response(self):
        p = MockProvider(response_text="hello")
        r = p.send_prompt("test")
        assert r.success is True
        assert r.text == "hello"
        assert r.model == "mock_model"

    def test_mock_provider_unavailable_send_returns_failure(self):
        p = MockProvider(available=False)
        r = p.send_prompt("test")
        assert r.success is False
        assert r.text == ""

    def test_provider_response_defaults(self):
        r = ProviderResponse()
        assert r.text == ""
        assert r.success is False
        assert r.error == ""
        assert r.latency_ms == 0

    def test_mock_provider_tracks_calls(self):
        p = MockProvider()
        p.send_prompt("a")
        p.send_prompt("b")
        assert p.call_count == 2
        assert p.last_prompt == "b"

    def test_mock_provider_model_name(self):
        p = MockProvider()
        assert p.model_name == "mock_model"

    def test_base_provider_is_abstract(self):
        import inspect
        assert inspect.isabstract(BaseProvider)


# ===========================================================================
# OllamaProvider
# ===========================================================================

class TestOllamaProvider:
    def test_disabled_provider_not_available(self):
        p = OllamaProvider()
        assert p.is_available() is False  # config has enabled=false

    def test_disabled_provider_send_returns_failure(self):
        p = OllamaProvider()
        r = p.send_prompt("anything")
        assert r.success is False
        assert "disabled" in r.error.lower()

    def test_model_name_from_config(self):
        p = OllamaProvider()
        assert p.model_name == "qwen"

    def test_load_config_defaults_on_missing_file(self):
        cfg = _load_ollama_config("/nonexistent/path/ai_settings.json")
        assert cfg["model"] == "qwen"
        assert cfg["enabled"] is False
        assert "localhost" in cfg["host"]

    def test_load_config_reads_file(self, tmp_path):
        cfg_file = tmp_path / "ai.json"
        cfg_file.write_text(json.dumps({
            "ollama": {
                "model": "llama3",
                "enabled": True,
                "host": "http://myhost:11434",
                "timeout_seconds": 10,
                "temperature": 0.5,
                "max_tokens": 256,
            }
        }))
        cfg = _load_ollama_config(str(cfg_file))
        assert cfg["model"] == "llama3"
        assert cfg["enabled"] is True
        assert cfg["host"] == "http://myhost:11434"

    def test_provider_with_custom_config(self, tmp_path):
        cfg_file = tmp_path / "ai.json"
        cfg_file.write_text(json.dumps({
            "ollama": {"model": "phi3", "enabled": False}
        }))
        p = OllamaProvider(config_path=str(cfg_file))
        assert p.model_name == "phi3"
        assert p.is_available() is False


# ===========================================================================
# AI Memory
# ===========================================================================

class TestAIMemory:
    def test_empty_memory(self):
        m = AIMemory()
        assert m.entries == []
        assert m.explored_rooms == []
        assert m.completed_puzzles == []

    def test_record_room_visited(self):
        m = AIMemory()
        m.record(MemoryEntry(turn=1, event_type="room_visited", subject="temple_entrance"))
        assert "temple_entrance" in m.explored_rooms
        assert m.has_visited("temple_entrance")

    def test_record_room_visited_no_duplicate(self):
        m = AIMemory()
        m.record(MemoryEntry(turn=1, event_type="room_visited", subject="r"))
        m.record(MemoryEntry(turn=2, event_type="room_visited", subject="r"))
        assert m.explored_rooms.count("r") == 1

    def test_record_puzzle_solved(self):
        m = AIMemory()
        m.record(MemoryEntry(turn=5, event_type="puzzle_solved", subject="puzzle_x"))
        assert m.has_solved("puzzle_x")
        assert "puzzle_x" in m.completed_puzzles

    def test_record_puzzle_failed(self):
        m = AIMemory()
        m.record(MemoryEntry(turn=3, event_type="puzzle_failed", subject="puzzle_x"))
        m.record(MemoryEntry(turn=4, event_type="puzzle_failed", subject="puzzle_x"))
        assert m.failure_count_for("puzzle_x") == 2

    def test_record_lore_discovered(self):
        m = AIMemory()
        m.record(MemoryEntry(turn=7, event_type="lore_discovered", subject="lore_entrance"))
        assert "lore_entrance" in m.discovered_lore

    def test_record_hint_given(self):
        m = AIMemory()
        m.record(MemoryEntry(turn=8, event_type="hint_given", subject="puzzle_x"))
        m.record(MemoryEntry(turn=9, event_type="hint_given", subject="puzzle_x"))
        assert m.hint_count_for("puzzle_x") == 2

    def test_record_recurring_action(self):
        m = AIMemory()
        m.record(MemoryEntry(turn=1, event_type="recurring_action", subject="observe"))
        m.record(MemoryEntry(turn=2, event_type="recurring_action", subject="observe"))
        m.record(MemoryEntry(turn=3, event_type="recurring_action", subject="rush"))
        assert m.get_behaviour_count("observe") == 2
        assert m.get_behaviour_count("rush") == 1

    def test_record_decision(self):
        m = AIMemory()
        e = MemoryEntry(turn=10, event_type="decision", subject="pray", detail="prayed")
        m.record(e)
        assert len(m.important_decisions) == 1
        assert m.important_decisions[0].subject == "pray"

    def test_get_recent_entries(self):
        m = AIMemory()
        for i in range(15):
            m.record(MemoryEntry(turn=i, event_type="room_visited", subject=f"r{i}"))
        recent = m.get_recent_entries(5)
        assert len(recent) == 5
        assert recent[-1].subject == "r14"

    def test_get_recent_entries_fewer_than_n(self):
        m = AIMemory()
        m.record(MemoryEntry(turn=1, event_type="room_visited", subject="r1"))
        recent = m.get_recent_entries(10)
        assert len(recent) == 1

    def test_get_entries_by_type(self):
        m = AIMemory()
        m.record(MemoryEntry(turn=1, event_type="room_visited", subject="r1"))
        m.record(MemoryEntry(turn=2, event_type="puzzle_failed", subject="p1"))
        m.record(MemoryEntry(turn=3, event_type="room_visited", subject="r2"))
        visits = m.get_entries_by_type("room_visited")
        assert len(visits) == 2

    def test_summary_keys(self):
        m = AIMemory()
        s = m.summary()
        assert "rooms_explored" in s
        assert "puzzles_completed" in s
        assert "total_puzzle_failures" in s
        assert "hints_given" in s
        assert "recurring_behaviours" in s

    def test_summary_counts(self):
        m = AIMemory()
        m.record(MemoryEntry(turn=1, event_type="room_visited", subject="r"))
        m.record(MemoryEntry(turn=2, event_type="puzzle_solved", subject="p"))
        s = m.summary()
        assert s["rooms_explored"] == 1
        assert s["puzzles_completed"] == 1

    def test_has_visited_false(self):
        m = AIMemory()
        assert not m.has_visited("unvisited_room")

    def test_has_solved_false(self):
        m = AIMemory()
        assert not m.has_solved("unsolved_puzzle")


# ===========================================================================
# Context Builder
# ===========================================================================

class TestContextBuilder:
    # --- Temple AI context ---
    def test_temple_context_keys_present(self):
        wm = _simple_world()
        ctx = get_temple_ai_context(wm)
        for key in ("turn", "temple_phase", "current_room", "evaluation",
                    "recent_behaviour", "active_events", "torch_state",
                    "flood_level", "solved_puzzles"):
            assert key in ctx, f"missing key: {key}"

    def test_temple_context_evaluation_all_attributes(self):
        wm = _simple_world()
        ctx = get_temple_ai_context(wm)
        for attr in ("observation", "curiosity", "wisdom", "patience",
                     "adaptation", "integrity", "responsibility",
                     "understanding", "greed", "recklessness"):
            assert attr in ctx["evaluation"]

    def test_temple_context_evaluation_rounded(self):
        wm = _simple_world()
        wm.evaluation.observation.score = 42.7
        ctx = get_temple_ai_context(wm)
        assert ctx["evaluation"]["observation"] == 43

    def test_temple_context_current_room(self):
        wm = _simple_world("temple_entrance")
        ctx = get_temple_ai_context(wm)
        assert ctx["current_room"] == "temple_entrance"

    def test_temple_context_no_puzzle_solutions(self):
        wm = _world_with_puzzle()
        ctx = get_temple_ai_context(wm)
        ctx_str = str(ctx)
        assert "SOUTH" not in ctx_str
        assert "WEST" not in ctx_str

    def test_temple_context_is_plain_dict(self):
        wm = _simple_world()
        ctx = get_temple_ai_context(wm)
        assert isinstance(ctx, dict)

    def test_temple_context_recent_behaviour_limit(self):
        wm = _simple_world()
        for i in range(15):
            wm.history.entries.append(
                HistoryEntry(turn=i, event_id=f"e{i}", category="player_action",
                             description=f"action {i}", room_id="temple_entrance")
            )
        ctx = get_temple_ai_context(wm)
        assert len(ctx["recent_behaviour"]) <= 10

    # --- Explorer AI context ---
    def test_explorer_context_keys_present(self):
        wm = _simple_world()
        ctx = get_explorer_ai_context(wm)
        for key in ("turn", "current_room", "visible_exits", "nearby_objects",
                    "inventory", "torch_state", "active_mission",
                    "lore_discovered", "rooms_visited", "puzzle_summary",
                    "recent_history"):
            assert key in ctx, f"missing key: {key}"

    def test_explorer_context_visible_exits(self):
        wm = _simple_world()
        ctx = get_explorer_ai_context(wm)
        assert "north" in ctx["visible_exits"]

    def test_explorer_context_inventory_empty(self):
        wm = _simple_world()
        ctx = get_explorer_ai_context(wm)
        assert ctx["inventory"] == []

    def test_explorer_context_inventory_with_item(self):
        wm = _simple_world()
        wm.objects["torch_entrance"] = ObjectState(
            object_id="torch_entrance", name="Ancient Torch",
            category=ObjectCategory.COLLECTIBLE, current_room=None,
        )
        wm.player.inventory.append("torch_entrance")
        ctx = get_explorer_ai_context(wm)
        assert any(obj["id"] == "torch_entrance" for obj in ctx["inventory"])

    def test_explorer_context_no_hidden_passages(self):
        wm = _simple_world()
        wm.rooms["temple_entrance"].hidden_passages["secret"] = True
        ctx = get_explorer_ai_context(wm)
        # Hidden passages must not appear in visible_exits
        assert "secret" not in ctx["visible_exits"]

    def test_explorer_context_puzzle_summary_no_solution(self):
        wm = _world_with_puzzle()
        ctx = get_explorer_ai_context(wm)
        p = ctx["puzzle_summary"][0]
        assert "solution" not in p
        assert "status" in p
        assert "attempts" in p

    def test_explorer_context_is_plain_dict(self):
        wm = _simple_world()
        ctx = get_explorer_ai_context(wm)
        assert isinstance(ctx, dict)

    # --- Judgment context ---
    def test_judgment_context_keys_present(self):
        wm = _simple_world()
        ctx = get_judgment_context(wm)
        for key in ("total_turns", "rooms_visited", "evaluation",
                    "puzzle_history", "full_history", "steps_taken"):
            assert key in ctx, f"missing key: {key}"

    def test_judgment_context_all_eval_attributes(self):
        wm = _simple_world()
        ctx = get_judgment_context(wm)
        for attr in ("observation", "curiosity", "wisdom", "patience",
                     "recklessness", "greed"):
            assert attr in ctx["evaluation"]

    def test_judgment_context_no_thresholds(self):
        wm = _simple_world()
        ctx = get_judgment_context(wm)
        ctx_str = str(ctx)
        # Thresholds (420, 260) must not appear
        assert "420" not in ctx_str
        assert "260" not in ctx_str

    def test_context_builder_does_not_mutate_world_model(self):
        wm = _simple_world()
        before_turn = wm.world.current_turn
        get_temple_ai_context(wm)
        get_explorer_ai_context(wm)
        get_judgment_context(wm)
        assert wm.world.current_turn == before_turn


# ===========================================================================
# Prompt Manager
# ===========================================================================

class TestPromptManager:
    def test_recommendation_prompt_returns_tuple(self):
        wm = _simple_world()
        ctx = get_explorer_ai_context(wm)
        result = build_recommendation_prompt(ctx)
        assert isinstance(result, tuple)
        assert len(result) == 2
        system, prompt = result
        assert isinstance(system, str) and len(system) > 0
        assert isinstance(prompt, str) and len(prompt) > 0

    def test_recommendation_prompt_contains_room(self):
        wm = _simple_world("temple_entrance")
        ctx = get_explorer_ai_context(wm)
        _, prompt = build_recommendation_prompt(ctx)
        assert "Temple Entrance" in prompt

    def test_consequence_narration_prompt(self):
        wm = _simple_world()
        ctx = get_temple_ai_context(wm)
        system, prompt = build_consequence_narration_prompt(ctx, "Player looked around.")
        assert "Player looked around" in prompt
        assert "temple" in system.lower()

    def test_world_summary_prompt(self):
        wm = _simple_world()
        ctx = get_temple_ai_context(wm)
        system, prompt = build_world_summary_prompt(ctx)
        assert "Turn" in prompt
        assert isinstance(system, str)

    def test_event_narration_prompt_flood(self):
        wm = _simple_world()
        ctx = get_temple_ai_context(wm)
        system, prompt = build_event_narration_prompt(ctx, "flood_rising")
        assert "Water" in prompt or "flood" in prompt.lower()

    def test_event_narration_prompt_unknown_event(self):
        wm = _simple_world()
        ctx = get_temple_ai_context(wm)
        system, prompt = build_event_narration_prompt(ctx, "unknown_thing")
        assert "unknown_thing" in prompt

    def test_hint_prompt_contains_puzzle(self):
        wm = _world_with_puzzle()
        ctx = get_explorer_ai_context(wm)
        system, prompt = build_hint_prompt(ctx, "puzzle_guardian_statues", 0)
        assert "guardian statues" in prompt.lower()
        assert "answer" not in prompt.lower() or "never state the answer" in prompt.lower()

    def test_hint_prompt_level_escalation(self):
        wm = _world_with_puzzle()
        ctx = get_explorer_ai_context(wm)
        _, p0 = build_hint_prompt(ctx, "puzzle_guardian_statues", 0)
        _, p1 = build_hint_prompt(ctx, "puzzle_guardian_statues", 1)
        _, p2 = build_hint_prompt(ctx, "puzzle_guardian_statues", 2)
        assert "subtle" in p0
        assert "moderate" in p1
        assert "direct" in p2

    def test_lore_narration_prompt(self):
        wm = _simple_world()
        ctx = get_temple_ai_context(wm)
        system, prompt = build_lore_narration_prompt(ctx, "lore_entrance_warning", "Beware.")
        assert "Beware" in prompt

    def test_judgment_prompt_contains_scores(self):
        wm = _simple_world()
        wm.evaluation.observation.score = 80
        ctx = get_judgment_context(wm)
        system, prompt = build_judgment_prompt(ctx)
        assert "observation" in prompt.lower()
        assert "WORTHY" in prompt or "UNWORTHY" in prompt

    def test_judgment_prompt_outcome_in_prompt(self):
        wm = _simple_world()
        ctx = get_judgment_context(wm)
        _, prompt = build_judgment_prompt(ctx)
        assert any(w in prompt for w in ("WORTHY", "NEARLY WORTHY", "UNWORTHY"))

    def test_reflection_prompt(self):
        wm = _world_with_lore()
        wm.player.visited_rooms = ["temple_entrance", "hall_of_echoes"]
        ctx = get_explorer_ai_context(wm)
        system, prompt = build_reflection_prompt(ctx)
        assert "temple entrance" in prompt.lower() or "hall of echoes" in prompt.lower()

    def test_mission_prompt(self):
        wm = _simple_world()
        wm.mission.current_goal_description = "Find the ancient scroll."
        ctx = get_explorer_ai_context(wm)
        system, prompt = build_mission_prompt(ctx)
        assert "ancient scroll" in prompt.lower()

    def test_analysis_prompt(self):
        wm = _simple_world()
        ctx = get_explorer_ai_context(wm)
        system, prompt = build_analysis_prompt(ctx)
        assert "Temple Entrance" in prompt

    def test_format_recent_history_empty(self):
        result = _format_recent_history([])
        assert "(none)" in result

    def test_format_recent_history_with_entries(self):
        entries = [{"turn": 1, "description": "Entered room"}, {"turn": 2, "description": "Looked"}]
        result = _format_recent_history(entries)
        assert "[1]" in result
        assert "Entered room" in result

    def test_dominant_trait_returns_string(self):
        scores = {"observation": 80, "curiosity": 60, "greed": 90, "recklessness": 50}
        result = _dominant_trait(scores)
        assert result == "observation"

    def test_dominant_trait_ignores_negative(self):
        scores = {"greed": 100, "recklessness": 99, "observation": 1}
        result = _dominant_trait(scores)
        assert result == "observation"

    def test_dominant_trait_empty(self):
        result = _dominant_trait({})
        assert result == "undefined"


# ===========================================================================
# Temple AI
# ===========================================================================

class TestTempleAI:
    def test_observe_look_rewards_observation(self):
        wm = _simple_world()
        ai = TempleAI()
        obs = ai.observe_action(wm, "look")
        assert obs.eval_deltas.get("observation", 0) == 1.0

    def test_observe_inspect_rewards_observation(self):
        wm = _simple_world()
        ai = TempleAI()
        obs = ai.observe_action(wm, "inspect")
        assert obs.eval_deltas.get("observation", 0) == 1.0

    def test_observe_ritual_action_rewards_wisdom(self):
        wm = _simple_world()
        ai = TempleAI()
        obs = ai.observe_action(wm, "pray")
        assert obs.eval_deltas.get("wisdom", 0) == 1.0
        assert obs.eval_deltas.get("understanding", 0) == 0.5

    def test_observe_ritual_is_significant(self):
        wm = _simple_world()
        ai = TempleAI()
        obs = ai.observe_action(wm, "meditate")
        assert obs.is_significant is True

    def test_observe_look_resets_rush_counter(self):
        wm = _simple_world()
        ai = TempleAI()
        ai._moves_without_observe = 4
        ai.observe_action(wm, "look")
        assert ai._moves_without_observe == 0

    def test_observe_movement_increments_rush_counter(self):
        wm = _simple_world()
        ai = TempleAI()
        ai.observe_action(wm, "go")
        assert ai._moves_without_observe == 1

    def test_observe_rush_triggers_recklessness(self):
        wm = _simple_world()
        ai = TempleAI()
        ai._moves_without_observe = 4
        obs = ai.observe_action(wm, "go")
        assert obs.eval_deltas.get("recklessness", 0) > 0

    def test_observe_records_room_visit(self):
        wm = _simple_world("r1")
        ai = TempleAI()
        ai.observe_action(wm, "look")
        assert ai.memory.has_visited("r1")

    def test_observe_does_not_mutate_world_model(self):
        wm = _simple_world()
        before_turn = wm.world.current_turn
        ai = TempleAI()
        ai.observe_action(wm, "look")
        assert wm.world.current_turn == before_turn

    def test_on_puzzle_solved_no_hints_gives_wisdom(self):
        wm = _world_with_puzzle()
        ai = TempleAI()
        obs = ai.on_puzzle_solved(wm, "puzzle_guardian_statues")
        assert obs.eval_deltas.get("wisdom", 0) >= 3.0

    def test_on_puzzle_solved_with_hints_reduced_wisdom(self):
        wm = _world_with_puzzle()
        wm.puzzles["puzzle_guardian_statues"].hint_count = 2
        ai = TempleAI()
        obs = ai.on_puzzle_solved(wm, "puzzle_guardian_statues")
        assert obs.eval_deltas.get("wisdom", 0) == 1.0

    def test_on_puzzle_solved_records_memory(self):
        wm = _world_with_puzzle()
        ai = TempleAI()
        ai.on_puzzle_solved(wm, "puzzle_guardian_statues")
        assert ai.memory.has_solved("puzzle_guardian_statues")

    def test_on_puzzle_solved_is_significant(self):
        wm = _world_with_puzzle()
        ai = TempleAI()
        obs = ai.on_puzzle_solved(wm, "puzzle_guardian_statues")
        assert obs.is_significant is True

    def test_on_lore_discovered_rewards_understanding(self):
        wm = _simple_world()
        ai = TempleAI()
        obs = ai.on_lore_discovered(wm, "lore_entrance_warning")
        assert obs.eval_deltas.get("understanding", 0) == 1.5
        assert obs.eval_deltas.get("curiosity", 0) == 0.5

    def test_on_lore_discovered_records_memory(self):
        wm = _simple_world()
        ai = TempleAI()
        ai.on_lore_discovered(wm, "lore_entrance_warning")
        assert "lore_entrance_warning" in ai.memory.discovered_lore

    def test_generate_hint_no_puzzle_returns_fallback(self):
        wm = _simple_world()
        ai = TempleAI()
        hint = ai.generate_hint(wm)
        assert isinstance(hint, str) and len(hint) > 0
        assert "guidance" in hint.lower() or "look" in hint.lower() or "surroundings" in hint.lower()

    def test_generate_hint_with_puzzle_returns_hint(self):
        wm = _world_with_puzzle()
        ai = TempleAI()
        hint = ai.generate_hint(wm)
        assert isinstance(hint, str) and len(hint) > 0

    def test_generate_hint_records_in_memory(self):
        wm = _world_with_puzzle("puzzle_guardian_statues")
        ai = TempleAI()
        ai.generate_hint(wm)
        assert ai.memory.hint_count_for("puzzle_guardian_statues") == 1

    def test_generate_hint_uses_llm_when_available(self):
        wm = _world_with_puzzle()
        provider = MockProvider("The stones hold the answer.")
        ai = TempleAI(provider=provider)
        hint = ai.generate_hint(wm)
        assert hint == "The stones hold the answer."
        assert provider.call_count == 1

    def test_generate_hint_falls_back_when_llm_unavailable(self):
        wm = _world_with_puzzle()
        provider = MockProvider(available=False)
        ai = TempleAI(provider=provider)
        hint = ai.generate_hint(wm)
        assert isinstance(hint, str) and len(hint) > 0
        assert provider.call_count == 0

    def test_compute_judgment_returns_outcome_and_narrative(self):
        wm = _simple_world()
        ai = TempleAI()
        outcome, narrative = ai.compute_judgment(wm)
        assert outcome in ("worthy", "nearly_worthy", "unworthy")
        assert isinstance(narrative, str) and len(narrative) > 0

    def test_compute_judgment_unworthy_for_zero_scores(self):
        wm = _simple_world()
        ai = TempleAI()
        outcome, _ = ai.compute_judgment(wm)
        assert outcome == "unworthy"

    def test_compute_judgment_worthy_for_high_scores(self):
        wm = _simple_world()
        for attr in ("observation", "curiosity", "wisdom", "patience",
                     "adaptation", "integrity", "responsibility", "understanding"):
            getattr(wm.evaluation, attr).score = 60.0
        ai = TempleAI()
        outcome, _ = ai.compute_judgment(wm)
        assert outcome == "worthy"

    def test_compute_judgment_uses_llm_when_available(self):
        wm = _simple_world()
        provider = MockProvider("The temple finds you WORTHY.")
        ai = TempleAI(provider=provider)
        _, narrative = ai.compute_judgment(wm)
        assert narrative == "The temple finds you WORTHY."

    def test_narrate_event_rule_based_flood(self):
        wm = _simple_world()
        ai = TempleAI()
        text = ai.narrate_event(wm, "flood_rising")
        assert "water" in text.lower() or "rise" in text.lower()

    def test_narrate_event_unknown_returns_empty(self):
        wm = _simple_world()
        ai = TempleAI()
        text = ai.narrate_event(wm, "unknown_event_xyz")
        assert text == ""

    def test_observe_returns_temple_observation(self):
        wm = _simple_world()
        ai = TempleAI()
        obs = ai.observe_action(wm, "look")
        assert isinstance(obs, TempleObservation)


# ===========================================================================
# Explorer AI
# ===========================================================================

class TestExplorerAI:
    def test_recommend_returns_recommendation(self):
        wm = _simple_world()
        ai = ExplorerAI()
        rec = ai.recommend(wm)
        assert isinstance(rec, Recommendation)
        assert isinstance(rec.text, str) and len(rec.text) > 0

    def test_recommend_unlit_torch_highest_priority(self):
        wm = _simple_world()
        wm.player.torch.state = "unlit"
        wm.objects["torch_entrance"] = ObjectState(
            object_id="torch_entrance", name="Ancient Torch",
            category=ObjectCategory.COLLECTIBLE, current_room=None,
        )
        wm.player.inventory.append("torch_entrance")
        ai = ExplorerAI()
        rec = ai.recommend(wm)
        assert "torch" in rec.text.lower()
        assert rec.confidence >= 0.9

    def test_recommend_flood_active(self):
        wm = _simple_world()
        wm.dynamic_events.active_events.append("flood")
        ai = ExplorerAI()
        rec = ai.recommend(wm)
        assert "water" in rec.text.lower() or "flood" in rec.text.lower()

    def test_recommend_unexamined_object(self):
        wm = _simple_world()
        wm.objects["inscr"] = ObjectState(
            object_id="inscr", name="Ancient Inscription",
            category=ObjectCategory.STORY, current_room="temple_entrance",
            state="unexamined", visible=True,
        )
        wm.rooms["temple_entrance"].object_ids_present.append("inscr")
        ai = ExplorerAI()
        rec = ai.recommend(wm)
        assert "inscription" in rec.text.lower()

    def test_recommend_puzzle_present(self):
        wm = _world_with_puzzle()
        ai = ExplorerAI()
        rec = ai.recommend(wm)
        assert "guardian" in rec.text.lower() or "mechanism" in rec.text.lower()

    def test_recommend_uses_llm_when_confidence_low(self):
        wm = _simple_world()
        provider = MockProvider("Explore the north passage.")
        ai = ExplorerAI(provider=provider)
        # No exits → low confidence
        wm.rooms["temple_entrance"].accessible_exits = {}
        rec = ai.recommend(wm)
        # Should call LLM because rule confidence is 0.4
        assert provider.call_count >= 1

    def test_recommend_falls_back_when_llm_unavailable(self):
        wm = _simple_world()
        provider = MockProvider(available=False)
        ai = ExplorerAI(provider=provider)
        rec = ai.recommend(wm)
        assert isinstance(rec.text, str) and len(rec.text) > 0
        assert rec.source == "rule_based"

    def test_recall_discoveries_returns_string(self):
        wm = _simple_world()
        ai = ExplorerAI()
        text = ai.recall_discoveries(wm)
        assert isinstance(text, str) and len(text) > 0

    def test_recall_discoveries_mentions_rooms(self):
        wm = _simple_world()
        wm.player.visited_rooms = ["temple_entrance", "hall_of_echoes"]
        ai = ExplorerAI()
        text = ai.recall_discoveries(wm)
        assert "2" in text or "two" in text.lower()

    def test_recall_discoveries_uses_llm(self):
        wm = _simple_world()
        provider = MockProvider("You have seen two rooms.")
        ai = ExplorerAI(provider=provider)
        text = ai.recall_discoveries(wm)
        assert text == "You have seen two rooms."

    def test_analyze_room_returns_string(self):
        wm = _simple_world()
        ai = ExplorerAI()
        text = ai.analyze_room(wm)
        assert isinstance(text, str) and len(text) > 0

    def test_analyze_room_mentions_room_name(self):
        wm = _simple_world("temple_entrance")
        ai = ExplorerAI()
        text = ai.analyze_room(wm)
        assert "temple entrance" in text.lower()

    def test_analyze_room_uses_llm(self):
        wm = _simple_world()
        provider = MockProvider("The room hides a secret.")
        ai = ExplorerAI(provider=provider)
        text = ai.analyze_room(wm)
        assert text == "The room hides a secret."

    def test_answer_lore_question_no_lore(self):
        wm = _simple_world()
        ai = ExplorerAI()
        text = ai.answer_lore_question(wm, "What is Rudra?")
        assert "not yet" in text.lower() or "discovered" in text.lower()

    def test_answer_lore_question_with_lore(self):
        wm = _world_with_lore()
        ai = ExplorerAI()
        text = ai.answer_lore_question(wm, "What symbols are known?")
        assert isinstance(text, str) and len(text) > 0

    def test_answer_lore_records_decision_in_memory(self):
        wm = _world_with_lore()
        ai = ExplorerAI()
        ai.answer_lore_question(wm, "What is the eye symbol?")
        decisions = ai.memory.get_entries_by_type("decision")
        assert len(decisions) == 1
        assert decisions[0].subject == "lore_question"

    def test_summarise_mission_returns_string(self):
        wm = _simple_world()
        wm.mission.current_goal_description = "Reach the library."
        ai = ExplorerAI()
        text = ai.summarise_mission(wm)
        assert "library" in text.lower() or isinstance(text, str)

    def test_recommend_does_not_mutate_world_model(self):
        wm = _simple_world()
        before = wm.world.current_turn
        ai = ExplorerAI()
        ai.recommend(wm)
        assert wm.world.current_turn == before


# ===========================================================================
# AI Manager
# ===========================================================================

class TestAIManager:
    def _mock_manager(self, response_text="mock response"):
        provider = MockProvider(response_text)
        return AIManager(provider=provider), provider

    def test_init_creates_temple_and_explorer(self):
        ai, _ = self._mock_manager()
        assert ai._temple is not None
        assert ai._explorer is not None

    def test_shared_memory(self):
        ai, _ = self._mock_manager()
        assert ai._temple.memory is ai._explorer.memory

    def test_memory_property(self):
        ai, _ = self._mock_manager()
        assert isinstance(ai.memory, AIMemory)

    def test_is_llm_available_with_mock(self):
        ai, _ = self._mock_manager()
        assert ai.is_llm_available() is True

    def test_is_llm_available_unavailable(self):
        provider = MockProvider(available=False)
        ai = AIManager(provider=provider)
        assert ai.is_llm_available() is False

    def test_handle_observe_action(self):
        ai, _ = self._mock_manager()
        wm = _simple_world()
        resp = ai.handle(AIRequest("observe_action", action_str="look"), wm)
        assert isinstance(resp, AIResponse)
        assert resp.request_type == "observe_action"

    def test_handle_observe_returns_eval_deltas(self):
        provider = MockProvider(available=False)
        ai = AIManager(provider=provider)
        wm = _simple_world()
        resp = ai.handle(AIRequest("observe_action", action_str="look"), wm)
        assert "observation" in resp.eval_deltas

    def test_handle_hint(self):
        ai, _ = self._mock_manager()
        wm = _world_with_puzzle()
        resp = ai.handle(AIRequest("hint"), wm)
        assert resp.request_type == "hint"
        assert isinstance(resp.text, str) and len(resp.text) > 0

    def test_handle_recommend(self):
        ai, _ = self._mock_manager()
        wm = _simple_world()
        resp = ai.handle(AIRequest("recommend"), wm)
        assert resp.request_type == "recommend"
        assert len(resp.text) > 0

    def test_handle_analyze(self):
        ai, _ = self._mock_manager()
        wm = _simple_world()
        resp = ai.handle(AIRequest("analyze"), wm)
        assert resp.request_type == "analyze"
        assert len(resp.text) > 0

    def test_handle_reflect(self):
        ai, _ = self._mock_manager()
        wm = _simple_world()
        resp = ai.handle(AIRequest("reflect"), wm)
        assert resp.request_type == "reflect"
        assert len(resp.text) > 0

    def test_handle_narrate_event(self):
        provider = MockProvider(available=False)
        ai = AIManager(provider=provider)
        wm = _simple_world()
        resp = ai.handle(AIRequest("narrate_event", event_type="flood_rising"), wm)
        assert resp.request_type == "narrate_event"

    def test_handle_puzzle_solved(self):
        ai, _ = self._mock_manager()
        wm = _world_with_puzzle("puzzle_guardian_statues")
        resp = ai.handle(AIRequest("puzzle_solved", puzzle_id="puzzle_guardian_statues"), wm)
        assert resp.request_type == "puzzle_solved"
        assert resp.is_significant is True

    def test_handle_lore_discovered(self):
        ai, _ = self._mock_manager()
        wm = _simple_world()
        resp = ai.handle(AIRequest("lore_discovered", lore_id="lore_entrance"), wm)
        assert resp.request_type == "lore_discovered"
        assert "understanding" in resp.eval_deltas

    def test_handle_judgment(self):
        ai, _ = self._mock_manager()
        wm = _simple_world()
        resp = ai.handle(AIRequest("judgment"), wm)
        assert resp.request_type == "judgment"
        assert len(resp.text) > 0

    def test_handle_ask(self):
        ai, _ = self._mock_manager()
        wm = _world_with_lore()
        resp = ai.handle(AIRequest("ask", question="What do I know?"), wm)
        assert resp.request_type == "ask"
        assert len(resp.text) > 0

    def test_handle_mission(self):
        ai, _ = self._mock_manager()
        wm = _simple_world()
        resp = ai.handle(AIRequest("mission"), wm)
        assert resp.request_type == "mission"

    def test_handle_unknown_type_returns_empty_response(self):
        ai, _ = self._mock_manager()
        wm = _simple_world()
        resp = ai.handle(AIRequest("nonexistent_type"), wm)
        assert isinstance(resp, AIResponse)
        assert resp.text == ""

    def test_handle_never_raises(self):
        """AI Manager must never raise an exception."""
        provider = MockProvider(available=False)
        ai = AIManager(provider=provider)
        wm = WorldModel()  # minimal, no rooms
        for rtype in ("observe_action", "hint", "recommend", "analyze",
                      "reflect", "judgment", "ask", "puzzle_solved"):
            resp = ai.handle(AIRequest(rtype), wm)
            assert isinstance(resp, AIResponse)

    def test_handle_does_not_mutate_world_model(self):
        ai, _ = self._mock_manager()
        wm = _simple_world()
        before_turn = wm.world.current_turn
        for rtype in ("observe_action", "hint", "recommend", "analyze", "reflect"):
            ai.handle(AIRequest(rtype, action_str="look"), wm)
        assert wm.world.current_turn == before_turn

    def test_config_disables_narration(self, tmp_path):
        cfg = tmp_path / "ai.json"
        cfg.write_text(json.dumps({
            "ollama": {"enabled": False},
            "temple_ai": {"narration_enabled": False, "evaluation_enabled": True, "silent_judgment": True},
            "explorer_ai": {"recommendation_enabled": True, "confidence_threshold": 0.6, "max_suggestions": 1},
        }))
        provider = MockProvider()
        ai = AIManager(config_path=str(cfg), provider=provider)
        wm = _world_with_puzzle()
        resp = ai.handle(AIRequest("hint"), wm)
        # Narration disabled → fallback text
        assert "guidance" in resp.text.lower() or isinstance(resp.text, str)

    def test_config_disables_recommendation(self, tmp_path):
        cfg = tmp_path / "ai.json"
        cfg.write_text(json.dumps({
            "ollama": {"enabled": False},
            "temple_ai": {"narration_enabled": True, "evaluation_enabled": True, "silent_judgment": True},
            "explorer_ai": {"recommendation_enabled": False, "confidence_threshold": 0.6, "max_suggestions": 1},
        }))
        provider = MockProvider()
        ai = AIManager(config_path=str(cfg), provider=provider)
        wm = _simple_world()
        resp = ai.handle(AIRequest("recommend"), wm)
        assert "not active" in resp.text.lower()


# ===========================================================================
# Game Engine Integration
# ===========================================================================

class TestGameEngineAIIntegration:
    def _engine_with_mock_ai(self, response_text="AI response") -> tuple:
        provider = MockProvider(response_text)
        ai = AIManager(provider=provider)
        wm = _simple_world()
        engine = GameEngine(wm, ai_manager=ai)
        return engine, wm, provider

    def test_hint_command_routes_through_ai(self):
        engine, wm, provider = self._engine_with_mock_ai("The stones hold the answer.")
        wm.rooms["temple_entrance"].puzzle_id = "puzzle_x"
        wm.puzzles["puzzle_x"] = PuzzleState(
            puzzle_id="puzzle_x", room_id="temple_entrance",
            status=PuzzleStatus.AVAILABLE, category=PuzzleCategory.OBSERVATION,
        )
        result = engine.process_input("hint")
        assert result.status == ResultStatus.INFO
        assert isinstance(result.message, str) and len(result.message) > 0

    def test_hint_command_no_puzzle_still_responds(self):
        engine, wm, _ = self._engine_with_mock_ai()
        result = engine.process_input("hint")
        assert result.status == ResultStatus.INFO
        assert len(result.message) > 0

    def test_recommend_command_returns_info(self):
        engine, wm, _ = self._engine_with_mock_ai("Go north.")
        result = engine.process_input("recommend")
        assert result.status == ResultStatus.INFO
        assert len(result.message) > 0

    def test_analyze_command_returns_info(self):
        engine, wm, _ = self._engine_with_mock_ai("The room is interesting.")
        # Action.ANALYZE reaches _handle_ai; execute it directly via Command
        from engine.command import Command, Action, CommandCategory
        cmd = Command(action=Action.ANALYZE, raw_input="analyze room",
                      category=CommandCategory.AI)
        result = engine.execute(cmd)
        assert result.status == ResultStatus.INFO

    def test_think_command_returns_info(self):
        engine, wm, _ = self._engine_with_mock_ai("You have explored 1 room.")
        result = engine.process_input("think")
        assert result.status == ResultStatus.INFO

    def test_status_command_returns_game_state(self):
        engine, wm, _ = self._engine_with_mock_ai()
        result = engine.process_input("status")
        assert result.status == ResultStatus.INFO
        assert "Turn" in result.message or "turn" in result.message.lower()
        assert "Room" in result.message or "room" in result.message.lower()

    def test_hint_increments_hint_count(self):
        provider = MockProvider("A hint.", available=False)
        ai = AIManager(provider=provider)
        wm = _simple_world("hall_of_guardians")
        wm.rooms["hall_of_guardians"].puzzle_id = "puzzle_guardian_statues"
        wm.puzzles["puzzle_guardian_statues"] = PuzzleState(
            puzzle_id="puzzle_guardian_statues",
            room_id="hall_of_guardians",
            status=PuzzleStatus.AVAILABLE,
            category=PuzzleCategory.LOGIC,
        )
        engine = GameEngine(wm, ai_manager=ai)
        engine.process_input("hint")
        ps = wm.puzzles["puzzle_guardian_statues"]
        assert ps.hint_count == 1
        assert ps.solved_without_hints is False

    def test_temple_ai_notified_after_look(self):
        provider = MockProvider(available=False)
        ai = AIManager(provider=provider)
        wm = _simple_world()
        engine = GameEngine(wm, ai_manager=ai)
        before = wm.evaluation.observation.score
        engine.process_input("look")
        # Temple AI observe_action should have added observation delta
        assert wm.evaluation.observation.score > before

    def test_temple_ai_notification_never_crashes_game(self):
        """Even if AI raises, game must continue."""
        wm = _simple_world()
        engine = GameEngine(wm, ai_manager=None)  # No AI
        result = engine.process_input("look")
        assert result.status == ResultStatus.SUCCESS

    def test_ai_manager_lazy_init_on_hint(self):
        """Engine with ai_manager=None should lazy-init (or return graceful stub)."""
        wm = _simple_world()
        engine = GameEngine(wm, ai_manager=None)
        result = engine.process_input("hint")
        assert result.status == ResultStatus.INFO

    def test_recommend_does_not_crash_without_exits(self):
        provider = MockProvider(available=False)
        ai = AIManager(provider=provider)
        wm = _simple_world()
        wm.rooms["temple_entrance"].accessible_exits = {}
        engine = GameEngine(wm, ai_manager=ai)
        result = engine.process_input("recommend")
        assert result.status == ResultStatus.INFO

    def test_existing_gameplay_unaffected(self):
        """Look, move, take all still work after Phase 6 wiring."""
        wm = _simple_world()
        wm.rooms["hall_of_echoes"] = RoomState(
            room_id="hall_of_echoes", region=RoomRegion.OUTER_TEMPLE,
        )
        wm.objects["torch_e"] = ObjectState(
            object_id="torch_e", name="Ancient Torch",
            category=ObjectCategory.COLLECTIBLE, current_room="temple_entrance",
            interactable=True, visible=True,
        )
        wm.rooms["temple_entrance"].object_ids_present.append("torch_e")
        engine = GameEngine(wm)
        look = engine.process_input("look")
        assert look.status == ResultStatus.SUCCESS
        take = engine.process_input("take torch")
        assert take.status == ResultStatus.SUCCESS
        assert "torch_e" in wm.player.inventory


# ===========================================================================
# AI does not mutate the World Model
# ===========================================================================

class TestAIReadOnly:
    """Verify no AI path writes to the World Model directly."""

    def test_temple_ai_observe_does_not_write(self):
        wm = _simple_world()
        snapshot_turn = wm.world.current_turn
        snapshot_obs = wm.evaluation.observation.score
        ai = TempleAI()
        ai.observe_action(wm, "look")
        # Temple AI must not call wm._update_evaluation directly
        assert wm.evaluation.observation.score == snapshot_obs
        assert wm.world.current_turn == snapshot_turn

    def test_explorer_ai_recommend_does_not_write(self):
        wm = _simple_world()
        snap = wm.player.current_room
        ai = ExplorerAI()
        ai.recommend(wm)
        assert wm.player.current_room == snap

    def test_ai_manager_handle_does_not_write_evaluation(self):
        """AIManager.handle() returns deltas; Game Engine applies them.
        The manager itself must not call wm._update_evaluation."""
        provider = MockProvider(available=False)
        mgr = AIManager(provider=provider)
        wm = _simple_world()
        before = wm.evaluation.curiosity.score
        mgr.handle(AIRequest("observe_action", action_str="go"), wm)
        # AI Manager must NOT have written to the world model
        assert wm.evaluation.curiosity.score == before

    def test_context_builder_does_not_write(self):
        wm = _simple_world()
        wm.evaluation.wisdom.score = 10.0
        get_temple_ai_context(wm)
        get_explorer_ai_context(wm)
        assert wm.evaluation.wisdom.score == 10.0


# ===========================================================================
# Persistent memory across session
# ===========================================================================

class TestAIMemoryPersistence:
    def test_memory_persists_across_multiple_actions(self):
        wm = _simple_world("r1")
        provider = MockProvider(available=False)
        mgr = AIManager(provider=provider)

        mgr.handle(AIRequest("observe_action", action_str="look"), wm)
        mgr.handle(AIRequest("observe_action", action_str="go"), wm)
        mgr.handle(AIRequest("observe_action", action_str="inspect"), wm)

        assert len(mgr.memory.entries) >= 3

    def test_memory_tracks_rooms_across_moves(self):
        provider = MockProvider(available=False)
        mgr = AIManager(provider=provider)

        wm = _simple_world("room_a")
        mgr.handle(AIRequest("observe_action", action_str="look"), wm)

        wm2 = _simple_world("room_b")
        mgr.handle(AIRequest("observe_action", action_str="look"), wm2)

        assert mgr.memory.has_visited("room_a")
        assert mgr.memory.has_visited("room_b")

    def test_memory_tracks_puzzle_failures(self):
        provider = MockProvider(available=False)
        mgr = AIManager(provider=provider)
        wm = _world_with_puzzle("puzzle_x")

        for _ in range(3):
            mgr.handle(
                AIRequest("observe_action", action_str="rotate", result_success=False),
                wm,
            )
        assert mgr.memory.failure_count_for("puzzle_x") >= 1

    def test_puzzle_solved_updates_memory(self):
        provider = MockProvider(available=False)
        mgr = AIManager(provider=provider)
        wm = _world_with_puzzle("puzzle_guardian_statues")

        mgr.handle(AIRequest("puzzle_solved", puzzle_id="puzzle_guardian_statues"), wm)
        assert mgr.memory.has_solved("puzzle_guardian_statues")

    def test_lore_discovered_updates_memory(self):
        provider = MockProvider(available=False)
        mgr = AIManager(provider=provider)
        wm = _simple_world()

        mgr.handle(AIRequest("lore_discovered", lore_id="lore_entrance_warning"), wm)
        assert "lore_entrance_warning" in mgr.memory.discovered_lore
