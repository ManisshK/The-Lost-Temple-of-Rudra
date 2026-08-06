"""
events.py - The Lost Temple of Rudra
Dynamic event engine. Called by the Game Engine after every player turn.
Returns list[EventEffect]. The Game Engine applies all effects.
Blueprint Reference: Chapter 13 (Dynamic Event Engine)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from .world_model import WorldModel
from .world_state import FloodLevel, CollapseStage


@dataclass
class EventEffect:
    effect_type: str
    payload: Any
    event_id: str = ""
    description: str = ""
    is_critical: bool = False


# Effect type constants
EFFECT_SET_FLOOD_LEVEL = "set_flood_level"
EFFECT_SET_FLOOD_ACTIVE = "set_flood_active"
EFFECT_SET_COLLAPSE_STAGE = "set_collapse_stage"
EFFECT_SET_DUST_DENSITY = "set_dust_density"
EFFECT_SET_WORLD_STABILITY = "set_world_stability"
EFFECT_SET_ROOM_WATER = "set_room_water_level"
EFFECT_SET_ROOM_DUST = "set_room_dust_level"
EFFECT_OPEN_EXIT = "open_exit"
EFFECT_CLOSE_EXIT = "close_exit"
EFFECT_REVEAL_HIDDEN_PASSAGE = "reveal_hidden_passage"
EFFECT_UPDATE_OBJECT = "update_object_state"
EFFECT_UPDATE_BRIDGE = "update_bridge_integrity"
EFFECT_UPDATE_TORCH = "update_torch"
EFFECT_UPDATE_EVALUATION = "update_evaluation"
EFFECT_APPEND_HISTORY = "append_history"
EFFECT_MARK_EVENT_ACTIVE = "mark_event_active"
EFFECT_MARK_EVENT_COMPLETE = "mark_event_complete"
EFFECT_RESET_STATUE = "reset_statue"
EFFECT_SET_FLOOD_STATE = "set_flood_state"

# Configuration constants
TORCH_BASE_BURN_PER_TURN = 1
TORCH_DIM_THRESHOLD = 30
TORCH_ALMOST_OUT_THRESHOLD = 10
FLOOD_TURNS_PER_LEVEL = 15
FLOOD_ROOMS = [
    ["underground_reservoir", "water_channel_network"],
    ["flood_control_room", "bridge_of_echoes"],
    ["hidden_maintenance_tunnel"],
    ["ancient_machinery_chamber"],
    ["chamber_of_reflection"],
]
DUST_ACCUMULATION_PER_TURN = 0.2
DUST_ROOM_THRESHOLD = 60.0
BRIDGE_DECAY_PER_TURN = 0.5
BRIDGE_COLLAPSE_THRESHOLD = 10.0
BRIDGE_OBJECTS = ["bridge_rope"]
STATUE_RESET_AFTER_TURNS = 20
GUARDIAN_STATUE_IDS = ["statue_guardian_n","statue_guardian_e","statue_guardian_s","statue_guardian_w"]
COLLAPSE_TRIGGER_STABILITY = 40.0
COLLAPSE_TURNS_PER_STAGE = 20
EVENTS_PER_PHASE = {1: 1, 2: 2, 3: 3, 4: 4}


def _evaluate_torch_decay(wm, turn):
    effects = []
    torch = wm.player.torch
    if torch.state not in ("lit", "dim", "almost_out"):
        return effects
    burn = wm.dynamic_events.torch_burn.current_burn_rate
    room = wm.get_current_room()
    if room and room.water_level > 10.0:
        burn = burn * wm.dynamic_events.torch_burn.flood_modifier
    new_fuel = max(0, torch.fuel - int(round(max(1, burn))))
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

    start_turn = flood_state.start_turn if flood_state.start_turn is not None else turn
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
