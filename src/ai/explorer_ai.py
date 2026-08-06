"""
explorer_ai.py — The Lost Temple of Rudra

Optional advisor to the player.
Reads the World Model (read-only) and recommends the most logical next action
based on current room, inventory, mission state, known clues, and dynamic events.

Never commands the player. Only suggests.
The player may always ignore recommendations.

TODO: Implement context reading from World Model via read-only interface.
TODO: Implement observe → reason → suggest recommendation pipeline.
TODO: Implement confidence scoring for each recommendation.
TODO: Implement rule-based fallback recommendations for Version 1.
TODO: Integrate with OllamaClient for LLM-powered reasoning (future phase).
TODO: Expose recommendation result for the UI recommendation panel.
"""
