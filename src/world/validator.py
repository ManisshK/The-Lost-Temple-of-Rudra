"""
validator.py — The Lost Temple of Rudra

Validates the integrity of a WorldModel instance before it is committed or saved.

The World Model is the single source of truth. An inconsistent World Model means
the entire game state is unreliable. Validation is therefore a hard gate —
any failed validation must be reported and, where appropriate, the update rejected.

Validation rules come directly from:
    Blueprint Chapter 10.8 — State Validation
    Blueprint Chapter 15.8 — Error Handling

This module contains NO gameplay logic.
It only inspects data — it never modifies the World Model.

Blueprint Reference:
    Chapter 10 — Section 10.8 — State Validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .world_model import WorldModel


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """
    The outcome of a WorldModel validation pass.

    is_valid   — True only if there are zero errors.
    errors     — Critical problems that must be fixed before saving or updating.
    warnings   — Non-blocking issues worth logging but not fatal.
    """
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def __str__(self) -> str:
        lines = []
        if self.is_valid:
            lines.append("WorldModel validation PASSED.")
        else:
            lines.append(f"WorldModel validation FAILED — {len(self.errors)} error(s).")
        for e in self.errors:
            lines.append(f"  [ERROR]   {e}")
        for w in self.warnings:
            lines.append(f"  [WARNING] {w}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validation exception
# ---------------------------------------------------------------------------

class WorldModelValidationError(Exception):
    """
    Raised by validate_or_raise() when the WorldModel fails validation.
    Carries the full ValidationResult for inspection.
    """
    def __init__(self, result: ValidationResult) -> None:
        self.result = result
        super().__init__(str(result))


# ---------------------------------------------------------------------------
# Individual validation checks
# ---------------------------------------------------------------------------

def _validate_player(wm: WorldModel, result: ValidationResult) -> None:
    """Validates PlayerState fields."""
    p = wm.player

    # Current room must exist in the rooms dict
    if p.current_room not in wm.rooms:
        result.add_error(
            f"player.current_room '{p.current_room}' does not exist in rooms dict."
        )

    # previous_room must be a known room if set
    if p.previous_room is not None and p.previous_room not in wm.rooms:
        result.add_error(
            f"player.previous_room '{p.previous_room}' does not exist in rooms dict."
        )

    # All visited rooms must exist in rooms dict
    for room_id in p.visited_rooms:
        if room_id not in wm.rooms:
            result.add_error(
                f"player.visited_rooms contains unknown room '{room_id}'."
            )

    # All inventory object IDs must exist in objects dict
    for obj_id in p.inventory:
        if obj_id not in wm.objects:
            result.add_error(
                f"player.inventory references unknown object '{obj_id}'."
            )

    # Torch fuel must be in valid range
    if not (0 <= p.torch.fuel <= 100):
        result.add_error(
            f"player.torch.fuel is {p.torch.fuel} — must be 0–100."
        )

    # Torch brightness must be in valid range
    if not (0 <= p.torch.brightness <= 100):
        result.add_error(
            f"player.torch.brightness is {p.torch.brightness} — must be 0–100."
        )

    # Steps and turns must not be negative
    if p.steps_taken < 0:
        result.add_error(f"player.steps_taken is negative ({p.steps_taken}).")
    if p.turns_elapsed < 0:
        result.add_error(f"player.turns_elapsed is negative ({p.turns_elapsed}).")

    # Score values must be non-negative
    for attr_name in ("observation", "curiosity", "adaptation", "knowledge", "guardian"):
        val = getattr(p.scores, attr_name, None)
        if val is not None and val < 0:
            result.add_error(
                f"player.scores.{attr_name} is negative ({val})."
            )


def _validate_world(wm: WorldModel, result: ValidationResult) -> None:
    """Validates WorldState fields."""
    w = wm.world

    if w.current_turn < 0:
        result.add_error(f"world.current_turn is negative ({w.current_turn}).")

    if not (1 <= w.current_chapter <= 13):
        result.add_error(
            f"world.current_chapter is {w.current_chapter} — must be 1–13."
        )

    if not (0.0 <= w.dust_density <= 100.0):
        result.add_error(
            f"world.dust_density is {w.dust_density} — must be 0.0–100.0."
        )

    if not (0.0 <= w.ambient_light <= 100.0):
        result.add_error(
            f"world.ambient_light is {w.ambient_light} — must be 0.0–100.0."
        )

    if not (0.0 <= w.world_stability <= 100.0):
        result.add_error(
            f"world.world_stability is {w.world_stability} — must be 0.0–100.0."
        )

    if not (0.0 <= w.temple_awareness <= 100.0):
        result.add_error(
            f"world.temple_awareness is {w.temple_awareness} — must be 0.0–100.0."
        )

    if w.temple_alert_level not in (0, 1, 2, 3):
        result.add_error(
            f"world.temple_alert_level is {w.temple_alert_level} — must be 0–3."
        )


def _validate_rooms(wm: WorldModel, result: ValidationResult) -> None:
    """Validates all RoomState entries."""
    for room_id, room in wm.rooms.items():

        # Room ID consistency
        if room.room_id != room_id:
            result.add_error(
                f"Room key '{room_id}' does not match room.room_id '{room.room_id}'."
            )

        # Environmental ranges
        if not (0.0 <= room.water_level <= 100.0):
            result.add_error(
                f"Room '{room_id}': water_level {room.water_level} out of range 0–100."
            )

        if not (0.0 <= room.dust_level <= 100.0):
            result.add_error(
                f"Room '{room_id}': dust_level {room.dust_level} out of range 0–100."
            )

        if not (0.0 <= room.environmental_damage <= 100.0):
            result.add_error(
                f"Room '{room_id}': environmental_damage {room.environmental_damage} "
                f"out of range 0–100."
            )

        # Objects present must exist in objects dict
        for obj_id in room.object_ids_present:
            if obj_id not in wm.objects:
                result.add_error(
                    f"Room '{room_id}': object_ids_present contains "
                    f"unknown object '{obj_id}'."
                )

        # Puzzle ID must exist if set
        if room.puzzle_id is not None and room.puzzle_id not in wm.puzzles:
            result.add_error(
                f"Room '{room_id}': puzzle_id '{room.puzzle_id}' "
                f"not found in puzzles dict."
            )

        # visit_count must not be negative
        if room.visit_count < 0:
            result.add_error(
                f"Room '{room_id}': visit_count is negative ({room.visit_count})."
            )


def _validate_objects(wm: WorldModel, result: ValidationResult) -> None:
    """Validates all ObjectState entries — no object may be in two places at once."""
    seen_object_ids: set[str] = set()

    for obj_id, obj in wm.objects.items():

        # Object ID consistency
        if obj.object_id != obj_id:
            result.add_error(
                f"Object key '{obj_id}' does not match object.object_id '{obj.object_id}'."
            )

        # No duplicate object IDs
        if obj_id in seen_object_ids:
            result.add_error(f"Duplicate object_id detected: '{obj_id}'.")
        seen_object_ids.add(obj_id)

        # Location consistency: object must be in inventory OR in a room, not both
        in_inventory = obj_id in wm.player.inventory
        in_room = obj.current_room is not None and obj.current_room in wm.rooms

        if in_inventory and in_room:
            result.add_error(
                f"Object '{obj_id}' is simultaneously in player inventory "
                f"and in room '{obj.current_room}'."
            )

        # If object claims to be in a room, that room must list it
        if obj.current_room is not None:
            room = wm.rooms.get(obj.current_room)
            if room is None:
                result.add_error(
                    f"Object '{obj_id}': current_room '{obj.current_room}' "
                    f"does not exist in rooms dict."
                )
            elif obj_id not in room.object_ids_present and not in_inventory:
                result.add_warning(
                    f"Object '{obj_id}' claims to be in room '{obj.current_room}' "
                    f"but is not listed in that room's object_ids_present."
                )

        # Condition range
        if not (0.0 <= obj.condition <= 100.0):
            result.add_error(
                f"Object '{obj_id}': condition {obj.condition} out of range 0–100."
            )

        # Dependencies must reference known objects
        for dep_id in obj.required_objects:
            if dep_id not in wm.objects:
                result.add_warning(
                    f"Object '{obj_id}': required_objects contains "
                    f"unknown object '{dep_id}'."
                )


def _validate_puzzles(wm: WorldModel, result: ValidationResult) -> None:
    """Validates all PuzzleState entries."""
    for puzzle_id, puzzle in wm.puzzles.items():

        # Puzzle ID consistency
        if puzzle.puzzle_id != puzzle_id:
            result.add_error(
                f"Puzzle key '{puzzle_id}' does not match "
                f"puzzle.puzzle_id '{puzzle.puzzle_id}'."
            )

        # Room must exist
        if puzzle.room_id and puzzle.room_id not in wm.rooms:
            result.add_error(
                f"Puzzle '{puzzle_id}': room_id '{puzzle.room_id}' "
                f"does not exist in rooms dict."
            )

        # Attempt counts non-negative
        if puzzle.attempt_count < 0:
            result.add_error(
                f"Puzzle '{puzzle_id}': attempt_count is negative."
            )
        if puzzle.failure_count < 0:
            result.add_error(
                f"Puzzle '{puzzle_id}': failure_count is negative."
            )

        # Hint level non-negative
        if puzzle.hint_level < 0:
            result.add_error(
                f"Puzzle '{puzzle_id}': hint_level is negative."
            )

        # Prerequisite puzzles must exist
        for prereq_id in puzzle.prerequisite_puzzle_ids:
            if prereq_id not in wm.puzzles:
                result.add_warning(
                    f"Puzzle '{puzzle_id}': prerequisite_puzzle_ids contains "
                    f"unknown puzzle '{prereq_id}'."
                )

        # Required objects must exist
        for obj_id in puzzle.required_objects:
            if obj_id not in wm.objects:
                result.add_warning(
                    f"Puzzle '{puzzle_id}': required_objects contains "
                    f"unknown object '{obj_id}'."
                )

        # Solved puzzle consistency: if solved, solved_turn should be set
        if puzzle.status.value == "solved" and puzzle.solved_turn is None:
            result.add_warning(
                f"Puzzle '{puzzle_id}' is solved but solved_turn is None."
            )


def _validate_story(wm: WorldModel, result: ValidationResult) -> None:
    """Validates StoryState for logical consistency."""
    s = wm.story

    # Chapter values must be valid (1–13)
    for ch_val in s.chapters_reached:
        if not (1 <= ch_val <= 13):
            result.add_error(
                f"story.chapters_reached contains invalid chapter value {ch_val}."
            )

    # If transformation is complete, revelation must have been triggered first
    if s.transformation_complete and not s.final_revelation_triggered:
        result.add_error(
            "story.transformation_complete is True but "
            "final_revelation_triggered is False — invalid progression."
        )

    # If collapse started, transformation must be complete
    if s.collapse_sequence_started and not s.transformation_complete:
        result.add_error(
            "story.collapse_sequence_started is True but "
            "transformation_complete is False — invalid progression."
        )

    # Ending eligibility: WORTHY requires revelation
    if (
        s.ending_eligibility.value == "worthy"
        and not s.final_revelation_triggered
    ):
        result.add_warning(
            "story.ending_eligibility is WORTHY but "
            "final_revelation_triggered is False."
        )


def _validate_evaluation(wm: WorldModel, result: ValidationResult) -> None:
    """Validates TempleEvaluation — all scores must be in range 0–100."""
    evaluation_attributes = (
        "observation", "curiosity", "wisdom", "patience", "adaptation",
        "integrity", "responsibility", "understanding", "greed", "recklessness",
    )
    for attr_name in evaluation_attributes:
        attr = getattr(wm.evaluation, attr_name, None)
        if attr is None:
            result.add_error(
                f"evaluation.{attr_name} is missing."
            )
            continue
        if not (0.0 <= attr.score <= 100.0):
            result.add_error(
                f"evaluation.{attr_name}.score is {attr.score} — must be 0.0–100.0."
            )


def _validate_dynamic_events(wm: WorldModel, result: ValidationResult) -> None:
    """Validates DynamicEventState for internal consistency."""
    de = wm.dynamic_events

    # Collapse stage must be 0–4
    if not (0 <= de.collapse.current_stage <= 4):
        result.add_error(
            f"dynamic_events.collapse.current_stage is "
            f"{de.collapse.current_stage} — must be 0–4."
        )

    # Flood stage must be 0–5
    if not (0 <= de.flood.current_stage <= 5):
        result.add_error(
            f"dynamic_events.flood.current_stage is "
            f"{de.flood.current_stage} — must be 0–5."
        )

    # Dust density non-negative
    if de.dust.global_density < 0:
        result.add_error(
            f"dynamic_events.dust.global_density is negative "
            f"({de.dust.global_density})."
        )

    # Bridge integrity values must be 0–100
    for bridge_id, integrity in de.bridge.integrity.items():
        if not (0.0 <= integrity <= 100.0):
            result.add_error(
                f"dynamic_events.bridge.integrity['{bridge_id}'] is "
                f"{integrity} — must be 0–100."
            )


def _validate_history(wm: WorldModel, result: ValidationResult) -> None:
    """Validates HistoryState — turn numbers must be non-decreasing."""
    entries = wm.history.entries
    for i in range(1, len(entries)):
        if entries[i].turn < entries[i - 1].turn:
            result.add_error(
                f"history.entries: turn number decreased from "
                f"{entries[i - 1].turn} to {entries[i].turn} at index {i} "
                f"— history must be chronologically ordered."
            )
            break  # Report once, not for every entry


def _validate_turn_consistency(wm: WorldModel, result: ValidationResult) -> None:
    """Cross-checks turn counters between player and world state."""
    if wm.player.turns_elapsed != wm.world.current_turn:
        result.add_warning(
            f"player.turns_elapsed ({wm.player.turns_elapsed}) does not match "
            f"world.current_turn ({wm.world.current_turn})."
        )


def _validate_inventory_ownership(wm: WorldModel, result: ValidationResult) -> None:
    """Every inventory item must have current_owner = 'player'."""
    for obj_id in wm.player.inventory:
        obj = wm.objects.get(obj_id)
        if obj is None:
            continue  # already caught by _validate_player
        if obj.current_owner != "player":
            result.add_error(
                f"Object '{obj_id}' is in player.inventory but "
                f"object.current_owner is '{obj.current_owner}' (expected 'player')."
            )
        if obj.current_room is not None:
            result.add_error(
                f"Object '{obj_id}' is in player.inventory but "
                f"object.current_room is '{obj.current_room}' (expected None)."
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate(wm: WorldModel) -> ValidationResult:
    """
    Runs all validation checks against the provided WorldModel.

    Returns a ValidationResult containing any errors and warnings found.
    Does NOT modify the WorldModel in any way.

    Usage:
        result = validate(world_model)
        if not result.is_valid:
            logger.error(str(result))
    """
    result = ValidationResult()

    _validate_player(wm, result)
    _validate_world(wm, result)
    _validate_rooms(wm, result)
    _validate_objects(wm, result)
    _validate_puzzles(wm, result)
    _validate_story(wm, result)
    _validate_evaluation(wm, result)
    _validate_dynamic_events(wm, result)
    _validate_history(wm, result)
    _validate_turn_consistency(wm, result)
    _validate_inventory_ownership(wm, result)

    return result


def validate_or_raise(wm: WorldModel) -> None:
    """
    Runs all validation checks. Raises WorldModelValidationError if any
    errors are found.

    Intended for use inside Game Engine update paths where an invalid
    state must be rejected immediately rather than silently accepted.

    Usage:
        validate_or_raise(world_model)  # raises if invalid
    """
    result = validate(wm)
    if not result.is_valid:
        raise WorldModelValidationError(result)
