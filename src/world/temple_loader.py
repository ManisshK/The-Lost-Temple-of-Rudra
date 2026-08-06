"""
temple_loader.py — The Lost Temple of Rudra

Wires the complete room graph and object set into a fresh WorldModel.

This is the single entry point for starting a new game:

    from src.world.temple_loader import load_temple
    world_model = load_temple()

Responsibilities:
    1. Call build_world_rooms() to create all 24 RoomState instances.
    2. Call build_world_objects() to create all ObjectState instances.
    3. Set the player's starting room to temple_entrance.
    4. Register all puzzle states using canonical categories and statuses.
    5. Set the initial mission objective.
    6. Return the fully initialised WorldModel.

The Game Engine is the only system that writes to the World Model after
this point. The loader is a one-time initialisation helper.

Blueprint Reference:
    Chapter 5  — Temple Layout
    Chapter 10 — Section 10.4 — World Model Structure
    Chapter 20 — Phase 4 — Room System + Object System
"""

from __future__ import annotations

from .world_model import WorldModel
from .rooms import build_world_rooms, ROOM_DEFINITIONS
from .objects import build_world_objects
from .puzzle_state import PuzzleState, PuzzleCategory, PuzzleStatus
from .puzzles import PUZZLE_DEFINITIONS


def load_temple() -> WorldModel:
    """
    Build and return a fully initialised WorldModel for a new game.

    Populates:
        - All 24 canonical rooms with their default accessibility
        - All temple objects placed in their starting rooms
        - Player positioned at temple_entrance
        - All puzzle states with correct categories and initial status
        - Initial mission goal

    Returns:
        A fresh WorldModel ready to be handed to the GameEngine.
    """
    wm = WorldModel()

    # 1. Load all rooms into the World Model
    wm.rooms = build_world_rooms()

    # 2. Load all objects into the World Model
    wm.objects = build_world_objects()

    # 3. Player starts at the temple entrance
    wm.player.current_room = "temple_entrance"
    wm.player.visited_rooms = []
    wm.player.movement_history = []

    # 4. Register puzzle states for every room that declares a puzzle_id.
    _register_puzzles(wm)

    # 5. Set initial mission
    wm.mission.current_goal_description = (
        "Explore the Temple Entrance and find out what lies within."
    )
    wm.mission.current_region_focus = "outer_temple"

    return wm


def _register_puzzles(wm: WorldModel) -> None:
    """
    Register a PuzzleState for every room that declares a puzzle_id.

    Puzzles with a canonical PuzzleDefinition get their real category.
    Remaining room puzzles get placeholder OBSERVATION stubs so the
    World Model validates correctly.
    """
    for rd in ROOM_DEFINITIONS.values():
        if not rd.puzzle_id:
            continue
        if rd.puzzle_id in wm.puzzles:
            continue

        defn = PUZZLE_DEFINITIONS.get(rd.puzzle_id)
        if defn:
            wm.puzzles[rd.puzzle_id] = PuzzleState(
                puzzle_id=rd.puzzle_id,
                room_id=rd.room_id,
                category=defn.category,
                status=PuzzleStatus.AVAILABLE,
                required_objects=list(defn.required_objects),
                required_knowledge=list(defn.required_knowledge),
                prerequisite_puzzle_ids=list(defn.prerequisite_puzzle_ids),
                reward_id=defn.reward_id,
            )
        else:
            # Stub for puzzles not yet fully defined
            wm.puzzles[rd.puzzle_id] = PuzzleState(
                puzzle_id=rd.puzzle_id,
                room_id=rd.room_id,
                category=PuzzleCategory.OBSERVATION,
                status=PuzzleStatus.AVAILABLE,
            )
