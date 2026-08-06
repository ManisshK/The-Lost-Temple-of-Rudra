"""
story_state.py — The Lost Temple of Rudra

Defines StoryState tracking all narrative progression throughout the explorer's journey.
The story is discovered through exploration, not delivered through cutscenes.

Part of the Persistent World Model (Chapter 10, Section 10.4.6).

Blueprint Reference:
    Chapter 2  — The Story
    Chapter 3  — Temple Lore
    Chapter 10 — Section 10.4.6 — Story State

READ-ONLY for all systems except the Game Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StoryChapter(Enum):
    """
    Canonical story chapters. (Blueprint Chapter 2)
    The player progresses through these chapters as the journey deepens.
    """
    THE_FORGOTTEN_AGE = 1
    THE_BIRTH_OF_THE_TEMPLE = 2
    THE_FIRST_GUARDIAN = 3
    THE_GUARDIANS_PURPOSE = 4
    THE_PASSING_CENTURIES = 5
    PRESENT_DAY = 6
    THE_JOURNEY = 7
    THE_LIVING_TEMPLE = 8
    THE_FINAL_CHAMBER = 9
    JUDGMENT = 10
    THE_TRUTH = 11
    THE_CHOICE = 12
    THE_ENDING = 13


class EndingEligibility(Enum):
    """
    The three possible final judgment outcomes. (Blueprint Chapter 11.6)
    """
    UNDETERMINED = "undetermined"
    UNWORTHY = "unworthy"
    NEARLY_WORTHY = "nearly_worthy"
    WORTHY = "worthy"


@dataclass
class StoryState:
    """
    Tracks all narrative milestones, lore discoveries, and the explorer's
    understanding of the temple's true purpose.

    The player begins believing they are searching for the Eye of Rudra as a
    physical treasure. The story state tracks when and how the truth unfolds.

    Blueprint Reference: Chapter 10, Section 10.4.6 — Story State.
    """

    # --- Chapter progression ---
    current_chapter: StoryChapter = StoryChapter.PRESENT_DAY
    chapters_reached: list[int] = field(default_factory=list)

    # --- Lore discovered ---
    lore_ids_discovered: list[str] = field(default_factory=list)
    murals_read: list[str] = field(default_factory=list)
    scrolls_read: list[str] = field(default_factory=list)
    inscriptions_read: list[str] = field(default_factory=list)
    tablets_read: list[str] = field(default_factory=list)

    # --- Symbols encountered ---
    # The five sacred symbols: eye, flame, river, circle, throne (Chapter 3.7)
    symbols_encountered: set = field(default_factory=set)

    # --- Key narrative flags ---
    entrance_inscription_read: bool = False       # "The temple does not remember your name..."
    guardian_truth_discovered: bool = False       # Player begins to understand the Eye is not an object
    eye_is_not_object_revealed: bool = False      # Full revelation in Final Chamber
    civilization_history_known: bool = False      # Player has read enough lore to understand builders

    # --- Dialogue progress ---
    temple_dialogues_heard: list[str] = field(default_factory=list)

    # --- Ending ---
    ending_eligibility: EndingEligibility = EndingEligibility.UNDETERMINED
    final_revelation_triggered: bool = False
    transformation_complete: bool = False
    collapse_sequence_started: bool = False

    # --- Optional discoveries ---
    secret_rooms_found: list[str] = field(default_factory=list)
    hidden_lore_found: list[str] = field(default_factory=list)
    guardian_names_learned: list[str] = field(default_factory=list)
