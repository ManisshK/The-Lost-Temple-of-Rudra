"""
test_objects.py — The Lost Temple of Rudra

Tests for Phase 4: Object System.

Covers:
    - All objects loaded into World Model
    - Object categories correct
    - Objects placed in correct rooms
    - Object state defaults
    - Object visibility and interactability
    - INSPECT returns object description
    - Collectible vs non-collectible enforcement
    - Object state updates via engine
    - Object lookup helpers
    - Usage history tracking
    - Evaluation updates on inspection
    - Story objects marked discovered on inspect
    - Torch lighting/extinguishing via engine
"""

import pytest

from src.world.temple_loader import load_temple
from src.world.world_model import WorldModel
from src.world.object_state import ObjectState, ObjectCategory, StatueDirection
from src.world.objects import (
    OBJECT_DEFINITIONS, build_world_objects, get_object_definition,
    get_objects_for_room, get_collectible_objects, ALL_OBJECT_IDS,
)
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
# Object count and existence
# ---------------------------------------------------------------------------

class TestObjectCount:
    def test_objects_loaded_into_world_model(self, wm):
        assert len(wm.objects) == len(OBJECT_DEFINITIONS)
        assert len(wm.objects) >= 50    # at least 50 objects

    def test_all_object_ids_in_frozenset(self):
        for oid in OBJECT_DEFINITIONS:
            assert oid in ALL_OBJECT_IDS

    def test_key_objects_exist(self, wm):
        key_objects = [
            "torch_entrance", "inscription_entrance",
            "key_archive", "guardian_mirror", "eye_of_rudra",
            "statue_guardian_n", "statue_guardian_e",
            "flood_gate_main", "water_wheel",
        ]
        for oid in key_objects:
            assert oid in wm.objects, f"Missing object: {oid}"


# ---------------------------------------------------------------------------
# Object categories
# ---------------------------------------------------------------------------

class TestObjectCategories:
    def test_torch_is_collectible(self, wm):
        assert wm.objects["torch_entrance"].category == ObjectCategory.COLLECTIBLE

    def test_inscription_is_story(self, wm):
        assert wm.objects["inscription_entrance"].category == ObjectCategory.STORY

    def test_guardian_statues_are_puzzle(self, wm):
        assert wm.objects["statue_guardian_n"].category == ObjectCategory.PUZZLE

    def test_flood_gate_is_environmental(self, wm):
        assert wm.objects["flood_gate_main"].category == ObjectCategory.ENVIRONMENTAL

    def test_lever_is_interactive(self, wm):
        assert wm.objects["lever_flood_control"].category == ObjectCategory.INTERACTIVE

    def test_reliefs_are_symbolic(self, wm):
        assert wm.objects["relief_eye"].category == ObjectCategory.SYMBOLIC

    def test_guardian_mirror_is_guardian_category(self, wm):
        assert wm.objects["guardian_mirror"].category == ObjectCategory.GUARDIAN

    def test_eye_of_rudra_is_guardian_category(self, wm):
        assert wm.objects["eye_of_rudra"].category == ObjectCategory.GUARDIAN

    def test_collectible_objects_are_only_collectibles(self, wm):
        collectibles = get_collectible_objects()
        for od in collectibles:
            assert od.category == ObjectCategory.COLLECTIBLE


# ---------------------------------------------------------------------------
# Object placement
# ---------------------------------------------------------------------------

class TestObjectPlacement:
    def test_torch_in_temple_entrance(self, wm):
        obj = wm.objects["torch_entrance"]
        assert obj.current_room == "temple_entrance"

    def test_inscription_in_temple_entrance(self, wm):
        obj = wm.objects["inscription_entrance"]
        assert obj.current_room == "temple_entrance"

    def test_guardian_statues_in_hall_of_guardians(self, wm):
        for statue_id in ["statue_guardian_n", "statue_guardian_e",
                          "statue_guardian_s", "statue_guardian_w"]:
            assert wm.objects[statue_id].current_room == "hall_of_guardians"

    def test_eye_of_rudra_in_final_chamber(self, wm):
        assert wm.objects["eye_of_rudra"].current_room == "final_chamber"

    def test_guardian_mirror_in_final_chamber(self, wm):
        assert wm.objects["guardian_mirror"].current_room == "final_chamber"

    def test_key_archive_in_archive_vault(self, wm):
        assert wm.objects["key_archive"].current_room == "archive_vault"

    def test_all_objects_placed_in_valid_rooms(self, wm):
        for oid, obj in wm.objects.items():
            if obj.current_room is not None:
                assert obj.current_room in wm.rooms, (
                    f"Object '{oid}' placed in unknown room '{obj.current_room}'"
                )

    def test_objects_present_in_room_match_object_current_room(self, wm):
        """Every object listed in a room's object_ids_present must have
        current_room pointing to that same room."""
        for room_id, room in wm.rooms.items():
            for oid in room.object_ids_present:
                obj = wm.objects.get(oid)
                assert obj is not None
                assert obj.current_room == room_id, (
                    f"Room {room_id} lists {oid} but object.current_room={obj.current_room}"
                )

    def test_get_objects_for_room_returns_correct_objects(self):
        entrance_objs = get_objects_for_room("temple_entrance")
        oids = [od.object_id for od in entrance_objs]
        assert "torch_entrance" in oids
        assert "inscription_entrance" in oids


# ---------------------------------------------------------------------------
# Object state defaults
# ---------------------------------------------------------------------------

