"""
world_model.py — The Lost Temple of Rudra

THE SINGLE SOURCE OF TRUTH for the entire game.

The World Model aggregates all eleven state sections into one authoritative container.
Every room, object, puzzle, event, player decision, and evaluation score exists here.

ACCESS RULES (immutable architectural constraint):
    WRITE → Game Engine ONLY, via update methods defined in this module.
    READ  → All systems, via read methods or get_snapshot().

"The temple does not remember your name. It remembers your choices."

Blueprint Reference:
    Chapter 10 — Persistent World Model Architecture
    Chapter 15 — Software Architecture (Section 15.4 — Core Software Modules)
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    # Imported at runtime only when methods are called, preventing circular imports
    # during the dataclass field resolution phase.
    from .serializer import WorldModelDeserializationError  # noqa: F401
    from .validator import ValidationResult, WorldModelValidationError  # noqa: F401

from .player_state import PlayerState
from .world_state import WorldState
from .room_state import RoomState
from .object_state import ObjectState
from .puzzle_state import PuzzleState
from .story_state import StoryState
from .event_state import DynamicEventState
from .evaluation_state import TempleEvaluation
from .mission_state import MissionState
from .history_state import HistoryState, HistoryEntry


# ---------------------------------------------------------------------------
# AI Context — sanitised read-only snapshot for AI systems
# ---------------------------------------------------------------------------

@dataclass
class AIContext:
    """
    A filtered, sanitised snapshot of the World Model provided to AI systems.

    Contains only the information relevant to the current interaction.
    Excludes: puzzle solutions, future room states, judgment thresholds,
    hidden passages not yet discovered, and any information the player
    has not yet earned.

    Both the Temple AI and Explorer AI receive this — never the full model.
    Blueprint Reference: Chapter 10, Section 10.4.9 — AI Context.
    """
    current_room: str = ""
    adjacent_rooms: list[str] = field(default_factory=list)
    room_description_hint: str = ""
    nearby_object_ids: list[str] = field(default_factory=list)
    inventory: list[str] = field(default_factory=list)
    torch_state: str = ""
    torch_fuel: int = 0
    active_mission: str = ""
    current_puzzle_id: Optional[str] = None
    recent_history: list[dict] = field(default_factory=list)  # Last 10 entries
    dynamic_events_active: list[str] = field(default_factory=list)
    flood_level: str = ""
    temple_phase: str = ""
    temple_awareness: float = 0.0
    evaluation_summary: dict = field(default_factory=dict)
    # e.g. {"observation": 87, "curiosity": 91}  — rounded for AI
    known_symbols: list[str] = field(default_factory=list)
    chapters_reached: list[int] = field(default_factory=list)
    recent_commands: list[str] = field(default_factory=list)  # Last 5 commands


# ---------------------------------------------------------------------------
# World Model
# ---------------------------------------------------------------------------

@dataclass
class WorldModel:
    """
    The Persistent World Model — aggregates all eleven state sections.

    This is the only permanent state container in the game.
    Instantiated once at game start and persisted across the entire session.

    Sections:
        1.  player         — PlayerState
        2.  world          — WorldState
        3.  rooms          — dict[room_id, RoomState]
        4.  objects        — dict[object_id, ObjectState]
        5.  inventory      — managed through player.inventory (list of object IDs)
        6.  puzzles        — dict[puzzle_id, PuzzleState]
        7.  story          — StoryState
        8.  dynamic_events — DynamicEventState
        9.  evaluation     — TempleEvaluation
        10. ai_context     — AIContext (computed, not stored permanently)
        11. mission        — MissionState
        +   history        — HistoryState (append-only event log)

    Blueprint Reference: Chapter 10.4 — World Model Structure.
    """

    # --- Section 1 ---
    player: PlayerState = field(default_factory=PlayerState)

    # --- Section 2 ---
    world: WorldState = field(default_factory=WorldState)

    # --- Section 3: rooms ---
    # Keyed by canonical room_id string (e.g. "hall_of_echoes")
    rooms: dict[str, RoomState] = field(default_factory=dict)

    # --- Section 4: objects ---
    # Keyed by canonical object_id string (e.g. "torch_entrance")
    objects: dict[str, ObjectState] = field(default_factory=dict)

    # Section 5 (inventory) is managed through player.inventory

    # --- Section 6: puzzles ---
    # Keyed by canonical puzzle_id string (e.g. "puzzle_guardian_statues")
    puzzles: dict[str, PuzzleState] = field(default_factory=dict)

    # --- Section 7 ---
    story: StoryState = field(default_factory=StoryState)

    # --- Section 8 ---
    dynamic_events: DynamicEventState = field(default_factory=DynamicEventState)

    # --- Section 9 ---
    evaluation: TempleEvaluation = field(default_factory=TempleEvaluation)

    # Section 10 (ai_context) is computed on demand — see get_ai_context()

    # --- Section 11 ---
    mission: MissionState = field(default_factory=MissionState)

    # --- Bonus: event history (append-only log) ---
    history: HistoryState = field(default_factory=HistoryState)

    # ---------------------------------------------------------------------------
    # READ INTERFACE — available to all systems
    # ---------------------------------------------------------------------------

    def get_snapshot(self) -> WorldModel:
        """
        Returns a deep copy of the World Model for safe read-only access.
        Systems that need to inspect multiple fields without risk of mutation
        should use this method.
        """
        return copy.deepcopy(self)

    def get_room(self, room_id: str) -> Optional[RoomState]:
        """Returns the state of a specific room, or None if not found."""
        return self.rooms.get(room_id)

    def get_object(self, object_id: str) -> Optional[ObjectState]:
        """Returns the state of a specific object, or None if not found."""
        return self.objects.get(object_id)

    def get_puzzle(self, puzzle_id: str) -> Optional[PuzzleState]:
        """Returns the state of a specific puzzle, or None if not found."""
        return self.puzzles.get(puzzle_id)

    def get_current_room(self) -> Optional[RoomState]:
        """Returns the state of the room the explorer currently occupies."""
        return self.rooms.get(self.player.current_room)

    def get_inventory_objects(self) -> list[ObjectState]:
        """Returns ObjectState for every item currently in the player's inventory."""
        return [
            self.objects[oid]
            for oid in self.player.inventory
            if oid in self.objects
        ]

    def get_ai_context(self) -> AIContext:
        """
        Builds and returns a sanitised AIContext snapshot.

        Excludes hidden information the player has not earned:
        - Undiscovered hidden passages
        - Puzzle solutions
        - Future story events
        - Judgment thresholds
        - Any object or room not yet encountered

        Both Temple AI and Explorer AI must use this method exclusively.
        Neither receives direct access to the full World Model.
        """
        current_room = self.get_current_room()

        # Only expose accessible, discovered exits
        adjacent_rooms: list[str] = []
        if current_room:
            adjacent_rooms = [
                room_id
                for room_id, accessible in current_room.accessible_exits.items()
                if accessible
            ]

        # Only expose visible objects in the current room
        nearby_object_ids: list[str] = []
        if current_room:
            nearby_object_ids = [
                oid for oid in current_room.object_ids_present
                if oid in self.objects and self.objects[oid].visible
            ]

        # Summarise evaluation scores (rounded integers — no raw floats to AI)
        evaluation_summary = {
            "observation": round(self.evaluation.observation.score),
            "curiosity": round(self.evaluation.curiosity.score),
            "wisdom": round(self.evaluation.wisdom.score),
            "patience": round(self.evaluation.patience.score),
            "adaptation": round(self.evaluation.adaptation.score),
        }

        # Recent history — last 10 entries, serialised as plain dicts
        recent_history = [
            {
                "turn": e.turn,
                "category": e.category,
                "description": e.description,
            }
            for e in self.history.get_last_n_entries(10)
        ]

        return AIContext(
            current_room=self.player.current_room,
            adjacent_rooms=adjacent_rooms,
            nearby_object_ids=nearby_object_ids,
            inventory=list(self.player.inventory),
            torch_state=self.player.torch.state,
            torch_fuel=self.player.torch.fuel,
            active_mission=self.mission.current_goal_description,
            current_puzzle_id=(
                current_room.puzzle_id if current_room else None
            ),
            recent_history=recent_history,
            dynamic_events_active=list(self.dynamic_events.active_events),
            flood_level=self.world.flood_level.name,
            temple_phase=self.world.temple_phase.name,
            temple_awareness=self.world.temple_awareness,
            evaluation_summary=evaluation_summary,
            known_symbols=list(self.story.symbols_encountered),
            chapters_reached=list(self.story.chapters_reached),
            recent_commands=self.player.command_history[-5:],
        )

    # ---------------------------------------------------------------------------
    # WRITE INTERFACE — Game Engine ONLY
    # The following methods must be called only from game_engine.py.
    # No other module may invoke write methods.
    # ---------------------------------------------------------------------------

    def _append_history(self, entry: HistoryEntry) -> None:
        """
        Appends a new entry to the event history log.
        Called by the Game Engine after every meaningful state change.
        The history is append-only — entries are never modified or deleted.
        """
        self.history.entries.append(entry)

    def _update_player_room(self, room_id: str, turn: int) -> None:
        """
        Updates the player's current room and movement history.
        Called by the Game Engine after a successful movement command.
        """
        self.player.previous_room = self.player.current_room
        self.player.current_room = room_id
        self.player.movement_history.append(room_id)
        self.player.steps_taken += 1

        if room_id not in self.player.visited_rooms:
            self.player.visited_rooms.append(room_id)

        room = self.rooms.get(room_id)
        if room and not room.visited:
            room.visited = True
            room.first_visited_turn = turn
        if room:
            room.visit_count += 1

    def _update_object_state(self, object_id: str, **kwargs) -> None:
        """
        Updates one or more fields on an ObjectState.
        Called by the Game Engine after an object interaction.
        kwargs must be valid ObjectState field names.
        """
        obj = self.objects.get(object_id)
        if obj is None:
            return
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

    def _update_puzzle_state(self, puzzle_id: str, **kwargs) -> None:
        """
        Updates one or more fields on a PuzzleState.
        Called by the Game Engine after a puzzle interaction.
        """
        puzzle = self.puzzles.get(puzzle_id)
        if puzzle is None:
            return
        for key, value in kwargs.items():
            if hasattr(puzzle, key):
                setattr(puzzle, key, value)

    def _update_evaluation(self, attribute: str, delta: float, reason: str, turn: int) -> None:
        """
        Adjusts a Guardian evaluation attribute by delta.
        Called by the Game Engine after behaviourally significant actions.
        Scores are clamped to 0.0–100.0.
        """
        attr = getattr(self.evaluation, attribute, None)
        if attr is None:
            return
        attr.score = max(0.0, min(100.0, attr.score + delta))
        attr.change_history.append((turn, delta, reason))

    def _add_to_inventory(self, object_id: str) -> None:
        """
        Adds an object to the player's inventory.
        Removes it from its current room.
        """
        if object_id not in self.player.inventory:
            self.player.inventory.append(object_id)
        obj = self.objects.get(object_id)
        if obj:
            obj.current_owner = "player"
            room = self.rooms.get(obj.current_room or "")
            if room and object_id in room.object_ids_present:
                room.object_ids_present.remove(object_id)
            obj.current_room = None

    def _remove_from_inventory(self, object_id: str, drop_room_id: str) -> None:
        """
        Removes an object from inventory and places it in a room.
        """
        if object_id in self.player.inventory:
            self.player.inventory.remove(object_id)
        obj = self.objects.get(object_id)
        if obj:
            obj.current_owner = None
            obj.current_room = drop_room_id
            room = self.rooms.get(drop_room_id)
            if room and object_id not in room.object_ids_present:
                room.object_ids_present.append(object_id)

    def _record_command(self, command_str: str) -> None:
        """Appends a command string to the player's command history."""
        self.player.command_history.append(command_str)

    def _increment_turn(self) -> None:
        """Increments the global turn counter on both player and world state."""
        self.player.turns_elapsed += 1
        self.world.current_turn += 1

    # ---------------------------------------------------------------------------
    # SERIALISATION & DESERIALISATION — used by Save Manager
    # Blueprint Reference: Chapter 10.7 — Save & Load Architecture
    # ---------------------------------------------------------------------------

    def to_dict(self) -> dict:
        """
        Serialises the entire World Model to a plain JSON-compatible dictionary.

        - Enums → their .value (str or int)
        - sets  → sorted list  (StoryState.symbols_encountered)
        - tuples → list        (EvaluationAttribute.change_history entries)
        - All nested dataclasses recursively converted.

        Delegates to serializer.world_model_to_dict().
        """
        from .serializer import world_model_to_dict  # noqa: PLC0415
        return world_model_to_dict(self)

    @classmethod
    def from_dict(cls, data: dict) -> WorldModel:
        """
        Deserialises a WorldModel from a plain dictionary.

        Reconstructs every Enum, nested dataclass, set, and tuple correctly.
        Safe to call with data produced by to_dict().

        Raises:
            WorldModelDeserializationError — if required keys are missing or
            values are invalid (e.g. unknown Enum member).

        Delegates to serializer.world_model_from_dict().
        """
        from .serializer import world_model_from_dict  # noqa: PLC0415
        return world_model_from_dict(data)

    def to_json(self, indent: int = 2) -> str:
        """
        Serialises the World Model to a formatted JSON string.
        Delegates to serializer.world_model_to_json().
        """
        from .serializer import world_model_to_json  # noqa: PLC0415
        return world_model_to_json(self, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> WorldModel:
        """
        Deserialises a WorldModel from a JSON string.

        Raises:
            WorldModelDeserializationError — on malformed JSON or invalid data.

        Delegates to serializer.world_model_from_json().
        """
        from .serializer import world_model_from_json  # noqa: PLC0415
        return world_model_from_json(json_str)

    # ---------------------------------------------------------------------------
    # VALIDATION — delegates to validator module
    # Blueprint Reference: Chapter 10.8 — State Validation
    # ---------------------------------------------------------------------------

    def validate(self) -> ValidationResult:
        """
        Runs all integrity checks against this World Model.

        Returns a ValidationResult with any errors and warnings found.
        Does NOT modify the World Model.

        Usage:
            result = world_model.validate()
            if not result.is_valid:
                print(result)
        """
        from .validator import validate  # noqa: PLC0415
        return validate(self)

    def validate_or_raise(self) -> None:
        """
        Runs all integrity checks. Raises WorldModelValidationError if any
        errors are found. Intended for Game Engine update paths.

        Usage:
            world_model.validate_or_raise()  # raises if invalid
        """
        from .validator import validate_or_raise  # noqa: PLC0415
        validate_or_raise(self)
