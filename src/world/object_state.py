"""
object_state.py — The Lost Temple of Rudra

Defines ObjectState and related enums representing the persistent state of every
object inside the temple. Object state always lives in the World Model — never
stored independently by other systems.

Part of the Persistent World Model (Chapter 10, Section 10.4.4).

Blueprint Reference:
    Chapter 7  — Object System
    Chapter 10 — Section 10.4.4 — Object State

READ-ONLY for all systems except the Game Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ObjectCategory(Enum):
    """
    Seven object categories. (Blueprint Chapter 7.3)
    """
    COLLECTIBLE = "collectible"    # Can be carried in inventory
    INTERACTIVE = "interactive"    # Remains in room; changes state
    STORY = "story"                # Communicates lore; read-only interaction
    ENVIRONMENTAL = "environmental"  # Participates in dynamic simulation
    PUZZLE = "puzzle"              # Required for puzzle interaction
    SYMBOLIC = "symbolic"          # Reinforces temple philosophy
    GUARDIAN = "guardian"          # Final chamber only; never collectible


# --- Object-specific state enums ---

class TorchState(Enum):
    UNLIT = "unlit"
    LIT = "lit"
    DIM = "dim"
    ALMOST_OUT = "almost_out"
    EXTINGUISHED = "extinguished"
    WET = "wet"
    DESTROYED = "destroyed"


class KeyState(Enum):
    UNUSED = "unused"
    USED = "used"
    INSERTED = "inserted"
    RECOVERED = "recovered"
    LOST = "lost"


class StatueDirection(Enum):
    NORTH = "north"
    EAST = "east"
    SOUTH = "south"
    WEST = "west"


class StatueState(Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    LOCKED = "locked"
    UNLOCKED = "unlocked"


class ScrollState(Enum):
    UNDISCOVERED = "undiscovered"
    DISCOVERED = "discovered"
    READ = "read"
    TRANSLATED = "translated"
    REFERENCED = "referenced"


class FloodGateState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    BLOCKED = "blocked"
    DAMAGED = "damaged"
    REPAIRED = "repaired"


class BridgeIntegrity(Enum):
    STABLE = "stable"
    WEATHERED = "weathered"
    WEAK = "weak"
    CRITICAL = "critical"
    COLLAPSED = "collapsed"
    REPAIRED = "repaired"


class DoorState(Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    OPEN = "open"
    CLOSED = "closed"
    SEALED = "sealed"
    BROKEN = "broken"


@dataclass
class ObjectState:
    """
    Persistent state for a single object inside the temple.

    Every object — from a torch to the Eye of Rudra — is represented here.
    Object state never lives outside the World Model.

    Blueprint Reference: Chapter 10, Section 10.4.4 — Object State.

    Example (Torch):
        object_id  = "torch_entrance"
        category   = ObjectCategory.COLLECTIBLE
        state      = TorchState.LIT.value
        current_room = None (held by player when in inventory)
        current_owner = "player"
        condition  = 64.0  (fuel percentage)
    """

    object_id: str = ""
    name: str = ""
    category: ObjectCategory = ObjectCategory.INTERACTIVE

    # --- Location ---
    current_room: Optional[str] = None    # None when held in inventory
    current_owner: Optional[str] = None   # "player" or None

    # --- Condition ---
    condition: float = 100.0              # 0.0 (destroyed) – 100.0 (perfect)
    state: str = ""                       # Enum value as string for flexibility

    # --- Visibility ---
    visible: bool = True
    discoverable: bool = True             # False = only findable through puzzle/event

    # --- Interactability ---
    interactable: bool = True
    destroyed: bool = False
    activated: bool = False

    # --- Usage tracking ---
    usage_history: list[str] = field(default_factory=list)
    # e.g. ["inspected_turn_5", "rotated_turn_12"]

    # --- Dependencies ---
    required_objects: list[str] = field(default_factory=list)
    unlocks: list[str] = field(default_factory=list)  # Object or room IDs this unlocks

    # --- Puzzle & story relevance ---
    puzzle_id: Optional[str] = None    # Puzzle this object belongs to
    story_importance: str = ""         # Brief lore note for AI context

    # --- Statue-specific (populated only for statue objects) ---
    facing_direction: Optional[StatueDirection] = None
    rotation_count: int = 0
    last_rotated_turn: Optional[int] = None

    # --- Scroll-specific ---
    content_id: Optional[str] = None   # References lore entry in data/lore/
