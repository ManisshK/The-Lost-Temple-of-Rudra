"""
test_world_model_write.py — The Lost Temple of Rudra

Tests for WorldModel write interface methods and AI context generation.

Verifies:
    - _increment_turn() updates both player and world counters
    - _record_command() appends to command history
    - _update_evaluation() clamps scores and records history
    - _update_player_room() updates position, visited rooms, movement history
    - _update_object_state() modifies correct object fields
    - _update_puzzle_state() modifies correct puzzle fields
    - _add_to_inventory() moves object from room to inventory
    - _remove_from_inventory() moves object from inventory to room
    - _append_history() appends an immutable entry
    - get_ai_context() returns a sanitised snapshot
    - get_ai_context() excludes hidden information

Blueprint Reference:
    Chapter 10 — Persistent World Model Architecture
    Chapter 9  — AI Architecture (AI Context section)
"""

import pytest

from world.world_model import WorldModel, AIContext
from world.room_state import RoomState, RoomRegion
from world.object_state import ObjectState, ObjectCategory
from world.puzzle_state import PuzzleState, PuzzleStatus
from world.history_state import HistoryEntry


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _world_with_room(room_id: str = "temple_entrance") -> WorldModel:
    wm = WorldModel()
    wm.rooms[room_id] = RoomState(room_id=room_id)
    wm.player.current_room = room_id
    return wm


# ---------------------------------------------------------------------------
# _increment_turn
# ---------------------------------------------------------------------------

class TestIncrementTurn:
    def test_increments_both_counters(self):
        wm = WorldModel()
        wm._increment_turn()
        assert wm.player.turns_elapsed == 1
        assert wm.world.current_turn == 1

    def test_multiple_increments(self):
        wm = WorldModel()
        for _ in range(5):
            wm._increment_turn()
        assert wm.player.turns_elapsed == 5
        assert wm.world.current_turn == 5


# ---------------------------------------------------------------------------
# _record_command
# ---------------------------------------------------------------------------

class TestRecordCommand:
    def test_appends_command(self):
        wm = WorldModel()
        wm._record_command("look")
        assert wm.player.command_history == ["look"]

    def test_multiple_commands_ordered(self):
        wm = WorldModel()
        for cmd in ["look", "inspect statue", "go north"]:
            wm._record_command(cmd)
        assert wm.player.command_history == ["look", "inspect statue", "go north"]


# ---------------------------------------------------------------------------
# _update_evaluation
# ---------------------------------------------------------------------------

class TestUpdateEvaluation:
    def test_increases_score(self):
        wm = WorldModel()
        wm._update_evaluation("observation", 10.0, "read inscription", 1)
        assert wm.evaluation.observation.score == 10.0

    def test_records_history_entry(self):
        wm = WorldModel()
        wm._update_evaluation("curiosity", 5.0, "explored optional room", 3)
        history = wm.evaluation.curiosity.change_history
        assert len(history) == 1
        assert history[0] == (3, 5.0, "explored optional room")

    def test_clamps_at_100(self):
        wm = WorldModel()
        wm._update_evaluation("wisdom", 200.0, "massive score", 1)
        assert wm.evaluation.wisdom.score == 100.0

    def test_clamps_at_0(self):
        wm = WorldModel()
        wm._update_evaluation("greed", -50.0, "negative delta", 1)
        assert wm.evaluation.greed.score == 0.0

    def test_unknown_attribute_does_nothing(self):
        """Updating a non-existent attribute must not crash."""
        wm = WorldModel()
        wm._update_evaluation("nonexistent_attr", 10.0, "test", 1)
        # No exception raised


# ---------------------------------------------------------------------------
# _update_player_room
# ---------------------------------------------------------------------------

class TestUpdatePlayerRoom:
    def test_updates_current_room(self):
        wm = _world_with_room("temple_entrance")
        wm.rooms["hall_of_echoes"] = RoomState(room_id="hall_of_echoes")
        wm._update_player_room("hall_of_echoes", turn=5)
        assert wm.player.current_room == "hall_of_echoes"

    def test_updates_previous_room(self):
        wm = _world_with_room("temple_entrance")
        wm.rooms["hall_of_echoes"] = RoomState(room_id="hall_of_echoes")
        wm._update_player_room("hall_of_echoes", turn=5)
        assert wm.player.previous_room == "temple_entrance"

    def test_adds_to_movement_history(self):
        wm = _world_with_room("temple_entrance")
        wm.rooms["hall_of_echoes"] = RoomState(room_id="hall_of_echoes")
        wm._update_player_room("hall_of_echoes", turn=5)
        assert "hall_of_echoes" in wm.player.movement_history

    def test_adds_to_visited_rooms_once(self):
        wm = _world_with_room("temple_entrance")
        wm.rooms["hall_of_echoes"] = RoomState(room_id="hall_of_echoes")
        wm._update_player_room("hall_of_echoes", turn=5)
        wm._update_player_room("hall_of_echoes", turn=6)
        assert wm.player.visited_rooms.count("hall_of_echoes") == 1

    def test_increments_steps_taken(self):
        wm = _world_with_room("temple_entrance")
        wm.rooms["hall_of_echoes"] = RoomState(room_id="hall_of_echoes")
        wm._update_player_room("hall_of_echoes", turn=5)
        assert wm.player.steps_taken == 1

    def test_marks_room_visited(self):
        wm = _world_with_room("temple_entrance")
        wm.rooms["hall_of_echoes"] = RoomState(room_id="hall_of_echoes")
        assert wm.rooms["hall_of_echoes"].visited is False
        wm._update_player_room("hall_of_echoes", turn=5)
        assert wm.rooms["hall_of_echoes"].visited is True
        assert wm.rooms["hall_of_echoes"].first_visited_turn == 5

    def test_visit_count_increments(self):
        wm = _world_with_room("temple_entrance")
        wm.rooms["hall_of_echoes"] = RoomState(room_id="hall_of_echoes")
        wm._update_player_room("hall_of_echoes", turn=5)
        wm._update_player_room("hall_of_echoes", turn=8)
        assert wm.rooms["hall_of_echoes"].visit_count == 2


