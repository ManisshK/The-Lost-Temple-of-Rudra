"""
test_dataclasses.py — The Lost Temple of Rudra

Tests for Phase 2.1: dataclass initialization and default values.

Verifies that every dataclass in the World Model:
    - Instantiates without errors using default values.
    - Produces the correct default field values.
    - Handles optional fields correctly.
    - Is independent (no shared mutable defaults).

Blueprint Reference: Chapter 10 — Persistent World Model Architecture
"""

import pytest
from world.player_state import PlayerState, TorchStatus, PlayerScores
from world.world_state import WorldState, TemplePhase, FloodLevel, CollapseStage
from world.room_state import RoomState, RoomRegion, LightLevel
from world.object_state import (
    ObjectState, ObjectCategory, TorchState, KeyState,
    StatueDirection, BridgeIntegrity, DoorState, ScrollState, FloodGateState,
)
from world.puzzle_state import PuzzleState, PuzzleCategory, PuzzleStatus
from world.story_state import StoryState, StoryChapter, EndingEligibility
from world.event_state import (
    DynamicEventState, FloodState, TorchBurnState, DustState,
    BridgeEventState, StatueResetState, CollapseState, EventRecord, EventType,
)
from world.evaluation_state import TempleEvaluation, EvaluationAttribute, JudgmentOutcome
from world.mission_state import MissionState, Objective, MissionStatus
from world.history_state import HistoryState, HistoryEntry
from world.world_model import WorldModel, AIContext


# ---------------------------------------------------------------------------
# TorchStatus
# ---------------------------------------------------------------------------

class TestTorchStatus:
    def test_default_state(self):
        t = TorchStatus()
        assert t.state == "unlit"
        assert t.fuel == 100
        assert t.brightness == 0
        assert t.last_lit_turn is None

    def test_custom_values(self):
        t = TorchStatus(state="lit", fuel=64, brightness=70, last_lit_turn=5)
        assert t.state == "lit"
        assert t.fuel == 64
        assert t.brightness == 70
        assert t.last_lit_turn == 5


# ---------------------------------------------------------------------------
# PlayerScores
# ---------------------------------------------------------------------------

class TestPlayerScores:
    def test_all_defaults_zero(self):
        s = PlayerScores()
        for attr in ("observation", "curiosity", "adaptation", "knowledge", "guardian"):
            assert getattr(s, attr) == 0.0

    def test_mutable_independence(self):
        """Two PlayerScores instances must not share state."""
        s1 = PlayerScores()
        s2 = PlayerScores()
        s1.observation = 50.0
        assert s2.observation == 0.0


# ---------------------------------------------------------------------------
# PlayerState
# ---------------------------------------------------------------------------

class TestPlayerState:
    def test_defaults(self):
        p = PlayerState()
        assert p.current_room == "temple_entrance"
        assert p.previous_room is None
        assert p.visited_rooms == []
        assert p.inventory == []
        assert p.steps_taken == 0
        assert p.turns_elapsed == 0
        assert p.health is None

    def test_mutable_list_independence(self):
        """Each PlayerState must get its own list instances."""
        p1 = PlayerState()
        p2 = PlayerState()
        p1.inventory.append("torch")
        assert p2.inventory == []

    def test_torch_is_separate_instance(self):
        p1 = PlayerState()
        p2 = PlayerState()
        p1.torch.fuel = 50
        assert p2.torch.fuel == 100


# ---------------------------------------------------------------------------
# WorldState
# ---------------------------------------------------------------------------

class TestWorldState:
    def test_defaults(self):
        w = WorldState()
        assert w.current_turn == 0
        assert w.current_chapter == 1
        assert w.temple_phase == TemplePhase.DISCOVERY
        assert w.flood_level == FloodLevel.DRY
        assert w.collapse_stage == CollapseStage.NONE
        assert w.dust_density == 0.0
        assert w.ambient_light == 80.0
        assert w.world_stability == 100.0
        assert w.temple_awareness == 0.0
        assert w.temple_alert_level == 0
        assert w.time_cycle == "day"

    def test_enum_values(self):
        assert TemplePhase.DISCOVERY.value == 1
        assert TemplePhase.JUDGMENT.value == 4
        assert FloodLevel.DRY.value == 0
        assert FloodLevel.CRITICAL.value == 5
        assert CollapseStage.NONE.value == 0
        assert CollapseStage.CRITICAL.value == 4


# ---------------------------------------------------------------------------
# RoomState
# ---------------------------------------------------------------------------

