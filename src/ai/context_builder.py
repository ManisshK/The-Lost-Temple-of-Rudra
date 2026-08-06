"""
context_builder.py — The Lost Temple of Rudra

Builds sanitised, read-only AI context snapshots from the World Model.
Filters out hidden information — puzzle solutions, future room states,
judgment thresholds — that the player has not yet earned.

Neither the Temple AI nor the Explorer AI should ever receive information
that would allow them to cheat or spoil the story.

TODO: Implement get_temple_ai_context(world_model) → dict
TODO: Implement get_explorer_ai_context(world_model) → dict
TODO: Implement get_judgment_context(world_model) → dict (full journey summary)
TODO: Ensure all contexts are read-only snapshots (not live references).
TODO: Validate that no hidden fields are exposed in any context output.
"""
