"""
test_inventory.py — The Lost Temple of Rudra

Tests for Phase 4: Inventory System.

Covers:
    - Inventory starts empty
    - TAKE adds collectible to inventory
    - TAKE removes object from room's object_ids_present
    - TAKE updates object.current_owner
    - TAKE updates object.current_room to None
    - TAKE rejects non-collectible objects
    - TAKE rejects objects not in current room
    - TAKE rejects objects already in inventory
    - DROP removes from inventory
    - DROP places in current room's object_ids_present
    - DROP updates object.current_room and current_owner
    - DROP fails if object not in inventory
    - INVENTORY command lists carried items
    - INVENTORY returns INFO status
    - INVENTORY on empty returns empty message
    - USE command validates object presence
    - Both World Model and ObjectState stay in sync after every operation
    - Inventory cannot hold non-collectible objects
    - Take then move then drop places object in new room
"""

import pytest

from src.world.temple_loader import load_temple
from src.world.world_model import WorldModel
from src.world.object_state import ObjectCategory
from src.engine.game_engine import GameEngine
from src.engine.command_result import ResultStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def wm() -> WorldModel:
    return load_temple()


@pytest.fixture
def engine(wm) -> GameEngine:
    return GameEngine(wm, debug_mode=False)


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

class TestInventoryInitialState:
    def test_inventory_starts_empty(self, wm):
        assert wm.player.inventory == []

    def test_inventory_command_on_empty(self, engine):
        r = engine.process_input("inventory")
        assert r.status == ResultStatus.INFO
        assert "nothing" in r.message.lower() or "empty" in r.message.lower()

    def test_inventory_data_on_empty(self, engine):
        r = engine.process_input("inventory")
        assert r.data.get("inventory") == []


# ---------------------------------------------------------------------------
# TAKE
# ---------------------------------------------------------------------------

class TestTake:
    def test_take_torch_succeeds(self, engine, wm):
        r = engine.process_input("take torch")
        assert r.status == ResultStatus.SUCCESS

    def test_take_adds_to_player_inventory(self, engine, wm):
        engine.process_input("take torch")
        assert "torch_entrance" in wm.player.inventory

    def test_take_removes_from_room(self, engine, wm):
        engine.process_input("take torch")
        room = wm.rooms["temple_entrance"]
        assert "torch_entrance" not in room.object_ids_present

    def test_take_sets_object_owner_to_player(self, engine, wm):
        engine.process_input("take torch")
        assert wm.objects["torch_entrance"].current_owner == "player"

    def test_take_sets_object_current_room_to_none(self, engine, wm):
        engine.process_input("take torch")
        assert wm.objects["torch_entrance"].current_room is None

    def test_take_non_collectible_fails(self, engine, wm):
        """Story objects, puzzle objects, etc. cannot be taken."""
        r = engine.process_input("take inscription")
        assert r.status == ResultStatus.FAILURE

    def test_take_interactive_fails(self, engine, wm):
        """Interactive objects stay in room."""
        # Move to flood control room — lever is there
        # For simplicity, add lever to entrance and try to take it
        from src.world.object_state import ObjectState
        wm.objects["lever_test"] = ObjectState(
            object_id="lever_test",
            name="Test Lever",
            category=ObjectCategory.INTERACTIVE,
            current_room="temple_entrance",
        )
        wm.rooms["temple_entrance"].object_ids_present.append("lever_test")
        r = engine.process_input("take lever")
        assert r.status == ResultStatus.FAILURE

    def test_take_environmental_fails(self, engine, wm):
        """Environmental objects cannot be picked up."""
        from src.world.object_state import ObjectState
        wm.objects["rubble_test"] = ObjectState(
            object_id="rubble_test",
            name="Test Rubble",
            category=ObjectCategory.ENVIRONMENTAL,
            current_room="temple_entrance",
        )
        wm.rooms["temple_entrance"].object_ids_present.append("rubble_test")
        r = engine.process_input("take rubble")
        assert r.status == ResultStatus.FAILURE

    def test_take_guardian_object_fails(self, engine, wm):
        """Guardian category objects are never collectible."""
        from src.world.object_state import ObjectState
        wm.objects["test_guardian"] = ObjectState(
            object_id="test_guardian",
            name="Test Guardian",
            category=ObjectCategory.GUARDIAN,
            current_room="temple_entrance",
        )
        wm.rooms["temple_entrance"].object_ids_present.append("test_guardian")
        r = engine.process_input("take guardian")
        assert r.status == ResultStatus.FAILURE

    def test_take_already_held_fails(self, engine, wm):
        engine.process_input("take torch")
        r = engine.process_input("take torch")
        assert r.status == ResultStatus.FAILURE

    def test_take_object_not_in_room_fails(self, engine):
        """key_archive is in archive_vault, not entrance."""
        r = engine.process_input("take key")
        assert r.status == ResultStatus.FAILURE

    def test_take_advances_turn(self, engine, wm):
        before = wm.world.current_turn
        engine.process_input("take torch")
        assert wm.world.current_turn == before + 1


# ---------------------------------------------------------------------------
# DROP
# ---------------------------------------------------------------------------

