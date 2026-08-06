"""
mission_state.py — The Lost Temple of Rudra

Defines MissionState tracking all player objectives throughout the journey.
Missions evolve naturally with story progression — never through menus.

Part of the Persistent World Model (Chapter 10, Section 10.4.10).

Blueprint Reference:
    Chapter 10 — Section 10.4.10 — Mission State
    Chapter 12 — Section 12.4.5 — Mission Tracking (Explorer AI)

READ-ONLY for all systems except the Game Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MissionStatus(Enum):
    """
    Lifecycle of a mission objective.
    """
    INACTIVE = "inactive"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"    # Non-fatal — alternate path activated


@dataclass
class Objective:
    """
    A single mission objective — primary, secondary, or optional.
    """
    objective_id: str = ""
    description: str = ""
    status: MissionStatus = MissionStatus.INACTIVE
    assigned_turn: Optional[int] = None
    completed_turn: Optional[int] = None
    region_hint: str = ""          # Vague directional hint for Explorer AI
    required_for_ending: bool = False


@dataclass
class MissionState:
    """
    Complete mission tracking for the explorer's journey.

    Primary objective is always singular — the most important current goal.
    Secondary objectives are supporting tasks.
    Optional discoveries reward exploration without blocking progress.

    Blueprint Reference: Chapter 10, Section 10.4.10 — Mission State.

    Example progression:
        Turn 1  → "Explore the temple entrance."
        Turn 10 → "Reach the Hall of Echoes."
        Turn 25 → "Investigate the Ancient Library."
        Turn 60 → "Find a way past the flooded corridor."
        Turn 90 → "Reach the Final Chamber."
    """

    primary_objective: Optional[Objective] = None
    secondary_objectives: list[Objective] = field(default_factory=list)
    optional_discoveries: list[Objective] = field(default_factory=list)

    completed_objectives: list[str] = field(default_factory=list)  # Objective IDs
    failed_objectives: list[str] = field(default_factory=list)     # Objective IDs

    current_goal_description: str = "Explore the temple."
    current_region_focus: str = "outer_temple"
