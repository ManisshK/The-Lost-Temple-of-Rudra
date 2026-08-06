"""
puzzles.py - The Lost Temple of Rudra
Canonical puzzle definitions and PuzzleRegistry.
Blueprint Reference: Chapter 6, Chapter 10.4.5
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from .world_model import WorldModel
from .puzzle_state import PuzzleCategory, PuzzleState, PuzzleStatus


@dataclass
class PuzzleAttemptResult:
    success: bool = False
    partial: bool = False
    message: str = ""
    eval_impacts: dict = field(default_factory=dict)
    world_effects: dict = field(default_factory=dict)
    reckless: bool = False


@dataclass
class PuzzleDefinition:
    puzzle_id: str = ""
    room_id: str = ""
    name: str = ""
    category: PuzzleCategory = PuzzleCategory.OBSERVATION
    description: str = ""
    required_objects: tuple = ()
    required_knowledge: tuple = ()
    prerequisite_puzzle_ids: tuple = ()
    solve_eval: dict = field(default_factory=dict)
    failure_eval: dict = field(default_factory=dict)
    solve_message: str = ""
    failure_message: str = ""
    already_solved_message: str = ""
    reward_id: Optional[str] = None


ValidatorFn = Callable[["str", "str", "WorldModel", "PuzzleState"], PuzzleAttemptResult]


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
    t = (command_target or "").strip().lower()
    if not t:
        return PuzzleAttemptResult(message="Specify which statue: northern, eastern, southern, or western.")
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


# ---------------------------------------------------------------------------
# Validator: Flood Control
# ---------------------------------------------------------------------------
def _validate_flood_control(command_action, command_target, wm, puzzle_state):
    t = (command_target or "").lower()
    has_wrench = "tool_wrench" in wm.player.inventory
    prog = dict(puzzle_state.current_progress)
    sec_open = prog.get("secondary_gate_open", False)
    main_open = prog.get("main_gate_open", False)

    if "secondary" in t or ("gate" in t and "main" not in t and not sec_open):
        if not has_wrench:
            return PuzzleAttemptResult(message="You are missing the stone wrench to operate the sluice gate.", eval_impacts={"observation":1.0})
        if sec_open:
            return PuzzleAttemptResult(partial=True, message="The secondary gate is already open.")
        prog["secondary_gate_open"] = True
        return PuzzleAttemptResult(partial=True, message="You engage the secondary gate. Overflow bypass active. Now open the main gate.",
            eval_impacts={"wisdom":2.0,"observation":1.0},
            world_effects={"update_object_state":("flood_gate_secondary",{"state":"open"}),"update_puzzle_progress":prog,"update_event_state":("water_gates","flood_gate_secondary",True)})

    if "main" in t or ("gate" in t and "secondary" not in t and sec_open):
        if not has_wrench:
            return PuzzleAttemptResult(message="You are missing the stone wrench.")
        if not sec_open:
            prog["flood_triggered"] = True
            return PuzzleAttemptResult(message="You open the main gate without the bypass. Water surges. The lower chambers will flood.",
                eval_impacts={"recklessness":5.0,"adaptation":-2.0},
                world_effects={"update_object_state":("flood_gate_main",{"state":"open"}),"trigger_flood":True,"update_puzzle_progress":prog}, reckless=True)
        if main_open:
            return PuzzleAttemptResult(partial=True, message="The main gate is already open.")
        prog["main_gate_open"] = True
        return PuzzleAttemptResult(partial=True, message="Main gate open. Water flows smoothly. The water wheel turns. Now engage the lever.",
            eval_impacts={"wisdom":2.0},
            world_effects={"update_object_state":("flood_gate_main",{"state":"open"}),"update_puzzle_progress":prog,"update_event_state":("water_gates","flood_gate_main",True)})

    if "lever" in t:
        if not sec_open or not main_open:
            return PuzzleAttemptResult(message="Open both flood gates in the correct sequence first.", eval_impacts={"recklessness":1.0}, reckless=True)
        return PuzzleAttemptResult(success=True, message="You pull the lever. The water wheel engages fully. The flood system is under control.",
            eval_impacts={"wisdom":5.0,"adaptation":3.0,"responsibility":3.0},
            world_effects={"update_object_state":("lever_flood_control",{"state":"engaged","activated":True}),"update_object_state_2":("water_wheel",{"state":"turning","activated":True}),"activate_water_wheel":True})

    return PuzzleAttemptResult(message="Secondary gate, main gate, lever. Operate in sequence.", eval_impacts={"observation":0.5})


# ---------------------------------------------------------------------------
# Validator: Bridge Integrity
# ---------------------------------------------------------------------------
def _validate_bridge_integrity(command_action, command_target, wm, puzzle_state):
    t = (command_target or "").lower()
    prog = dict(puzzle_state.current_progress)
    bridge_obj = wm.objects.get("bridge_rope")
    rope_ok = bridge_obj is not None and bridge_obj.condition > 20.0

    if "rope" in t or "descend" in command_action.lower():
        if not rope_ok:
            return PuzzleAttemptResult(message="The rope is too frayed. Another way down must exist.", eval_impacts={"observation":1.0})
        prog["rope_used"] = True
        return PuzzleAttemptResult(success=True, message="The rope holds. You descend to the underground reservoir.",
            eval_impacts={"curiosity":3.0,"adaptation":2.0},
            world_effects={"open_exit":("bridge_of_echoes","down","underground_reservoir"),"reveal_hidden_passage":("bridge_of_echoes","down"),"update_puzzle_progress":prog})

    if "cross" in t or "bridge" in t:
        crossings = prog.get("bridge_crossings", 0) + 1
        prog["bridge_crossings"] = crossings
        bid = "bridge_rope"
        integrity = max(0.0, wm.dynamic_events.bridge.integrity.get(bid, 100.0) - 5.0)
        fx = {"update_bridge_integrity":(bid, integrity),"update_puzzle_progress":prog}
        if integrity < 30.0:
            return PuzzleAttemptResult(partial=True, message="The bridge groans alarmingly.", eval_impacts={"adaptation":1.0}, world_effects=fx)
        return PuzzleAttemptResult(partial=True, message=f"You cross carefully. ({crossings} crossing(s).)", world_effects=fx)

    return PuzzleAttemptResult(message="A rope is attached to the bridge railing — it might allow descent.", eval_impacts={"observation":0.5})


# ---------------------------------------------------------------------------
# Validator: Symbol Alignment
# ---------------------------------------------------------------------------
def _validate_symbol_alignment(command_action, command_target, wm, puzzle_state):
    SEQ = ["eye","flame","river","circle","throne"]
    t = (command_target or "").lower()
    mural = wm.objects.get("mural_symbol_gallery")
    mural_read = mural is not None and mural.state in ("read","discovered")
    if not (mural_read or len(wm.story.symbols_encountered) >= 3):
        return PuzzleAttemptResult(message="You sense a specific order, but haven't learned enough about the symbols.", eval_impacts={"observation":1.0})
    prog = dict(puzzle_state.current_progress)
    aligned = list(prog.get("aligned_sequence", []))
    symbol = next((s for s in SEQ if s in t), None)
    if not symbol:
        return PuzzleAttemptResult(message=f"Which symbol? Eye, flame, river, circle, throne. Aligned: {', '.join(aligned) or 'none'}.")
    if symbol in aligned:
        return PuzzleAttemptResult(partial=True, message=f"The {symbol} relief is already in position.")
    expected = SEQ[len(aligned)] if len(aligned) < 5 else None
    if expected and symbol != expected:
        prog["aligned_sequence"] = []
        return PuzzleAttemptResult(message=f"Wrong order. The symbols scatter back.", eval_impacts={"recklessness":1.0}, world_effects={"update_puzzle_progress":prog}, reckless=True)
    aligned.append(symbol)
    prog["aligned_sequence"] = aligned
    if len(aligned) == 5:
        return PuzzleAttemptResult(success=True, message="Eye. Flame. River. Circle. Throne. The gallery illuminates. The northern passage opens.",
            eval_impacts={"wisdom":6.0,"understanding":4.0,"observation":3.0},
            world_effects={"update_puzzle_progress":prog,"open_exit":("symbol_gallery","north","chamber_of_maps")})
    return PuzzleAttemptResult(partial=True, message=f"The {symbol} relief settles into place. ({len(aligned)}/5 aligned.)",
        eval_impacts={"wisdom":1.0}, world_effects={"update_puzzle_progress":prog})


# ---------------------------------------------------------------------------
# Validator: Clear Rubble
# ---------------------------------------------------------------------------
def _validate_clear_rubble(command_action, command_target, wm, puzzle_state):
    t = (command_target or "").lower()
    has_chisel = "tool_chisel" in wm.player.inventory
    if not has_chisel:
        return PuzzleAttemptResult(message="The rubble is too dense to move by hand. You are missing a sharp tool (iron chisel) to loosen the key stones.", eval_impacts={"observation":1.0})
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
            return PuzzleAttemptResult(message="You try to still your mind, but you haven't yet truly looked at what the pool is showing you.", eval_impacts={"patience":0.5})
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
            return PuzzleAttemptResult(message=f"No definition for puzzle '{puzzle_id}'.")
        if puzzle_state.status == PuzzleStatus.SOLVED:
            return PuzzleAttemptResult(message=defn.already_solved_message or "That puzzle has already been solved.")
        if puzzle_state.status == PuzzleStatus.LOCKED:
            return PuzzleAttemptResult(message="This puzzle feels inaccessible right now.")
        missing = [p for p in defn.prerequisite_puzzle_ids
                   if p not in wm.puzzles or wm.puzzles[p].status != PuzzleStatus.SOLVED]
        if missing:
            return PuzzleAttemptResult(message="This puzzle is connected to others you have not yet resolved.")
        missing_obj = [o for o in defn.required_objects if o not in wm.player.inventory]
        validator = PUZZLE_VALIDATORS.get(puzzle_id)
        if missing_obj and validator is None:
            return PuzzleAttemptResult(message="You are missing something needed to interact with this puzzle.")
        if validator is None:
            return PuzzleAttemptResult(message="The puzzle mechanism does not respond.")
        try:
            return validator(command_action, command_target, wm, puzzle_state)
        except Exception as exc:
            return PuzzleAttemptResult(message=f"The puzzle mechanism jams. ({exc})")
