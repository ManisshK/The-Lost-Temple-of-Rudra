"""
turn_manager.py — The Lost Temple of Rudra

Manages the turn counter and time-based world progression.
Each valid player command advances the turn counter by one.
Time-based dynamic events (flood rise, torch decay, bridge weakening)
are scheduled relative to turn count and temple phase.

TODO: Implement turn counter (increment on each valid command execution).
TODO: Implement time-based event scheduling (flood every N turns, etc.).
TODO: Implement temple phase tracker (early / mid / late / final).
TODO: Implement elapsed real-time tracking (optional, for evaluation metrics).
TODO: Provide current turn and phase data to World Model after each increment.
"""
