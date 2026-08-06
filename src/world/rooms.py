"""
rooms.py — The Lost Temple of Rudra

Defines all eleven temple rooms and the static room connection graph.
The physical layout never changes. Only room state changes via the World Model.

Rooms:
    01. temple_entrance
    02. hall_of_echoes
    03. hall_of_guardians
    04. ancient_library
    05. statue_gallery
    06. bridge_of_echoes
    07. flood_control_room
    08. underground_reservoir
    09. chamber_of_reflection
    10. hall_of_judgment
    11. final_chamber

TODO: Define static room graph (connections between rooms — never changes).
TODO: Define room metadata (name, category, description template, symbols present).
TODO: Implement get_accessible_exits(room_id, world_model) — dynamic accessibility.
TODO: Implement get_room_description(room_id, world_model) — context-aware narration.
TODO: Ensure no hard locks — always at least one valid route forward.
TODO: Define secret passage conditions (world state requirements for access).
"""
