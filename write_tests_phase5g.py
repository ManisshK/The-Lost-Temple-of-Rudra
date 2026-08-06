import pathlib

PART7 = r'''

class TestBridgeIntegrityDecay:
    def test_bridge_decays_in_phase_2(self):
        wm = _world_with_room()
        wm.world.temple_phase = TemplePhase(2)
        wm.dynamic_events.bridge.integrity["bridge_rope"] = 100.0
        wm.objects["bridge_rope"] = ObjectState(
            object_id="bridge_rope", name="Bridge Rope",
            category=ObjectCategory.ENVIRONMENTAL, current_room="r",
        )
        effects = _evaluate_bridge_integrity(wm, 1)
        bridge_fx = next((e for e in effects if e.effect_type == EFFECT_UPDATE_BRIDGE), None)
        assert bridge_fx is not None
        assert bridge_fx.payload["integrity"] < 100.0

    def test_bridge_stable_in_phase_1(self):
        wm = _world_with_room()
        wm.world.temple_phase = TemplePhase(1)
        wm.dynamic_events.bridge.integrity["bridge_rope"] = 100.0
        effects = _evaluate_bridge_integrity(wm, 1)
        bridge_fx = [e for e in effects if e.effect_type == EFFECT_UPDATE_BRIDGE]
        assert len(bridge_fx) == 0

    def test_collapsed_bridge_not_decayed_further(self):
        wm = _world_with_room()
        wm.world.temple_phase = TemplePhase(2)
        wm.dynamic_events.bridge.collapsed_bridges.append("bridge_rope")
        effects = _evaluate_bridge_integrity(wm, 1)
        bridge_fx = [e for e in effects if e.effect_type == EFFECT_UPDATE_BRIDGE]
        assert len(bridge_fx) == 0

    def test_bridge_collapse_event_fires_at_threshold(self):
        wm = _world_with_room()
        wm.world.temple_phase = TemplePhase(2)
        from world.events import BRIDGE_COLLAPSE_THRESHOLD, BRIDGE_DECAY_PER_TURN
        # Set just above threshold so one decay crosses it
        wm.dynamic_events.bridge.integrity["bridge_rope"] = BRIDGE_COLLAPSE_THRESHOLD + BRIDGE_DECAY_PER_TURN * 0.5
        effects = _evaluate_bridge_integrity(wm, 1)
        history_fx = [e for e in effects if e.effect_type == "append_history"]
        assert len(history_fx) > 0  # collapse event logged


class TestStatueReset:
    def _statue_reset_world(self, turns_since_attempt=25):
        wm = WorldModel()
        wm.rooms["hall_of_guardians"] = RoomState(room_id="hall_of_guardians")
        wm.player.current_room = "hall_of_guardians"
        wm.puzzles["puzzle_guardian_statues"] = PuzzleState(
            puzzle_id="puzzle_guardian_statues", room_id="hall_of_guardians",
            category=PuzzleCategory.LOGIC, status=PuzzleStatus.IN_PROGRESS,
            first_attempted_turn=1,
        )
        for sid, facing in [
            ("statue_guardian_n", StatueDirection.EAST),   # wrong
            ("statue_guardian_e", StatueDirection.NORTH),  # wrong
            ("statue_guardian_s", StatueDirection.SOUTH),  # wrong (should be NORTH)
            ("statue_guardian_w", StatueDirection.WEST),   # wrong
        ]:
            wm.objects[sid] = ObjectState(
                object_id=sid, name=f"Guardian Statue",
                category=ObjectCategory.PUZZLE,
                current_room="hall_of_guardians",
                facing_direction=facing,
            )
        return wm, 1 + turns_since_attempt  # current_turn

    def test_statues_reset_after_timeout(self):
        wm, current_turn = self._statue_reset_world(turns_since_attempt=25)
        effects = _evaluate_statue_reset(wm, current_turn)
        reset_fx = [e for e in effects if e.effect_type == EFFECT_RESET_STATUE]
        assert len(reset_fx) > 0

    def test_reset_returns_to_original_facing(self):
        wm, current_turn = self._statue_reset_world(turns_since_attempt=25)
        effects = _evaluate_statue_reset(wm, current_turn)
        for fx in effects:
            if fx.effect_type == EFFECT_RESET_STATUE:
                sid = fx.payload["statue_id"]
                expected = {"statue_guardian_n": "north", "statue_guardian_e": "east",
                            "statue_guardian_s": "south", "statue_guardian_w": "west"}
                assert fx.payload["direction"] == expected[sid]

    def test_no_reset_before_timeout(self):
        wm, _ = self._statue_reset_world(turns_since_attempt=5)
        effects = _evaluate_statue_reset(wm, 6)
        reset_fx = [e for e in effects if e.effect_type == EFFECT_RESET_STATUE]
        assert len(reset_fx) == 0

    def test_solved_puzzle_never_resets(self):
        wm, current_turn = self._statue_reset_world(turns_since_attempt=25)
        wm.puzzles["puzzle_guardian_statues"].status = PuzzleStatus.SOLVED
        effects = _evaluate_statue_reset(wm, current_turn)
        reset_fx = [e for e in effects if e.effect_type == EFFECT_RESET_STATUE]
        assert len(reset_fx) == 0

    def test_recent_rotation_prevents_reset(self):
        wm, current_turn = self._statue_reset_world(turns_since_attempt=25)
        # Simulate recent rotation (only 5 turns ago)
        wm.dynamic_events.statues.last_rotated["statue_guardian_n"] = current_turn - 5
        effects = _evaluate_statue_reset(wm, current_turn)
        reset_fx = [e for e in effects if e.effect_type == EFFECT_RESET_STATUE]
        assert len(reset_fx) == 0


class TestHiddenPassageActivation:
    def test_bridge_passage_revealed_after_rope_used(self):
        wm = WorldModel()
        wm.rooms["bridge_of_echoes"] = RoomState(
            room_id="bridge_of_echoes", hidden_passages={"down": False},
        )
        wm.rooms["underground_reservoir"] = RoomState(room_id="underground_reservoir")
        wm.player.current_room = "bridge_of_echoes"
        wm.puzzles["puzzle_bridge_integrity"] = PuzzleState(
            puzzle_id="puzzle_bridge_integrity", room_id="bridge_of_echoes",
            category=PuzzleCategory.ENVIRONMENTAL, status=PuzzleStatus.AVAILABLE,
            current_progress={"rope_used": True},
        )
        effects = _evaluate_hidden_passage_activation(wm, 5)
        reveal_fx = [e for e in effects if e.effect_type == EFFECT_REVEAL_HIDDEN_PASSAGE]
        assert len(reveal_fx) > 0
        assert reveal_fx[0].payload == {"room_id": "bridge_of_echoes", "direction": "down"}

    def test_bridge_passage_not_revealed_without_rope(self):
        wm = WorldModel()
        wm.rooms["bridge_of_echoes"] = RoomState(
            room_id="bridge_of_echoes", hidden_passages={"down": False},
        )
        wm.player.current_room = "bridge_of_echoes"
        wm.puzzles["puzzle_bridge_integrity"] = PuzzleState(
            puzzle_id="puzzle_bridge_integrity", room_id="bridge_of_echoes",
            category=PuzzleCategory.ENVIRONMENTAL, status=PuzzleStatus.AVAILABLE,
        )
        effects = _evaluate_hidden_passage_activation(wm, 5)
        reveal_fx = [e for e in effects if e.effect_type == EFFECT_REVEAL_HIDDEN_PASSAGE]
        assert len(reveal_fx) == 0

    def test_channel_passage_revealed_with_key_in_room(self):
        wm = WorldModel()
        wm.rooms["water_channel_network"] = RoomState(
            room_id="water_channel_network", hidden_passages={"east": False},
        )
        wm.rooms["hidden_maintenance_tunnel"] = RoomState(room_id="hidden_maintenance_tunnel")
        wm.player.current_room = "water_channel_network"
        wm.objects["ancient_key_reservoir"] = ObjectState(
            object_id="ancient_key_reservoir", name="Reservoir Key",
            category=ObjectCategory.COLLECTIBLE, current_owner="player",
        )
        wm.player.inventory.append("ancient_key_reservoir")
        effects = _evaluate_hidden_passage_activation(wm, 5)
        open_fx = [e for e in effects if e.effect_type == EFFECT_OPEN_EXIT]
        assert len(open_fx) > 0

    def test_channel_passage_not_revealed_in_wrong_room(self):
        wm = WorldModel()
        wm.rooms["water_channel_network"] = RoomState(
            room_id="water_channel_network", hidden_passages={"east": False},
        )
        wm.rooms["temple_entrance"] = RoomState(room_id="temple_entrance")
        wm.player.current_room = "temple_entrance"  # wrong room
        wm.objects["ancient_key_reservoir"] = ObjectState(
            object_id="ancient_key_reservoir", name="Reservoir Key",
            category=ObjectCategory.COLLECTIBLE, current_owner="player",
        )
        wm.player.inventory.append("ancient_key_reservoir")
        effects = _evaluate_hidden_passage_activation(wm, 5)
        open_fx = [e for e in effects if e.effect_type == EFFECT_OPEN_EXIT]
        assert len(open_fx) == 0


class TestEvaluateEventsIntegration:
    def test_returns_list(self):
        wm = _world_with_room()
        effects = evaluate_events(wm, 1)
        assert isinstance(effects, list)

    def test_never_raises(self):
        for phase in (1, 2, 3, 4):
            wm = _world_with_room()
            wm.world.temple_phase = TemplePhase(phase)
            try:
                evaluate_events(wm, 99)
            except Exception as e:
                pytest.fail(f"evaluate_events raised for phase {phase}: {e}")

    def test_all_effects_are_event_effect_instances(self):
        wm = _world_with_room()
        wm.player.torch.state = "lit"
        wm.player.torch.fuel = 50
        effects = evaluate_events(wm, 1)
        for e in effects:
            assert isinstance(e, EventEffect)

    def test_phase_1_limits_non_critical_events(self):
        wm = _world_with_room()
        wm.world.temple_phase = TemplePhase(1)
        # Bridge decay is phase 2+ so should not fire
        wm.dynamic_events.bridge.integrity["bridge_rope"] = 100.0
        effects = evaluate_events(wm, 1)
        bridge_fx = [e for e in effects if e.effect_type == EFFECT_UPDATE_BRIDGE]
        assert len(bridge_fx) == 0
'''

p = pathlib.Path('tests/test_phase5.py')
p.write_text(p.read_text(encoding='utf-8') + PART7, encoding='utf-8')
print('part7 ok, lines:', len(p.read_text(encoding='utf-8').splitlines()))
