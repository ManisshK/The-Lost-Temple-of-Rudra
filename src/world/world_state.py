"""
world_state.py — The Lost Temple of Rudra

Defines the WorldState dataclass representing the global condition of the temple.
Part of the Persistent World Model (Chapter 10, Section 10.4.2).

READ-ONLY for all systems except the Game Engine.
"""

from dataclasses import dataclass, field
from enum import Enum


class TemplePhase(Enum):
    """
    Macro game phase controlling event density and environmental pressure.

    Blueprint Reference: Chapter 4.13 — Progression Through the Temple.
        DISCOVERY   — Region I.  Stable. Minimal dynamic events.
        UNDERSTANDING — Region II. Puzzles interconnect. Events begin.
        ADAPTATION  — Region III. Temple actively evolves. Floods, decay.
        JUDGMENT    — Region IV.  Final evaluation. Collapse sequence.
    """
    DISCOVERY = 1
    UNDERSTANDING = 2
    ADAPTATION = 3
    JUDGMENT = 4


class FloodLevel(Enum):
    """
    Represents the current water level throughout the temple.

    Blueprint Reference: Chapter 13.7 — Flood Simulation.
    """
    DRY = 0
    MOIST = 1
    SHALLOW = 2
    FLOODED = 3
    HIGH = 4
    CRITICAL = 5


class CollapseStage(Enum):
    """
    Tracks temple structural collapse progression.

    Blueprint Reference: Chapter 13.13 — Temple Collapse.
        NONE     — Normal operation.
        MINOR    — Vibrations, dust falls, small cracks.
        MODERATE — Machinery stops, doors malfunction, bridges weaken.
        SEVERE   — Flood spreads rapidly, walls fracture.
        CRITICAL — Massive collapse, escape routes narrow.
    """
    NONE = 0
    MINOR = 1
    MODERATE = 2
    SEVERE = 3
    CRITICAL = 4


@dataclass
class WorldState:
    """
    Global condition of the Lost Temple of Rudra.

    Represents the temple as a living system independent of the explorer's actions.
    The world continues evolving whether or not the player acts.

    Blueprint Reference: Chapter 10, Section 10.4.2 — World State.
    """

    # --- Temporal ---
    current_turn: int = 0
    current_chapter: int = 1        # Story chapter 1–13 (Blueprint Chapter 2)

    # --- Phase ---
    temple_phase: TemplePhase = TemplePhase.DISCOVERY

    # --- Environmental conditions ---
    flood_level: FloodLevel = FloodLevel.DRY
    collapse_stage: CollapseStage = CollapseStage.NONE
    dust_density: float = 0.0       # 0.0 (clean) – 100.0 (completely obscured)
    ambient_light: float = 80.0     # 0.0 (pitch black) – 100.0 (fully illuminated)
    world_stability: float = 100.0  # 100.0 (stable) → 0.0 (collapsing)

    # --- Temple intelligence indicators ---
    temple_awareness: float = 0.0   # 0–100. Rises as explorer triggers significant events.
    temple_alert_level: int = 0     # 0 = passive, 1 = attentive, 2 = active, 3 = urgent

    # --- Time cycle (optional atmospheric system) ---
    time_cycle: str = "day"         # day | dusk | night | dawn
