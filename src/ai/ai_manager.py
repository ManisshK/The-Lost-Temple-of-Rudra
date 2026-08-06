"""
ai_manager.py — The Lost Temple of Rudra

Central coordinator for all AI systems.
Manages Temple AI and Explorer AI instances.
Provides a unified interface for the Game Engine to request evaluations,
narration, and recommendations without directly coupling to individual AI modules.

TODO: Initialise Temple AI and Explorer AI instances.
TODO: Expose request_narration(world_state) → str for Game Engine.
TODO: Expose request_recommendation(world_state) → str for Game Engine.
TODO: Expose request_evaluation(world_state) for Temple AI evaluation updates.
TODO: Handle Ollama availability — fall back to rule-based if unavailable.
TODO: Load AI configuration from config/ai_settings.json.
"""
