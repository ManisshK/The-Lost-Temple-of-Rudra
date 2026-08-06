"""
command_parser.py — The Lost Temple of Rudra

Translates raw player text into a structured Command object.

Design rules (Blueprint Chapter 8):
    - Understands intent, not just literal keywords.
    - All synonym resolution lives in command_registry.py.
    - Never executes actions — only produces Command objects.
    - Returns a ParseResult (Command | failure message) — never raises.
    - Errors are phrased as natural narration, never technical messages.
    - Debug commands are gated by a debug_mode flag.
    - Hidden commands are silently supported.

Pipeline:
    raw input → normalise → extract verb phrase → resolve action →
    extract target(s) → build Command → return ParseResult
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .command import Action, Command, CommandCategory
from .command_registry import (
    VERB_MAP,
    DIRECTION_MAP,
    STRIP_WORDS,
    SECONDARY_PREPOSITIONS,
)


# ---------------------------------------------------------------------------
# Parse result
# ---------------------------------------------------------------------------

@dataclass
class ParseResult:
    """
    The outcome of attempting to parse one player input.

    success     — True when a valid Command was produced.
    command     — Populated when success is True.
    error_message — Natural-language feedback when success is False.
                    Never a raw technical error; always an in-world response.
    """
    success: bool
    command: Optional[Command] = None
    error_message: str = ""

    @classmethod
    def ok(cls, command: Command) -> ParseResult:
        return cls(success=True, command=command)

    @classmethod
    def fail(cls, message: str) -> ParseResult:
        return cls(success=False, error_message=message)


# ---------------------------------------------------------------------------
# CommandParser
# ---------------------------------------------------------------------------

class CommandParser:
    """
    Translates natural-language player input into canonical Command objects.

    Usage:
        parser = CommandParser(debug_mode=False)
        result = parser.parse("inspect the eastern statue")
        if result.success:
            engine.execute(result.command)

    Blueprint Reference: Chapter 8 — Command System & Natural Language Parser.
    """

    def __init__(self, debug_mode: bool = False) -> None:
        self.debug_mode = debug_mode

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, raw_input: str) -> ParseResult:
        """
        Parse one line of player input into a Command.

        Returns ParseResult.ok(command) on success.
        Returns ParseResult.fail(message) on any parse failure.
        Never raises an exception.
        """
        if not raw_input or not raw_input.strip():
            return ParseResult.fail(
                "The silence stretches out. You haven't said anything."
            )

        normalised = self._normalise(raw_input)

        # --- Try multi-word verb phrases first (longest match) ---
        action, remainder = self._resolve_verb(normalised)

        if action is None:
            return ParseResult.fail(
                f"You consider '{raw_input.strip()}', "
                "but the temple offers no clear path for that intention."
            )

        # --- Gate debug commands ---
        if action in (
            Action.DEBUG_WORLD, Action.DEBUG_EVENTS,
            Action.DEBUG_ROOM, Action.DEBUG_OBJECTS, Action.DEBUG_EVAL,
        ):
            if not self.debug_mode:
                return ParseResult.fail(
                    "That command is not available here."
                )

        # --- Extract target(s) ---
        target, secondary_target = self._extract_targets(remainder, action)

        command = Command(
            action=action,
            target=target,
            secondary_target=secondary_target,
            raw_input=raw_input.strip(),
        )
        return ParseResult.ok(command)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(text: str) -> str:
        """
        Lower-case, collapse whitespace, strip punctuation at ends.
        Preserves internal spacing for multi-word matching.
        Special case: bare '?' is preserved as a valid verb.
        """
        stripped = text.strip()
        if stripped == "?":
            return "?"
        text = stripped.lower()
        text = re.sub(r"[^\w\s]", "", text)   # strip punctuation
        text = re.sub(r"\s+", " ", text)       # collapse whitespace
        return text

    def _resolve_verb(self, normalised: str) -> tuple[Optional[Action], str]:
        """
        Find the longest matching verb phrase at the start of the input.

        Returns (action, remainder) where remainder is the part of the
        string after the matched verb phrase.
        Returns (None, normalised) if no match is found.
        """
        # Sort by length descending so longer phrases match first
        # e.g. "pick up" before "pick"
        candidates = sorted(VERB_MAP.keys(), key=len, reverse=True)

        for phrase in candidates:
            if normalised == phrase:
                # If the verb is itself a direction word (e.g. "north", "n"),
                # pass it as the remainder so _extract_targets can resolve it.
                if VERB_MAP[phrase] == Action.GO and phrase in DIRECTION_MAP:
                    return VERB_MAP[phrase], phrase
                return VERB_MAP[phrase], ""
            if normalised.startswith(phrase + " "):
                remainder = normalised[len(phrase):].strip()
                return VERB_MAP[phrase], remainder

        # Bare direction words (n, s, e, w, north, south …)
        # Also handles direction words that appear in VERB_MAP directly.
        # We must pass the direction word as the remainder so _extract_targets
        # can resolve it to a canonical direction string.
        first_word = normalised.split()[0] if normalised else ""
        if first_word in DIRECTION_MAP:
            # Pass the first word as remainder so direction resolution works.
            return Action.GO, first_word

        return None, normalised

    def _extract_targets(
        self, remainder: str, action: Action
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Extract primary and optional secondary target from the remainder string.

        Strips articles and common prepositions.
        Handles:
            "statue"                 → ("statue", None)
            "disc into pedestal"     → ("disc", "pedestal")
            "key with locked door"   → ("key", "locked door")
            "north"                  → ("north", None)   [direction]
        """
        if not remainder:
            return None, None

        # --- Direction shorthand for GO commands ---
        if action == Action.GO:
            direction = DIRECTION_MAP.get(remainder.strip())
            if direction:
                return direction, None
            # "go to the north" → normalise "to the north" → "north"
            cleaned = self._strip_articles(remainder)
            direction = DIRECTION_MAP.get(cleaned.strip())
            if direction:
                return direction, None
            # Fallback: return whatever is there
            return cleaned.strip() or None, None

        # --- Split on secondary prepositions ---
        # Use the full padded preposition (with surrounding spaces) for matching
        # so that e.g. " at " does not falsely match inside "statue".
        secondary_target: Optional[str] = None
        primary = remainder

        # Pad the remainder with spaces so that prepositions at the start/end
        # of the string are also matched correctly.
        padded = f" {remainder} "
        for prep in SECONDARY_PREPOSITIONS:
            if prep in padded:
                # Split the original remainder on the stripped preposition
                # but only at a true word boundary (using the padded version).
                parts = padded.split(prep, maxsplit=1)
                if len(parts) == 2:
                    primary = parts[0].strip()
                    secondary_target = self._strip_articles(parts[1].strip()) or None
                    break

        primary_clean = self._strip_articles(primary)

        return (primary_clean or None), secondary_target

    @staticmethod
    def _strip_articles(text: str) -> str:
        """Remove leading/trailing articles and common prepositions."""
        words = text.split()
        filtered = [w for w in words if w not in STRIP_WORDS]
        return " ".join(filtered)
