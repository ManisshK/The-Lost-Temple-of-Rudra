import pathlib

PART1 = r'''"""
test_phase5.py - The Lost Temple of Rudra

Tests for Phase 5: Puzzle System + Dynamic Event Engine.

Covers:
    Puzzle framework:
        - PuzzleDefinition and PuzzleRegistry structure
        - PuzzleAttemptResult fields
        - PuzzleRegistry.attempt(): solved/locked/prereq/missing-object guards
        - Guardian statues: rotate, partial progress, full solve, recklessness
        - Flood control: wrong order triggers flood, correct sequence solves
        - Bridge: rope descent, crossing degrades integrity
        - Symbol alignment: wrong order resets, correct order solves
        - Clear rubble: missing chisel, correct use solves
        - Reflection pool: inspect-then-meditate sequence
        - Final judgment: composite score gate

    Dynamic events:
        - Torch decay each turn
        - Torch state transitions (lit -> dim -> almost_out -> extinguished)
        - Flood progression: auto-trigger at phase 3, stage advance
        - Flood: solved puzzle prevents auto-trigger
        - Dust accumulation
        - Bridge integrity decay (phase 2+)
        - Statue reset timer
        - Hidden passage activation
        - evaluate_events() never raises

    Game Engine integration:
        - Puzzle dispatch routes to registry
        - Puzzle solve opens exit in World Model
        - Puzzle failure records in history
        - Event effects applied after turn
        - Torch fuel decrements after each turn
        - World Model validates after puzzle + event operations
        - Serialization round-trip after puzzle solve
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from world.world_model import WorldModel
from world.room_state import RoomState, RoomRegion
from world.object_state import ObjectState, ObjectCategory, StatueDirection
from world.puzzle_state import PuzzleState, PuzzleCategory, PuzzleStatus
from world.player_state import TorchStatus
from world.world_state import TemplePhase, FloodLevel
from world.event_state import DynamicEventState
from world.puzzles import (
    PuzzleRegistry, PuzzleDefinition, PuzzleAttemptResult,
    PUZZLE_DEFINITIONS, PUZZLE_VALIDATORS,
)
from world.events import (
    evaluate_events, EventEffect,
    _evaluate_torch_decay, _evaluate_flood_progression,
    _evaluate_dust_accumulation, _evaluate_bridge_integrity,
    _evaluate_statue_reset, _evaluate_hidden_passage_activation,
    EFFECT_UPDATE_TORCH, EFFECT_SET_FLOOD_LEVEL, EFFECT_SET_FLOOD_ACTIVE,
    EFFECT_SET_DUST_DENSITY, EFFECT_UPDATE_BRIDGE, EFFECT_RESET_STATUE,
    EFFECT_REVEAL_HIDDEN_PASSAGE, EFFECT_OPEN_EXIT,
)
from engine.game_engine import GameEngine
from engine.command_result import ResultStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _world_with_room(room_id="temple_entrance"):
    wm = WorldModel()
    wm.rooms[room_id] = RoomState(room_id=room_id)
    wm.player.current_room = room_id
    return wm


def _statues_world():
    """WorldModel with hall_of_guardians puzzle fully set up."""
    wm = WorldModel()
    wm.rooms["hall_of_guardians"] = RoomState(
        room_id="hall_of_guardians",
        region=RoomRegion.OUTER_TEMPLE,
        accessible_exits={},
        puzzle_id="puzzle_guardian_statues",
    )
    wm.player.current_room = "hall_of_guardians"
    wm.puzzles["puzzle_guardian_statues"] = PuzzleState(
        puzzle_id="puzzle_guardian_statues",
        room_id="hall_of_guardians",
        category=PuzzleCategory.LOGIC,
        status=PuzzleStatus.AVAILABLE,
    )
    NAMES = {
        "statue_guardian_n": ("Northern Guardian Statue", StatueDirection.NORTH),
        "statue_guardian_e": ("Eastern Guardian Statue", StatueDirection.EAST),
        "statue_guardian_s": ("Southern Guardian Statue", StatueDirection.SOUTH),
        "statue_guardian_w": ("Western Guardian Statue", StatueDirection.WEST),
    }
    for sid, (name, facing) in NAMES.items():
        wm.objects[sid] = ObjectState(
            object_id=sid, name=name,
            category=ObjectCategory.PUZZLE,
            current_room="hall_of_guardians",
            facing_direction=facing,
        )
        wm.rooms["hall_of_guardians"].object_ids_present.append(sid)
    return wm


def _flood_world():
    """WorldModel with flood_control_room puzzle set up."""
    wm = WorldModel()
    wm.rooms["flood_control_room"] = RoomState(
        room_id="flood_control_room", region=RoomRegion.LIVING_TEMPLE,
        accessible_exits={}, puzzle_id="puzzle_flood_control",
    )
    wm.player.current_room = "flood_control_room"
    wm.puzzles["puzzle_flood_control"] = PuzzleState(
        puzzle_id="puzzle_flood_control", room_id="flood_control_room",
        category=PuzzleCategory.ENVIRONMENTAL, status=PuzzleStatus.AVAILABLE,
    )
    for oid, name in [("flood_gate_secondary", "Secondary Flood Gate"),
                      ("flood_gate_main", "Main Flood Gate"),
                      ("lever_flood_control", "Flood Control Lever"),
                      ("water_wheel", "Ancient Water Wheel")]:
        wm.objects[oid] = ObjectState(
            object_id=oid, name=name, category=ObjectCategory.ENVIRONMENTAL,
            current_room="flood_control_room", state="closed",
        )
        wm.rooms["flood_control_room"].object_ids_present.append(oid)
    # Give player the wrench
    wm.objects["tool_wrench"] = ObjectState(
        object_id="tool_wrench", name="Stone Wrench",
        category=ObjectCategory.COLLECTIBLE, current_owner="player",
    )
    wm.player.inventory.append("tool_wrench")
    return wm
'''

pathlib.Path('tests/test_phase5.py').write_text(PART1, encoding='utf-8')
print('part1 ok, lines:', len(PART1.splitlines()))