# ---------------------------------------------------------------------------
# _update_object_state
# ---------------------------------------------------------------------------

class TestUpdateObjectState:
    def test_updates_existing_field(self):
        wm = _world_with_room()
        wm.objects["torch"] = ObjectState(object_id="torch", state="unlit")
        wm._update_object_state("torch", state="lit")
        assert wm.objects["torch"].state == "lit"

    def test_updates_condition(self):
        wm = _world_with_room()
        wm.objects["torch"] = ObjectState(object_id="torch", condition=100.0)
        wm._update_object_state("torch", condition=64.0)
        assert wm.objects["torch"].condition == 64.0

    def test_unknown_object_does_nothing(self):
        """Updating a non-existent object must not crash."""
        wm = WorldModel()
        wm._update_object_state("ghost_object", state="lit")

    def test_unknown_field_does_nothing(self):
        """Updating an unknown field must not crash."""
        wm = _world_with_room()
        wm.objects["torch"] = ObjectState(object_id="torch")
        wm._update_object_state("torch", nonexistent_field=True)


# ---------------------------------------------------------------------------
# _update_puzzle_state
# ---------------------------------------------------------------------------

class TestUpdatePuzzleState:
    def test_updates_status(self):
        wm = _world_with_room()
        wm.puzzles["p1"] = PuzzleState(puzzle_id="p1", room_id="temple_entrance")
        wm._update_puzzle_state("p1", status=PuzzleStatus.SOLVED)
        assert wm.puzzles["p1"].status == PuzzleStatus.SOLVED

    def test_updates_attempt_count(self):
        wm = _world_with_room()
        wm.puzzles["p1"] = PuzzleState(puzzle_id="p1", room_id="temple_entrance")
        wm._update_puzzle_state("p1", attempt_count=3)
        assert wm.puzzles["p1"].attempt_count == 3

    def test_unknown_puzzle_does_nothing(self):
        wm = WorldModel()
        wm._update_puzzle_state("ghost_puzzle", status=PuzzleStatus.SOLVED)


# ---------------------------------------------------------------------------
# _add_to_inventory
# ---------------------------------------------------------------------------

class TestAddToInventory:
    def test_adds_to_player_inventory(self):
        wm = _world_with_room()
        wm.objects["torch"] = ObjectState(
            object_id="torch",
            current_room="temple_entrance",
        )
        wm.rooms["temple_entrance"].object_ids_present.append("torch")
        wm._add_to_inventory("torch")
        assert "torch" in wm.player.inventory

    def test_removes_from_room(self):
        wm = _world_with_room()
        wm.objects["torch"] = ObjectState(
            object_id="torch",
            current_room="temple_entrance",
        )
        wm.rooms["temple_entrance"].object_ids_present.append("torch")
        wm._add_to_inventory("torch")
        assert "torch" not in wm.rooms["temple_entrance"].object_ids_present

    def test_sets_owner_to_player(self):
        wm = _world_with_room()
        wm.objects["torch"] = ObjectState(
            object_id="torch",
            current_room="temple_entrance",
        )
        wm._add_to_inventory("torch")
        assert wm.objects["torch"].current_owner == "player"
        assert wm.objects["torch"].current_room is None

    def test_no_duplicate_in_inventory(self):
        wm = _world_with_room()
        wm.objects["torch"] = ObjectState(object_id="torch")
        wm._add_to_inventory("torch")
        wm._add_to_inventory("torch")  # second call
        assert wm.player.inventory.count("torch") == 1


# ---------------------------------------------------------------------------
# _remove_from_inventory
# ---------------------------------------------------------------------------