class TestObjectStateDefaults:
    def test_torch_starts_unlit(self, wm):
        assert wm.objects["torch_entrance"].state == "unlit"

    def test_key_starts_unused(self, wm):
        assert wm.objects["key_archive"].state == "unused"

    def test_objects_start_with_no_owner(self, wm):
        for obj in wm.objects.values():
            assert obj.current_owner is None

    def test_usage_history_starts_empty(self, wm):
        for obj in wm.objects.values():
            assert obj.usage_history == []

    def test_condition_starts_at_100_for_most(self, wm):
        # Bridge rope starts degraded by design
        assert wm.objects["bridge_rope"].condition < 100.0
        # Others should be 100
        assert wm.objects["torch_entrance"].condition == 100.0

    def test_guardian_statues_have_facing_direction(self, wm):
        statues = {
            "statue_guardian_n": StatueDirection.NORTH,
            "statue_guardian_e": StatueDirection.EAST,
            "statue_guardian_s": StatueDirection.SOUTH,
            "statue_guardian_w": StatueDirection.WEST,
        }
        for statue_id, expected_dir in statues.items():
            assert wm.objects[statue_id].facing_direction == expected_dir

    def test_story_objects_start_undiscovered(self, wm):
        undiscovered = [
            "scroll_hall_of_echoes", "tablet_inscriptions_01",
            "scroll_ancient_library_01",
        ]
        for oid in undiscovered:
            assert wm.objects[oid].state == "undiscovered"


# ---------------------------------------------------------------------------
# Object visibility
# ---------------------------------------------------------------------------

class TestObjectVisibility:
    def test_most_objects_start_visible(self, wm):
        visible_count = sum(1 for o in wm.objects.values() if o.visible)
        assert visible_count > len(wm.objects) * 0.9   # >90% visible

    def test_eye_of_rudra_starts_invisible(self, wm):
        """Eye is revealed only at the narrative climax."""
        assert wm.objects["eye_of_rudra"].visible is False

    def test_visible_objects_in_room_appear_in_look(self, engine, wm):
        r = engine.process_input("look")
        assert r.data.get("objects_present") is not None
        # Only visible objects should appear
        for oid in r.data["objects_present"]:
            assert wm.objects[oid].visible is True


# ---------------------------------------------------------------------------
# Object definition helpers
# ---------------------------------------------------------------------------

class TestObjectDefinitionHelpers:
    def test_get_object_definition_returns_definition(self):
        od = get_object_definition("torch_entrance")
        assert od is not None
        assert od.object_id == "torch_entrance"
        assert od.name == "Ancient Torch"

    def test_get_object_definition_unknown_returns_none(self):
        assert get_object_definition("nonexistent_obj") is None

    def test_collectible_definition_has_collectible_true(self):
        od = get_object_definition("torch_entrance")
        assert od.collectible is True

    def test_non_collectible_definition_has_collectible_false(self):
        od = get_object_definition("guardian_mirror")
        assert od.collectible is False


# ---------------------------------------------------------------------------
# INSPECT via engine
# ---------------------------------------------------------------------------

class TestInspectViaEngine:
    def test_inspect_torch_succeeds(self, engine, wm):
        r = engine.process_input("inspect torch")
        assert r.status == ResultStatus.SUCCESS

    def test_inspect_returns_object_description(self, engine, wm):
        r = engine.process_input("inspect torch")
        assert "torch" in r.message.lower() or "fuel" in r.message.lower()

    def test_inspect_adds_to_usage_history(self, engine, wm):
        engine.process_input("inspect torch")
        assert any("observed" in h for h in wm.objects["torch_entrance"].usage_history)

    def test_inspect_increases_observation_score(self, engine, wm):
        before = wm.evaluation.observation.score
        engine.process_input("inspect torch")
        assert wm.evaluation.observation.score > before

    def test_inspect_unknown_object_fails(self, engine):
        r = engine.process_input("inspect golden_crown")
        assert r.status == ResultStatus.FAILURE

    def test_inspect_story_object_marks_discovered(self, engine, wm):
        """Inspecting a story object changes its state from undiscovered to discovered."""
        assert wm.objects["scroll_hall_of_echoes"].state == "undiscovered"
        # Navigate to hall_of_echoes first
        engine.process_input("go north")
        engine.process_input("inspect scroll")
        assert wm.objects["scroll_hall_of_echoes"].state != "undiscovered"

    def test_inspect_data_contains_object_id(self, engine, wm):
        r = engine.process_input("inspect torch")
        assert r.data.get("object_id") == "torch_entrance"

    def test_inspect_object_in_inventory(self, engine, wm):
        """Objects in inventory can be inspected."""
        wm._add_to_inventory("torch_entrance")
        r = engine.process_input("inspect torch")
        assert r.status == ResultStatus.SUCCESS


# ---------------------------------------------------------------------------
# Torch light/extinguish via engine
# ---------------------------------------------------------------------------

class TestTorchLighting:
    def test_light_torch_from_room(self, engine, wm):
        """Torch must be in inventory to light."""
        wm._add_to_inventory("torch_entrance")
        r = engine.process_input("light torch")
        assert r.status == ResultStatus.SUCCESS
        assert wm.objects["torch_entrance"].state == "lit"

    def test_light_torch_updates_player_torch_state(self, engine, wm):
        wm._add_to_inventory("torch_entrance")
        engine.process_input("light torch")
        assert wm.player.torch.state == "lit"

    def test_extinguish_torch(self, engine, wm):
        wm._add_to_inventory("torch_entrance")
        wm._update_object_state("torch_entrance", state="lit", activated=True)
        r = engine.process_input("extinguish torch")
        assert r.status == ResultStatus.SUCCESS
        assert wm.objects["torch_entrance"].state == "extinguished"

    def test_cannot_light_nonexistent_object(self, engine):
        r = engine.process_input("light candle")
        assert r.status == ResultStatus.FAILURE
