"""
serializer.py — The Lost Temple of Rudra

Handles complete serialization and deserialization of the WorldModel.

Responsibilities:
    - WorldModel → dict  (to_dict)
    - dict → WorldModel  (from_dict)
    - WorldModel → JSON string  (to_json)
    - JSON string → WorldModel  (from_json)

Design rules:
    - Uses only standard Python libraries (dataclasses, json, enum).
    - All Enum fields are serialized as their string values.
    - StoryState.symbols_encountered (set) serializes as a sorted list.
    - EvaluationAttribute.change_history (list[tuple]) serializes as list[list].
    - Deserialization reconstructs every Enum and nested dataclass exactly.
    - This module contains NO gameplay logic.

Blueprint Reference:
    Chapter 10 — Section 10.7 — Save & Load Architecture
    Chapter 15 — Section 15.4 — Save Manager
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from .player_state import PlayerState, TorchStatus, PlayerScores
from .world_state import WorldState, TemplePhase, FloodLevel, CollapseStage
from .room_state import RoomState, RoomRegion, LightLevel
from .object_state import ObjectState, ObjectCategory, StatueDirection
from .puzzle_state import PuzzleState, PuzzleCategory, PuzzleStatus
from .story_state import StoryState, StoryChapter, EndingEligibility
from .event_state import (
    DynamicEventState, FloodState, TorchBurnState, DustState,
    BridgeEventState, StatueResetState, CollapseState,
    EventType, EventStatus, EventRecord,
)
from .evaluation_state import TempleEvaluation, EvaluationAttribute, JudgmentOutcome
from .mission_state import MissionState, Objective, MissionStatus
from .history_state import HistoryState, HistoryEntry


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _enum_safe_asdict(obj: Any) -> Any:
    """
    Recursively converts a dataclass to a plain dict, ensuring:
    - Enums become their .value string/int
    - sets become sorted lists (for JSON compatibility)
    - tuples become lists (for JSON compatibility)
    - None values are preserved
    """
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _enum_safe_asdict(v) for k, v in obj.__dict__.items()}
    if isinstance(obj, dict):
        return {k: _enum_safe_asdict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_enum_safe_asdict(i) for i in obj]
    if isinstance(obj, set):
        return sorted([_enum_safe_asdict(i) for i in obj])
    if isinstance(obj, type) and issubclass(obj, object):
        return obj
    # Enum: return its value (string or int)
    try:
        from enum import Enum as _Enum
        if isinstance(obj, _Enum):
            return obj.value
    except ImportError:
        pass
    return obj


# ---------------------------------------------------------------------------
# Deserialization helpers — one function per nested dataclass
# ---------------------------------------------------------------------------

def _deserialize_torch_status(d: dict) -> TorchStatus:
    return TorchStatus(
        state=d.get("state", "unlit"),
        fuel=d.get("fuel", 100),
        brightness=d.get("brightness", 0),
        last_lit_turn=d.get("last_lit_turn"),
    )


def _deserialize_player_scores(d: dict) -> PlayerScores:
    return PlayerScores(
        observation=d.get("observation", 0.0),
        curiosity=d.get("curiosity", 0.0),
        adaptation=d.get("adaptation", 0.0),
        knowledge=d.get("knowledge", 0.0),
        guardian=d.get("guardian", 0.0),
    )


def _deserialize_player_state(d: dict) -> PlayerState:
    return PlayerState(
        current_room=d.get("current_room", "temple_entrance"),
        previous_room=d.get("previous_room"),
        visited_rooms=list(d.get("visited_rooms", [])),
        movement_history=list(d.get("movement_history", [])),
        inventory=list(d.get("inventory", [])),
        torch=_deserialize_torch_status(d.get("torch", {})),
        steps_taken=d.get("steps_taken", 0),
        turns_elapsed=d.get("turns_elapsed", 0),
        scores=_deserialize_player_scores(d.get("scores", {})),
        active_mission_id=d.get("active_mission_id"),
        command_history=list(d.get("command_history", [])),
        health=d.get("health"),
    )


def _deserialize_world_state(d: dict) -> WorldState:
    return WorldState(
        current_turn=d.get("current_turn", 0),
        current_chapter=d.get("current_chapter", 1),
        temple_phase=TemplePhase(d.get("temple_phase", 1)),
        flood_level=FloodLevel(d.get("flood_level", 0)),
        collapse_stage=CollapseStage(d.get("collapse_stage", 0)),
        dust_density=d.get("dust_density", 0.0),
        ambient_light=d.get("ambient_light", 80.0),
        world_stability=d.get("world_stability", 100.0),
        temple_awareness=d.get("temple_awareness", 0.0),
        temple_alert_level=d.get("temple_alert_level", 0),
        time_cycle=d.get("time_cycle", "day"),
    )


def _deserialize_room_state(d: dict) -> RoomState:
    return RoomState(
        room_id=d.get("room_id", ""),
        region=RoomRegion(d.get("region", "outer_temple")),
        visited=d.get("visited", False),
        visit_count=d.get("visit_count", 0),
        first_visited_turn=d.get("first_visited_turn"),
        light_level=LightLevel(d.get("light_level", "normal")),
        water_level=d.get("water_level", 0.0),
        dust_level=d.get("dust_level", 0.0),
        environmental_damage=d.get("environmental_damage", 0.0),
        object_ids_present=list(d.get("object_ids_present", [])),
        puzzle_id=d.get("puzzle_id"),
        puzzle_solved=d.get("puzzle_solved", False),
        accessible_exits=dict(d.get("accessible_exits", {})),
        hidden_passages=dict(d.get("hidden_passages", {})),
        symbols_found=list(d.get("symbols_found", [])),
        lore_discovered=list(d.get("lore_discovered", [])),
        story_progress=d.get("story_progress", 0),
        times_inspected=d.get("times_inspected", 0),
        ambient_effects_active=list(d.get("ambient_effects_active", [])),
    )


def _deserialize_object_state(d: dict) -> ObjectState:
    # facing_direction may be None or a StatueDirection value
    fd_raw = d.get("facing_direction")
    facing_direction = StatueDirection(fd_raw) if fd_raw is not None else None

    return ObjectState(
        object_id=d.get("object_id", ""),
        name=d.get("name", ""),
        category=ObjectCategory(d.get("category", "interactive")),
        current_room=d.get("current_room"),
        current_owner=d.get("current_owner"),
        condition=d.get("condition", 100.0),
        state=d.get("state", ""),
        visible=d.get("visible", True),
        discoverable=d.get("discoverable", True),
        interactable=d.get("interactable", True),
        destroyed=d.get("destroyed", False),
        activated=d.get("activated", False),
        usage_history=list(d.get("usage_history", [])),
        required_objects=list(d.get("required_objects", [])),
        unlocks=list(d.get("unlocks", [])),
        puzzle_id=d.get("puzzle_id"),
        story_importance=d.get("story_importance", ""),
        facing_direction=facing_direction,
        rotation_count=d.get("rotation_count", 0),
        last_rotated_turn=d.get("last_rotated_turn"),
        content_id=d.get("content_id"),
    )


def _deserialize_puzzle_state(d: dict) -> PuzzleState:
    return PuzzleState(
        puzzle_id=d.get("puzzle_id", ""),
        room_id=d.get("room_id", ""),
        category=PuzzleCategory(d.get("category", "observation")),
        status=PuzzleStatus(d.get("status", "locked")),
        attempt_count=d.get("attempt_count", 0),
        failure_count=d.get("failure_count", 0),
        first_attempted_turn=d.get("first_attempted_turn"),
        solved_turn=d.get("solved_turn"),
        current_progress=dict(d.get("current_progress", {})),
        hint_level=d.get("hint_level", 0),
        hint_count=d.get("hint_count", 0),
        required_knowledge=list(d.get("required_knowledge", [])),
        required_objects=list(d.get("required_objects", [])),
        prerequisite_puzzle_ids=list(d.get("prerequisite_puzzle_ids", [])),
        reward_given=d.get("reward_given", False),
        reward_id=d.get("reward_id"),
        world_model_changes=dict(d.get("world_model_changes", {})),
        observation_before_action=d.get("observation_before_action", False),
        solved_without_hints=d.get("solved_without_hints", True),
        time_to_solve_turns=d.get("time_to_solve_turns"),
        failure_history=list(d.get("failure_history", [])),
    )


def _deserialize_story_state(d: dict) -> StoryState:
    return StoryState(
        current_chapter=StoryChapter(d.get("current_chapter", 6)),
        chapters_reached=list(d.get("chapters_reached", [])),
        lore_ids_discovered=list(d.get("lore_ids_discovered", [])),
        murals_read=list(d.get("murals_read", [])),
        scrolls_read=list(d.get("scrolls_read", [])),
        inscriptions_read=list(d.get("inscriptions_read", [])),
        tablets_read=list(d.get("tablets_read", [])),
        # Stored as list in JSON, restored as set
        symbols_encountered=set(d.get("symbols_encountered", [])),
        entrance_inscription_read=d.get("entrance_inscription_read", False),
        guardian_truth_discovered=d.get("guardian_truth_discovered", False),
        eye_is_not_object_revealed=d.get("eye_is_not_object_revealed", False),
        civilization_history_known=d.get("civilization_history_known", False),
        temple_dialogues_heard=list(d.get("temple_dialogues_heard", [])),
        ending_eligibility=EndingEligibility(
            d.get("ending_eligibility", "undetermined")
        ),
        final_revelation_triggered=d.get("final_revelation_triggered", False),
        transformation_complete=d.get("transformation_complete", False),
        collapse_sequence_started=d.get("collapse_sequence_started", False),
        secret_rooms_found=list(d.get("secret_rooms_found", [])),
        hidden_lore_found=list(d.get("hidden_lore_found", [])),
        guardian_names_learned=list(d.get("guardian_names_learned", [])),
    )


def _deserialize_flood_state(d: dict) -> FloodState:
    return FloodState(
        active=d.get("active", False),
        start_turn=d.get("start_turn"),
        current_stage=d.get("current_stage", 0),
        affected_rooms=list(d.get("affected_rooms", [])),
        flood_gates_open=list(d.get("flood_gates_open", [])),
        water_wheel_active=d.get("water_wheel_active", False),
    )


def _deserialize_torch_burn_state(d: dict) -> TorchBurnState:
    return TorchBurnState(
        base_burn_rate=d.get("base_burn_rate", 1.0),
        current_burn_rate=d.get("current_burn_rate", 1.0),
        flood_modifier=d.get("flood_modifier", 1.5),
    )


def _deserialize_dust_state(d: dict) -> DustState:
    return DustState(
        global_density=d.get("global_density", 0.0),
        accumulation_rate=d.get("accumulation_rate", 0.5),
        rooms_affected=list(d.get("rooms_affected", [])),
        ventilation_active=d.get("ventilation_active", False),
    )


def _deserialize_bridge_event_state(d: dict) -> BridgeEventState:
    return BridgeEventState(
        integrity=dict(d.get("integrity", {})),
        collapsed_bridges=list(d.get("collapsed_bridges", [])),
        repaired_bridges=list(d.get("repaired_bridges", [])),
    )


def _deserialize_statue_reset_state(d: dict) -> StatueResetState:
    return StatueResetState(
        last_rotated=dict(d.get("last_rotated", {})),
        reset_after_turns=d.get("reset_after_turns", 20),
    )


def _deserialize_collapse_state(d: dict) -> CollapseState:
    return CollapseState(
        active=d.get("active", False),
        current_stage=d.get("current_stage", 0),
        start_turn=d.get("start_turn"),
        escape_route_available=d.get("escape_route_available", True),
    )


def _deserialize_dynamic_event_state(d: dict) -> DynamicEventState:
    return DynamicEventState(
        flood=_deserialize_flood_state(d.get("flood", {})),
        torch_burn=_deserialize_torch_burn_state(d.get("torch_burn", {})),
        dust=_deserialize_dust_state(d.get("dust", {})),
        bridge=_deserialize_bridge_event_state(d.get("bridge", {})),
        statues=_deserialize_statue_reset_state(d.get("statues", {})),
        collapse=_deserialize_collapse_state(d.get("collapse", {})),
        door_states=dict(d.get("door_states", {})),
        active_events=list(d.get("active_events", [])),
        completed_events=list(d.get("completed_events", [])),
        water_gates=dict(d.get("water_gates", {})),
    )


def _deserialize_evaluation_attribute(d: dict) -> EvaluationAttribute:
    # change_history stored as list[list] in JSON → restore as list[tuple]
    raw_history = d.get("change_history", [])
    change_history = [tuple(entry) for entry in raw_history]
    return EvaluationAttribute(
        name=d.get("name", ""),
        score=d.get("score", 0.0),
        change_history=change_history,  # type: ignore[arg-type]
    )


def _deserialize_temple_evaluation(d: dict) -> TempleEvaluation:
    return TempleEvaluation(
        observation=_deserialize_evaluation_attribute(d.get("observation", {})),
        curiosity=_deserialize_evaluation_attribute(d.get("curiosity", {})),
        wisdom=_deserialize_evaluation_attribute(d.get("wisdom", {})),
        patience=_deserialize_evaluation_attribute(d.get("patience", {})),
        adaptation=_deserialize_evaluation_attribute(d.get("adaptation", {})),
        integrity=_deserialize_evaluation_attribute(d.get("integrity", {})),
        responsibility=_deserialize_evaluation_attribute(d.get("responsibility", {})),
        understanding=_deserialize_evaluation_attribute(d.get("understanding", {})),
        greed=_deserialize_evaluation_attribute(d.get("greed", {})),
        recklessness=_deserialize_evaluation_attribute(d.get("recklessness", {})),
        final_judgment=JudgmentOutcome(
            d.get("final_judgment", "undetermined")
        ),
        judgment_turn=d.get("judgment_turn"),
        judgment_narrative=d.get("judgment_narrative", ""),
    )


def _deserialize_objective(d: dict) -> Objective:
    return Objective(
        objective_id=d.get("objective_id", ""),
        description=d.get("description", ""),
        status=MissionStatus(d.get("status", "inactive")),
        assigned_turn=d.get("assigned_turn"),
        completed_turn=d.get("completed_turn"),
        region_hint=d.get("region_hint", ""),
        required_for_ending=d.get("required_for_ending", False),
    )


def _deserialize_mission_state(d: dict) -> MissionState:
    primary_raw = d.get("primary_objective")
    primary = _deserialize_objective(primary_raw) if primary_raw else None

    return MissionState(
        primary_objective=primary,
        secondary_objectives=[
            _deserialize_objective(o)
            for o in d.get("secondary_objectives", [])
        ],
        optional_discoveries=[
            _deserialize_objective(o)
            for o in d.get("optional_discoveries", [])
        ],
        completed_objectives=list(d.get("completed_objectives", [])),
        failed_objectives=list(d.get("failed_objectives", [])),
        current_goal_description=d.get("current_goal_description", "Explore the temple."),
        current_region_focus=d.get("current_region_focus", "outer_temple"),
    )


def _deserialize_history_entry(d: dict) -> HistoryEntry:
    return HistoryEntry(
        turn=d.get("turn", 0),
        event_id=d.get("event_id", ""),
        category=d.get("category", ""),
        description=d.get("description", ""),
        room_id=d.get("room_id"),
        object_ids=list(d.get("object_ids", [])),
        evaluation_impact=dict(d.get("evaluation_impact", {})),
    )


def _deserialize_history_state(d: dict) -> HistoryState:
    return HistoryState(
        entries=[_deserialize_history_entry(e) for e in d.get("entries", [])]
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def world_model_to_dict(wm: "WorldModel") -> dict:  # noqa: F821 — forward ref
    """
    Serializes a WorldModel to a plain JSON-compatible dictionary.

    - Enums → their .value (str or int)
    - sets  → sorted list
    - tuples → list
    - All nested dataclasses recursively converted.

    Returns a dict that json.dumps() can handle without a custom encoder.
    """
    return _enum_safe_asdict(wm)


def world_model_to_json(wm: "WorldModel", indent: int = 2) -> str:  # noqa: F821
    """
    Serializes a WorldModel to a formatted JSON string.
    Uses world_model_to_dict() internally.
    """
    return json.dumps(world_model_to_dict(wm), indent=indent)


def world_model_from_dict(data: dict) -> "WorldModel":  # noqa: F821
    """
    Deserializes a WorldModel from a plain dictionary.

    Reconstructs every Enum, nested dataclass, set, and tuple correctly.
    Safe to call with data produced by world_model_to_dict().

    Raises:
        WorldModelDeserializationError — if required keys are missing or
        values are invalid (e.g. unknown Enum member).
    """
    # Import here to avoid circular import at module level
    from .world_model import WorldModel  # noqa: PLC0415

    try:
        return WorldModel(
            player=_deserialize_player_state(data.get("player", {})),
            world=_deserialize_world_state(data.get("world", {})),
            rooms={
                room_id: _deserialize_room_state(room_data)
                for room_id, room_data in data.get("rooms", {}).items()
            },
            objects={
                obj_id: _deserialize_object_state(obj_data)
                for obj_id, obj_data in data.get("objects", {}).items()
            },
            puzzles={
                puzzle_id: _deserialize_puzzle_state(puzzle_data)
                for puzzle_id, puzzle_data in data.get("puzzles", {}).items()
            },
            story=_deserialize_story_state(data.get("story", {})),
            dynamic_events=_deserialize_dynamic_event_state(
                data.get("dynamic_events", {})
            ),
            evaluation=_deserialize_temple_evaluation(
                data.get("evaluation", {})
            ),
            mission=_deserialize_mission_state(data.get("mission", {})),
            history=_deserialize_history_state(data.get("history", {})),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise WorldModelDeserializationError(
            f"Failed to deserialize WorldModel: {exc}"
        ) from exc


def world_model_from_json(json_str: str) -> "WorldModel":  # noqa: F821
    """
    Deserializes a WorldModel from a JSON string.
    Raises WorldModelDeserializationError on malformed input.
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise WorldModelDeserializationError(
            f"Invalid JSON: {exc}"
        ) from exc
    return world_model_from_dict(data)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class WorldModelDeserializationError(Exception):
    """
    Raised when deserialization of a WorldModel fails due to missing,
    invalid, or incompatible data.

    The game should catch this in SaveManager and offer the player a
    safe fallback rather than crashing.
    """
