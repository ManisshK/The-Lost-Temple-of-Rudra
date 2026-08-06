"""
conftest.py — The Lost Temple of Rudra

Pytest configuration and shared fixtures for the World Model test suite.

Provides a realistic WorldModel fixture used across all test modules.
The fixture contains enough populated state to meaningfully exercise
serialization, deserialization, and validation.
"""

import sys
import os

# Ensure src/ is on the path regardless of how pytest is invoked
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from world.world_model import WorldModel
from world.player_state import PlayerState, TorchStatus, PlayerScores
from world.world_state import WorldState, TemplePhase, FloodLevel, CollapseStage
from world.room_state import RoomState, RoomRegion, LightLevel
from world.object_state import ObjectState, ObjectCategory, StatueDirection
from world.puzzle_state import PuzzleState, PuzzleCategory, PuzzleStatus
from world.story_state import StoryState, StoryChapter, EndingEligibility
from world.event_state import DynamicEventState, FloodState, CollapseState
from world.evaluation_state import TempleEvaluation, EvaluationAttribute, JudgmentOutcome
from world.mission_state import MissionState, Objective, MissionStatus
from world.history_state import HistoryState, HistoryEntry


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_room(room_id: str, region: RoomRegion = RoomRegion.OUTER_TEMPLE,
               visited: bool = False) -> RoomState:
    return RoomState(
        room_id=room_id,
        region=region,
        visited=visited,
        accessible_exits={},
        hidden_passages={},
    )


def _make_object(object_id: str, name: str,
                 category: ObjectCategory = ObjectCategory.COLLECTIBLE,
                 room: str | None = "temple_entrance") -> ObjectState:
    return ObjectState(
        object_id=object_id,
        name=name,
        category=category,
        current_room=room,
        state="unlit" if category == ObjectCategory.COLLECTIBLE else "",
    )


def _make_puzzle(puzzle_id: str, room_id: str,
                 status: PuzzleStatus = PuzzleStatus.AVAILABLE) -> PuzzleState:
    return PuzzleState(
        puzzle_id=puzzle_id,
        room_id=room_id,
        category=PuzzleCategory.OBSERVATION,
        status=status,
    )


# ---------------------------------------------------------------------------
# Realistic WorldModel fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_world() -> WorldModel:
    """
    An empty WorldModel with only the default field values.
    Useful for testing defaults and isolated state changes.
    """
    return WorldModel()


