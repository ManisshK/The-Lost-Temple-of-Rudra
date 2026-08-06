"""
test_rooms.py — The Lost Temple of Rudra

Tests for Phase 4: Room System.

Covers:
    - All 24 canonical rooms exist in the loaded World Model
    - Room region assignment
    - Static connection graph structure
    - Default accessible exits vs sealed passages
    - Navigation through the engine (go north/south/etc.)
    - Room visit count and first_visited_turn tracking
    - accessible_exits are modified at runtime, not static_connections
    - Reachability: 23 of 24 rooms reachable from entrance without puzzles
    - final_chamber sealed until arch opened
    - Room descriptions returned by LOOK
    - Room objects populated correctly
    - Room light levels
    - Hidden passages start inaccessible
"""

import pytest

from src.world.temple_loader import load_temple
from src.world.world_model import WorldModel
from src.world.room_state import RoomState, RoomRegion, LightLevel
from src.world.rooms import (
    ROOM_DEFINITIONS, build_world_rooms, get_room_definition,
    get_connected_rooms, ALL_ROOM_IDS,
)
from src.engine.game_engine import GameEngine
from src.engine.command_result import ResultStatus
from src.utils.constants import (
    ROOM_TEMPLE_ENTRANCE, ROOM_HALL_OF_ECHOES, ROOM_HALL_OF_GUARDIANS,
    ROOM_ANCIENT_LIBRARY, ROOM_FINAL_CHAMBER,
)


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
# Room count and existence
# ---------------------------------------------------------------------------

class TestRoomCount:
    def test_24_rooms_defined(self):
        assert len(ROOM_DEFINITIONS) == 24

    def test_24_rooms_in_loaded_world_model(self, wm):
        assert len(wm.rooms) == 24

    def test_all_canonical_room_ids_present(self, wm):
        canonical = [
            "temple_entrance", "hall_of_echoes", "hall_of_guardians",
            "chamber_of_inscriptions", "first_meditation_hall",
            "ancient_library", "archive_vault", "symbol_gallery",
            "astronomers_chamber", "statue_gallery", "chamber_of_maps",
            "forgotten_classroom", "bridge_of_echoes", "flood_control_room",
            "underground_reservoir", "water_channel_network",
            "collapsed_hallway", "ancient_machinery_chamber",
            "hidden_maintenance_tunnel", "chamber_of_reflection",
            "hall_of_judgment", "guardian_archive", "throne_approach",
            "final_chamber",
        ]
        for room_id in canonical:
            assert room_id in wm.rooms, f"Missing room: {room_id}"

    def test_all_room_ids_in_frozenset(self):
        for room_id in ROOM_DEFINITIONS:
            assert room_id in ALL_ROOM_IDS


# ---------------------------------------------------------------------------
# Room regions
# ---------------------------------------------------------------------------

class TestRoomRegions:
    @pytest.mark.parametrize("room_id", [
        "temple_entrance", "hall_of_echoes", "hall_of_guardians",
        "chamber_of_inscriptions", "first_meditation_hall",
    ])
    def test_outer_temple_rooms(self, wm, room_id):
        assert wm.rooms[room_id].region == RoomRegion.OUTER_TEMPLE

    @pytest.mark.parametrize("room_id", [
        "ancient_library", "archive_vault", "symbol_gallery",
        "astronomers_chamber", "statue_gallery", "chamber_of_maps",
        "forgotten_classroom",
    ])
    def test_knowledge_sanctum_rooms(self, wm, room_id):
        assert wm.rooms[room_id].region == RoomRegion.KNOWLEDGE_SANCTUM

    @pytest.mark.parametrize("room_id", [
        "bridge_of_echoes", "flood_control_room", "underground_reservoir",
        "water_channel_network", "collapsed_hallway",
        "ancient_machinery_chamber", "hidden_maintenance_tunnel",
    ])
    def test_living_temple_rooms(self, wm, room_id):
        assert wm.rooms[room_id].region == RoomRegion.LIVING_TEMPLE

    @pytest.mark.parametrize("room_id", [
        "chamber_of_reflection", "hall_of_judgment", "guardian_archive",
        "throne_approach", "final_chamber",
    ])
    def test_guardian_core_rooms(self, wm, room_id):
        assert wm.rooms[room_id].region == RoomRegion.GUARDIAN_CORE


# ---------------------------------------------------------------------------
# Static connection graph
# ---------------------------------------------------------------------------

