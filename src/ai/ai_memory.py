"""
ai_memory.py — The Lost Temple of Rudra

Persistent AI memory layer for the current play session.

Tracks all behaviourally significant events observed by both the Temple AI
and the Explorer AI. Memory persists for the full session duration and is
used to detect long-term patterns, prevent repetitive hints, and support
the final judgment narrative.

Blueprint Reference: Chapter 10 — Persistent World Model Architecture
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Individual memory entries
# ---------------------------------------------------------------------------

@dataclass
class MemoryEntry:
    """A single remembered event recorded by an AI system."""
    turn: int
    event_type: str          # "room_visited" | "puzzle_solved" | "puzzle_failed" |
                             # "lore_discovered" | "hint_given" | "behaviour_pattern" |
                             # "decision" | "recurring_action"
    subject: str             # Room ID, puzzle ID, lore ID, behaviour key, etc.
    detail: str = ""         # Human-readable detail
    source: str = "system"   # "temple_ai" | "explorer_ai" | "system"


# ---------------------------------------------------------------------------
# AI Memory store
# ---------------------------------------------------------------------------

@dataclass
class AIMemory:
    """
    Session-scoped memory shared between Temple AI and Explorer AI.

    Append-only per category. Provides query helpers so AI systems can
    retrieve relevant context without reading the full log.
    """

    # All entries in chronological order
    entries: list[MemoryEntry] = field(default_factory=list)

    # Derived indexes for fast lookup (maintained on every append)
    explored_rooms: list[str] = field(default_factory=list)
    completed_puzzles: list[str] = field(default_factory=list)
    failed_puzzle_attempts: list[str] = field(default_factory=list)
    discovered_lore: list[str] = field(default_factory=list)
    hints_given: list[str] = field(default_factory=list)
    recurring_behaviours: dict[str, int] = field(default_factory=dict)
    important_decisions: list[MemoryEntry] = field(default_factory=list)

    # ---------------------------------------------------------------------------
    # Write interface — called only from TempleAI / ExplorerAI
    # ---------------------------------------------------------------------------

    def record(self, entry: MemoryEntry) -> None:
        """Append a memory entry and update derived indexes."""
        self.entries.append(entry)

        if entry.event_type == "room_visited":
            if entry.subject not in self.explored_rooms:
                self.explored_rooms.append(entry.subject)

        elif entry.event_type == "puzzle_solved":
            if entry.subject not in self.completed_puzzles:
                self.completed_puzzles.append(entry.subject)

        elif entry.event_type == "puzzle_failed":
            self.failed_puzzle_attempts.append(entry.subject)

        elif entry.event_type == "lore_discovered":
            if entry.subject not in self.discovered_lore:
                self.discovered_lore.append(entry.subject)

        elif entry.event_type == "hint_given":
            self.hints_given.append(entry.subject)

        elif entry.event_type == "recurring_action":
            self.recurring_behaviours[entry.subject] = (
                self.recurring_behaviours.get(entry.subject, 0) + 1
            )

        elif entry.event_type == "decision":
            self.important_decisions.append(entry)

    # ---------------------------------------------------------------------------
    # Read interface
    # ---------------------------------------------------------------------------

    def has_visited(self, room_id: str) -> bool:
        return room_id in self.explored_rooms

    def has_solved(self, puzzle_id: str) -> bool:
        return puzzle_id in self.completed_puzzles

    def hint_count_for(self, puzzle_id: str) -> int:
        return sum(1 for h in self.hints_given if h == puzzle_id)

    def failure_count_for(self, puzzle_id: str) -> int:
        return sum(1 for f in self.failed_puzzle_attempts if f == puzzle_id)

    def get_behaviour_count(self, behaviour_key: str) -> int:
        return self.recurring_behaviours.get(behaviour_key, 0)

    def get_recent_entries(self, n: int = 10) -> list[MemoryEntry]:
        return self.entries[-n:] if len(self.entries) >= n else list(self.entries)

    def get_entries_by_type(self, event_type: str) -> list[MemoryEntry]:
        return [e for e in self.entries if e.event_type == event_type]

    def summary(self) -> dict:
        """Return a compact summary dict for prompt injection."""
        return {
            "rooms_explored": len(self.explored_rooms),
            "puzzles_completed": len(self.completed_puzzles),
            "total_puzzle_failures": len(self.failed_puzzle_attempts),
            "lore_discovered": len(self.discovered_lore),
            "hints_given": len(self.hints_given),
            "recurring_behaviours": dict(self.recurring_behaviours),
            "important_decisions": len(self.important_decisions),
        }
