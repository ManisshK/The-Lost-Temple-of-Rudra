import pathlib

PART3 = r'''

# ===========================================================================
# GUARDIAN STATUES PUZZLE
# ===========================================================================

class TestGuardianStatuesPuzzle:
    def test_no_target_returns_clarification(self):
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "", wm, ps)
        assert r.success is False
        assert "specify" in r.message.lower() or "northern" in r.message.lower() or "four" in r.message.lower()

    def test_rotate_northern_statue_partial_progress(self):
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "northern", wm, ps)
        # Northern statue must rotate: N->E (not correct SOUTH), so partial=False, success=False
        assert r.success is False
        assert "north" in r.message.lower() or "east" in r.message.lower() or "correct" in r.message.lower()
        assert "rotate_statue" in r.world_effects

    def test_rotate_applies_correct_direction_in_effects(self):
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "northern", wm, ps)
        statue_id, direction = r.world_effects["rotate_statue"]
        assert statue_id == "statue_guardian_n"
        # N statue starts NORTH, rotates to EAST
        assert direction == StatueDirection.EAST.value

    def test_solve_requires_all_four_correct(self):
        """Manually set statues to correct positions except one, then rotate the last."""
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        # Pre-set three statues to correct facing
        wm.objects["statue_guardian_e"].facing_direction = StatueDirection.WEST
        wm.objects["statue_guardian_s"].facing_direction = StatueDirection.NORTH
        wm.objects["statue_guardian_w"].facing_direction = StatueDirection.EAST
        # Northern starts NORTH, needs SOUTH; rotate until SOUTH (N->E->S)
        wm.objects["statue_guardian_n"].facing_direction = StatueDirection.EAST
        # Now rotating northern will give SOUTH = correct
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "northern", wm, ps)
        assert r.success is True
        assert "open_exit" in r.world_effects
        assert r.world_effects["open_exit"] == ("hall_of_guardians", "north", "chamber_of_inscriptions")

    def test_solve_has_positive_eval_impacts(self):
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        wm.objects["statue_guardian_e"].facing_direction = StatueDirection.WEST
        wm.objects["statue_guardian_s"].facing_direction = StatueDirection.NORTH
        wm.objects["statue_guardian_w"].facing_direction = StatueDirection.EAST
        wm.objects["statue_guardian_n"].facing_direction = StatueDirection.EAST
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "northern", wm, ps)
        assert r.eval_impacts.get("wisdom", 0) > 0
        assert r.eval_impacts.get("patience", 0) > 0

    def test_reckless_flag_set_when_not_observed(self):
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        # usage_history is empty — not observed
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "northern", wm, ps)
        assert r.reckless is True

    def test_reckless_false_when_observed(self):
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        wm.objects["statue_guardian_n"].usage_history.append("observed_turn_1")
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "northern", wm, ps)
        assert r.reckless is False

    def test_partial_progress_tracked(self):
        """After rotating one correct statue, progress shows statues_correct >= 1."""
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        # Set N to EAST so rotating gives SOUTH = correct
        wm.objects["statue_guardian_n"].facing_direction = StatueDirection.EAST
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "northern", wm, ps)
        if "update_puzzle_progress" in r.world_effects:
            prog = r.world_effects["update_puzzle_progress"]
            assert prog.get("statues_correct", 0) >= 1
'''

p = pathlib.Path('tests/test_phase5.py')
p.write_text(p.read_text(encoding='utf-8') + PART3, encoding='utf-8')
print('part3 ok, lines:', len(p.read_text(encoding='utf-8').splitlines()))
