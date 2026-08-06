import pathlib

PUZZLES_PY = r'''"""
puzzles.py - The Lost Temple of Rudra
Canonical puzzle definitions and PuzzleRegistry.
Blueprint Reference: Chapter 6, Chapter 10.4.5
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from src.world.world_model import WorldModel
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
'''

pathlib.Path('src/world/puzzles.py').write_text(PUZZLES_PY, encoding='utf-8')
print('step1 ok')
