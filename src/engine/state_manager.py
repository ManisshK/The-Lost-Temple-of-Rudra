"""
state_manager.py — The Lost Temple of Rudra

Macro game-state machine.

States
──────
  LOADING      → Assets being loaded, world model being initialised.
  TITLE        → Title screen shown; no game active.
  PLAYING      → Active exploration and puzzle solving.
  PAUSED       → Pause menu open; game logic frozen.
  JUDGMENT     → Final Chamber reached; judgment sequence running.
  ENDING       → Ending cutscene / narrative being displayed.
  CREDITS      → Credits screen.
  GAME_OVER    → Player quit / story concluded.

Transitions are triggered by the Game Engine or UI events.
Observers are notified on every transition (UI panels, AI, audio).
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, Optional


class GameState(Enum):
    LOADING   = "loading"
    TITLE     = "title"
    PLAYING   = "playing"
    PAUSED    = "paused"
    JUDGMENT  = "judgment"
    ENDING    = "ending"
    CREDITS   = "credits"
    GAME_OVER = "game_over"


# Valid transitions: {from_state: {to_state, ...}}
_TRANSITIONS: dict[GameState, set[GameState]] = {
    GameState.LOADING:   {GameState.TITLE, GameState.PLAYING},
    GameState.TITLE:     {GameState.PLAYING, GameState.GAME_OVER},
    GameState.PLAYING:   {GameState.PAUSED, GameState.JUDGMENT, GameState.TITLE, GameState.GAME_OVER},
    GameState.PAUSED:    {GameState.PLAYING, GameState.TITLE, GameState.GAME_OVER},
    GameState.JUDGMENT:  {GameState.ENDING, GameState.GAME_OVER},
    GameState.ENDING:    {GameState.CREDITS, GameState.TITLE, GameState.GAME_OVER},
    GameState.CREDITS:   {GameState.TITLE, GameState.GAME_OVER},
    GameState.GAME_OVER: {GameState.TITLE},
}

ObserverFn = Callable[[GameState, GameState], None]   # (from, to)


class StateManager:
    """
    Lightweight finite-state machine for macro game flow.

    Usage::

        sm = StateManager()
        sm.add_observer(my_callback)   # called on every transition
        sm.transition(GameState.PLAYING)
    """

    def __init__(self) -> None:
        self._state: GameState = GameState.LOADING
        self._observers: list[ObserverFn] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> GameState:
        return self._state

    def is_playing(self) -> bool:
        return self._state == GameState.PLAYING

    def is_paused(self) -> bool:
        return self._state == GameState.PAUSED

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def transition(self, new_state: GameState) -> bool:
        """
        Move to new_state if the transition is valid.

        Returns True on success, False if the transition is invalid.
        Never raises.
        """
        allowed = _TRANSITIONS.get(self._state, set())
        if new_state not in allowed:
            return False
        old = self._state
        self._state = new_state
        for obs in self._observers:
            try:
                obs(old, new_state)
            except Exception:
                pass
        return True

    def force(self, new_state: GameState) -> None:
        """Force a transition regardless of validity (use sparingly)."""
        old = self._state
        self._state = new_state
        for obs in self._observers:
            try:
                obs(old, new_state)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Observers
    # ------------------------------------------------------------------

    def add_observer(self, fn: ObserverFn) -> None:
        if fn not in self._observers:
            self._observers.append(fn)

    def remove_observer(self, fn: ObserverFn) -> None:
        self._observers = [o for o in self._observers if o is not fn]
