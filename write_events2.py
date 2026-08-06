import pathlib

CHUNK = r'''

def _evaluate_torch_decay(wm, turn):
    effects = []
    torch = wm.player.torch
    if torch.state not in ("lit", "dim", "almost_out"):
        return effects
    burn = wm.dynamic_events.torch_burn.current_burn_rate
    room = wm.get_current_room()
    if room and room.water_level > 10.0:
        burn = burn * wm.dynamic_events.torch_burn.flood_modifier
    new_fuel = max(0, torch.fuel - int(max(1, burn)))
    if new_fuel <= 0:
        new_state, new_brightness = "extinguished", 0
    elif new_fuel <= TORCH_ALMOST_OUT_THRESHOLD:
        new_state, new_brightness = "almost_out", 10
    elif new_fuel <= TORCH_DIM_THRESHOLD:
        new_state, new_brightness = "dim", 40
    else:
        new_state, new_brightness = "lit", 80
    state_changed = new_state != torch.state
    effects.append(EventEffect(EFFECT_UPDATE_TORCH, {"fuel": new_fuel, "state": new_state, "brightness": new_brightness}, f"torch_decay_{turn}", f"Torch: {new_fuel}% ({new_state})"))
    if state_changed and new_state == "almost_out":
        effects.append(EventEffect(EFFECT_APPEND_HISTORY, {"event_id": f"torch_warn_{turn}", "category": "environmental", "description": "The torch gutters. Its light is almost gone.", "room_id": wm.player.current_room}, f"torch_warn_{turn}"))
    elif state_changed and new_state == "extinguished":
        effects.append(EventEffect(EFFECT_APPEND_HISTORY, {"event_id": f"torch_out_{turn}", "category": "environmental", "description": "The torch goes out. Darkness presses in.", "room_id": wm.player.current_room}, f"torch_out_{turn}", is_critical=True))
    return effects


def _evaluate_flood_progression(wm, turn):
    effects = []
    flood_state = wm.dynamic_events.flood
    phase_value = wm.world.temple_phase.value
    flood_puzzle = wm.puzzles.get("puzzle_flood_control")
    flood_triggered = flood_puzzle and flood_puzzle.current_progress.get("flood_triggered", False)
    flood_active = flood_state.active or bool(flood_triggered)

    if not flood_active and phase_value >= 3:
        flood_solved = flood_puzzle and flood_puzzle.status.value == "solved"
        if not flood_solved:
            effects.append(EventEffect(EFFECT_SET_FLOOD_ACTIVE, {"active": True, "start_turn": turn}, f"flood_begin_{turn}", "Flood begins.", is_critical=True))
            effects.append(EventEffect(EFFECT_APPEND_HISTORY, {"event_id": f"flood_begin_{turn}", "category": "environmental", "description": "Water begins seeping through the lower floors.", "room_id": wm.player.current_room}, f"flood_begin_{turn}", is_critical=True))
            return effects

    if not flood_active:
        return effects

    start_turn = flood_state.start_turn or turn
    turns_flooded = max(0, turn - start_turn)
    expected_stage = min(5, turns_flooded // FLOOD_TURNS_PER_LEVEL)
    current_stage = flood_state.current_stage
    if expected_stage <= current_stage:
        return effects

    new_stage = expected_stage
    try:
        new_flood_level = FloodLevel(new_stage)
    except ValueError:
        new_flood_level = FloodLevel(5)

    effects.append(EventEffect(EFFECT_SET_FLOOD_LEVEL, {"flood_level": new_flood_level, "stage": new_stage}, f"flood_rise_{new_stage}_{turn}", f"Flood level: stage {new_stage}", is_critical=True))

    rooms_to_flood = []
    for idx in range(current_stage, new_stage):
        if idx < len(FLOOD_ROOMS):
            rooms_to_flood.extend(FLOOD_ROOMS[idx])
    water_level = min(100.0, new_stage * 20.0)
    for room_id in rooms_to_flood:
        if room_id in wm.rooms:
            effects.append(EventEffect(EFFECT_SET_ROOM_WATER, {"room_id": room_id, "water_level": water_level}, f"flood_room_{room_id}_{turn}"))
    effects.append(EventEffect(EFFECT_SET_FLOOD_STATE, {"current_stage": new_stage, "affected_rooms": rooms_to_flood}, f"flood_state_{turn}"))
    effects.append(EventEffect(EFFECT_APPEND_HISTORY, {"event_id": f"flood_rise_{new_stage}_{turn}", "category": "environmental", "description": f"The water level rises. Stage {new_stage}/5.", "room_id": wm.player.current_room}, f"flood_rise_{new_stage}_{turn}", is_critical=True))
    return effects


def _evaluate_dust_accumulation(wm, turn):
    effects = []
    dust = wm.dynamic_events.dust
    rate = dust.accumulation_rate
    if wm.dynamic_events.flood.water_wheel_active:
        rate = rate * 0.5
    new_density = min(100.0, dust.global_density + rate)
    if abs(new_density - dust.global_density) < 0.01:
        return effects
    effects.append(EventEffect(EFFECT_SET_DUST_DENSITY, {"global_density": new_density}, f"dust_{turn}", f"Dust: {new_density:.1f}%"))
    if new_density > DUST_ROOM_THRESHOLD:
        for room_id, room in wm.rooms.items():
            if room.dust_level < new_density * 0.6:
                effects.append(EventEffect(EFFECT_SET_ROOM_DUST, {"room_id": room_id, "dust_level": new_density * 0.6}, f"room_dust_{room_id}_{turn}"))
    return effects


def _evaluate_bridge_integrity(wm, turn):
    effects = []
    if wm.world.temple_phase.value < 2:
        return effects
    bridge_state = wm.dynamic_events.bridge
    for bridge_id in BRIDGE_OBJECTS:
        if bridge_id in bridge_state.collapsed_bridges:
            continue
        cur = bridge_state.integrity.get(bridge_id, 100.0)
        new_i = max(0.0, cur - BRIDGE_DECAY_PER_TURN)
        if abs(new_i - cur) < 0.01:
            continue
        effects.append(EventEffect(EFFECT_UPDATE_BRIDGE, {"bridge_id": bridge_id, "integrity": new_i}, f"bridge_decay_{bridge_id}_{turn}", f"Bridge integrity: {new_i:.1f}"))
        if new_i <= BRIDGE_COLLAPSE_THRESHOLD and cur > BRIDGE_COLLAPSE_THRESHOLD:
            effects.append(EventEffect(EFFECT_UPDATE_OBJECT, {"object_id": bridge_id, "state": "collapsed", "condition": 0.0}, f"bridge_collapse_{bridge_id}_{turn}", is_critical=True))
            effects.append(EventEffect(EFFECT_APPEND_HISTORY, {"event_id": f"bridge_collapse_{bridge_id}_{turn}", "category": "environmental", "description": "The bridge rope snaps. The descent is no longer safe.", "room_id": wm.player.current_room}, f"bridge_collapse_{bridge_id}_{turn}", is_critical=True))
    return effects
'''

p = pathlib.Path('src/world/events.py')
p.write_text(p.read_text(encoding='utf-8') + CHUNK, encoding='utf-8')
print('events step2 ok, lines:', len(p.read_text(encoding='utf-8').splitlines()))
