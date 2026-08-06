import pathlib

PART2 = r'''

# ===========================================================================
# PUZZLE FRAMEWORK TESTS
# ===========================================================================

class TestPuzzleAttemptResult:
    def test_default_fields(self):
        r = PuzzleAttemptResult()
        assert r.success is False
        assert r.partial is False
        assert r.message == ""
        assert r.eval_impacts == {}
        assert r.world_effects == {}
        assert r.reckless is False

    def test_success_result(self):
        r = PuzzleAttemptResult(success=True, message="Solved.", eval_impacts={"wisdom": 5.0})
        assert r.success is True
        assert r.eval_impacts["wisdom"] == 5.0

    def test_partial_result(self):
        r = PuzzleAttemptResult(partial=True, message="Progress.")
        assert r.partial is True
        assert r.success is False


class TestPuzzleDefinition:
    def test_all_canonical_puzzles_defined(self):
        expected = [
            "puzzle_guardian_statues", "puzzle_flood_control",
            "puzzle_bridge_integrity", "puzzle_symbol_alignment",
            "puzzle_clear_rubble", "puzzle_reflection_pool",
            "puzzle_final_judgment",
        ]
        for pid in expected:
            assert pid in PUZZLE_DEFINITIONS, f"Missing: {pid}"

    def test_all_canonical_puzzles_have_validators(self):
        for pid in PUZZLE_DEFINITIONS:
            assert pid in PUZZLE_VALIDATORS, f"No validator for: {pid}"

    def test_definition_fields_populated(self):
        defn = PUZZLE_DEFINITIONS["puzzle_guardian_statues"]
        assert defn.puzzle_id == "puzzle_guardian_statues"
        assert defn.room_id == "hall_of_guardians"
        assert defn.category == PuzzleCategory.LOGIC
        assert defn.solve_eval  # not empty

    def test_flood_control_requires_wrench(self):
        defn = PUZZLE_DEFINITIONS["puzzle_flood_control"]
        assert "tool_wrench" in defn.required_objects

    def test_clear_rubble_requires_chisel(self):
        defn = PUZZLE_DEFINITIONS["puzzle_clear_rubble"]
        assert "tool_chisel" in defn.required_objects

    def test_final_judgment_has_prerequisites(self):
        defn = PUZZLE_DEFINITIONS["puzzle_final_judgment"]
        assert "puzzle_guardian_statues" in defn.prerequisite_puzzle_ids
        assert "puzzle_reflection_pool" in defn.prerequisite_puzzle_ids


class TestPuzzleRegistryGuards:
    def test_unknown_puzzle_id_returns_message(self):
        wm = _world_with_room()
        ps = PuzzleState(puzzle_id="ghost", room_id="temple_entrance", status=PuzzleStatus.AVAILABLE)
        result = PuzzleRegistry.attempt("ghost", "rotate", "thing", wm, ps)
        assert result.success is False
        assert result.message

    def test_solved_puzzle_returns_already_solved(self):
        wm = _world_with_room()
        ps = PuzzleState(puzzle_id="puzzle_guardian_statues", room_id="hall_of_guardians", status=PuzzleStatus.SOLVED)
        result = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "statue", wm, ps)
        assert result.success is False
        assert "solved" in result.message.lower() or "already" in result.message.lower()

    def test_locked_puzzle_returns_inaccessible(self):
        wm = _world_with_room()
        ps = PuzzleState(puzzle_id="puzzle_guardian_statues", room_id="hall_of_guardians", status=PuzzleStatus.LOCKED)
        result = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "statue", wm, ps)
        assert result.success is False

    def test_missing_prerequisite_blocks_attempt(self):
        wm = _world_with_room()
        # final_judgment requires two prerequisites not solved
        ps = PuzzleState(puzzle_id="puzzle_final_judgment", room_id="throne_approach", status=PuzzleStatus.AVAILABLE)
        result = PuzzleRegistry.attempt("puzzle_final_judgment", "open", "arch", wm, ps)
        assert result.success is False
        assert "connected" in result.message.lower() or "resolved" in result.message.lower()

    def test_missing_required_object_blocks_attempt(self):
        wm = _world_with_room()
        wm.rooms["flood_control_room"] = RoomState(room_id="flood_control_room")
        ps = PuzzleState(puzzle_id="puzzle_flood_control", room_id="flood_control_room", status=PuzzleStatus.AVAILABLE)
        # No wrench in inventory
        result = PuzzleRegistry.attempt("puzzle_flood_control", "open", "secondary gate", wm, ps)
        assert result.success is False
        assert "missing" in result.message.lower()

    def test_get_definition_returns_correct_object(self):
        defn = PuzzleRegistry.get_definition("puzzle_guardian_statues")
        assert isinstance(defn, PuzzleDefinition)
        assert defn.puzzle_id == "puzzle_guardian_statues"

    def test_get_definition_unknown_returns_none(self):
        assert PuzzleRegistry.get_definition("not_a_puzzle") is None

    def test_get_validator_returns_callable(self):
        v = PuzzleRegistry.get_validator("puzzle_guardian_statues")
        assert callable(v)
'''

p = pathlib.Path('tests/test_phase5.py')
p.write_text(p.read_text(encoding='utf-8') + PART2, encoding='utf-8')
print('part2 ok, lines:', len(p.read_text(encoding='utf-8').splitlines()))
