"""
test_serialization.py — The Lost Temple of Rudra

Tests for Phase 2.2: serialization and deserialization of the WorldModel.

Verifies:
    - to_dict() produces a valid plain dictionary
    - to_json() produces valid JSON
    - from_dict() restores the exact same state
    - from_json() restores the exact same state
    - Enum values round-trip correctly (stored as primitives, restored as Enums)
    - set (symbols_encountered) round-trips correctly
    - tuple entries (change_history) round-trip correctly
    - Deserialization errors are raised correctly

Blueprint Reference: Chapter 10.7 — Save & Load Architecture
"""

import json
import pytest

from world.world_model import WorldModel
from world.world_state import TemplePhase, FloodLevel, CollapseStage
from world.room_state import RoomState, RoomRegion, LightLevel
from world.object_state import ObjectState, ObjectCategory, StatueDirection
from world.puzzle_state import PuzzleState, PuzzleCategory, PuzzleStatus
from world.story_state import StoryState, StoryChapter, EndingEligibility
from world.evaluation_state import JudgmentOutcome
from world.mission_state import MissionStatus
from world.history_state import HistoryEntry, HistoryState
from world.serializer import (
    WorldModelDeserializationError,
    world_model_to_dict,
    world_model_from_dict,
    world_model_to_json,
    world_model_from_json,
)


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------

class TestToDict:
    def test_returns_dict(self, minimal_world):
        result = minimal_world.to_dict()
        assert isinstance(result, dict)

    def test_all_top_level_sections_present(self, minimal_world):
        result = minimal_world.to_dict()
        for key in ("player", "world", "rooms", "objects", "puzzles",
                    "story", "dynamic_events", "evaluation", "mission", "history"):
            assert key in result, f"Missing top-level key: {key}"

    def test_enum_serialized_as_primitive(self, minimal_world):
        result = minimal_world.to_dict()
        # TemplePhase.DISCOVERY → 1 (int)
        assert result["world"]["temple_phase"] == 1
        # FloodLevel.DRY → 0
        assert result["world"]["flood_level"] == 0
        # RoomRegion value is a string
        # (no rooms in minimal_world, check with populated)

    def test_enum_in_rooms_serialized(self, populated_world):
        result = populated_world.to_dict()
        room = result["rooms"]["temple_entrance"]
        assert room["region"] == "outer_temple"
        assert room["light_level"] == "dim"

    def test_set_serialized_as_list(self, populated_world):
        """StoryState.symbols_encountered must become a JSON-compatible list."""
        result = populated_world.to_dict()
        symbols = result["story"]["symbols_encountered"]
        assert isinstance(symbols, list)
        assert "eye" in symbols

    def test_tuple_serialized_as_list(self, populated_world):
        """EvaluationAttribute.change_history tuples must become lists."""
        result = populated_world.to_dict()
        history = result["evaluation"]["observation"]["change_history"]
        assert isinstance(history, list)
        for entry in history:
            assert isinstance(entry, list)  # tuples become lists in JSON

    def test_no_unserializable_types(self, populated_world):
        """to_dict output must be directly passable to json.dumps."""
        result = populated_world.to_dict()
        # Should not raise
        json.dumps(result)

    def test_object_category_serialized(self, populated_world):
        result = populated_world.to_dict()
        torch = result["objects"]["torch_carried"]
        assert torch["category"] == "collectible"

    def test_statue_direction_serialized(self, populated_world):
        result = populated_world.to_dict()
        statue = result["objects"]["guardian_statue_east"]
        assert statue["facing_direction"] == "north"

    def test_puzzle_status_serialized(self, populated_world):
        result = populated_world.to_dict()
        puzzle = result["puzzles"]["puzzle_entrance_inscription"]
        assert puzzle["status"] == "solved"
        assert puzzle["category"] == "observation"


# ---------------------------------------------------------------------------
# to_json
# ---------------------------------------------------------------------------

