"""
command_registry.py — The Lost Temple of Rudra

The canonical synonym map: every accepted word or phrase → Action.

This module is the single place where all input vocabulary lives.
The CommandParser consults this registry; nothing else needs to know it.

Blueprint Reference:
    Chapter 8 — Command System & Natural Language Parser
    Section 8.2  — Design Philosophy (parser understands intent, not literals)
    Section 8.5  — Canonical Command Dictionary
    Section 8.10 — Hidden Commands
"""

from __future__ import annotations

from .command import Action

# ---------------------------------------------------------------------------
# Primary verb → Action mapping
# Each key is a lower-cased, stripped word or short phrase that a player
# might type as the first meaningful word of their command.
# ---------------------------------------------------------------------------

VERB_MAP: dict[str, Action] = {
    # --- Observation ---
    "look":         Action.LOOK,
    "l":            Action.LOOK,
    "look around":  Action.LOOK,
    "inspect":      Action.INSPECT,
    "examine":      Action.INSPECT,
    "observe":      Action.INSPECT,
    "check":        Action.INSPECT,
    "watch":        Action.INSPECT,
    "view":         Action.INSPECT,
    "read":         Action.READ,
    "listen":       Action.LISTEN,
    "listen to":    Action.LISTEN,
    "hear":         Action.LISTEN,
    "touch":        Action.TOUCH,
    "feel":         Action.TOUCH,
    "smell":        Action.SMELL,
    "sniff":        Action.SMELL,

    # --- Movement ---
    "go":           Action.GO,
    "walk":         Action.GO,
    "move":         Action.GO,
    "run":          Action.GO,
    "head":         Action.GO,
    "travel":       Action.GO,
    "north":        Action.GO,
    "south":        Action.GO,
    "east":         Action.GO,
    "west":         Action.GO,
    "up":           Action.GO,
    "down":         Action.GO,
    "n":            Action.GO,
    "s":            Action.GO,
    "e":            Action.GO,
    "w":            Action.GO,
    "enter":        Action.ENTER,
    "go in":        Action.ENTER,
    "go into":      Action.ENTER,
    "leave":        Action.LEAVE,
    "exit":         Action.LEAVE,
    "go out":       Action.LEAVE,
    "cross":        Action.CROSS,
    "climb":        Action.CLIMB,
    "ascend":       Action.CLIMB,
    "descend":      Action.DESCEND,
    "go down":      Action.DESCEND,

    # --- Inventory ---
    "take":         Action.TAKE,
    "grab":         Action.TAKE,
    "pick up":      Action.TAKE,
    "collect":      Action.TAKE,
    "get":          Action.TAKE,
    "acquire":      Action.TAKE,
    "drop":         Action.DROP,
    "put down":     Action.DROP,
    "place":        Action.DROP,
    # Note: "leave" as DROP only applies with a target ("leave torch here")
    # Bare "leave" resolves to LEAVE via separate entry below.
    "inventory":    Action.INVENTORY,
    "items":        Action.INVENTORY,
    "i":            Action.INVENTORY,
    "inv":          Action.INVENTORY,
    "use":          Action.USE,
    "apply":        Action.USE,
    "equip":        Action.EQUIP,
    "wear":         Action.EQUIP,
    "hold":         Action.EQUIP,
    "light":        Action.LIGHT,
    "ignite":       Action.LIGHT,
    "extinguish":   Action.EXTINGUISH,
    "put out":      Action.EXTINGUISH,
    "douse":        Action.EXTINGUISH,
    "snuff":        Action.EXTINGUISH,

    # --- Puzzle ---
    "rotate":       Action.ROTATE,
    "turn":         Action.ROTATE,
    "spin":         Action.ROTATE,
    "push":         Action.PUSH,
    "press":        Action.PUSH,
    "shove":        Action.PUSH,
    "pull":         Action.PULL,
    "yank":         Action.PULL,
    "tug":          Action.PULL,
    "insert":       Action.INSERT,
    "put":          Action.INSERT,
    "place into":   Action.INSERT,
    "remove":       Action.REMOVE,
    "take out":     Action.REMOVE,
    "align":        Action.ALIGN,
    "position":     Action.ALIGN,
    "arrange":      Action.ALIGN,
    "activate":     Action.ACTIVATE,
    "start":        Action.ACTIVATE,
    "trigger":      Action.ACTIVATE,
    "deactivate":   Action.DEACTIVATE,
    "stop":         Action.DEACTIVATE,
    "disable":      Action.DEACTIVATE,
    "open":         Action.OPEN,
    "unlock":       Action.OPEN,
    "close":        Action.CLOSE,
    "shut":         Action.CLOSE,
    "lock":         Action.CLOSE,

    # --- Knowledge ---
    "translate":    Action.TRANSLATE,
    "decipher":     Action.TRANSLATE,
    "study":        Action.STUDY,
    "analyse":      Action.STUDY,
    "analyze":      Action.STUDY,
    "remember":     Action.REMEMBER,
    "recall":       Action.REMEMBER,
    "compare":      Action.COMPARE,

    # --- AI assistance ---
    "recommend":    Action.RECOMMEND,
    "suggest":      Action.RECOMMEND,
    "advice":       Action.RECOMMEND,
    "advise":       Action.RECOMMEND,
    "status":       Action.STATUS,
    "hint":         Action.HINT,
    "clue":         Action.HINT,
    "think":        Action.THINK,

    # --- System ---
    "help":         Action.HELP,
    "?":            Action.HELP,
    "mission":      Action.MISSION,
    "objective":    Action.MISSION,
    "goal":         Action.MISSION,
    "journal":      Action.JOURNAL,
    "log":          Action.JOURNAL,
    "notes":        Action.JOURNAL,
    "history":      Action.HISTORY,
    "past":         Action.HISTORY,
    "save":         Action.SAVE,
    "load":         Action.LOAD,
    "restore":      Action.LOAD,
    "quit":         Action.QUIT,
    "q":            Action.QUIT,
    "restart":      Action.RESTART,

    # --- Debug (dev only — gated by debug_mode) ---
    "worldmodel":   Action.DEBUG_WORLD,
    "world":        Action.DEBUG_WORLD,
    "events":       Action.DEBUG_EVENTS,
    "roomstate":    Action.DEBUG_ROOM,
    "room":         Action.DEBUG_ROOM,
    "objects":      Action.DEBUG_OBJECTS,
    "evaluation":   Action.DEBUG_EVAL,

    # --- Hidden (not documented to player) ---
    "pray":         Action.PRAY,
    "meditate":     Action.MEDITATE,
    "wait":         Action.WAIT,
    "kneel":        Action.KNEEL,
    "silence":      Action.SILENCE,
    "be silent":    Action.SILENCE,
    "observe silence": Action.SILENCE,
    "remain silent":   Action.SILENCE,
}

# ---------------------------------------------------------------------------
# Direction normalisation
# Maps shorthand and synonyms to the canonical direction string.
# ---------------------------------------------------------------------------

DIRECTION_MAP: dict[str, str] = {
    "north": "north", "n": "north",
    "south": "south", "s": "south",
    "east":  "east",  "e": "east",
    "west":  "west",  "w": "west",
    "up":    "up",
    "down":  "down",
    "forward": "north",   # contextual fallback
    "back":    "south",
    "left":    "west",
    "right":   "east",
}

# ---------------------------------------------------------------------------
# Prepositions to strip when extracting targets
# "inspect the statue" → target = "statue"
# "go to the north"    → target = "north"
# ---------------------------------------------------------------------------

STRIP_WORDS: frozenset[str] = frozenset({
    "the", "a", "an", "to", "into", "onto",
    "inside", "against", "from",
})

# Prepositions that signal a secondary target
SECONDARY_PREPOSITIONS: tuple[str, ...] = (
    " into ", " onto ", " on ", " with ", " using ",
    " against ", " in ", " from ", " at ",
)
