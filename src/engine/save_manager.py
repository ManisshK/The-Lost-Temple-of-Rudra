"""
save_manager.py — The Lost Temple of Rudra

Handles saving and loading game state.
The World Model IS the save system. Saving = serialising the World Model to JSON.
Loading = deserialising JSON and restoring all World Model state.
No separate save architecture exists.

TODO: Implement save(world_model) → writes JSON to data/saves/.
TODO: Implement load(save_file) → reads JSON and restores World Model.
TODO: Implement autosave (triggered every N turns from game_settings.json).
TODO: Implement list_saves() → returns available save files for the load menu.
TODO: Implement save file validation (detect corrupt or version-mismatched files).
"""
