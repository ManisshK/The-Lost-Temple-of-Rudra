"""
player_state.py — The Lost Temple of Rudra

Defines the PlayerState dataclass representing everything known about the explorer.
Part of the Persistent World Model (Chapter 10, Section 10.4.1).

READ-ONLY for all systems except the Game Engine.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TorchStatus:
    """
    Tracks the explorer's torch state.

    The torch symbolises knowledge — its gradual extinguishing represents
    fading understanding. (Blueprint Chapter 7.5)
    """
    state: str = "unlit"          # unlit | lit | dim | almost_out | extinguished | wet | destroyed
    fuel: int = 100               # 0–100 percentage
    brightness: int = 0          # 0–100 effective light radius
    last_lit_turn: Optional[int] = None  # Turn number the torch was last lit


@dataclass
class PlayerScores:
    """
    Behavioural metrics tracked continuously throughout the journey.
    These contribute directly to the Guardian Evaluation and final judgment.
    (Blueprint Chapter 10.4.1)
    """
    observation: float = 0.0     # Rewards inspecting, reading, listening
    curiosity: float = 0.0       # Rewards exploring optional areas, examining objects
    adaptation: float = 0.0      # Rewards responding to environmental changes
    knowledge: float = 0.0       # Rewards reading scrolls, translating inscriptions
    guardian: float = 0.0        # Composite score used in final judgment


@dataclass
class PlayerState:
    """
    Complete state of the explorer at any point in time.

    Stores position, movement history, inventory references, torch status,
    behavioural scores, and command history.

    Blueprint Reference: Chapter 10, Section 10.4.1 — Player State.
    """

    # --- Position ---
    current_room: str = "temple_entrance"
    previous_room: Optional[str] = None

    # --- Navigation history ---
    visited_rooms: list[str] = field(default_factory=list)
    movement_history: list[str] = field(default_factory=list)  # Ordered list of room IDs

    # --- Inventory ---
    # Stores object IDs of carried items. Actual object state lives in ObjectState.
    inventory: list[str] = field(default_factory=list)

    # --- Resources ---
    torch: TorchStatus = field(default_factory=TorchStatus)

    # --- Metrics ---
    steps_taken: int = 0
    turns_elapsed: int = 0

    # --- Behavioural scores ---
    scores: PlayerScores = field(default_factory=PlayerScores)

    # --- Mission ---
    active_mission_id: Optional[str] = None

    # --- Command history (last N commands for AI context) ---
    command_history: list[str] = field(default_factory=list)

    # --- Health (optional — blueprint marks as optional) ---
    health: Optional[int] = None
