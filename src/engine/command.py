"""
command.py — The Lost Temple of Rudra

Defines the canonical command vocabulary and the Command dataclass.

The Command object is the contract between the parser and the game engine.
The parser produces it; the engine consumes it.
Nothing else should need to know how the player typed their input.

Blueprint Reference:
    Chapter 8 — Command System & Natural Language Parser
    Section 8.4 — Command Categories
    Section 8.5 — Canonical Command Dictionary
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Command categories (blueprint Section 8.4)
# ---------------------------------------------------------------------------

class CommandCategory(Enum):
    """
    The nine command categories defined in the blueprint.
    Every canonical action belongs to exactly one category.
    """
    OBSERVATION = "observation"    # look, inspect, examine, read, listen …
    MOVEMENT    = "movement"       # go north, enter, cross, climb …
    INVENTORY   = "inventory"      # take, drop, use, light, equip …
    PUZZLE      = "puzzle"         # rotate, push, pull, insert, align …
    KNOWLEDGE   = "knowledge"      # read, translate, study, remember, compare …
    AI          = "ai"             # recommend, status, hint, analyze …
    SYSTEM      = "system"         # save, load, help, quit, restart …
    DEBUG       = "debug"          # worldmodel, events, roomstate … (dev only)
    HIDDEN      = "hidden"         # pray, meditate, wait … (discovered by player)


# ---------------------------------------------------------------------------
# Canonical action enum (blueprint Section 8.5)
# ---------------------------------------------------------------------------

class Action(Enum):
    """
    Every player intention maps to one of these canonical actions.
    The parser resolves synonyms; the engine switches on Action values.

    Observation
    """
    # --- Observation ---
    LOOK        = "look"        # look / look around
    INSPECT     = "inspect"     # inspect / examine / observe / study <target>
    READ        = "read"        # read <target>
    LISTEN      = "listen"      # listen [to <target>]
    TOUCH       = "touch"       # touch / feel <target>
    SMELL       = "smell"       # smell <target>

    # --- Movement ---
    GO          = "go"          # go <direction>
    ENTER       = "enter"       # enter <target>
    LEAVE       = "leave"       # leave / exit
    CROSS       = "cross"       # cross <target>
    CLIMB       = "climb"       # climb <target>
    DESCEND     = "descend"     # descend / go down

    # --- Inventory ---
    TAKE        = "take"        # take / grab / pick up / collect <target>
    DROP        = "drop"        # drop / put down <target>
    INVENTORY   = "inventory"   # inventory / i / items
    USE         = "use"         # use <object> [on <target>]
    EQUIP       = "equip"       # equip <target>
    LIGHT       = "light"       # light <target>
    EXTINGUISH  = "extinguish"  # extinguish / put out <target>

    # --- Puzzle ---
    ROTATE      = "rotate"      # rotate / turn <target>
    PUSH        = "push"        # push <target>
    PULL        = "pull"        # pull <target>
    INSERT      = "insert"      # insert <object> into <target>
    REMOVE      = "remove"      # remove <target>
    ALIGN       = "align"       # align <target>
    ACTIVATE    = "activate"    # activate / start <target>
    DEACTIVATE  = "deactivate"  # deactivate / stop <target>
    OPEN        = "open"        # open <target>
    CLOSE       = "close"       # close <target>

    # --- Knowledge ---
    TRANSLATE   = "translate"   # translate <target>
    STUDY       = "study"       # study <target>
    REMEMBER    = "remember"    # remember <target>
    COMPARE     = "compare"     # compare <target> [with <secondary>]

    # --- AI assistance ---
    RECOMMEND   = "recommend"   # recommend / suggest
    STATUS      = "status"      # status
    HINT        = "hint"        # hint
    ANALYZE     = "analyze"     # analyze [room]
    THINK       = "think"       # think

    # --- System ---
    HELP        = "help"        # help
    MISSION     = "mission"     # mission / objective
    JOURNAL     = "journal"     # journal
    HISTORY     = "history"     # history
    SAVE        = "save"        # save
    LOAD        = "load"        # load
    QUIT        = "quit"        # quit / exit game
    RESTART     = "restart"     # restart

    # --- Debug (dev only) ---
    DEBUG_WORLD  = "debug_world"   # worldmodel
    DEBUG_EVENTS = "debug_events"  # events
    DEBUG_ROOM   = "debug_room"    # roomstate
    DEBUG_OBJECTS = "debug_objects"  # objects
    DEBUG_EVAL   = "debug_eval"    # evaluation

    # --- Hidden (discovered through play) ---
    PRAY        = "pray"
    MEDITATE    = "meditate"
    WAIT        = "wait"
    KNEEL       = "kneel"
    SILENCE     = "silence"     # "observe silence" / "be silent"


# ---------------------------------------------------------------------------
# Category mapping (Action → CommandCategory)
# ---------------------------------------------------------------------------

ACTION_CATEGORY: dict[Action, CommandCategory] = {
    Action.LOOK:        CommandCategory.OBSERVATION,
    Action.INSPECT:     CommandCategory.OBSERVATION,
    Action.READ:        CommandCategory.OBSERVATION,
    Action.LISTEN:      CommandCategory.OBSERVATION,
    Action.TOUCH:       CommandCategory.OBSERVATION,
    Action.SMELL:       CommandCategory.OBSERVATION,

    Action.GO:          CommandCategory.MOVEMENT,
    Action.ENTER:       CommandCategory.MOVEMENT,
    Action.LEAVE:       CommandCategory.MOVEMENT,
    Action.CROSS:       CommandCategory.MOVEMENT,
    Action.CLIMB:       CommandCategory.MOVEMENT,
    Action.DESCEND:     CommandCategory.MOVEMENT,

    Action.TAKE:        CommandCategory.INVENTORY,
    Action.DROP:        CommandCategory.INVENTORY,
    Action.INVENTORY:   CommandCategory.INVENTORY,
    Action.USE:         CommandCategory.INVENTORY,
    Action.EQUIP:       CommandCategory.INVENTORY,
    Action.LIGHT:       CommandCategory.INVENTORY,
    Action.EXTINGUISH:  CommandCategory.INVENTORY,

    Action.ROTATE:      CommandCategory.PUZZLE,
    Action.PUSH:        CommandCategory.PUZZLE,
    Action.PULL:        CommandCategory.PUZZLE,
    Action.INSERT:      CommandCategory.PUZZLE,
    Action.REMOVE:      CommandCategory.PUZZLE,
    Action.ALIGN:       CommandCategory.PUZZLE,
    Action.ACTIVATE:    CommandCategory.PUZZLE,
    Action.DEACTIVATE:  CommandCategory.PUZZLE,
    Action.OPEN:        CommandCategory.PUZZLE,
    Action.CLOSE:       CommandCategory.PUZZLE,

    Action.TRANSLATE:   CommandCategory.KNOWLEDGE,
    Action.STUDY:       CommandCategory.KNOWLEDGE,
    Action.REMEMBER:    CommandCategory.KNOWLEDGE,
    Action.COMPARE:     CommandCategory.KNOWLEDGE,

    Action.RECOMMEND:   CommandCategory.AI,
    Action.STATUS:      CommandCategory.AI,
    Action.HINT:        CommandCategory.AI,
    Action.ANALYZE:     CommandCategory.AI,
    Action.THINK:       CommandCategory.AI,

    Action.HELP:        CommandCategory.SYSTEM,
    Action.MISSION:     CommandCategory.SYSTEM,
    Action.JOURNAL:     CommandCategory.SYSTEM,
    Action.HISTORY:     CommandCategory.SYSTEM,
    Action.SAVE:        CommandCategory.SYSTEM,
    Action.LOAD:        CommandCategory.SYSTEM,
    Action.QUIT:        CommandCategory.SYSTEM,
    Action.RESTART:     CommandCategory.SYSTEM,

    Action.DEBUG_WORLD:   CommandCategory.DEBUG,
    Action.DEBUG_EVENTS:  CommandCategory.DEBUG,
    Action.DEBUG_ROOM:    CommandCategory.DEBUG,
    Action.DEBUG_OBJECTS: CommandCategory.DEBUG,
    Action.DEBUG_EVAL:    CommandCategory.DEBUG,

    Action.PRAY:        CommandCategory.HIDDEN,
    Action.MEDITATE:    CommandCategory.HIDDEN,
    Action.WAIT:        CommandCategory.HIDDEN,
    Action.KNEEL:       CommandCategory.HIDDEN,
    Action.SILENCE:     CommandCategory.HIDDEN,
}


# ---------------------------------------------------------------------------
# Command dataclass
# ---------------------------------------------------------------------------

@dataclass
class Command:
    """
    A structured, canonical representation of one player input.

    Produced exclusively by CommandParser.
    Consumed exclusively by GameEngine.

    Fields:
        action          The canonical action (what the player wants to do).
        target          Primary target of the action, normalised lowercase.
                        e.g. "statue", "north", "torch"
        secondary_target  Optional secondary target for two-object commands.
                        e.g. "insert disc into pedestal" → target="disc",
                             secondary_target="pedestal"
        raw_input       The original, unmodified player string.
        category        Derived from ACTION_CATEGORY; set by parser.
    """
    action: Action
    target: Optional[str] = None
    secondary_target: Optional[str] = None
    raw_input: str = ""
    category: CommandCategory = CommandCategory.OBSERVATION

    def __post_init__(self) -> None:
        # Derive category from action if not explicitly supplied
        self.category = ACTION_CATEGORY.get(self.action, CommandCategory.OBSERVATION)

    def __str__(self) -> str:
        parts = [self.action.value]
        if self.target:
            parts.append(self.target)
        if self.secondary_target:
            parts.append(f"→ {self.secondary_target}")
        return " ".join(parts)
