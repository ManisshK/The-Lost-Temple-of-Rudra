"""
constants.py — The Lost Temple of Rudra

Shared constants used across all game systems.
All magic numbers, string keys, enum values, and fixed identifiers live here.
"""

# ---------------------------------------------------------------------------
# Room IDs
# ---------------------------------------------------------------------------
ROOM_TEMPLE_ENTRANCE = "temple_entrance"
ROOM_HALL_OF_ECHOES = "hall_of_echoes"
ROOM_HALL_OF_GUARDIANS = "hall_of_guardians"
ROOM_CHAMBER_OF_INSCRIPTIONS = "chamber_of_inscriptions"
ROOM_FIRST_MEDITATION_HALL = "first_meditation_hall"
ROOM_ANCIENT_LIBRARY = "ancient_library"
ROOM_ARCHIVE_VAULT = "archive_vault"
ROOM_SYMBOL_GALLERY = "symbol_gallery"
ROOM_ASTRONOMERS_CHAMBER = "astronomers_chamber"
ROOM_STATUE_GALLERY = "statue_gallery"
ROOM_CHAMBER_OF_MAPS = "chamber_of_maps"
ROOM_FORGOTTEN_CLASSROOM = "forgotten_classroom"
ROOM_BRIDGE_OF_ECHOES = "bridge_of_echoes"
ROOM_FLOOD_CONTROL_ROOM = "flood_control_room"
ROOM_UNDERGROUND_RESERVOIR = "underground_reservoir"
ROOM_WATER_CHANNEL_NETWORK = "water_channel_network"
ROOM_COLLAPSED_HALLWAY = "collapsed_hallway"
ROOM_ANCIENT_MACHINERY_CHAMBER = "ancient_machinery_chamber"
ROOM_HIDDEN_MAINTENANCE_TUNNEL = "hidden_maintenance_tunnel"
ROOM_CHAMBER_OF_REFLECTION = "chamber_of_reflection"
ROOM_HALL_OF_JUDGMENT = "hall_of_judgment"
ROOM_GUARDIAN_ARCHIVE = "guardian_archive"
ROOM_THRONE_APPROACH = "throne_approach"
ROOM_FINAL_CHAMBER = "final_chamber"

# ---------------------------------------------------------------------------
# Canonical direction strings
# ---------------------------------------------------------------------------
DIR_NORTH = "north"
DIR_SOUTH = "south"
DIR_EAST = "east"
DIR_WEST = "west"
DIR_UP = "up"
DIR_DOWN = "down"

# ---------------------------------------------------------------------------
# Evaluation attribute keys (match TempleEvaluation field names)
# ---------------------------------------------------------------------------
EVAL_OBSERVATION = "observation"
EVAL_CURIOSITY = "curiosity"
EVAL_WISDOM = "wisdom"
EVAL_PATIENCE = "patience"
EVAL_ADAPTATION = "adaptation"
EVAL_INTEGRITY = "integrity"
EVAL_RESPONSIBILITY = "responsibility"
EVAL_UNDERSTANDING = "understanding"
EVAL_GREED = "greed"
EVAL_RECKLESSNESS = "recklessness"

# ---------------------------------------------------------------------------
# Judgment outcomes
# ---------------------------------------------------------------------------
JUDGMENT_WORTHY = "worthy"
JUDGMENT_NEARLY_WORTHY = "nearly_worthy"
JUDGMENT_UNWORTHY = "unworthy"
JUDGMENT_UNDETERMINED = "undetermined"

# ---------------------------------------------------------------------------
# History event categories
# ---------------------------------------------------------------------------
HISTORY_PLAYER_ACTION = "player_action"
HISTORY_ENVIRONMENTAL = "environmental"
HISTORY_PUZZLE = "puzzle"
HISTORY_STORY = "story"
HISTORY_EVALUATION = "evaluation"

# ---------------------------------------------------------------------------
# Evaluation deltas for common actions (blueprint-aligned defaults)
# ---------------------------------------------------------------------------
EVAL_DELTA_OBSERVE = 1.0       # Inspecting objects, reading inscriptions
EVAL_DELTA_EXPLORE = 1.5       # Entering a room for the first time
EVAL_DELTA_RUSH = -1.0         # Moving without observing
EVAL_DELTA_REPEAT_COMMAND = -0.5  # Repeating the exact same failing action
