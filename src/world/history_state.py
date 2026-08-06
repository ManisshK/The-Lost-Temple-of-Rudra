"""
history_state.py — The Lost Temple of Rudra

Defines HistoryState — the append-only event log that forms the temple's permanent memory.
Nothing important is ever forgotten. Every meaningful event is stamped with its turn number.

"The temple does not remember your name. It remembers your choices."

Part of the Persistent World Model (Chapter 10, Section 10.4.11).

Blueprint Reference:
    Chapter 10 — Section 10.4.11 — Event History

READ-ONLY for all systems except the Game Engine.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HistoryEntry:
    """
    A single immutable record in the temple's memory.

    Once written, a history entry is never modified or deleted.
    The temple never forgets.
    """
    turn: int = 0
    event_id: str = ""
    category: str = ""         # "player_action" | "environmental" | "puzzle" | "story" | "evaluation"
    description: str = ""      # Human-readable event description
    room_id: Optional[str] = None
    object_ids: list[str] = field(default_factory=list)
    evaluation_impact: dict = field(default_factory=dict)
    # e.g. {"observation": +2.5, "recklessness": -1.0}


@dataclass
class HistoryState:
    """
    The complete, append-only event log for the entire game session.

    Used by:
    - Temple AI: to evaluate long-term behavioural patterns
    - Explorer AI: to recall previous discoveries for recommendation
    - Judgment AI: to construct the full journey narrative for final evaluation
    - Save Manager: as part of complete World Model serialisation

    Blueprint Reference: Chapter 10, Section 10.4.11 — Event History.

    Example entries:
        Turn 1   | player_action  | "Entered Temple Entrance."
        Turn 5   | player_action  | "Read entrance inscription."
        Turn 18  | puzzle         | "Solved Guardian Statue puzzle."
        Turn 29  | environmental  | "Flood started in lower chambers."
        Turn 42  | environmental  | "Bridge of Echoes weakened."
        Turn 71  | player_action  | "Retrieved Ancient Scroll."
        Turn 115 | story          | "Entered Final Chamber."
    """

    entries: list[HistoryEntry] = field(default_factory=list)

    def get_entries_for_room(self, room_id: str) -> list[HistoryEntry]:
        """Returns all history entries associated with a specific room."""
        return [e for e in self.entries if e.room_id == room_id]

    def get_entries_by_category(self, category: str) -> list[HistoryEntry]:
        """Returns all history entries of a specific category."""
        return [e for e in self.entries if e.category == category]

    def get_last_n_entries(self, n: int) -> list[HistoryEntry]:
        """Returns the most recent N entries for AI context windows."""
        return self.entries[-n:] if len(self.entries) >= n else self.entries[:]

    @property
    def total_turns(self) -> int:
        """Returns the turn number of the most recent entry."""
        return self.entries[-1].turn if self.entries else 0
