"""
command_parser.py — The Lost Temple of Rudra

Translates raw player text input into structured Command objects.
Normalises synonyms so all equivalent inputs resolve to the same action.
Does not execute actions — only interprets intent.

Command categories:
    Observation, Movement, Inventory, Puzzle, Knowledge,
    Help, AI, Debug (dev only), Hidden (discovered via gameplay).

TODO: Implement synonym map (look/observe/inspect/examine → OBSERVE, etc.).
TODO: Implement tokeniser (split raw input into verb + target + modifiers).
TODO: Implement Command dataclass (action, target, modifiers, raw_input).
TODO: Implement handler for all nine command categories.
TODO: Implement hidden command detection (pray, meditate, observe silence).
TODO: Gate debug commands behind debug_mode flag from game_settings.json.
TODO: Return contextual error messages — never "Unknown command."
"""
