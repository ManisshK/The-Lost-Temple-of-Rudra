import pathlib

PART5 = r'''

# ===========================================================================
# CLEAR RUBBLE PUZZLE
# ===========================================================================

class TestClearRubblePuzzle:
    def _rubble_world(self, has_chisel=True):
        wm = WorldModel()
        wm.rooms["collapsed_hallway"] = RoomState(
            room_id="collapsed_hallway", region=RoomRegion.LIVING_TEMPLE,
            accessible_exits={}, puzzle_id="puzzle_clear_rubble",
        )
        wm.rooms["chamber_of_reflection"] = RoomState(room_id="chamber_of_reflection")
        wm.player.current_room = "collapsed_hallway"
        wm.puzzles["puzzle_clear_rubble"] = PuzzleState(
            puzzle_id="puzzle_clear_rubble", room_id="collapsed_hallway",
            category=PuzzleCategory.ENVIRONMENTAL, status=PuzzleStatus.AVAILABLE,
        )
        wm.objects["rubble_pile"] = ObjectState(
            object_id="rubble_pile", name="Collapsed Rubble",
            category=ObjectCategory.ENVIRONMENTAL,
            current_room="collapsed_hallway", state="blocking",
        )
        wm.rooms["collapsed_hallway"].object_ids_present.append("rubble_pile")
        if has_chisel:
            wm.objects["tool_chisel"] = ObjectState(
                object_id="tool_chisel", name="Iron Chisel",
                category=ObjectCategory.COLLECTIBLE, current_owner="player",
            )
            wm.player.inventory.append("tool_chisel")
        return wm

    def test_without_chisel_blocked(self):
        wm = self._rubble_world(has_chisel=False)
        ps = wm.puzzles["puzzle_clear_rubble"]
        r = PuzzleRegistry.attempt("puzzle_clear_rubble", "push", "rubble", wm, ps)
        assert r.success is False
        assert "tool" in r.message.lower() or "chisel" in r.message.lower() or "hand" in r.message.lower()

    def test_with_chisel_clears_rubble(self):
        wm = self._rubble_world(has_chisel=True)
        ps = wm.puzzles["puzzle_clear_rubble"]
        r = PuzzleRegistry.attempt("puzzle_clear_rubble", "push", "rubble", wm, ps)
        assert r.success is True
        assert r.world_effects.get("open_exit") == ("collapsed_hallway", "north", "chamber_of_reflection")
        assert r.world_effects.get("consume_object") == "tool_chisel"

    def test_unclear_target_blocked(self):
        wm = self._rubble_world(has_chisel=True)
        ps = wm.puzzles["puzzle_clear_rubble"]
        r = PuzzleRegistry.attempt("puzzle_clear_rubble", "push", "door", wm, ps)
        assert r.success is False

    def test_solve_eval_includes_patience(self):
        wm = self._rubble_world(has_chisel=True)
        ps = wm.puzzles["puzzle_clear_rubble"]
        r = PuzzleRegistry.attempt("puzzle_clear_rubble", "push", "rubble", wm, ps)
        assert r.eval_impacts.get("patience", 0) > 0


# ===========================================================================
# REFLECTION POOL PUZZLE
# ===========================================================================

class TestReflectionPoolPuzzle:
    def _pool_world(self):
        wm = WorldModel()
        wm.rooms["chamber_of_reflection"] = RoomState(
            room_id="chamber_of_reflection", region=RoomRegion.GUARDIAN_CORE,
            accessible_exits={}, puzzle_id="puzzle_reflection_pool",
        )
        wm.rooms["hall_of_judgment"] = RoomState(room_id="hall_of_judgment")
        wm.player.current_room = "chamber_of_reflection"
        wm.puzzles["puzzle_reflection_pool"] = PuzzleState(
            puzzle_id="puzzle_reflection_pool", room_id="chamber_of_reflection",
            category=PuzzleCategory.OBSERVATION, status=PuzzleStatus.AVAILABLE,
        )
        wm.objects["pool_reflection"] = ObjectState(
            object_id="pool_reflection", name="Reflection Pool",
            category=ObjectCategory.ENVIRONMENTAL,
            current_room="chamber_of_reflection", state="still",
        )
        wm.rooms["chamber_of_reflection"].object_ids_present.append("pool_reflection")
        return wm

    def test_meditate_without_inspecting_fails(self):
        wm = self._pool_world()
        ps = wm.puzzles["puzzle_reflection_pool"]
        r = PuzzleRegistry.attempt("puzzle_reflection_pool", "meditate", "pool", wm, ps)
        assert r.success is False
        assert "looked" in r.message.lower() or "pool" in r.message.lower()

    def test_inspect_pool_partial_progress(self):
        wm = self._pool_world()
        ps = wm.puzzles["puzzle_reflection_pool"]
        r = PuzzleRegistry.attempt("puzzle_reflection_pool", "inspect", "pool", wm, ps)
        assert r.success is False
        assert r.world_effects.get("update_puzzle_progress", {}).get("pool_inspections", 0) >= 1

    def test_inspect_twice_partial_true(self):
        wm = self._pool_world()
        ps = wm.puzzles["puzzle_reflection_pool"]
        ps.current_progress["pool_inspections"] = 1
        r = PuzzleRegistry.attempt("puzzle_reflection_pool", "inspect", "pool", wm, ps)
        assert r.partial is True

    def test_meditate_after_inspecting_solves(self):
        wm = self._pool_world()
        ps = wm.puzzles["puzzle_reflection_pool"]
        ps.current_progress["pool_inspections"] = 1
        r = PuzzleRegistry.attempt("puzzle_reflection_pool", "meditate", "pool", wm, ps)
        assert r.success is True
        assert r.world_effects.get("open_exit") == ("chamber_of_reflection", "north", "hall_of_judgment")

    def test_kneel_after_inspecting_solves(self):
        wm = self._pool_world()
        ps = wm.puzzles["puzzle_reflection_pool"]
        ps.current_progress["pool_inspections"] = 2
        r = PuzzleRegistry.attempt("puzzle_reflection_pool", "kneel", "", wm, ps)
        assert r.success is True

    def test_solve_eval_includes_patience_and_understanding(self):
        wm = self._pool_world()
        ps = wm.puzzles["puzzle_reflection_pool"]
        ps.current_progress["pool_inspections"] = 1
        r = PuzzleRegistry.attempt("puzzle_reflection_pool", "meditate", "", wm, ps)
        assert r.eval_impacts.get("patience", 0) > 0
        assert r.eval_impacts.get("understanding", 0) > 0


# ===========================================================================
# FINAL JUDGMENT PUZZLE
# ===========================================================================

class TestFinalJudgmentPuzzle:
    def _judgment_world(self, composite_score=0.0):
        wm = WorldModel()
        wm.rooms["throne_approach"] = RoomState(
            room_id="throne_approach", region=RoomRegion.GUARDIAN_CORE,
            accessible_exits={}, puzzle_id="puzzle_final_judgment",
        )
        wm.rooms["final_chamber"] = RoomState(room_id="final_chamber")
        wm.player.current_room = "throne_approach"
        wm.puzzles["puzzle_final_judgment"] = PuzzleState(
            puzzle_id="puzzle_final_judgment", room_id="throne_approach",
            category=PuzzleCategory.FINAL_JUDGMENT, status=PuzzleStatus.AVAILABLE,
        )
        # Satisfy prerequisites
        for pid in ("puzzle_guardian_statues", "puzzle_reflection_pool"):
            wm.puzzles[pid] = PuzzleState(puzzle_id=pid, room_id="hall_of_guardians", status=PuzzleStatus.SOLVED)
        wm.objects["arch_seal"] = ObjectState(
            object_id="arch_seal", name="Sealed Arch",
            category=ObjectCategory.INTERACTIVE,
            current_room="throne_approach", state="sealed",
        )
        # Set evaluation scores to reach desired composite
        if composite_score >= 40.0:
            for attr in ("observation","curiosity","wisdom","patience","adaptation","integrity","responsibility","understanding"):
                getattr(wm.evaluation, attr).score = 50.0
        return wm

    def test_unworthy_player_blocked(self):
        wm = self._judgment_world(composite_score=0.0)
        ps = wm.puzzles["puzzle_final_judgment"]
        r = PuzzleRegistry.attempt("puzzle_final_judgment", "open", "arch", wm, ps)
        assert r.success is False
        assert "incomplete" in r.message.lower() or "readiness" in r.message.lower()

    def test_worthy_player_passes(self):
        wm = self._judgment_world(composite_score=50.0)
        ps = wm.puzzles["puzzle_final_judgment"]
        r = PuzzleRegistry.attempt("puzzle_final_judgment", "open", "arch", wm, ps)
        assert r.success is True
        assert r.world_effects.get("open_exit") == ("throne_approach", "north", "final_chamber")
        assert r.world_effects.get("set_ending_eligibility") == "worthy"

    def test_partial_progress_when_half_ready(self):
        wm = self._judgment_world()
        for attr in ("observation","curiosity","wisdom","patience"):
            getattr(wm.evaluation, attr).score = 50.0
        ps = wm.puzzles["puzzle_final_judgment"]
        r = PuzzleRegistry.attempt("puzzle_final_judgment", "open", "arch", wm, ps)
        assert r.partial is True or r.success is True  # depends on exact score
'''

p = pathlib.Path('tests/test_phase5.py')
p.write_text(p.read_text(encoding='utf-8') + PART5, encoding='utf-8')
print('part5 ok, lines:', len(p.read_text(encoding='utf-8').splitlines()))
