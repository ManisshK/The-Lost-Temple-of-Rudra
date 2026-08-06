"""
puzzle_state.py — The Lost Temple of Rudra

Defines PuzzleState representing the persistent state of every puzzle in the temple.
Puzzles never lose their history — every attempt, hint, and partial solution is remembered.

Part of the Persistent World Model (Chapter 10, Section 10.4.5).

Blueprint Reference:
    Chapter 6  — Room Design Bible (puzzle definitions per room)
    Chapter 10 — Section 10.4.5 — Puzzle State

READ-ONLY for all systems except the Game Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PuzzleCategory(Enum):
    """
    Six puzzle categories. (Blueprint Chapter 6, Puzzle System)
    """
    OBSERVATION = "observation"      # Requires inspecting the environment
    LOGIC = "logic"                  # Requires connecting discovered information
    ENVIRONMENTAL = "environmental"  # Uses the environment as the mechanism
    MEMORY = "memory"                # Requires recalling earlier discoveries
    DYNAMIC = "dynamic"              # Solution changes with world state
    FINAL_JUDGMENT = "final_judgment"  # Evaluates the entire journey


class PuzzleStatus(Enum):
    """
    Lifecycle state of a puzzle.
    """
    LOCKED = "locked"          # Prerequisites not yet met
    AVAILABLE = "available"    # Ready to be attempted
    IN_PROGRESS = "in_progress"
    SOLVED = "solved"
    FAILED = "failed"          # Non-fatal failure state (consequences applied)
    RESET = "reset"            # Puzzle reset after a dynamic event


@dataclass
class PuzzleState:
    """
    Persistent state for a single temple puzzle.

    The temple evaluates HOW puzzles are solved, not merely IF they are solved.
    Attempt count, hint usage, and time spent all contribute to Guardian Evaluation.

    Blueprint Reference: Chapter 10, Section 10.4.5 — Puzzle State.
    """

    puzzle_id: str = ""
    room_id: str = ""
    category: PuzzleCategory = PuzzleCategory.OBSERVATION
    status: PuzzleStatus = PuzzleStatus.LOCKED

    # --- Attempt tracking ---
    attempt_count: int = 0
    failure_count: int = 0
    first_attempted_turn: Optional[int] = None
    solved_turn: Optional[int] = None

    # --- Progress ---
    current_progress: dict = field(default_factory=dict)
    # e.g. {"statues_correct": 2, "statues_total": 4}

    # --- Hints ---
    hint_level: int = 0       # 0 = no hints used, higher = more assistance used
    hint_count: int = 0       # Total number of hints requested

    # --- Dependencies ---
    required_knowledge: list[str] = field(default_factory=list)  # Lore IDs needed
    required_objects: list[str] = field(default_factory=list)    # Object IDs needed
    prerequisite_puzzle_ids: list[str] = field(default_factory=list)

    # --- Outcomes ---
    reward_given: bool = False
    reward_id: Optional[str] = None  # Object ID or lore ID awarded on completion

    # --- World impact ---
    world_model_changes: dict = field(default_factory=dict)
    # e.g. {"hidden_passage_to_library": True, "flood_gate_unlocked": True}

    # --- Evaluation ---
    observation_before_action: bool = False  # Did player inspect before interacting?
    solved_without_hints: bool = True
    time_to_solve_turns: Optional[int] = None

    # --- Failure history ---
    failure_history: list[str] = field(default_factory=list)
    # e.g. ["wrong_statue_direction_turn_15", "flood_triggered_turn_22"]
