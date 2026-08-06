import pathlib

PART6 = r'''

# ===========================================================================
# DYNAMIC EVENT ENGINE TESTS
# ===========================================================================

class TestTorchDecay:
    def _lit_world(self, fuel=100):
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r")
        wm.player.current_room = "r"
        wm.player.torch.state = "lit"
        wm.player.torch.fuel = fuel
        wm.player.torch.brightness = 80
        wm.dynamic_events.torch_burn.current_burn_rate = 1.0
        return wm

    def test_torch_fuel_decrements_when_lit(self):
        wm = self._lit_world(fuel=50)
        effects = _evaluate_torch_decay(wm, 1)
        torch_fx = next((e for e in effects if e.effect_type == EFFECT_UPDATE_TORCH), None)
        assert torch_fx is not None
        assert torch_fx.payload["fuel"] < 50

    def test_torch_unlit_no_effects(self):
        wm = self._lit_world()
        wm.player.torch.state = "unlit"
        effects = _evaluate_torch_decay(wm, 1)
        torch_fx = [e for e in effects if e.effect_type == EFFECT_UPDATE_TORCH]
        assert len(torch_fx) == 0

    def test_torch_transitions_to_dim(self):
        wm = self._lit_world(fuel=31)
        effects = _evaluate_torch_decay(wm, 1)
        torch_fx = next((e for e in effects if e.effect_type == EFFECT_UPDATE_TORCH), None)
        assert torch_fx.payload["state"] == "dim"

    def test_torch_transitions_to_almost_out(self):
        wm = self._lit_world(fuel=11)
        effects = _evaluate_torch_decay(wm, 1)
        torch_fx = next((e for e in effects if e.effect_type == EFFECT_UPDATE_TORCH), None)
        assert torch_fx.payload["state"] == "almost_out"

    def test_torch_transitions_to_extinguished(self):
        wm = self._lit_world(fuel=1)
        effects = _evaluate_torch_decay(wm, 1)
        torch_fx = next((e for e in effects if e.effect_type == EFFECT_UPDATE_TORCH), None)
        assert torch_fx.payload["state"] == "extinguished"
        assert torch_fx.payload["fuel"] == 0

    def test_history_appended_on_extinguish(self):
        wm = self._lit_world(fuel=1)
        wm.player.torch.state = "almost_out"
        effects = _evaluate_torch_decay(wm, 5)
        history_fx = [e for e in effects if e.effect_type == "append_history"]
        assert len(history_fx) > 0

    def test_burn_rate_increases_near_water(self):
        wm = self._lit_world(fuel=50)
        wm.rooms["r"].water_level = 30.0
        effects = _evaluate_torch_decay(wm, 1)
        torch_fx = next(e for e in effects if e.effect_type == EFFECT_UPDATE_TORCH)
        # With flood modifier 1.5, burn >= 1 * 1.5 rounded = 2 per turn minimum
        assert torch_fx.payload["fuel"] <= 48


class TestFloodProgression:
    def _dry_world(self, phase=1):
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r")
        wm.rooms["underground_reservoir"] = RoomState(room_id="underground_reservoir")
        wm.rooms["water_channel_network"] = RoomState(room_id="water_channel_network")
        wm.player.current_room = "r"
        wm.world.temple_phase = TemplePhase(phase)
        wm.puzzles["puzzle_flood_control"] = PuzzleState(
            puzzle_id="puzzle_flood_control", room_id="r",
            category=PuzzleCategory.ENVIRONMENTAL, status=PuzzleStatus.AVAILABLE,
        )
        return wm

    def test_no_flood_in_discovery_phase(self):
        wm = self._dry_world(phase=1)
        effects = _evaluate_flood_progression(wm, 5)
        flood_active_fx = [e for e in effects if e.effect_type == EFFECT_SET_FLOOD_ACTIVE]
        assert len(flood_active_fx) == 0

    def test_flood_auto_triggers_at_adaptation_phase(self):
        wm = self._dry_world(phase=3)
        effects = _evaluate_flood_progression(wm, 1)
        flood_fx = [e for e in effects if e.effect_type == EFFECT_SET_FLOOD_ACTIVE]
        assert len(flood_fx) > 0
        assert flood_fx[0].payload["active"] is True

    def test_flood_does_not_trigger_if_puzzle_solved(self):
        wm = self._dry_world(phase=3)
        wm.puzzles["puzzle_flood_control"].status = PuzzleStatus.SOLVED
        effects = _evaluate_flood_progression(wm, 1)
        flood_fx = [e for e in effects if e.effect_type == EFFECT_SET_FLOOD_ACTIVE]
        assert len(flood_fx) == 0

    def test_flood_advances_stage_after_enough_turns(self):
        wm = self._dry_world(phase=3)
        # Activate flood manually at turn 0
        wm.dynamic_events.flood.active = True
        wm.dynamic_events.flood.start_turn = 0
        wm.dynamic_events.flood.current_stage = 0
        # After FLOOD_TURNS_PER_LEVEL turns, stage should advance
        from world.events import FLOOD_TURNS_PER_LEVEL
        effects = _evaluate_flood_progression(wm, FLOOD_TURNS_PER_LEVEL + 1)
        level_fx = [e for e in effects if e.effect_type == EFFECT_SET_FLOOD_LEVEL]
        assert len(level_fx) > 0
        assert level_fx[0].payload["stage"] >= 1

    def test_flood_rooms_get_water_level(self):
        wm = self._dry_world(phase=3)
        wm.dynamic_events.flood.active = True
        wm.dynamic_events.flood.start_turn = 0
        wm.dynamic_events.flood.current_stage = 0
        from world.events import FLOOD_TURNS_PER_LEVEL
        effects = _evaluate_flood_progression(wm, FLOOD_TURNS_PER_LEVEL + 1)
        water_fx = [e for e in effects if e.effect_type == EFFECT_SET_ROOM_WATER]
        assert len(water_fx) > 0
        for fx in water_fx:
            assert fx.payload["water_level"] > 0

    def test_flood_triggered_by_puzzle_failure(self):
        wm = self._dry_world(phase=1)
        wm.puzzles["puzzle_flood_control"].current_progress["flood_triggered"] = True
        wm.dynamic_events.flood.start_turn = 0
        wm.dynamic_events.flood.current_stage = 0
        from world.events import FLOOD_TURNS_PER_LEVEL
        effects = _evaluate_flood_progression(wm, FLOOD_TURNS_PER_LEVEL + 1)
        # Should advance flood even in phase 1 because trigger flag is set
        level_fx = [e for e in effects if e.effect_type == EFFECT_SET_FLOOD_LEVEL]
        assert len(level_fx) > 0


class TestDustAccumulation:
    def test_dust_increases_each_turn(self):
        wm = _world_with_room()
        wm.dynamic_events.dust.global_density = 0.0
        wm.dynamic_events.dust.accumulation_rate = 0.2
        effects = _evaluate_dust_accumulation(wm, 1)
        dust_fx = next((e for e in effects if e.effect_type == EFFECT_SET_DUST_DENSITY), None)
        assert dust_fx is not None
        assert dust_fx.payload["global_density"] > 0.0

    def test_water_wheel_halves_accumulation(self):
        wm = _world_with_room()
        wm.dynamic_events.dust.global_density = 0.0
        wm.dynamic_events.dust.accumulation_rate = 0.4
        wm.dynamic_events.flood.water_wheel_active = True
        effects = _evaluate_dust_accumulation(wm, 1)
        dust_fx = next(e for e in effects if e.effect_type == EFFECT_SET_DUST_DENSITY)
        # Should be 0.4 * 0.5 = 0.2
        assert abs(dust_fx.payload["global_density"] - 0.2) < 0.01

    def test_dust_capped_at_100(self):
        wm = _world_with_room()
        wm.dynamic_events.dust.global_density = 99.9
        effects = _evaluate_dust_accumulation(wm, 1)
        dust_fx = next(e for e in effects if e.effect_type == EFFECT_SET_DUST_DENSITY)
        assert dust_fx.payload["global_density"] <= 100.0
'''

p = pathlib.Path('tests/test_phase5.py')
p.write_text(p.read_text(encoding='utf-8') + PART6, encoding='utf-8')
print('part6 ok, lines:', len(p.read_text(encoding='utf-8').splitlines()))
