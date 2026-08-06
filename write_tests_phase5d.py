import pathlib

PART4 = r'''

# ===========================================================================
# FLOOD CONTROL PUZZLE
# ===========================================================================

class TestFloodControlPuzzle:
    def test_no_wrench_blocked(self):
        wm = _flood_world()
        wm.player.inventory.remove("tool_wrench")
        ps = wm.puzzles["puzzle_flood_control"]
        r = PuzzleRegistry.attempt("puzzle_flood_control", "open", "secondary gate", wm, ps)
        assert r.success is False
        assert "wrench" in r.message.lower()

    def test_open_secondary_gate_first(self):
        wm = _flood_world()
        ps = wm.puzzles["puzzle_flood_control"]
        r = PuzzleRegistry.attempt("puzzle_flood_control", "open", "secondary gate", wm, ps)
        assert r.partial is True
        assert r.world_effects.get("update_object_state") == ("flood_gate_secondary", {"state": "open"})
        assert r.world_effects.get("update_puzzle_progress", {}).get("secondary_gate_open") is True

    def test_open_main_without_secondary_triggers_flood(self):
        wm = _flood_world()
        ps = wm.puzzles["puzzle_flood_control"]
        r = PuzzleRegistry.attempt("puzzle_flood_control", "open", "main gate", wm, ps)
        assert r.success is False
        assert r.reckless is True
        assert r.world_effects.get("trigger_flood") is True
        assert "flood" in r.message.lower()

    def test_open_main_after_secondary_ok(self):
        wm = _flood_world()
        ps = wm.puzzles["puzzle_flood_control"]
        ps.current_progress["secondary_gate_open"] = True
        r = PuzzleRegistry.attempt("puzzle_flood_control", "open", "main gate", wm, ps)
        assert r.partial is True
        assert "trigger_flood" not in r.world_effects
        assert r.world_effects.get("update_puzzle_progress", {}).get("main_gate_open") is True

    def test_lever_without_both_gates_fails(self):
        wm = _flood_world()
        ps = wm.puzzles["puzzle_flood_control"]
        r = PuzzleRegistry.attempt("puzzle_flood_control", "pull", "lever", wm, ps)
        assert r.success is False
        assert r.reckless is True

    def test_lever_after_both_gates_solves(self):
        wm = _flood_world()
        ps = wm.puzzles["puzzle_flood_control"]
        ps.current_progress["secondary_gate_open"] = True
        ps.current_progress["main_gate_open"] = True
        r = PuzzleRegistry.attempt("puzzle_flood_control", "pull", "lever", wm, ps)
        assert r.success is True
        assert r.world_effects.get("activate_water_wheel") is True
        assert r.eval_impacts.get("responsibility", 0) > 0

    def test_wrong_order_increases_recklessness(self):
        wm = _flood_world()
        ps = wm.puzzles["puzzle_flood_control"]
        r = PuzzleRegistry.attempt("puzzle_flood_control", "open", "main gate", wm, ps)
        assert r.eval_impacts.get("recklessness", 0) > 0


# ===========================================================================
# BRIDGE PUZZLE
# ===========================================================================

class TestBridgeIntegrityPuzzle:
    def _bridge_world(self):
        wm = WorldModel()
        wm.rooms["bridge_of_echoes"] = RoomState(
            room_id="bridge_of_echoes", region=RoomRegion.LIVING_TEMPLE,
            accessible_exits={}, puzzle_id="puzzle_bridge_integrity",
        )
        wm.rooms["underground_reservoir"] = RoomState(room_id="underground_reservoir")
        wm.player.current_room = "bridge_of_echoes"
        wm.puzzles["puzzle_bridge_integrity"] = PuzzleState(
            puzzle_id="puzzle_bridge_integrity", room_id="bridge_of_echoes",
            category=PuzzleCategory.ENVIRONMENTAL, status=PuzzleStatus.AVAILABLE,
        )
        wm.objects["bridge_rope"] = ObjectState(
            object_id="bridge_rope", name="Bridge Rope",
            category=ObjectCategory.ENVIRONMENTAL,
            current_room="bridge_of_echoes", state="intact", condition=80.0,
        )
        wm.rooms["bridge_of_echoes"].object_ids_present.append("bridge_rope")
        wm.dynamic_events.bridge.integrity["bridge_rope"] = 100.0
        return wm

    def test_rope_descent_solves_puzzle(self):
        wm = self._bridge_world()
        ps = wm.puzzles["puzzle_bridge_integrity"]
        r = PuzzleRegistry.attempt("puzzle_bridge_integrity", "use", "rope", wm, ps)
        assert r.success is True
        assert r.world_effects.get("open_exit") == ("bridge_of_echoes", "down", "underground_reservoir")
        assert r.world_effects.get("reveal_hidden_passage") == ("bridge_of_echoes", "down")

    def test_frayed_rope_blocks_descent(self):
        wm = self._bridge_world()
        wm.objects["bridge_rope"].condition = 10.0
        ps = wm.puzzles["puzzle_bridge_integrity"]
        r = PuzzleRegistry.attempt("puzzle_bridge_integrity", "use", "rope", wm, ps)
        assert r.success is False
        assert "frayed" in r.message.lower() or "weight" in r.message.lower()

    def test_crossing_degrades_bridge(self):
        wm = self._bridge_world()
        ps = wm.puzzles["puzzle_bridge_integrity"]
        r = PuzzleRegistry.attempt("puzzle_bridge_integrity", "cross", "bridge", wm, ps)
        assert r.partial is True
        fx = r.world_effects.get("update_bridge_integrity")
        assert fx is not None
        bridge_id, new_integrity = fx
        assert new_integrity < 100.0

    def test_multiple_crossings_accumulate_damage(self):
        wm = self._bridge_world()
        ps = wm.puzzles["puzzle_bridge_integrity"]
        r1 = PuzzleRegistry.attempt("puzzle_bridge_integrity", "cross", "bridge", wm, ps)
        # Simulate applying the effect
        _, i1 = r1.world_effects["update_bridge_integrity"]
        wm.dynamic_events.bridge.integrity["bridge_rope"] = i1
        r2 = PuzzleRegistry.attempt("puzzle_bridge_integrity", "cross", "bridge", wm, ps)
        _, i2 = r2.world_effects["update_bridge_integrity"]
        assert i2 < i1


# ===========================================================================
# SYMBOL ALIGNMENT PUZZLE
# ===========================================================================

class TestSymbolAlignmentPuzzle:
    def _symbol_world(self, mural_read=True, symbols=3):
        wm = WorldModel()
        wm.rooms["symbol_gallery"] = RoomState(
            room_id="symbol_gallery", region=RoomRegion.KNOWLEDGE_SANCTUM,
            accessible_exits={}, puzzle_id="puzzle_symbol_alignment",
        )
        wm.rooms["chamber_of_maps"] = RoomState(room_id="chamber_of_maps")
        wm.player.current_room = "symbol_gallery"
        wm.puzzles["puzzle_symbol_alignment"] = PuzzleState(
            puzzle_id="puzzle_symbol_alignment", room_id="symbol_gallery",
            category=PuzzleCategory.MEMORY, status=PuzzleStatus.AVAILABLE,
        )
        wm.objects["mural_symbol_gallery"] = ObjectState(
            object_id="mural_symbol_gallery", name="Symbol Gallery Mural",
            category=ObjectCategory.STORY, current_room="symbol_gallery",
            state="read" if mural_read else "undiscovered",
        )
        for sym in list({"eye","flame","river","circle","throne"})[:symbols]:
            wm.story.symbols_encountered.add(sym)
        return wm

    def test_without_knowledge_blocked(self):
        wm = self._symbol_world(mural_read=False, symbols=1)
        ps = wm.puzzles["puzzle_symbol_alignment"]
        r = PuzzleRegistry.attempt("puzzle_symbol_alignment", "align", "eye", wm, ps)
        assert r.success is False
        assert "haven" in r.message.lower() or "learned" in r.message.lower()

    def test_with_mural_read_unlocked(self):
        wm = self._symbol_world(mural_read=True, symbols=1)
        ps = wm.puzzles["puzzle_symbol_alignment"]
        r = PuzzleRegistry.attempt("puzzle_symbol_alignment", "align", "eye", wm, ps)
        # Should not be blocked by knowledge gate
        assert "haven" not in r.message.lower() or r.partial

    def test_correct_first_symbol_partial(self):
        wm = self._symbol_world()
        ps = wm.puzzles["puzzle_symbol_alignment"]
        r = PuzzleRegistry.attempt("puzzle_symbol_alignment", "align", "eye", wm, ps)
        assert r.partial is True
        assert r.world_effects.get("update_puzzle_progress", {}).get("aligned_sequence") == ["eye"]

    def test_wrong_order_resets(self):
        wm = self._symbol_world()
        ps = wm.puzzles["puzzle_symbol_alignment"]
        # Flame is second, but try it first
        r = PuzzleRegistry.attempt("puzzle_symbol_alignment", "align", "flame", wm, ps)
        assert r.success is False
        assert r.world_effects.get("update_puzzle_progress", {}).get("aligned_sequence") == []

    def test_full_correct_sequence_solves(self):
        wm = self._symbol_world()
        ps = wm.puzzles["puzzle_symbol_alignment"]
        for sym in ["eye", "flame", "river", "circle"]:
            ps.current_progress.setdefault("aligned_sequence", []).append(sym)
        # Add throne — last one
        r = PuzzleRegistry.attempt("puzzle_symbol_alignment", "align", "throne", wm, ps)
        assert r.success is True
        assert r.world_effects.get("open_exit") == ("symbol_gallery", "north", "chamber_of_maps")

    def test_duplicate_symbol_rejected(self):
        wm = self._symbol_world()
        ps = wm.puzzles["puzzle_symbol_alignment"]
        ps.current_progress["aligned_sequence"] = ["eye"]
        r = PuzzleRegistry.attempt("puzzle_symbol_alignment", "align", "eye", wm, ps)
        assert r.partial is True
        assert "already" in r.message.lower()
'''

p = pathlib.Path('tests/test_phase5.py')
p.write_text(p.read_text(encoding='utf-8') + PART4, encoding='utf-8')
print('part4 ok, lines:', len(p.read_text(encoding='utf-8').splitlines()))
