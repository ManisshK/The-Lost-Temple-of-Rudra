"""
room_state.py — The Lost Temple of Rudra

Defines the RoomState dataclass representing the dynamic condition of a single room.
The physical layout of rooms never changes — only their state does.

Part of the Persistent World Model (Chapter 10, Section 10.4.3).

Blueprint Reference:
    Chapter 5  — Temple Layout & World Design
    Chapter 6  — Room Design Bible
    Chapter 10 — Section 10.4.3 — Room State

READ-ONLY for all systems except the Game Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RoomRegion(Enum):
    """
    The four major temple regions. (Blueprint Chapter 5.3)
    """
    OUTER_TEMPLE = "outer_temple"
    KNOWLEDGE_SANCTUM = "knowledge_sanctum"
    LIVING_TEMPLE = "living_temple"
    GUARDIAN_CORE = "guardian_core"


class LightLevel(Enum):
    """
    Visibility state of a room based on torch and ambient conditions.
    """
    BRIGHT = "bright"
    NORMAL = "normal"
    DIM = "dim"
    DARK = "dark"
    PITCH_BLACK = "pitch_black"


@dataclass
class RoomState:
    """
    Dynamic state of a single temple room.

    Every room is always present in the World Model.
    Only its state changes — rooms never disappear.

    Blueprint Reference: Chapter 10, Section 10.4.3 — Room State.

    Canonical room IDs:
        temple_entrance, hall_of_echoes, hall_of_guardians,
        chamber_of_inscriptions, first_meditation_hall,
        ancient_library, archive_vault, symbol_gallery,
        astronomers_chamber, statue_gallery, chamber_of_maps,
        forgotten_classroom, bridge_of_echoes, flood_control_room,
        underground_reservoir, water_channel_network, collapsed_hallway,
        ancient_machinery_chamber, hidden_maintenance_tunnel,
        chamber_of_reflection, hall_of_judgment, guardian_archive,
        throne_approach, final_chamber
    """

    room_id: str = ""
    region: RoomRegion = RoomRegion.OUTER_TEMPLE

    # --- Exploration ---
    visited: bool = False
    visit_count: int = 0
    first_visited_turn: Optional[int] = None

    # --- Environment ---
    light_level: LightLevel = LightLevel.NORMAL
    water_level: float = 0.0          # 0.0 (dry) – 100.0 (fully flooded)
    dust_level: float = 0.0           # 0.0 (clean) – 100.0 (completely obscured)
    environmental_damage: float = 0.0 # 0.0 (intact) – 100.0 (destroyed)

    # --- Objects ---
    object_ids_present: list[str] = field(default_factory=list)  # Object IDs currently in room

    # --- Puzzles ---
    puzzle_id: Optional[str] = None   # ID of the puzzle in this room (if any)
    puzzle_solved: bool = False

    # --- Connectivity ---
    # Static connections defined in rooms.py — accessibility is dynamic
    accessible_exits: dict[str, bool] = field(default_factory=dict)
    # e.g. {"north": True, "east": False, "hidden_passage": False}

    # --- Hidden passages ---
    hidden_passages: dict[str, bool] = field(default_factory=dict)
    # e.g. {"passage_to_reservoir": False}  — True when discovered/accessible

    # --- Story & lore ---
    symbols_found: list[str] = field(default_factory=list)  # e.g. ["eye", "flame"]
    lore_discovered: list[str] = field(default_factory=list)  # Lore IDs found here
    story_progress: int = 0  # Narrative milestone counter for this room

    # --- Temple AI tracking ---
    times_inspected: int = 0
    ambient_effects_active: list[str] = field(default_factory=list)
