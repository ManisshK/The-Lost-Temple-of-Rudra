import pathlib

CHUNK = '''

# ---------------------------------------------------------------------------
# Registry and definitions
# ---------------------------------------------------------------------------
PUZZLE_VALIDATORS: dict = {
    "puzzle_guardian_statues": _validate_guardian_statues,
    "puzzle_flood_control": _validate_flood_control,
    "puzzle_bridge_integrity": _validate_bridge_integrity,
    "puzzle_symbol_alignment": _validate_symbol_alignment,
    "puzzle_clear_rubble": _validate_clear_rubble,
    "puzzle_reflection_pool": _validate_reflection_pool,
    "puzzle_final_judgment": _validate_final_judgment,
}

PUZZLE_DEFINITIONS: dict = {
    "puzzle_guardian_statues": PuzzleDefinition(
        puzzle_id="puzzle_guardian_statues", room_id="hall_of_guardians",
        name="The Four Guardians", category=PuzzleCategory.LOGIC,
        description="Rotate all four guardian statues to face inward.",
        solve_eval={"wisdom":5.0,"observation":3.0,"patience":3.0},
        failure_eval={"recklessness":0.5},
        solve_message="All four guardians face inward. The northern door unlocks.",
    ),
    "puzzle_flood_control": PuzzleDefinition(
        puzzle_id="puzzle_flood_control", room_id="flood_control_room",
        name="The Flood Control Sequence", category=PuzzleCategory.ENVIRONMENTAL,
        description="Open secondary gate, then main gate, then engage lever.",
        required_objects=("tool_wrench",),
        solve_eval={"wisdom":5.0,"adaptation":3.0,"responsibility":3.0},
        failure_eval={"recklessness":5.0},
        solve_message="The flood control system is operational.",
    ),
    "puzzle_bridge_integrity": PuzzleDefinition(
        puzzle_id="puzzle_bridge_integrity", room_id="bridge_of_echoes",
        name="The Bridge of Echoes", category=PuzzleCategory.ENVIRONMENTAL,
        description="Use the rope to descend to the underground reservoir.",
        solve_eval={"curiosity":3.0,"adaptation":2.0},
        solve_message="The rope holds. You descend to the reservoir.",
    ),
    "puzzle_symbol_alignment": PuzzleDefinition(
        puzzle_id="puzzle_symbol_alignment", room_id="symbol_gallery",
        name="The Five Sacred Symbols", category=PuzzleCategory.MEMORY,
        description="Align the five symbol reliefs: Eye, Flame, River, Circle, Throne.",
        required_knowledge=("mural_symbol_gallery",),
        solve_eval={"wisdom":6.0,"understanding":4.0,"observation":3.0},
        failure_eval={"recklessness":1.0},
        solve_message="The symbols align. The northern passage opens.",
    ),
    "puzzle_clear_rubble": PuzzleDefinition(
        puzzle_id="puzzle_clear_rubble", room_id="collapsed_hallway",
        name="The Collapsed Passage", category=PuzzleCategory.ENVIRONMENTAL,
        description="Clear the rubble pile using the iron chisel.",
        required_objects=("tool_chisel",),
        solve_eval={"patience":4.0,"adaptation":2.0},
        solve_message="The passage to the north is cleared.",
    ),
    "puzzle_reflection_pool": PuzzleDefinition(
        puzzle_id="puzzle_reflection_pool", room_id="chamber_of_reflection",
        name="The Reflection Pool", category=PuzzleCategory.OBSERVATION,
        description="Inspect the pool, then meditate or kneel before it.",
        solve_eval={"patience":6.0,"understanding":5.0,"integrity":3.0},
        solve_message="The pool illuminates. The Hall of Judgment opens.",
    ),
    "puzzle_final_judgment": PuzzleDefinition(
        puzzle_id="puzzle_final_judgment", room_id="throne_approach",
        name="The Final Judgment", category=PuzzleCategory.FINAL_JUDGMENT,
        description="The arch opens only when the Guardian deems you worthy.",
        prerequisite_puzzle_ids=("puzzle_guardian_statues","puzzle_reflection_pool"),
        solve_eval={"understanding":5.0},
        solve_message="The arch opens. The Final Chamber awaits.",
        failure_message="The temple finds your journey incomplete.",
    ),
}


class PuzzleRegistry:
    """Stateless access to puzzle definitions and validators."""

    @staticmethod
    def get_definition(puzzle_id):
        return PUZZLE_DEFINITIONS.get(puzzle_id)

    @staticmethod
    def get_validator(puzzle_id):
        return PUZZLE_VALIDATORS.get(puzzle_id)

    @staticmethod
    def attempt(puzzle_id, command_action, command_target, wm, puzzle_state):
        defn = PUZZLE_DEFINITIONS.get(puzzle_id)
        if defn is None:
            return PuzzleAttemptResult(message=f"No definition for puzzle \'{puzzle_id}\'.")
        if puzzle_state.status == PuzzleStatus.SOLVED:
            return PuzzleAttemptResult(message=defn.already_solved_message or "That puzzle has already been solved.")
        if puzzle_state.status == PuzzleStatus.LOCKED:
            return PuzzleAttemptResult(message="This puzzle feels inaccessible right now.")
        missing = [p for p in defn.prerequisite_puzzle_ids
                   if p not in wm.puzzles or wm.puzzles[p].status != PuzzleStatus.SOLVED]
        if missing:
            return PuzzleAttemptResult(message="This puzzle is connected to others you have not yet resolved.")
        missing_obj = [o for o in defn.required_objects if o not in wm.player.inventory]
        if missing_obj:
            return PuzzleAttemptResult(message="You are missing something needed to interact with this puzzle.")
        validator = PUZZLE_VALIDATORS.get(puzzle_id)
        if validator is None:
            return PuzzleAttemptResult(message="The puzzle mechanism does not respond.")
        try:
            return validator(command_action, command_target, wm, puzzle_state)
        except Exception as exc:
            return PuzzleAttemptResult(message=f"The puzzle mechanism jams. ({exc})")
'''

p = pathlib.Path('src/world/puzzles.py')
p.write_text(p.read_text(encoding='utf-8') + CHUNK, encoding='utf-8')
print('step5 ok, lines:', len(p.read_text(encoding='utf-8').splitlines()))
