import pathlib

CHUNK = '''

# ---------------------------------------------------------------------------
# Validator: Guardian Statues
# ---------------------------------------------------------------------------
def _validate_guardian_statues(command_action, command_target, wm, puzzle_state):
    from .object_state import StatueDirection
    STATUE_IDS = ["statue_guardian_n","statue_guardian_e","statue_guardian_s","statue_guardian_w"]
    CORRECT = {
        "statue_guardian_n": StatueDirection.SOUTH,
        "statue_guardian_e": StatueDirection.WEST,
        "statue_guardian_s": StatueDirection.NORTH,
        "statue_guardian_w": StatueDirection.EAST,
    }
    t = (command_target or "").lower()
    target_id = next((s for s in STATUE_IDS if wm.objects.get(s) and t in wm.objects[s].name.lower()), None)
    if not target_id:
        return PuzzleAttemptResult(message="Specify which statue: northern, eastern, southern, or western.")
    obj = wm.objects[target_id]
    observed = any("observed_turn" in h for h in obj.usage_history)
    CYCLE = [StatueDirection.NORTH, StatueDirection.EAST, StatueDirection.SOUTH, StatueDirection.WEST]
    cur = obj.facing_direction or StatueDirection.NORTH
    idx = CYCLE.index(cur) if cur in CYCLE else 0
    new_dir = CYCLE[(idx + 1) % 4]
    correct_this = new_dir == CORRECT[target_id]
    all_correct = all(
        (new_dir if sid == target_id else (wm.objects[sid].facing_direction if wm.objects.get(sid) else None)) == CORRECT[sid]
        for sid in STATUE_IDS
    )
    count = sum(
        1 for sid in STATUE_IDS
        if (new_dir if sid == target_id else (wm.objects[sid].facing_direction if wm.objects.get(sid) else None)) == CORRECT[sid]
    )
    progress = dict(puzzle_state.current_progress)
    progress.update({"statues_correct": count, "statues_total": 4, "rotate_target": target_id, "rotate_direction": new_dir.value})
    if all_correct:
        return PuzzleAttemptResult(
            success=True,
            message="All four guardians face inward. A grinding of stone announces the northern door unlocking.",
            eval_impacts={"wisdom": 5.0, "observation": 3.0, "patience": 3.0},
            world_effects={
                "rotate_statue": (target_id, new_dir.value),
                "open_exit": ("hall_of_guardians", "north", "chamber_of_inscriptions"),
                "update_object_state": ("door_guardian_chamber", {"state": "open"}),
            },
            reckless=not observed,
        )
    fb = "That feels correct." if correct_this else "Something still feels off."
    return PuzzleAttemptResult(
        partial=count > 0,
        message=f"The statue now faces {new_dir.name.lower()}. {fb} ({count}/4 aligned.)",
        eval_impacts={"patience": 0.5 if correct_this else 0.0, "recklessness": 0.5 if (not observed and not correct_this) else 0.0},
        world_effects={"rotate_statue": (target_id, new_dir.value), "update_puzzle_progress": progress},
        reckless=not observed,
    )
'''

p = pathlib.Path('src/world/puzzles.py')
p.write_text(p.read_text(encoding='utf-8') + CHUNK, encoding='utf-8')
print('step2 ok, lines:', len(p.read_text(encoding='utf-8').splitlines()))
