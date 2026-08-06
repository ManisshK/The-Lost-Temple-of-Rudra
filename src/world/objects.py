"""
objects.py — The Lost Temple of Rudra

Defines all interactable objects in the temple and their state machines.
Every object has a lifecycle: spawn → discovered → observed → interacted →
state changes → world model update → future gameplay impact.

Object categories:
    Collectible, Interactive, Story, Environmental, Puzzle, Symbolic, Ending.

Key objects:
    Torch, Ancient Key, Guardian Statue, Ancient Scroll, Flood Gate,
    Bridge, Stone Door, Temple Inscription, Water Wheel, Eye of Rudra.

TODO: Define object state enums for each object (Torch: Lit/Dim/Extinguished...).
TODO: Define valid state transitions per object.
TODO: Define object metadata (category, purpose, location, interactions, world model vars).
TODO: Implement get_object_state(object_id, world_model) — reads from World Model.
TODO: Implement get_valid_interactions(object_id, world_model) — context-aware actions.
TODO: Enforce: Eye of Rudra is never collectible, never usable, never droppable.
"""