class TestRemoveFromInventory:
    def test_removes_from_inventory(self):
        wm = _world_with_room()
        wm.objects["torch"] = ObjectState(
            object_id="torch",
            current_owner="player",
            current_room=None,
        )
        wm.player.inventory.append("torch")
        wm._remove_from_inventory("torch", "temple_entrance")
        assert "torch" not in wm.player.inventory

    def test_places_in_room(self):
        wm = _world_with_room()
        wm.objects["torch"] = ObjectState(
            object_id="torch",
            current_owner="player",
            current_room=None,
        )
        wm.player.inventory.append("torch")
        wm._remove_from_inventory("torch", "temple_entrance")
        assert "torch" in wm.rooms["temple_entrance"].object_ids_present

    def test_clears_owner(self):
        wm = _world_with_room()
        wm.objects["torch"] = ObjectState(
            object_id="torch",
            current_owner="player",
            current_room=None,
        )
        wm.player.inventory.append("torch")
        wm._remove_from_inventory("torch", "temple_entrance")
        assert wm.objects["torch"].current_owner is None
        assert wm.objects["torch"].current_room == "temple_entrance"


# ---------------------------------------------------------------------------
# _append_history
# ---------------------------------------------------------------------------

class TestAppendHistory:
    def test_appends_entry(self):
        wm = WorldModel()
        entry = HistoryEntry(turn=1, event_id="enter_temple",
                             category="player_action",
                             description="Entered temple.")
        wm._append_history(entry)
        assert len(wm.history.entries) == 1
        assert wm.history.entries[0].event_id == "enter_temple"

    def test_multiple_entries_ordered(self):
        wm = WorldModel()
        for i in range(3):
            wm._append_history(HistoryEntry(turn=i, event_id=f"e{i}"))
        assert wm.history.entries[2].event_id == "e2"


# ---------------------------------------------------------------------------
# get_ai_context
# ---------------------------------------------------------------------------

class TestGetAIContext:
    def test_returns_ai_context_instance(self, populated_world):
        ctx = populated_world.get_ai_context()
        assert isinstance(ctx, AIContext)

    def test_current_room_correct(self, populated_world):
        ctx = populated_world.get_ai_context()
        assert ctx.current_room == "hall_of_echoes"

    def test_inventory_reflected(self, populated_world):
        ctx = populated_world.get_ai_context()
        assert "torch_carried" in ctx.inventory

    def test_torch_state_reflected(self, populated_world):
        ctx = populated_world.get_ai_context()
        assert ctx.torch_state == "lit"
        assert ctx.torch_fuel == 64

    def test_flood_level_is_string(self, populated_world):
        ctx = populated_world.get_ai_context()
        assert isinstance(ctx.flood_level, str)
        assert ctx.flood_level == "DRY"

    def test_temple_phase_is_string(self, populated_world):
        ctx = populated_world.get_ai_context()
        assert isinstance(ctx.temple_phase, str)

    def test_evaluation_summary_contains_expected_keys(self, populated_world):
        ctx = populated_world.get_ai_context()
        assert "observation" in ctx.evaluation_summary
        assert "curiosity" in ctx.evaluation_summary
        assert isinstance(ctx.evaluation_summary["observation"], int)

    def test_recent_commands_limited(self, populated_world):
        """AI context must contain at most 5 recent commands."""
        ctx = populated_world.get_ai_context()
        assert len(ctx.recent_commands) <= 5

    def test_recent_history_limited(self, populated_world):
        """AI context must contain at most 10 recent history entries."""
        ctx = populated_world.get_ai_context()
        assert len(ctx.recent_history) <= 10

    def test_known_symbols_is_list(self, populated_world):
        ctx = populated_world.get_ai_context()
        assert isinstance(ctx.known_symbols, list)
        assert "eye" in ctx.known_symbols

    def test_invisible_objects_excluded(self):
        """Objects with visible=False must not appear in nearby_object_ids."""
        wm = WorldModel()
        wm.rooms["room_a"] = RoomState(room_id="room_a")
        wm.player.current_room = "room_a"
        wm.objects["hidden_obj"] = ObjectState(
            object_id="hidden_obj",
            current_room="room_a",
            visible=False,
        )
        wm.rooms["room_a"].object_ids_present.append("hidden_obj")
        ctx = wm.get_ai_context()
        assert "hidden_obj" not in ctx.nearby_object_ids

    def test_inaccessible_exits_excluded(self):
        """Exits with accessible=False must not appear in adjacent_rooms."""
        wm = WorldModel()
        wm.rooms["room_a"] = RoomState(
            room_id="room_a",
            accessible_exits={"north": True, "east": False},
        )
        wm.player.current_room = "room_a"
        ctx = wm.get_ai_context()
        assert "north" in ctx.adjacent_rooms
        assert "east" not in ctx.adjacent_rooms

    def test_active_mission_reflected(self, populated_world):
        ctx = populated_world.get_ai_context()
        assert "Library" in ctx.active_mission

    def test_ai_context_on_empty_world(self):
        """get_ai_context() must not raise on an empty WorldModel."""
        wm = WorldModel()
        ctx = wm.get_ai_context()
        assert ctx.current_room == "temple_entrance"
        assert ctx.inventory == []
