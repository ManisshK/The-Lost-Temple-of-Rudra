import pathlib

CHUNK = r'''

def _evaluate_statue_reset(wm, turn):
    effects = []
    puzzle_state = wm.puzzles.get("puzzle_guardian_statues")
    if not puzzle_state or puzzle_state.status.value in ("solved", "locked"):
        return effects
    if puzzle_state.first_attempted_turn is None:
        return effects
    if (turn - puzzle_state.first_attempted_turn) < STATUE_RESET_AFTER_TURNS:
        return effects
    statues_state = wm.dynamic_events.statues
    recently_rotated = any((turn - last) < STATUE_RESET_AFTER_TURNS for last in statues_state.last_rotated.values())
    if recently_rotated:
        return effects
    from .object_state import StatueDirection
    ORIGINAL = {"statue_guardian_n": StatueDirection.NORTH, "statue_guardian_e": StatueDirection.EAST,
                "statue_guardian_s": StatueDirection.SOUTH, "statue_guardian_w": StatueDirection.WEST}
    any_reset = False
    for sid, orig_dir in ORIGINAL.items():
        obj = wm.objects.get(sid)
        if obj and obj.facing_direction != orig_dir:
            effects.append(EventEffect(EFFECT_RESET_STATUE, {"statue_id": sid, "direction": orig_dir.value}, f"statue_reset_{sid}_{turn}"))
            any_reset = True
    if any_reset:
        effects.append(EventEffect(EFFECT_APPEND_HISTORY, {"event_id": f"statues_reset_{turn}", "category": "environmental", "description": "A tremor passes through the Hall of Guardians. The statues return to their original positions.", "room_id": "hall_of_guardians"}, f"statues_reset_{turn}"))
    return effects


def _evaluate_hidden_passage_activation(wm, turn):
    effects = []
    bridge_room = wm.rooms.get("bridge_of_echoes")
    if bridge_room:
        if not bridge_room.hidden_passages.get("down", False):
            bp = wm.puzzles.get("puzzle_bridge_integrity")
            if bp and bp.current_progress.get("rope_used", False):
                effects.append(EventEffect(EFFECT_REVEAL_HIDDEN_PASSAGE, {"room_id": "bridge_of_echoes", "direction": "down"}, f"reveal_bridge_down_{turn}"))
    channel_room = wm.rooms.get("water_channel_network")
    if channel_room:
        if not channel_room.hidden_passages.get("east", False):
            has_key = "ancient_key_reservoir" in wm.player.inventory
            in_channel = wm.player.current_room == "water_channel_network"
            if has_key and in_channel:
                effects.append(EventEffect(EFFECT_REVEAL_HIDDEN_PASSAGE, {"room_id": "water_channel_network", "direction": "east"}, f"reveal_channel_east_{turn}"))
                effects.append(EventEffect(EFFECT_OPEN_EXIT, {"room_id": "water_channel_network", "direction": "east", "destination": "hidden_maintenance_tunnel"}, f"open_channel_east_{turn}"))
    return effects


def _evaluate_temple_collapse(wm, turn):
    effects = []
    collapse = wm.dynamic_events.collapse
    if not collapse.active:
        if wm.world.temple_phase.value >= 4 and wm.world.world_stability < COLLAPSE_TRIGGER_STABILITY:
            effects.append(EventEffect(EFFECT_APPEND_HISTORY, {"event_id": f"collapse_begin_{turn}", "category": "environmental", "description": "The temple shudders. The ancient structure is giving way.", "room_id": wm.player.current_room}, f"collapse_begin_{turn}", is_critical=True))
        return effects
    start_turn = collapse.start_turn or turn
    turns_collapsing = max(0, turn - start_turn)
    expected_stage = min(4, turns_collapsing // COLLAPSE_TURNS_PER_STAGE)
    if expected_stage <= collapse.current_stage:
        return effects
    new_stage = expected_stage
    try:
        new_cs = CollapseStage(new_stage)
    except ValueError:
        new_cs = CollapseStage(4)
    new_stability = max(0.0, wm.world.world_stability - new_stage * 10.0)
    effects.append(EventEffect(EFFECT_SET_COLLAPSE_STAGE, {"stage": new_stage, "collapse_stage": new_cs}, f"collapse_{new_stage}_{turn}", is_critical=True))
    effects.append(EventEffect(EFFECT_SET_WORLD_STABILITY, {"world_stability": new_stability}, f"stability_{turn}"))
    stage_desc = {1:"Cracks spider across the walls.", 2:"Part of the ceiling gives way.", 3:"The walls fracture. Water floods through gaps.", 4:"Massive collapse. Escape routes are narrowing."}
    effects.append(EventEffect(EFFECT_APPEND_HISTORY, {"event_id": f"collapse_{new_stage}_{turn}", "category": "environmental", "description": stage_desc.get(new_stage, "The collapse worsens."), "room_id": wm.player.current_room}, f"collapse_{new_stage}_{turn}", is_critical=True))
    return effects


def evaluate_events(wm, turn):
    """
    Main entry point. Called by the Game Engine after every player turn.
    Returns list[EventEffect]. Never raises. Never writes to the World Model.
    Blueprint Reference: Chapter 13.
    """
    effects = []
    phase = wm.world.temple_phase.value
    phase_gates = {
        "_torch": 1, "_dust": 1, "_hidden": 1,
        "_bridge": 2, "_statue": 2,
        "_flood": 2,
        "_collapse": 4,
    }
    evaluators = [
        ("_torch", _evaluate_torch_decay),
        ("_dust", _evaluate_dust_accumulation),
        ("_hidden", _evaluate_hidden_passage_activation),
        ("_bridge", _evaluate_bridge_integrity),
        ("_statue", _evaluate_statue_reset),
        ("_flood", _evaluate_flood_progression),
        ("_collapse", _evaluate_temple_collapse),
    ]
    critical_keys = {"_torch", "_flood", "_collapse"}
    max_non_critical = EVENTS_PER_PHASE.get(phase, 1)
    non_critical_fired = 0

    for key, fn in evaluators:
        if phase < phase_gates.get(key, 1):
            continue
        is_critical = key in critical_keys
        if not is_critical and non_critical_fired >= max_non_critical:
            continue
        try:
            new_fx = fn(wm, turn)
        except Exception:
            continue
        if new_fx:
            effects.extend(new_fx)
            if not is_critical:
                non_critical_fired += 1

    return effects
'''

p = pathlib.Path('src/world/events.py')
p.write_text(p.read_text(encoding='utf-8') + CHUNK, encoding='utf-8')
print('events step3 ok, lines:', len(p.read_text(encoding='utf-8').splitlines()))
