import pathlib

CHUNK = '''

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
            return PuzzleAttemptResult(message="You need the stone wrench to operate the sluice gate.", eval_impacts={"observation":1.0})
        if sec_open:
            return PuzzleAttemptResult(partial=True, message="The secondary gate is already open.")
        prog["secondary_gate_open"] = True
        return PuzzleAttemptResult(partial=True, message="You engage the secondary gate. Overflow bypass active. Now open the main gate.",
            eval_impacts={"wisdom":2.0,"observation":1.0},
            world_effects={"update_object_state":("flood_gate_secondary",{"state":"open"}),"update_puzzle_progress":prog,"update_event_state":("water_gates","flood_gate_secondary",True)})

    if "main" in t or ("gate" in t and "secondary" not in t and sec_open):
        if not has_wrench:
            return PuzzleAttemptResult(message="You need the stone wrench.")
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
'''

p = pathlib.Path('src/world/puzzles.py')
p.write_text(p.read_text(encoding='utf-8') + CHUNK, encoding='utf-8')
print('step3 ok, lines:', len(p.read_text(encoding='utf-8').splitlines()))
