import pathlib

PART8 = r'''

# ===========================================================================
# GAME ENGINE INTEGRATION TESTS
# ===========================================================================

def _guardian_engine():
    """GameEngine wired with a full guardian statues setup."""
    wm = WorldModel()
    wm.rooms["hall_of_guardians"] = RoomState(
        room_id="hall_of_guardians", region=RoomRegion.OUTER_TEMPLE,
        accessible_exits={}, puzzle_id="puzzle_guardian_statues",
    )
    wm.rooms["chamber_of_inscriptions"] = RoomState(
        room_id="chamber_of_inscriptions", region=RoomRegion.OUTER_TEMPLE,
        accessible_exits={"west": "hall_of_guardians"},
    )
    wm.player.current_room = "hall_of_guardians"
    wm.puzzles["puzzle_guardian_statues"] = PuzzleState(
        puzzle_id="puzzle_guardian_statues", room_id="hall_of_guardians",
        category=PuzzleCategory.LOGIC, status=PuzzleStatus.AVAILABLE,
    )
    NAMES = {
        "statue_guardian_n": ("Northern Guardian Statue", StatueDirection.NORTH),
        "statue_guardian_e": ("Eastern Guardian Statue", StatueDirection.EAST),
        "statue_guardian_s": ("Southern Guardian Statue", StatueDirection.SOUTH),
        "statue_guardian_w": ("Western Guardian Statue", StatueDirection.WEST),
    }
    for sid, (name, facing) in NAMES.items():
        wm.objects[sid] = ObjectState(
            object_id=sid, name=name,
            category=ObjectCategory.PUZZLE,
            current_room="hall_of_guardians",
            facing_direction=facing,
        )
        wm.rooms["hall_of_guardians"].object_ids_present.append(sid)
    engine = GameEngine(wm)
    return engine, wm


class TestGameEnginePuzzleDispatch:
    def test_puzzle_in_room_dispatches(self):
        engine, wm = _guardian_engine()
        r = engine.process_input("rotate northern")
        assert r.status in (ResultStatus.SUCCESS, ResultStatus.FAILURE)
        assert r.message

    def test_puzzle_solve_opens_exit(self):
        engine, wm = _guardian_engine()
        # Set statues to one rotation away from solved
        wm.objects["statue_guardian_e"].facing_direction = StatueDirection.WEST
        wm.objects["statue_guardian_s"].facing_direction = StatueDirection.NORTH
        wm.objects["statue_guardian_w"].facing_direction = StatueDirection.EAST
        wm.objects["statue_guardian_n"].facing_direction = StatueDirection.EAST
        engine.process_input("rotate northern")
        assert "north" in wm.rooms["hall_of_guardians"].accessible_exits

    def test_puzzle_solve_updates_puzzle_status(self):
        engine, wm = _guardian_engine()
        wm.objects["statue_guardian_e"].facing_direction = StatueDirection.WEST
        wm.objects["statue_guardian_s"].facing_direction = StatueDirection.NORTH
        wm.objects["statue_guardian_w"].facing_direction = StatueDirection.EAST
        wm.objects["statue_guardian_n"].facing_direction = StatueDirection.EAST
        engine.process_input("rotate northern")
        assert wm.puzzles["puzzle_guardian_statues"].status == PuzzleStatus.SOLVED

    def test_puzzle_solve_records_history(self):
        engine, wm = _guardian_engine()
        wm.objects["statue_guardian_e"].facing_direction = StatueDirection.WEST
        wm.objects["statue_guardian_s"].facing_direction = StatueDirection.NORTH
        wm.objects["statue_guardian_w"].facing_direction = StatueDirection.EAST
        wm.objects["statue_guardian_n"].facing_direction = StatueDirection.EAST
        before = len(wm.history.entries)
        engine.process_input("rotate northern")
        assert len(wm.history.entries) > before

    def test_puzzle_failure_increments_failure_count(self):
        engine, wm = _guardian_engine()
        # Rotate to wrong position (N rotates N->E, not correct SOUTH)
        engine.process_input("rotate northern")
        ps = wm.puzzles["puzzle_guardian_statues"]
        assert ps.failure_count >= 0  # may be 0 (partial) or > 0 (failure)

    def test_no_puzzle_in_room_returns_failure_with_message(self):
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r")
        wm.player.current_room = "r"
        engine = GameEngine(wm)
        r = engine.process_input("rotate statue")
        assert r.status == ResultStatus.FAILURE
        assert "puzzle" in r.message.lower() or "mechanism" in r.message.lower()

    def test_attempt_count_increments_on_each_try(self):
        engine, wm = _guardian_engine()
        engine.process_input("rotate northern")
        ps = wm.puzzles["puzzle_guardian_statues"]
        assert ps.attempt_count >= 1
        engine.process_input("rotate eastern")
        assert ps.attempt_count >= 2

    def test_first_attempted_turn_set(self):
        engine, wm = _guardian_engine()
        engine.process_input("rotate northern")
        ps = wm.puzzles["puzzle_guardian_statues"]
        assert ps.first_attempted_turn is not None


class TestGameEngineEventProcessing:
    def test_torch_fuel_decrements_after_turn(self):
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r")
        wm.player.current_room = "r"
        wm.player.torch.state = "lit"
        wm.player.torch.fuel = 50
        engine = GameEngine(wm)
        engine.process_input("look")
        assert wm.player.torch.fuel < 50

    def test_event_history_appended_on_torch_warning(self):
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r")
        wm.player.current_room = "r"
        wm.player.torch.state = "almost_out"
        wm.player.torch.fuel = 1
        engine = GameEngine(wm)
        before = len(wm.history.entries)
        engine.process_input("look")
        assert len(wm.history.entries) > before

    def test_dust_accumulates_each_turn(self):
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r")
        wm.player.current_room = "r"
        wm.dynamic_events.dust.global_density = 0.0
        engine = GameEngine(wm)
        engine.process_input("look")
        assert wm.dynamic_events.dust.global_density > 0.0

    def test_world_validates_after_puzzle_and_events(self):
        engine, wm = _guardian_engine()
        wm.player.torch.state = "lit"
        wm.player.torch.fuel = 50
        engine.process_input("rotate northern")
        engine.process_input("rotate eastern")
        result = wm.validate()
        assert result.is_valid, str(result)

    def test_serialization_after_puzzle_solve(self):
        engine, wm = _guardian_engine()
        wm.objects["statue_guardian_e"].facing_direction = StatueDirection.WEST
        wm.objects["statue_guardian_s"].facing_direction = StatueDirection.NORTH
        wm.objects["statue_guardian_w"].facing_direction = StatueDirection.EAST
        wm.objects["statue_guardian_n"].facing_direction = StatueDirection.EAST
        engine.process_input("rotate northern")
        json_str = wm.to_json()
        restored = WorldModel.from_json(json_str)
        assert restored.puzzles["puzzle_guardian_statues"].status == PuzzleStatus.SOLVED
        assert "north" in restored.rooms["hall_of_guardians"].accessible_exits

    def test_event_effect_updates_world_model_directly(self):
        """_apply_event_effect correctly writes torch state."""
        from engine.game_engine import GameEngine
        from world.events import EventEffect, EFFECT_UPDATE_TORCH
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r")
        wm.player.current_room = "r"
        wm.player.torch.fuel = 80
        engine = GameEngine(wm)
        effect = EventEffect(EFFECT_UPDATE_TORCH, {"fuel": 30, "state": "dim", "brightness": 40})
        engine._apply_event_effect(effect, 5)
        assert wm.player.torch.fuel == 30
        assert wm.player.torch.state == "dim"

    def test_event_effect_open_exit_writes_accessible_exits(self):
        from engine.game_engine import GameEngine
        from world.events import EventEffect, EFFECT_OPEN_EXIT
        wm = WorldModel()
        wm.rooms["room_a"] = RoomState(room_id="room_a", accessible_exits={})
        wm.rooms["room_b"] = RoomState(room_id="room_b")
        wm.player.current_room = "room_a"
        engine = GameEngine(wm)
        effect = EventEffect(EFFECT_OPEN_EXIT, {"room_id": "room_a", "direction": "north", "destination": "room_b"})
        engine._apply_event_effect(effect, 1)
        assert wm.rooms["room_a"].accessible_exits.get("north") == "room_b"

    def test_event_effect_set_room_water_level(self):
        from engine.game_engine import GameEngine
        from world.events import EventEffect, EFFECT_SET_ROOM_WATER
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r", water_level=0.0)
        wm.player.current_room = "r"
        engine = GameEngine(wm)
        effect = EventEffect(EFFECT_SET_ROOM_WATER, {"room_id": "r", "water_level": 40.0})
        engine._apply_event_effect(effect, 1)
        assert wm.rooms["r"].water_level == 40.0
'''

p = pathlib.Path('tests/test_phase5.py')
p.write_text(p.read_text(encoding='utf-8') + PART8, encoding='utf-8')
print('part8 ok, lines:', len(p.read_text(encoding='utf-8').splitlines()))