class TestRoomState:
    def test_defaults(self):
        r = RoomState()
        assert r.room_id == ""
        assert r.region == RoomRegion.OUTER_TEMPLE
        assert r.visited is False
        assert r.visit_count == 0
        assert r.first_visited_turn is None
        assert r.light_level == LightLevel.NORMAL
        assert r.water_level == 0.0
        assert r.dust_level == 0.0
        assert r.object_ids_present == []
        assert r.puzzle_id is None
        assert r.puzzle_solved is False
        assert r.accessible_exits == {}
        assert r.hidden_passages == {}
        assert r.symbols_found == []
        assert r.lore_discovered == []
        assert r.ambient_effects_active == []

    def test_region_enum_values(self):
        assert RoomRegion.OUTER_TEMPLE.value == "outer_temple"
        assert RoomRegion.GUARDIAN_CORE.value == "guardian_core"

    def test_light_level_enum_values(self):
        assert LightLevel.PITCH_BLACK.value == "pitch_black"
        assert LightLevel.BRIGHT.value == "bright"

    def test_mutable_list_independence(self):
        r1 = RoomState()
        r2 = RoomState()
        r1.object_ids_present.append("torch")
        assert r2.object_ids_present == []


# ---------------------------------------------------------------------------
# ObjectState
# ---------------------------------------------------------------------------

class TestObjectState:
    def test_defaults(self):
        o = ObjectState()
        assert o.object_id == ""
        assert o.name == ""
        assert o.category == ObjectCategory.INTERACTIVE
        assert o.current_room is None
        assert o.current_owner is None
        assert o.condition == 100.0
        assert o.state == ""
        assert o.visible is True
        assert o.discoverable is True
        assert o.interactable is True
        assert o.destroyed is False
        assert o.activated is False
        assert o.facing_direction is None
        assert o.rotation_count == 0
        assert o.last_rotated_turn is None
        assert o.content_id is None

    def test_object_category_enum(self):
        assert ObjectCategory.COLLECTIBLE.value == "collectible"
        assert ObjectCategory.GUARDIAN.value == "guardian"

    def test_statue_direction_enum(self):
        for direction in ("NORTH", "EAST", "SOUTH", "WEST"):
            assert StatueDirection[direction].value == direction.lower()

    def test_all_state_enums_have_values(self):
        """Ensure no state enum is accidentally empty."""
        assert len(TorchState) > 0
        assert len(KeyState) > 0
        assert len(BridgeIntegrity) > 0
        assert len(DoorState) > 0
        assert len(ScrollState) > 0
        assert len(FloodGateState) > 0


# ---------------------------------------------------------------------------
# PuzzleState
# ---------------------------------------------------------------------------

class TestPuzzleState:
    def test_defaults(self):
        p = PuzzleState()
        assert p.puzzle_id == ""
        assert p.room_id == ""
        assert p.category == PuzzleCategory.OBSERVATION
        assert p.status == PuzzleStatus.LOCKED
        assert p.attempt_count == 0
        assert p.failure_count == 0
        assert p.hint_level == 0
        assert p.hint_count == 0
        assert p.reward_given is False
        assert p.reward_id is None
        assert p.observation_before_action is False
        assert p.solved_without_hints is True
        assert p.time_to_solve_turns is None
        assert p.failure_history == []

    def test_puzzle_category_enum(self):
        assert PuzzleCategory.FINAL_JUDGMENT.value == "final_judgment"

    def test_puzzle_status_enum(self):
        assert PuzzleStatus.SOLVED.value == "solved"
        assert PuzzleStatus.RESET.value == "reset"


# ---------------------------------------------------------------------------
# StoryState
# ---------------------------------------------------------------------------

class TestStoryState:
    def test_defaults(self):
        s = StoryState()
        assert s.current_chapter == StoryChapter.PRESENT_DAY
        assert s.chapters_reached == []
        assert s.symbols_encountered == set()
        assert s.entrance_inscription_read is False
        assert s.guardian_truth_discovered is False
        assert s.eye_is_not_object_revealed is False
        assert s.civilization_history_known is False
        assert s.ending_eligibility == EndingEligibility.UNDETERMINED
        assert s.final_revelation_triggered is False
        assert s.transformation_complete is False
        assert s.collapse_sequence_started is False

    def test_story_chapter_range(self):
        """All 13 story chapters must be defined."""
        assert len(StoryChapter) == 13
        assert StoryChapter(1).name == "THE_FORGOTTEN_AGE"
        assert StoryChapter(13).name == "THE_ENDING"

    def test_symbols_encountered_is_set(self):
        s = StoryState()
        s.symbols_encountered.add("eye")
        s.symbols_encountered.add("eye")  # duplicate
        assert len(s.symbols_encountered) == 1

    def test_mutable_set_independence(self):
        s1 = StoryState()
        s2 = StoryState()
        s1.symbols_encountered.add("flame")
        assert "flame" not in s2.symbols_encountered


# ---------------------------------------------------------------------------
# DynamicEventState
# ---------------------------------------------------------------------------

class TestDynamicEventState:
    def test_defaults(self):
        de = DynamicEventState()
        assert de.flood.active is False
        assert de.flood.current_stage == 0
        assert de.torch_burn.base_burn_rate == 1.0
        assert de.dust.global_density == 0.0
        assert de.collapse.active is False
        assert de.collapse.current_stage == 0
        assert de.collapse.escape_route_available is True
        assert de.active_events == []
        assert de.completed_events == []
        assert de.door_states == {}
        assert de.water_gates == {}

    def test_bridge_event_state_defaults(self):
        b = BridgeEventState()
        assert b.integrity == {}
        assert b.collapsed_bridges == []
        assert b.repaired_bridges == []

    def test_statue_reset_defaults(self):
        s = StatueResetState()
        assert s.last_rotated == {}
        assert s.reset_after_turns == 20

    def test_event_type_enum(self):
        assert EventType.ENVIRONMENTAL.value == "environmental"
        assert EventType.COMBINED.value == "combined"


