"""
event_state.py — The Lost Temple of Rudra

Defines DynamicEventState tracking all active and historical environmental events.
The temple is alive through simulation, not randomness. Every event has a cause.

Part of the Persistent World Model (Chapter 10, Section 10.4.7).

Blueprint Reference:
    Chapter 13 — Dynamic Event Engine & Living Temple Simulation
    Chapter 10 — Section 10.4.7 — Dynamic Event State

READ-ONLY for all systems except the Game Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EventType(Enum):
    """
    Six major event categories. (Blueprint Chapter 13.4)
    """
    ENVIRONMENTAL = "environmental"    # Natural changes over time
    MECHANICAL = "mechanical"          # Ancient engineering events
    STORY = "story"                    # Narrative progression triggers
    EVALUATION = "evaluation"          # Triggered by player behaviour
    TIME = "time"                      # Triggered solely by elapsed turns
    COMBINED = "combined"              # Triggered by multiple conditions


class EventStatus(Enum):
    """
    Lifecycle of a single event instance.
    """
    PENDING = "pending"        # Conditions not yet met
    ACTIVE = "active"          # Currently in progress
    COMPLETED = "completed"    # Finished
    CANCELLED = "cancelled"    # Overridden by another event


@dataclass
class EventRecord:
    """
    An individual event instance — a snapshot of one specific occurrence.
    Stored in the append-only event history.

    Blueprint Reference: Chapter 10, Section 10.4.11 — Event History.
    """
    event_id: str = ""
    event_type: EventType = EventType.ENVIRONMENTAL
    description: str = ""
    turn: int = 0
    cause: str = ""               # What triggered this event
    affected_rooms: list[str] = field(default_factory=list)
    affected_objects: list[str] = field(default_factory=list)
    world_model_changes: dict = field(default_factory=dict)


@dataclass
class FloodState:
    """
    State of the temple's underground water and flood system.
    Blueprint Reference: Chapter 13.7 — Flood Simulation.
    """
    active: bool = False
    start_turn: Optional[int] = None
    current_stage: int = 0     # Maps to FloodLevel in world_state.py
    affected_rooms: list[str] = field(default_factory=list)
    flood_gates_open: list[str] = field(default_factory=list)
    water_wheel_active: bool = False


@dataclass
class TorchBurnState:
    """
    Global torch consumption rate, affected by environmental conditions.
    Blueprint Reference: Chapter 13.8 — Torch Simulation.
    """
    base_burn_rate: float = 1.0    # Fuel lost per turn (from game_settings.json)
    current_burn_rate: float = 1.0  # May increase near water
    flood_modifier: float = 1.5    # Multiplier when torch is wet


@dataclass
class DustState:
    """
    Dust accumulation system — passages become obscured over time.
    Blueprint Reference: Chapter 13.9 — Dust System.
    """
    global_density: float = 0.0   # 0.0–100.0
    accumulation_rate: float = 0.5  # Per turn
    rooms_affected: list[str] = field(default_factory=list)
    ventilation_active: bool = False


@dataclass
class BridgeEventState:
    """
    Bridge integrity tracking for all bridges.
    Blueprint Reference: Chapter 13.12 — Bridge Integrity.
    """
    # Maps bridge object ID to integrity float (0–100)
    integrity: dict[str, float] = field(default_factory=dict)
    collapsed_bridges: list[str] = field(default_factory=list)
    repaired_bridges: list[str] = field(default_factory=list)


@dataclass
class StatueResetState:
    """
    Tracks statue reset timers.
    Blueprint Reference: Chapter 13.11 — Statue Reset System.
    """
    # Maps statue object ID to the turn it was last rotated
    last_rotated: dict[str, int] = field(default_factory=dict)
    reset_after_turns: int = 20     # Default turns before a statue resets


@dataclass
class CollapseState:
    """
    Temple collapse progression.
    Blueprint Reference: Chapter 13.13 — Temple Collapse.
    """
    active: bool = False
    current_stage: int = 0     # 0 = none, 1–4 = collapse stages
    start_turn: Optional[int] = None
    escape_route_available: bool = True


@dataclass
class DynamicEventState:
    """
    Master container for all dynamic environmental event subsystems.

    Every event updates the World Model through the Game Engine.
    Nothing changes without being recorded here.

    Blueprint Reference: Chapter 10, Section 10.4.7 — Dynamic Event State.
    """

    flood: FloodState = field(default_factory=FloodState)
    torch_burn: TorchBurnState = field(default_factory=TorchBurnState)
    dust: DustState = field(default_factory=DustState)
    bridge: BridgeEventState = field(default_factory=BridgeEventState)
    statues: StatueResetState = field(default_factory=StatueResetState)
    collapse: CollapseState = field(default_factory=CollapseState)

    # --- Door states (dynamic changes) ---
    # Maps door object ID to its current DoorState string
    door_states: dict[str, str] = field(default_factory=dict)

    # --- Active event registry ---
    active_events: list[str] = field(default_factory=list)    # Active event IDs
    completed_events: list[str] = field(default_factory=list)  # Completed event IDs

    # --- Water gates ---
    # Maps flood gate object ID to open/closed state
    water_gates: dict[str, bool] = field(default_factory=dict)  # True = open