class TestToJson:
    def test_returns_string(self, minimal_world):
        result = minimal_world.to_json()
        assert isinstance(result, str)

    def test_valid_json(self, populated_world):
        json_str = populated_world.to_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_default_indent(self, minimal_world):
        json_str = minimal_world.to_json()
        assert "\n" in json_str  # indented output

    def test_custom_indent(self, minimal_world):
        json_str = minimal_world.to_json(indent=4)
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_content_matches_to_dict(self, populated_world):
        from_dict_result = populated_world.to_dict()
        from_json_result = json.loads(populated_world.to_json())
        assert from_dict_result == from_json_result


# ---------------------------------------------------------------------------
# from_dict / from_json — round-trip correctness
# ---------------------------------------------------------------------------

class TestFromDict:
    def test_roundtrip_minimal(self, minimal_world):
        data = minimal_world.to_dict()
        restored = WorldModel.from_dict(data)
        assert restored.player.current_room == minimal_world.player.current_room
        assert restored.world.current_turn == minimal_world.world.current_turn

    def test_roundtrip_populated(self, populated_world):
        data = populated_world.to_dict()
        restored = WorldModel.from_dict(data)

        # Player
        assert restored.player.current_room == "hall_of_echoes"
        assert restored.player.previous_room == "temple_entrance"
        assert restored.player.steps_taken == 12
        assert restored.player.turns_elapsed == 18
        assert restored.player.inventory == ["torch_carried"]
        assert restored.player.torch.fuel == 64
        assert restored.player.torch.state == "lit"

        # World
        assert restored.world.current_turn == 18
        assert restored.world.current_chapter == 6
        assert restored.world.ambient_light == 75.0

    def test_enum_restored_correctly(self, populated_world):
        restored = WorldModel.from_dict(populated_world.to_dict())
        assert restored.world.temple_phase == TemplePhase.DISCOVERY
        assert restored.world.flood_level == FloodLevel.DRY
        assert restored.world.collapse_stage == CollapseStage.NONE

    def test_room_enum_restored(self, populated_world):
        restored = WorldModel.from_dict(populated_world.to_dict())
        assert restored.rooms["temple_entrance"].region == RoomRegion.OUTER_TEMPLE
        assert restored.rooms["temple_entrance"].light_level == LightLevel.DIM

    def test_object_category_enum_restored(self, populated_world):
        restored = WorldModel.from_dict(populated_world.to_dict())
        assert restored.objects["torch_carried"].category == ObjectCategory.COLLECTIBLE
        assert restored.objects["inscription_entrance"].category == ObjectCategory.STORY

    def test_statue_direction_enum_restored(self, populated_world):
        restored = WorldModel.from_dict(populated_world.to_dict())
        statue = restored.objects["guardian_statue_east"]
        assert statue.facing_direction == StatueDirection.NORTH

    def test_puzzle_enums_restored(self, populated_world):
        restored = WorldModel.from_dict(populated_world.to_dict())
        solved = restored.puzzles["puzzle_entrance_inscription"]
        assert solved.status == PuzzleStatus.SOLVED
        assert solved.category == PuzzleCategory.OBSERVATION

        locked = restored.puzzles["puzzle_guardian_statues"]
        assert locked.status == PuzzleStatus.LOCKED
        assert locked.category == PuzzleCategory.LOGIC

    def test_story_chapter_enum_restored(self, populated_world):
        restored = WorldModel.from_dict(populated_world.to_dict())
        assert restored.story.current_chapter == StoryChapter.THE_JOURNEY

    def test_set_restored_as_set(self, populated_world):
        """symbols_encountered must come back as a Python set."""
        restored = WorldModel.from_dict(populated_world.to_dict())
        assert isinstance(restored.story.symbols_encountered, set)
        assert "eye" in restored.story.symbols_encountered

    def test_tuple_restored_as_tuple(self, populated_world):
        """change_history entries must come back as tuples."""
        restored = WorldModel.from_dict(populated_world.to_dict())
        history = restored.evaluation.observation.change_history
        assert len(history) == 2
        for entry in history:
            assert isinstance(entry, tuple), f"Expected tuple, got {type(entry)}"
        assert history[0] == (3, 10.0, "read entrance inscription")

    def test_evaluation_scores_restored(self, populated_world):
        restored = WorldModel.from_dict(populated_world.to_dict())
        assert restored.evaluation.observation.score == 88.0
        assert restored.evaluation.curiosity.score == 55.0
        assert restored.evaluation.greed.score == 0.0

    def test_mission_state_restored(self, populated_world):
        restored = WorldModel.from_dict(populated_world.to_dict())
        assert restored.mission.primary_objective is not None
        assert restored.mission.primary_objective.objective_id == "obj_reach_library"
        assert restored.mission.primary_objective.status == MissionStatus.ACTIVE
        assert restored.mission.current_goal_description == "Reach the Ancient Library."

    def test_history_entries_restored(self, populated_world):
        restored = WorldModel.from_dict(populated_world.to_dict())
        assert len(restored.history.entries) == 4
        first = restored.history.entries[0]
        assert first.turn == 1
        assert first.event_id == "enter_temple"
        assert first.room_id == "temple_entrance"

    def test_rooms_preserved(self, populated_world):
        restored = WorldModel.from_dict(populated_world.to_dict())
        assert "temple_entrance" in restored.rooms
        assert "hall_of_echoes" in restored.rooms
        assert "hall_of_guardians" in restored.rooms
        assert restored.rooms["temple_entrance"].visited is True
        assert restored.rooms["hall_of_guardians"].visited is False

    def test_none_fields_preserved(self, populated_world):
        restored = WorldModel.from_dict(populated_world.to_dict())
        assert restored.player.health is None
        assert restored.puzzles["puzzle_guardian_statues"].solved_turn is None