class TestDrop:
    def test_drop_torch_succeeds(self, engine, wm):
        engine.process_input("take torch")
        r = engine.process_input("drop torch")
        assert r.status == ResultStatus.SUCCESS

    def test_drop_removes_from_inventory(self, engine, wm):
        engine.process_input("take torch")
        engine.process_input("drop torch")
        assert "torch_entrance" not in wm.player.inventory

    def test_drop_adds_to_current_room(self, engine, wm):
        engine.process_input("take torch")
        engine.process_input("drop torch")
        room = wm.rooms["temple_entrance"]
        assert "torch_entrance" in room.object_ids_present

    def test_drop_sets_object_current_room(self, engine, wm):
        engine.process_input("take torch")
        engine.process_input("drop torch")
        assert wm.objects["torch_entrance"].current_room == "temple_entrance"

    def test_drop_clears_owner(self, engine, wm):
        engine.process_input("take torch")
        engine.process_input("drop torch")
        assert wm.objects["torch_entrance"].current_owner is None

    def test_drop_object_not_in_inventory_fails(self, engine):
        r = engine.process_input("drop torch")
        assert r.status == ResultStatus.FAILURE

    def test_drop_in_different_room(self, engine, wm):
        """Take object in room A, move to room B, drop there."""
        engine.process_input("take torch")
        engine.process_input("go north")        # → hall_of_echoes
        r = engine.process_input("drop torch")
        assert r.status == ResultStatus.SUCCESS
        assert wm.objects["torch_entrance"].current_room == "hall_of_echoes"
        assert "torch_entrance" in wm.rooms["hall_of_echoes"].object_ids_present
        assert "torch_entrance" not in wm.rooms["temple_entrance"].object_ids_present

    def test_drop_advances_turn(self, engine, wm):
        wm._add_to_inventory("torch_entrance")
        before = wm.world.current_turn
        engine.process_input("drop torch")
        assert wm.world.current_turn == before + 1


# ---------------------------------------------------------------------------
# INVENTORY command
# ---------------------------------------------------------------------------

class TestInventoryCommand:
    def test_inventory_after_take_shows_item(self, engine, wm):
        engine.process_input("take torch")
        r = engine.process_input("inventory")
        assert r.status == ResultStatus.INFO
        assert "torch" in r.message.lower()

    def test_inventory_data_contains_object_ids(self, engine, wm):
        engine.process_input("take torch")
        r = engine.process_input("inventory")
        assert "torch_entrance" in r.data.get("inventory", [])

    def test_inventory_does_not_advance_turn(self, engine, wm):
        before = wm.world.current_turn
        engine.process_input("inventory")
        assert wm.world.current_turn == before

    def test_inventory_synonyms_work(self, engine):
        for cmd in ("inventory", "i", "inv", "items"):
            r = engine.process_input(cmd)
            assert r.status == ResultStatus.INFO

    def test_inventory_multiple_items(self, engine, wm):
        engine.process_input("take torch")
        # Add second item to entrance for testing
        from src.world.object_state import ObjectState
        wm.objects["second_key"] = ObjectState(
            object_id="second_key",
            name="Second Key",
            category=ObjectCategory.COLLECTIBLE,
            current_room="temple_entrance",
            state="unused",
            interactable=True,
        )
        wm.rooms["temple_entrance"].object_ids_present.append("second_key")
        engine.process_input("take key")
        r = engine.process_input("inventory")
        assert "torch_entrance" in r.data["inventory"]
        assert "second_key" in r.data["inventory"]


# ---------------------------------------------------------------------------
# World Model synchronisation after operations
# ---------------------------------------------------------------------------

class TestWorldModelSync:
    def test_take_then_validate(self, engine, wm):
        engine.process_input("take torch")
        result = wm.validate()
        assert result.is_valid, str(result)

    def test_drop_then_validate(self, engine, wm):
        engine.process_input("take torch")
        engine.process_input("drop torch")
        result = wm.validate()
        assert result.is_valid, str(result)

    def test_move_with_item_then_validate(self, engine, wm):
        engine.process_input("take torch")
        engine.process_input("go north")
        result = wm.validate()
        assert result.is_valid, str(result)

    def test_full_inventory_lifecycle_then_validate(self, engine, wm):
        """Take → inspect → move → drop → validate."""
        engine.process_input("take torch")
        engine.process_input("inspect torch")
        engine.process_input("go north")
        engine.process_input("drop torch")
        result = wm.validate()
        assert result.is_valid, str(result)

    def test_serialise_with_inventory_item(self, engine, wm):
        engine.process_input("take torch")
        json_str = wm.to_json()
        restored = WorldModel.from_json(json_str)
        assert "torch_entrance" in restored.player.inventory
        assert restored.objects["torch_entrance"].current_owner == "player"
        assert restored.objects["torch_entrance"].current_room is None


# ---------------------------------------------------------------------------
# USE command
# ---------------------------------------------------------------------------

class TestUseCommand:
    def test_use_item_in_inventory(self, engine, wm):
        wm._add_to_inventory("torch_entrance")
        r = engine.process_input("use torch")
        assert r.status == ResultStatus.SUCCESS

    def test_use_item_not_present_fails(self, engine):
        r = engine.process_input("use golden_crown")
        assert r.status == ResultStatus.FAILURE
