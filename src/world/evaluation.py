"""
evaluation.py — The Lost Temple of Rudra

Guardian evaluation system. Tracks and updates the ten evaluation attributes
that determine the final judgment at the end of the game.

Ten attributes (float 0–100 each):
    Observation, Curiosity, Patience, Adaptation, Integrity,
    Wisdom, Greed, Recklessness, Consistency, Understanding.

The final judgment (Worthy / Nearly Worthy / Unworthy) is derived
from a weighted aggregate of these scores across the entire journey.

TODO: Define scoring rules for every meaningful player action.
TODO: Implement update_score(attribute, delta, reason, world_model).
TODO: Implement calculate_judgment(world_model) → JudgmentResult.
TODO: Implement get_evaluation_summary(world_model) → human-readable report.
TODO: Define weighting for each attribute in the final judgment calculation.
TODO: Ensure scores are always written through the Game Engine, never directly.
"""