@pytest.fixture
def populated_world() -> WorldModel:
    """
    A realistic WorldModel with rooms, objects, puzzles, story progress,
    evaluation scores, history entries, and mission state populated.

    Represents a mid-game save point — the explorer has reached the
    Hall of Guardians and solved the entrance puzzle.
    """
    wm = WorldModel()

    # --- Rooms ---
    wm.rooms["temple_entrance"] = RoomState(
        room_id="temple_entrance",
        region=RoomRegion.OUTER_TEMPLE,
        visited=True,
        visit_count=2,
        first_visited_turn=1,
        light_level=LightLevel.DIM,
        water_level=0.0,
        dust_level=5.0,
        object_ids_present=["inscription_entrance"],
        puzzle_id="puzzle_entrance_inscription",
        puzzle_solved=True,
        accessible_exits={"north": True},
        symbols_found=["eye"],
        lore_discovered=["lore_entrance_warning"],
    )
    wm.rooms["hall_of_echoes"] = RoomState(
        room_id="hall_of_echoes",
        region=RoomRegion.OUTER_TEMPLE,
        visited=True,
        visit_count=1,
        first_visited_turn=8,
        light_level=LightLevel.NORMAL,
        object_ids_present=["bronze_bell"],
        accessible_exits={"south": True, "north": True},
        symbols_found=["river"],
    )
    wm.rooms["hall_of_guardians"] = RoomState(
        room_id="hall_of_guardians",
        region=RoomRegion.OUTER_TEMPLE,
        visited=False,
        accessible_exits={"south": True},
        puzzle_id="puzzle_guardian_statues",
    )

    # --- Objects ---
    wm.objects["torch_carried"] = ObjectState(
        object_id="torch_carried",
        name="Ancient Torch",
        category=ObjectCategory.COLLECTIBLE,
        current_room=None,
        current_owner="player",
        state="lit",
        condition=64.0,
    )
    wm.objects["inscription_entrance"] = ObjectState(
        object_id="inscription_entrance",
        name="Entrance Inscription",
        category=ObjectCategory.STORY,
        current_room="temple_entrance",
        current_owner=None,
        state="read",
        condition=100.0,
    )
    wm.objects["bronze_bell"] = ObjectState(
        object_id="bronze_bell",
        name="Bronze Bell",
        category=ObjectCategory.INTERACTIVE,
        current_room="hall_of_echoes",
        state="intact",
        condition=80.0,
    )
    wm.objects["guardian_statue_east"] = ObjectState(
        object_id="guardian_statue_east",
        name="Eastern Guardian Statue",
        category=ObjectCategory.PUZZLE,
        current_room="hall_of_guardians",
        state="facing_north",
        condition=90.0,
        facing_direction=StatueDirection.NORTH,
        rotation_count=0,
    )

    # --- Player ---
    wm.player = PlayerState(
        current_room="hall_of_echoes",
        previous_room="temple_entrance",
        visited_rooms=["temple_entrance", "hall_of_echoes"],
        movement_history=["temple_entrance", "hall_of_echoes"],
        inventory=["torch_carried"],
        torch=TorchStatus(state="lit", fuel=64, brightness=70),
        steps_taken=12,
        turns_elapsed=18,
        scores=PlayerScores(observation=15.0, curiosity=8.0),
        active_mission_id="mission_reach_library",
        command_history=["look", "inspect inscription", "go north", "inspect bell"],
    )

    # --- World ---
    wm.world = WorldState(
        current_turn=18,
        current_chapter=6,
        temple_phase=TemplePhase.DISCOVERY,
        flood_level=FloodLevel.DRY,
        collapse_stage=CollapseStage.NONE,
        dust_density=3.0,
        ambient_light=75.0,
        world_stability=100.0,
        temple_awareness=5.0,
        temple_alert_level=0,
    )

    # --- Puzzles ---
    wm.puzzles["puzzle_entrance_inscription"] = PuzzleState(
        puzzle_id="puzzle_entrance_inscription",
        room_id="temple_entrance",
        category=PuzzleCategory.OBSERVATION,
        status=PuzzleStatus.SOLVED,
        attempt_count=1,
        failure_count=0,
        first_attempted_turn=3,
        solved_turn=3,
        hint_level=0,
        hint_count=0,
        observation_before_action=True,
        solved_without_hints=True,
        time_to_solve_turns=2,
    )
    wm.puzzles["puzzle_guardian_statues"] = PuzzleState(
        puzzle_id="puzzle_guardian_statues",
        room_id="hall_of_guardians",
        category=PuzzleCategory.LOGIC,
        status=PuzzleStatus.LOCKED,
        required_knowledge=["lore_guardian_directions"],
        required_objects=["guardian_statue_east"],
    )

    # --- Story ---
    wm.story = StoryState(
        current_chapter=StoryChapter.THE_JOURNEY,
        chapters_reached=[6, 7],
        lore_ids_discovered=["lore_entrance_warning"],
        inscriptions_read=["lore_entrance_warning"],
        symbols_encountered={"eye"},
        entrance_inscription_read=True,
        guardian_truth_discovered=False,
        ending_eligibility=EndingEligibility.UNDETERMINED,
    )

    # --- Evaluation ---
    wm.evaluation.observation.score = 88.0
    wm.evaluation.observation.change_history = [
        (3, 10.0, "read entrance inscription"),
        (8, 78.0, "inspected bronze bell carefully"),  # cumulative updates
    ]
    wm.evaluation.curiosity.score = 55.0
    wm.evaluation.wisdom.score = 20.0
    wm.evaluation.greed.score = 0.0
    wm.evaluation.recklessness.score = 5.0

    # --- Mission ---
    primary = Objective(
        objective_id="obj_reach_library",
        description="Reach the Ancient Library.",
        status=MissionStatus.ACTIVE,
        assigned_turn=1,
        required_for_ending=True,
    )
    wm.mission = MissionState(
        primary_objective=primary,
        secondary_objectives=[],
        optional_discoveries=[],
        completed_objectives=["obj_read_entrance"],
        current_goal_description="Reach the Ancient Library.",
        current_region_focus="outer_temple",
    )

    # --- History ---
    entries = [
        HistoryEntry(turn=1, event_id="enter_temple", category="player_action",
                     description="Entered Temple Entrance.", room_id="temple_entrance"),
        HistoryEntry(turn=3, event_id="read_inscription", category="player_action",
                     description="Read entrance inscription.",
                     room_id="temple_entrance",
                     evaluation_impact={"observation": 10.0}),
        HistoryEntry(turn=8, event_id="enter_echoes", category="player_action",
                     description="Entered Hall of Echoes.", room_id="hall_of_echoes"),
        HistoryEntry(turn=12, event_id="inspect_bell", category="player_action",
                     description="Inspected bronze bell.",
                     room_id="hall_of_echoes",
                     evaluation_impact={"observation": 5.0, "curiosity": 3.0}),
    ]
    wm.history = HistoryState(entries=entries)

    return wm
