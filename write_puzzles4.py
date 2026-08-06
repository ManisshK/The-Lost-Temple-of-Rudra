import pathlib

CHUNK = '''

# ---------------------------------------------------------------------------
# Validator: Clear Rubble
# ---------------------------------------------------------------------------
def _validate_clear_rubble(command_action, command_target, wm, puzzle_state):
    t = (command_target or "").lower()
    has_chisel = "tool_chisel" in wm.player.inventory
    if not has_chisel:
        return PuzzleAttemptResult(message="The rubble is too dense to move by hand. A sharp tool might loosen the key stones.", eval_impacts={"observation":1.0})
    if not any(w in t for w in ("rubble","passage","hallway","stones","rocks")):
        return PuzzleAttemptResult(message="Clear what? The rubble pile blocks the northern passage.")
    return PuzzleAttemptResult(success=True, message="Working methodically with the chisel, you loosen the key stones. A passage opens to the north.",
        eval_impacts={"patience":4.0,"adaptation":2.0},
        world_effects={"update_object_state":("rubble_pile",{"state":"cleared","interactable":False}),"open_exit":("collapsed_hallway","north","chamber_of_reflection"),"consume_object":"tool_chisel"})


# ---------------------------------------------------------------------------
# Validator: Reflection Pool
# ---------------------------------------------------------------------------
def _validate_reflection_pool(command_action, command_target, wm, puzzle_state):
    a = command_action.lower()
    t = (command_target or "").lower()
    contemplative = a in ("meditate","pray","kneel","silence","wait")
    inspecting = a in ("inspect","look","examine","study","observe","read")
    prog = dict(puzzle_state.current_progress)

    if inspecting and "pool" in t:
        n = prog.get("pool_inspections", 0) + 1
        prog["pool_inspections"] = n
        msg = "The pool is perfectly still. Your reflection stares back with a subtly different expression."
        if n >= 2:
            msg += " You begin to understand what the room is asking of you."
        return PuzzleAttemptResult(partial=n>=2, message=msg, eval_impacts={"observation":1.5,"wisdom":1.0}, world_effects={"update_puzzle_progress":prog})

    if contemplative:
        if prog.get("pool_inspections", 0) == 0:
            return PuzzleAttemptResult(message="You try to still your mind, but you haven\'t yet truly looked at what the pool is showing you.", eval_impacts={"patience":0.5})
        return PuzzleAttemptResult(success=True, message="You kneel before the pool and remain perfectly still. It responds with light. The Hall of Judgment opens.",
            eval_impacts={"patience":6.0,"understanding":5.0,"integrity":3.0},
            world_effects={"update_object_state":("pool_reflection",{"state":"illuminated","activated":True}),"open_exit":("chamber_of_reflection","north","hall_of_judgment")})

    return PuzzleAttemptResult(message="The reflection pool is perfectly still. Perhaps stillness is its own answer.", eval_impacts={"observation":0.5})


# ---------------------------------------------------------------------------
# Validator: Final Judgment
# ---------------------------------------------------------------------------
def _validate_final_judgment(command_action, command_target, wm, puzzle_state):
    ev = wm.evaluation
    positive = (ev.observation.score + ev.curiosity.score + ev.wisdom.score
                + ev.patience.score + ev.adaptation.score + ev.integrity.score
                + ev.responsibility.score + ev.understanding.score) / 8.0
    negative = (ev.greed.score + ev.recklessness.score) / 2.0
    composite = max(0.0, positive - negative * 0.5)
    if composite >= 40.0:
        return PuzzleAttemptResult(success=True, message="The five symbols glow. The seal releases. The temple has made its judgment. Enter the Final Chamber.",
            eval_impacts={"understanding":5.0},
            world_effects={"update_object_state":("arch_seal",{"state":"open","activated":True}),"open_exit":("throne_approach","north","final_chamber"),"set_ending_eligibility":"worthy"})
    return PuzzleAttemptResult(partial=composite>=20.0,
        message=f"You stand before the sealed arch. The symbols remain dark. The temple finds your journey incomplete. (Readiness: {int(composite)}/40)",
        eval_impacts={"understanding":1.0})
'''

p = pathlib.Path('src/world/puzzles.py')
p.write_text(p.read_text(encoding='utf-8') + CHUNK, encoding='utf-8')
print('step4 ok, lines:', len(p.read_text(encoding='utf-8').splitlines()))
