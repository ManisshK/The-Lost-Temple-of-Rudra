"""
test_validation.py — The Lost Temple of Rudra

Tests for Phase 2.2: WorldModel validation.

Verifies:
    - A correctly populated WorldModel passes validation
    - Each validation rule correctly detects its specific error
    - validate() returns a ValidationResult (never raises)
    - validate_or_raise() raises WorldModelValidationError on failure
    - Warnings are generated for non-blocking issues
    - All eleven validation checks are exercised

Blueprint Reference:
    Chapter 10.8 — State Validation
    Chapter 18   — Testing Strategy
"""

import pytest

from world.world_model import WorldModel
from world.room_state import RoomState, RoomRegion
from world.object_state import ObjectState, ObjectCategory
from world.puzzle_state import PuzzleState, PuzzleCategory, PuzzleStatus
from world.story_state import StoryState, EndingEligibility, StoryChapter
from world.evaluation_state import EvaluationAttribute
from world.history_state import HistoryEntry, HistoryState
from world.validator import (
    validate,
    validate_or_raise,
    ValidationResult,
    WorldModelValidationError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _basic_valid_world() -> WorldModel:
    """
    Constructs the absolute minimum valid WorldModel:
    player sits in temple_entrance which exists in rooms.
    """
    wm = WorldModel()
    wm.rooms["temple_entrance"] = RoomState(room_id="temple_entrance")
    wm.player.current_room = "temple_entrance"
    return wm


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestValidationHappyPath:
    def test_minimal_valid_world_passes(self):
        wm = _basic_valid_world()
        result = validate(wm)
        assert result.is_valid, str(result)
        assert result.errors == []

    def test_populated_fixture_passes(self, populated_world):
        result = validate(populated_world)
        assert result.is_valid, str(result)

    def test_validation_result_str_on_pass(self):
        wm = _basic_valid_world()
        result = validate(wm)
        assert "PASSED" in str(result)

    def test_validate_or_raise_does_not_raise_on_valid(self):
        wm = _basic_valid_world()
        validate_or_raise(wm)  # must not raise

    def test_method_interface_matches_function(self, populated_world):
        """WorldModel.validate() must produce the same result as validator.validate()."""
        via_method = populated_world.validate()
        via_function = validate(populated_world)
        assert via_method.is_valid == via_function.is_valid
        assert via_method.errors == via_function.errors


# ---------------------------------------------------------------------------
# Player validation
# ---------------------------------------------------------------------------

class TestPlayerValidation:
    def test_current_room_not_in_rooms(self):
        wm = WorldModel()
        wm.player.current_room = "nonexistent_room"
        result = validate(wm)
        assert not result.is_valid
        assert any("current_room" in e and "nonexistent_room" in e
                   for e in result.errors)

    def test_previous_room_not_in_rooms(self):
        wm = _basic_valid_world()
        wm.player.previous_room = "ghost_room"
        result = validate(wm)
        assert not result.is_valid
        assert any("previous_room" in e for e in result.errors)

    def test_inventory_references_unknown_object(self):
        wm = _basic_valid_world()
        wm.player.inventory.append("nonexistent_object")
        result = validate(wm)
        assert not result.is_valid
        assert any("nonexistent_object" in e for e in result.errors)

    def test_torch_fuel_out_of_range_high(self):
        wm = _basic_valid_world()
        wm.player.torch.fuel = 150
        result = validate(wm)
        assert not result.is_valid
        assert any("torch.fuel" in e for e in result.errors)

    def test_torch_fuel_out_of_range_negative(self):
        wm = _basic_valid_world()
        wm.player.torch.fuel = -1
        result = validate(wm)
        assert not result.is_valid

    def test_torch_brightness_out_of_range(self):
        wm = _basic_valid_world()
        wm.player.torch.brightness = 200
        result = validate(wm)
        assert not result.is_valid

    def test_negative_steps_taken(self):
        wm = _basic_valid_world()
        wm.player.steps_taken = -5
        result = validate(wm)
        assert not result.is_valid

    def test_negative_turns_elapsed(self):
        wm = _basic_valid_world()
        wm.player.turns_elapsed = -1
        result = validate(wm)
        assert not result.is_valid

    def test_visited_rooms_contains_unknown_room(self):
        wm = _basic_valid_world()
        wm.player.visited_rooms.append("mystery_room")
        result = validate(wm)
        assert not result.is_valid


# ---------------------------------------------------------------------------
# World state validation
# ---------------------------------------------------------------------------

class TestWorldStateValidation:
    def test_negative_turn(self):
        wm = _basic_valid_world()
        wm.world.current_turn = -1
        result = validate(wm)
        assert not result.is_valid

    def test_chapter_out_of_range_low(self):
        wm = _basic_valid_world()
        wm.world.current_chapter = 0
        result = validate(wm)
        assert not result.is_valid

    def test_chapter_out_of_range_high(self):
        wm = _basic_valid_world()
        wm.world.current_chapter = 14
        result = validate(wm)
        assert not result.is_valid

    def test_dust_density_out_of_range(self):
        wm = _basic_valid_world()
        wm.world.dust_density = 101.0
        result = validate(wm)
        assert not result.is_valid

    def test_ambient_light_negative(self):
        wm = _basic_valid_world()
        wm.world.ambient_light = -10.0
        result = validate(wm)
        assert not result.is_valid

    def test_world_stability_out_of_range(self):
        wm = _basic_valid_world()
        wm.world.world_stability = 200.0
        result = validate(wm)
        assert not result.is_valid

    def test_temple_awareness_out_of_range(self):
        wm = _basic_valid_world()
        wm.world.temple_awareness = 101.0
        result = validate(wm)
        assert not result.is_valid

    def test_invalid_alert_level(self):
        wm = _basic_valid_world()
        wm.world.temple_alert_level = 5
        result = validate(wm)
        assert not result.is_valid


# ---------------------------------------------------------------------------
# Room validation
# ---------------------------------------------------------------------------

class TestRoomValidation:
    def test_room_id_key_mismatch(self):
        wm = _basic_valid_world()
        wm.rooms["wrong_key"] = RoomState(room_id="actual_id")
        wm.player.current_room = "temple_entrance"
        result = validate(wm)
        assert not result.is_valid
        assert any("wrong_key" in e for e in result.errors)

    def test_water_level_out_of_range(self):
        wm = _basic_valid_world()
        wm.rooms["temple_entrance"].water_level = 150.0
        result = validate(wm)
        assert not result.is_valid

    def test_dust_level_out_of_range(self):
        wm = _basic_valid_world()
        wm.rooms["temple_entrance"].dust_level = -5.0
        result = validate(wm)
        assert not result.is_valid

    def test_environmental_damage_out_of_range(self):
        wm = _basic_valid_world()
        wm.rooms["temple_entrance"].environmental_damage = 110.0
        result = validate(wm)
        assert not result.is_valid

    def test_room_references_unknown_object(self):
        wm = _basic_valid_world()
        wm.rooms["temple_entrance"].object_ids_present.append("ghost_object")
        result = validate(wm)
        assert not result.is_valid
        assert any("ghost_object" in e for e in result.errors)

    def test_room_references_unknown_puzzle(self):
        wm = _basic_valid_world()
        wm.rooms["temple_entrance"].puzzle_id = "nonexistent_puzzle"
        result = validate(wm)
        assert not result.is_valid

    def test_negative_visit_count(self):
        wm = _basic_valid_world()
        wm.rooms["temple_entrance"].visit_count = -1
        result = validate(wm)
        assert not result.is_valid


# ---------------------------------------------------------------------------
# Object validation
# ---------------------------------------------------------------------------

class TestObjectValidation:
    def test_object_in_inventory_and_room_simultaneously(self):
        """An object cannot be both in inventory and in a room."""
        wm = _basic_valid_world()
        wm.objects["torch"] = ObjectState(
            object_id="torch",
            current_room="temple_entrance",
            current_owner="player",
        )
        wm.player.inventory.append("torch")
        wm.rooms["temple_entrance"].object_ids_present.append("torch")
        result = validate(wm)
        assert not result.is_valid
        assert any("simultaneously" in e for e in result.errors)

    def test_object_references_nonexistent_room(self):
        wm = _basic_valid_world()
        wm.objects["torch"] = ObjectState(
            object_id="torch",
            current_room="ghost_room",
        )
        result = validate(wm)
        assert not result.is_valid

    def test_object_condition_out_of_range(self):
        wm = _basic_valid_world()
        wm.objects["torch"] = ObjectState(
            object_id="torch",
            current_room="temple_entrance",
            condition=110.0,
        )
        result = validate(wm)
        assert not result.is_valid

    def test_object_key_mismatch(self):
        wm = _basic_valid_world()
        wm.objects["wrong_key"] = ObjectState(object_id="actual_id")
        result = validate(wm)
        assert not result.is_valid

    def test_object_in_room_but_not_listed_generates_warning(self):
        """
        Object claims to be in a room but not listed in object_ids_present
        — should be a warning, not an error.
        """
        wm = _basic_valid_world()
        wm.objects["torch"] = ObjectState(
            object_id="torch",
            current_room="temple_entrance",
            # NOT added to room.object_ids_present
        )
        result = validate(wm)
        # May have a warning but should still be valid (no hard errors from this alone)
        assert any("not listed" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Inventory ownership validation
# ---------------------------------------------------------------------------

class TestInventoryOwnership:
    def test_inventory_item_wrong_owner(self):
        wm = _basic_valid_world()
        wm.objects["torch"] = ObjectState(
            object_id="torch",
            current_owner=None,  # wrong — should be "player"
            current_room=None,
        )
        wm.player.inventory.append("torch")
        result = validate(wm)
        assert not result.is_valid
        assert any("current_owner" in e for e in result.errors)

    def test_inventory_item_still_has_room(self):
        wm = _basic_valid_world()
        wm.objects["torch"] = ObjectState(
            object_id="torch",
            current_owner="player",
            current_room="temple_entrance",  # wrong — should be None
        )
        wm.player.inventory.append("torch")
        # The "simultaneously in inventory and room" check fires first
        result = validate(wm)
        assert not result.is_valid


# ---------------------------------------------------------------------------
# Puzzle validation
# ---------------------------------------------------------------------------

class TestPuzzleValidation:
    def test_puzzle_key_mismatch(self):
        wm = _basic_valid_world()
        wm.puzzles["wrong_key"] = PuzzleState(
            puzzle_id="actual_id",
            room_id="temple_entrance",
        )
        result = validate(wm)
        assert not result.is_valid

    def test_puzzle_references_unknown_room(self):
        wm = _basic_valid_world()
        wm.puzzles["p1"] = PuzzleState(
            puzzle_id="p1",
            room_id="ghost_room",
        )
        result = validate(wm)
        assert not result.is_valid

    def test_puzzle_negative_attempt_count(self):
        wm = _basic_valid_world()
        wm.puzzles["p1"] = PuzzleState(
            puzzle_id="p1",
            room_id="temple_entrance",
            attempt_count=-1,
        )
        result = validate(wm)
        assert not result.is_valid

    def test_puzzle_negative_failure_count(self):
        wm = _basic_valid_world()
        wm.puzzles["p1"] = PuzzleState(
            puzzle_id="p1",
            room_id="temple_entrance",
            failure_count=-3,
        )
        result = validate(wm)
        assert not result.is_valid

    def test_puzzle_negative_hint_level(self):
        wm = _basic_valid_world()
        wm.puzzles["p1"] = PuzzleState(
            puzzle_id="p1",
            room_id="temple_entrance",
            hint_level=-1,
        )
        result = validate(wm)
        assert not result.is_valid

    def test_solved_puzzle_without_solved_turn_warning(self):
        wm = _basic_valid_world()
        wm.puzzles["p1"] = PuzzleState(
            puzzle_id="p1",
            room_id="temple_entrance",
            status=PuzzleStatus.SOLVED,
            solved_turn=None,  # missing
        )
        result = validate(wm)
        assert any("solved_turn" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Story validation
# ---------------------------------------------------------------------------

class TestStoryValidation:
    def test_invalid_chapter_value_in_reached(self):
        wm = _basic_valid_world()
        wm.story.chapters_reached = [0]  # invalid — chapters are 1–13
        result = validate(wm)
        assert not result.is_valid

    def test_transformation_without_revelation(self):
        wm = _basic_valid_world()
        wm.story.transformation_complete = True
        wm.story.final_revelation_triggered = False
        result = validate(wm)
        assert not result.is_valid
        assert any("transformation_complete" in e for e in result.errors)

    def test_collapse_without_transformation(self):
        wm = _basic_valid_world()
        wm.story.collapse_sequence_started = True
        wm.story.transformation_complete = False
        result = validate(wm)
        assert not result.is_valid

    def test_worthy_without_revelation_warning(self):
        wm = _basic_valid_world()
        wm.story.ending_eligibility = EndingEligibility.WORTHY
        wm.story.final_revelation_triggered = False
        result = validate(wm)
        # Warning, not error
        assert any("WORTHY" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Evaluation validation
# ---------------------------------------------------------------------------

class TestEvaluationValidation:
    def test_score_above_100(self):
        wm = _basic_valid_world()
        wm.evaluation.observation.score = 101.0
        result = validate(wm)
        assert not result.is_valid

    def test_score_below_0(self):
        wm = _basic_valid_world()
        wm.evaluation.curiosity.score = -1.0
        result = validate(wm)
        assert not result.is_valid

    def test_all_ten_attributes_validated(self):
        """Each of the ten attributes must be individually range-checked."""
        attributes = [
            "observation", "curiosity", "wisdom", "patience", "adaptation",
            "integrity", "responsibility", "understanding", "greed", "recklessness"
        ]
        for attr in attributes:
            wm = _basic_valid_world()
            getattr(wm.evaluation, attr).score = -5.0
            result = validate(wm)
            assert not result.is_valid, f"{attr} should have failed validation"
            assert any(attr in e for e in result.errors), \
                f"Error message should mention '{attr}'"


# ---------------------------------------------------------------------------
# Dynamic event validation
# ---------------------------------------------------------------------------

class TestDynamicEventValidation:
    def test_collapse_stage_out_of_range(self):
        wm = _basic_valid_world()
        wm.dynamic_events.collapse.current_stage = 5  # valid range is 0–4
        result = validate(wm)
        assert not result.is_valid

    def test_flood_stage_out_of_range(self):
        wm = _basic_valid_world()
        wm.dynamic_events.flood.current_stage = 6  # valid range is 0–5
        result = validate(wm)
        assert not result.is_valid

    def test_negative_dust_density(self):
        wm = _basic_valid_world()
        wm.dynamic_events.dust.global_density = -1.0
        result = validate(wm)
        assert not result.is_valid

    def test_bridge_integrity_out_of_range(self):
        wm = _basic_valid_world()
        wm.dynamic_events.bridge.integrity["bridge_of_echoes"] = 150.0
        result = validate(wm)
        assert not result.is_valid


# ---------------------------------------------------------------------------
# History validation
# ---------------------------------------------------------------------------

class TestHistoryValidation:
    def test_out_of_order_history(self):
        wm = _basic_valid_world()
        wm.history.entries = [
            HistoryEntry(turn=10),
            HistoryEntry(turn=5),  # goes backwards — invalid
        ]
        result = validate(wm)
        assert not result.is_valid
        assert any("chronologically" in e for e in result.errors)

    def test_monotonically_increasing_history_passes(self):
        wm = _basic_valid_world()
        wm.history.entries = [
            HistoryEntry(turn=1),
            HistoryEntry(turn=1),  # same turn is allowed (multiple events per turn)
            HistoryEntry(turn=5),
            HistoryEntry(turn=10),
        ]
        result = validate(wm)
        assert result.is_valid, str(result)


# ---------------------------------------------------------------------------
# Turn consistency validation
# ---------------------------------------------------------------------------

class TestTurnConsistency:
    def test_player_turns_mismatch_world_turn_warning(self):
        wm = _basic_valid_world()
        wm.player.turns_elapsed = 5
        wm.world.current_turn = 10  # mismatch
        result = validate(wm)
        assert any("turns_elapsed" in w for w in result.warnings)

    def test_matching_turns_no_warning(self):
        wm = _basic_valid_world()
        wm.player.turns_elapsed = 7
        wm.world.current_turn = 7
        result = validate(wm)
        assert not any("turns_elapsed" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# validate_or_raise
# ---------------------------------------------------------------------------

class TestValidateOrRaise:
    def test_raises_on_invalid(self):
        wm = WorldModel()  # player.current_room not in rooms
        with pytest.raises(WorldModelValidationError) as exc_info:
            validate_or_raise(wm)
        assert not exc_info.value.result.is_valid

    def test_exception_carries_result(self):
        wm = WorldModel()
        try:
            validate_or_raise(wm)
        except WorldModelValidationError as e:
            assert isinstance(e.result, ValidationResult)
            assert len(e.result.errors) > 0

    def test_exception_str_contains_error_count(self):
        wm = WorldModel()
        try:
            validate_or_raise(wm)
        except WorldModelValidationError as e:
            assert "FAILED" in str(e)

    def test_does_not_raise_on_valid(self):
        wm = _basic_valid_world()
        # Must not raise
        validate_or_raise(wm)