class TestRoomConnections:
    def test_entrance_has_north_exit(self):
        rd = get_room_definition("temple_entrance")
        assert "north" in rd.static_connections
        assert rd.static_connections["north"] == "hall_of_echoes"

    def test_all_connection_destinations_are_known_rooms(self):
        for room_id, rd in ROOM_DEFINITIONS.items():
            for direction, dest in rd.static_connections.items():
                assert dest in ROOM_DEFINITIONS, (
                    f"{room_id} connects {direction}→{dest} but {dest} is unknown"
                )

    def test_get_connected_rooms_returns_dict(self):
        conns = get_connected_rooms("hall_of_echoes")
        assert isinstance(conns, dict)
        assert "south" in conns

    def test_get_room_definition_returns_definition(self):
        rd = get_room_definition("final_chamber")
        assert rd is not None
        assert rd.room_id == "final_chamber"

    def test_get_room_definition_unknown_returns_none(self):
        assert get_room_definition("nonexistent_room") is None


# ---------------------------------------------------------------------------
# Default accessibility
# ---------------------------------------------------------------------------

class TestDefaultAccessibility:
    def test_entrance_north_accessible_by_default(self, wm):
        room = wm.rooms["temple_entrance"]
        assert "north" in room.accessible_exits
        assert room.accessible_exits["north"] == "hall_of_echoes"

    def test_hall_of_guardians_north_sealed_by_default(self, wm):
        """Guardian puzzle must be solved before north door opens."""
        room = wm.rooms["hall_of_guardians"]
        assert "north" not in room.accessible_exits

    def test_throne_approach_north_sealed_by_default(self, wm):
        """Final chamber sealed until player is evaluated as worthy."""
        room = wm.rooms["throne_approach"]
        assert "north" not in room.accessible_exits

    def test_collapsed_hallway_north_sealed_by_default(self, wm):
        """North passage blocked by rubble until cleared."""
        room = wm.rooms["collapsed_hallway"]
        assert "north" not in room.accessible_exits

    def test_23_rooms_reachable_from_entrance_without_puzzles(self, wm):
        """All rooms except final_chamber are reachable from entrance by default."""
        from collections import deque
        visited = set()
        queue = deque(["temple_entrance"])
        while queue:
            room_id = queue.popleft()
            if room_id in visited:
                continue
            visited.add(room_id)
            room = wm.rooms[room_id]
            for dest in room.accessible_exits.values():
                if isinstance(dest, str) and dest not in visited:
                    queue.append(dest)
        assert len(visited) == 23
        assert "final_chamber" not in visited

    def test_final_chamber_sealed_at_start(self, wm):
        room = wm.rooms["throne_approach"]
        assert "north" not in room.accessible_exits


# ---------------------------------------------------------------------------
# Hidden passages
# ---------------------------------------------------------------------------

class TestHiddenPassages:
    def test_bridge_of_echoes_has_hidden_down(self, wm):
        room = wm.rooms["bridge_of_echoes"]
        assert "down" in room.hidden_passages
        assert room.hidden_passages["down"] is False

    def test_hidden_passages_start_inaccessible(self, wm):
        for room in wm.rooms.values():
            for passage, accessible in room.hidden_passages.items():
                assert accessible is False, (
                    f"Hidden passage '{passage}' in {room.room_id} "
                    "should start inaccessible"
                )

    def test_hidden_passages_not_in_accessible_exits(self, wm):
        """Hidden passages are not exposed in accessible_exits until discovered."""
        for room in wm.rooms.values():
            for passage in room.hidden_passages:
                assert passage not in room.accessible_exits or \
                       room.accessible_exits.get(passage) is False


# ---------------------------------------------------------------------------
# Room state defaults
# ---------------------------------------------------------------------------

class TestRoomStateDefaults:
    def test_rooms_start_unvisited(self, wm):
        for room in wm.rooms.values():
            assert room.visited is False

    def test_visit_count_starts_zero(self, wm):
        for room in wm.rooms.values():
            assert room.visit_count == 0

    def test_first_visited_turn_starts_none(self, wm):
        for room in wm.rooms.values():
            assert room.first_visited_turn is None

    def test_temple_entrance_light_level_dim(self, wm):
        assert wm.rooms["temple_entrance"].light_level == LightLevel.DIM

    def test_final_chamber_light_level_bright(self, wm):
        assert wm.rooms["final_chamber"].light_level == LightLevel.BRIGHT

    def test_dark_rooms_exist(self, wm):
        dark_rooms = [r for r in wm.rooms.values() if r.light_level == LightLevel.DARK]
        assert len(dark_rooms) >= 1


# ---------------------------------------------------------------------------
# Objects in rooms
# ---------------------------------------------------------------------------

class TestRoomObjects:
    def test_temple_entrance_has_torch(self, wm):
        room = wm.rooms["temple_entrance"]
        assert "torch_entrance" in room.object_ids_present

    def test_temple_entrance_has_inscription(self, wm):
        room = wm.rooms["temple_entrance"]
        assert "inscription_entrance" in room.object_ids_present

    def test_hall_of_guardians_has_statues(self, wm):
        room = wm.rooms["hall_of_guardians"]
        statue_ids = [oid for oid in room.object_ids_present if "statue_guardian" in oid]
        assert len(statue_ids) == 4

    def test_all_room_objects_exist_in_world_model(self, wm):
        for room in wm.rooms.values():
            for oid in room.object_ids_present:
                assert oid in wm.objects, (
                    f"Room {room.room_id} references unknown object '{oid}'"
                )

    def test_symbol_gallery_has_five_reliefs(self, wm):
        room = wm.rooms["symbol_gallery"]
        relief_ids = [oid for oid in room.object_ids_present if oid.startswith("relief_")]
        assert len(relief_ids) == 5