class TestFromJson:
    def test_roundtrip_from_json(self, populated_world):
        json_str = populated_world.to_json()
        restored = WorldModel.from_json(json_str)
        assert restored.player.current_room == "hall_of_echoes"
        assert restored.world.temple_phase == TemplePhase.DISCOVERY

    def test_invalid_json_raises_error(self):
        with pytest.raises(WorldModelDeserializationError):
            WorldModel.from_json("{bad json}")

    def test_empty_json_object_deserializes(self):
        """An empty JSON object {} should produce a valid default WorldModel."""
        wm = WorldModel.from_json("{}")
        assert wm.player.current_room == "temple_entrance"

    def test_deserialization_error_on_invalid_enum(self):
        """An unknown enum value must raise WorldModelDeserializationError."""
        import json as _json
        data = WorldModel().to_dict()
        data["world"]["temple_phase"] = 999  # invalid TemplePhase value
        with pytest.raises(WorldModelDeserializationError):
            WorldModel.from_dict(data)

    def test_standalone_serializer_functions(self, populated_world):
        """The module-level serializer functions must produce identical results."""
        via_method = populated_world.to_dict()
        via_function = world_model_to_dict(populated_world)
        assert via_method == via_function

        json_via_method = populated_world.to_json()
        json_via_function = world_model_to_json(populated_world)
        assert json_via_method == json_via_function


# ---------------------------------------------------------------------------
# Deep copy / snapshot
# ---------------------------------------------------------------------------

class TestSnapshot:
    def test_get_snapshot_returns_independent_copy(self, populated_world):
        snapshot = populated_world.get_snapshot()
        # Mutate the original
        populated_world.player.steps_taken = 9999
        # Snapshot must be unaffected
        assert snapshot.player.steps_taken == 12

    def test_snapshot_rooms_independent(self, populated_world):
        snapshot = populated_world.get_snapshot()
        populated_world.rooms["temple_entrance"].visited = False
        assert snapshot.rooms["temple_entrance"].visited is True

    def test_snapshot_history_independent(self, populated_world):
        snapshot = populated_world.get_snapshot()
        populated_world.history.entries.append(
            HistoryEntry(turn=999, event_id="phantom")
        )
        assert len(snapshot.history.entries) == 4
