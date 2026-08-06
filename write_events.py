import pathlib

EVENTS_PART1 = r'''"""
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
'''

pathlib.Path('src/world/events.py').write_text(EVENTS_PART1, encoding='utf-8')
print('events step1 ok, lines:', len(EVENTS_PART1.splitlines()))
