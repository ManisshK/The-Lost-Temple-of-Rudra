"""
state_manager.py — The Lost Temple of Rudra

Manages macro game state transitions.
Tracks the current game phase and coordinates transitions between major stages.

Game phases:
    LOADING → INTRO → EXPLORATION → FINAL_CHAMBER → ENDING → CREDITS

TODO: Implement game phase state machine.
TODO: Implement phase transition triggers (story events, room arrivals, puzzle completions).
TODO: Implement game-over detection and restart logic.
TODO: Notify UI and Game Engine on phase transitions.
"""