# ---------------------------------------------------------------------------
# TempleEvaluation
# ---------------------------------------------------------------------------

class TestTempleEvaluation:
    def test_all_ten_attributes_present(self):
        e = TempleEvaluation()
        attributes = [
            "observation", "curiosity", "wisdom", "patience", "adaptation",
            "integrity", "responsibility", "understanding", "greed", "recklessness"
        ]
        for attr in attributes:
            val = getattr(e, attr)
            assert isinstance(val, EvaluationAttribute), f"{attr} is not an EvaluationAttribute"
            assert val.score == 0.0
            assert val.change_history == []

    def test_attribute_names_match(self):
        """Each EvaluationAttribute must carry its own name."""
        e = TempleEvaluation()
        assert e.observation.name == "observation"
        assert e.greed.name == "greed"

    def test_judgment_outcome_defaults(self):
        e = TempleEvaluation()
        assert e.final_judgment == JudgmentOutcome.UNDETERMINED
        assert e.judgment_turn is None
        assert e.judgment_narrative == ""

    def test_attribute_independence(self):
        e = TempleEvaluation()
        e.observation.score = 90.0
        assert e.curiosity.score == 0.0


# ---------------------------------------------------------------------------
# MissionState
# ---------------------------------------------------------------------------

class TestMissionState:
    def test_defaults(self):
        m = MissionState()
        assert m.primary_objective is None
        assert m.secondary_objectives == []
        assert m.optional_discoveries == []
        assert m.completed_objectives == []
        assert m.failed_objectives == []
        assert m.current_goal_description == "Explore the temple."
        assert m.current_region_focus == "outer_temple"

    def test_objective_defaults(self):
        o = Objective()
        assert o.objective_id == ""
        assert o.status == MissionStatus.INACTIVE
        assert o.assigned_turn is None
        assert o.completed_turn is None
        assert o.required_for_ending is False


# ---------------------------------------------------------------------------
# HistoryState
# ---------------------------------------------------------------------------

class TestHistoryState:
    def test_defaults(self):
        h = HistoryState()
        assert h.entries == []
        assert h.total_turns == 0

    def test_get_last_n_entries(self):
        h = HistoryState()
        h.entries = [
            HistoryEntry(turn=i, event_id=f"e{i}") for i in range(10)
        ]
        last_3 = h.get_last_n_entries(3)
        assert len(last_3) == 3
        assert last_3[-1].turn == 9

    def test_get_last_n_entries_fewer_than_n(self):
        h = HistoryState()
        h.entries = [HistoryEntry(turn=1)]
        result = h.get_last_n_entries(10)
        assert len(result) == 1

    def test_get_entries_for_room(self):
        h = HistoryState()
        h.entries = [
            HistoryEntry(turn=1, room_id="temple_entrance"),
            HistoryEntry(turn=2, room_id="hall_of_echoes"),
            HistoryEntry(turn=3, room_id="temple_entrance"),
        ]
        result = h.get_entries_for_room("temple_entrance")
        assert len(result) == 2

    def test_get_entries_by_category(self):
        h = HistoryState()
        h.entries = [
            HistoryEntry(turn=1, category="player_action"),
            HistoryEntry(turn=2, category="environmental"),
            HistoryEntry(turn=3, category="player_action"),
        ]
        result = h.get_entries_by_category("player_action")
        assert len(result) == 2

    def test_total_turns_property(self):
        h = HistoryState()
        h.entries = [HistoryEntry(turn=42)]
        assert h.total_turns == 42


# ---------------------------------------------------------------------------
# WorldModel (integration of all sections)
# ---------------------------------------------------------------------------

class TestWorldModelInit:
    def test_instantiates_without_error(self):
        wm = WorldModel()
        assert wm is not None

    def test_all_sections_present(self):
        wm = WorldModel()
        assert hasattr(wm, "player")
        assert hasattr(wm, "world")
        assert hasattr(wm, "rooms")
        assert hasattr(wm, "objects")
        assert hasattr(wm, "puzzles")
        assert hasattr(wm, "story")
        assert hasattr(wm, "dynamic_events")
        assert hasattr(wm, "evaluation")
        assert hasattr(wm, "mission")
        assert hasattr(wm, "history")

    def test_empty_collections_are_independent(self):
        wm1 = WorldModel()
        wm2 = WorldModel()
        wm1.rooms["test"] = RoomState(room_id="test")
        assert "test" not in wm2.rooms

    def test_read_methods_on_empty_model(self):
        wm = WorldModel()
        assert wm.get_room("nonexistent") is None
        assert wm.get_object("nonexistent") is None
        assert wm.get_puzzle("nonexistent") is None
        assert wm.get_current_room() is None
        assert wm.get_inventory_objects() == []