# ---------------------------------------------------------------------------
# Navigation via engine
# ---------------------------------------------------------------------------

class TestNavigationViaEngine:
    def test_go_north_from_entrance_to_hall_of_echoes(self, engine, wm):
        r = engine.process_input("go north")
        assert r.status == ResultStatus.SUCCESS
        assert wm.player.current_room == "hall_of_echoes"

    def test_go_south_returns_to_entrance(self, engine, wm):
        engine.process_input("go north")
        r = engine.process_input("go south")
        assert r.status == ResultStatus.SUCCESS
        assert wm.player.current_room == "temple_entrance"

    def test_sealed_north_fails_at_guardians(self, engine, wm):
        engine.process_input("go north")          # → hall_of_echoes
        engine.process_input("go east")           # → hall_of_guardians
        r = engine.process_input("go north")      # sealed — puzzle unsolved
        assert r.status == ResultStatus.FAILURE
        assert wm.player.current_room == "hall_of_guardians"

    def test_movement_updates_visited_rooms(self, engine, wm):
        engine.process_input("go north")
        assert "hall_of_echoes" in wm.player.visited_rooms

    def test_movement_updates_movement_history(self, engine, wm):
        engine.process_input("go north")
        assert "hall_of_echoes" in wm.player.movement_history

    def test_first_visit_sets_visited_flag(self, engine, wm):
        assert wm.rooms["hall_of_echoes"].visited is False
        engine.process_input("go north")
        assert wm.rooms["hall_of_echoes"].visited is True

    def test_first_visit_sets_first_visited_turn(self, engine, wm):
        engine.process_input("go north")
        assert wm.rooms["hall_of_echoes"].first_visited_turn is not None

    def test_visit_count_increments(self, engine, wm):
        engine.process_input("go north")
        assert wm.rooms["hall_of_echoes"].visit_count == 1
        engine.process_input("go south")
        engine.process_input("go north")
        assert wm.rooms["hall_of_echoes"].visit_count == 2

    def test_bare_direction_word_works(self, engine, wm):
        r = engine.process_input("north")
        assert r.status == ResultStatus.SUCCESS
        assert wm.player.current_room == "hall_of_echoes"

    def test_invalid_direction_fails(self, engine, wm):
        r = engine.process_input("go east")   # no east from entrance
        assert r.status == ResultStatus.FAILURE
        assert wm.player.current_room == "temple_entrance"

    def test_engine_can_open_exit_at_runtime(self, engine, wm):
        """Simulates what a puzzle solver would do — open an exit."""
        wm.rooms["hall_of_guardians"].accessible_exits["north"] = "chamber_of_inscriptions"
        engine.process_input("go north")      # → hall_of_echoes
        engine.process_input("go east")       # → hall_of_guardians
        r = engine.process_input("go north")  # now accessible
        assert r.status == ResultStatus.SUCCESS
        assert wm.player.current_room == "chamber_of_inscriptions"


# ---------------------------------------------------------------------------
# LOOK command describes room
# ---------------------------------------------------------------------------

class TestLookCommand:
    def test_look_succeeds(self, engine):
        r = engine.process_input("look")
        assert r.status == ResultStatus.SUCCESS

    def test_look_returns_room_description(self, engine):
        r = engine.process_input("look")
        # Should contain the room description text
        assert "temple" in r.message.lower() or "entrance" in r.message.lower()

    def test_look_message_includes_exits(self, engine):
        r = engine.process_input("look")
        assert "north" in r.message.lower()

    def test_look_data_contains_room_id(self, engine, wm):
        r = engine.process_input("look")
        assert r.data.get("room_id") == wm.player.current_room

    def test_look_data_contains_exits(self, engine):
        r = engine.process_input("look")
        assert "exits" in r.data
        assert "north" in r.data["exits"]

    def test_look_data_contains_objects_present(self, engine):
        r = engine.process_input("look")
        assert "objects_present" in r.data
        assert "torch_entrance" in r.data["objects_present"]

    def test_look_after_move_shows_new_room(self, engine):
        engine.process_input("go north")
        r = engine.process_input("look")
        assert "echoes" in r.message.lower() or "hall" in r.message.lower()

    def test_look_increments_times_inspected(self, engine, wm):
        before = wm.rooms["temple_entrance"].times_inspected
        engine.process_input("look")
        assert wm.rooms["temple_entrance"].times_inspected == before + 1
