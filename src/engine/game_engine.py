"""
game_engine.py — The Lost Temple of Rudra

THE ONLY SYSTEM PERMITTED TO WRITE TO THE WORLD MODEL.

Execution pipeline (every command, every turn):
    1. Receive Command from CommandParser.
    2. Validate against current World Model state.
    3. Execute the command handler.
    4. Update World Model via write interface.
    5. Advance turn counter.
    6. Record history entry.
    7. Return GameResult.

No Temple AI. No Explorer AI. No narration generation. No puzzle logic.
No dynamic events. Phase 4 scope: Room System + Object System + Inventory.

Blueprint Reference:
    Chapter 8  - Command System & Natural Language Parser
    Chapter 15 - Software Architecture
    Chapter 20 - Development Roadmap
"""

from __future__ import annotations

from typing import Optional

from src.world.world_model import WorldModel
from src.world.history_state import HistoryEntry
from src.world.object_state import ObjectCategory
from src.utils.constants import (
    HISTORY_PLAYER_ACTION,
    EVAL_OBSERVATION, EVAL_CURIOSITY, EVAL_RECKLESSNESS,
    EVAL_DELTA_OBSERVE, EVAL_DELTA_EXPLORE,
    DIR_NORTH, DIR_SOUTH, DIR_EAST, DIR_WEST,
)

from .command import Action, Command, CommandCategory
from .command_parser import CommandParser, ParseResult
from .command_result import GameResult, ResultStatus
from .turn_manager import TurnManager


class GameEngine:
    """
    Central authority for all gameplay logic.

    Owns the TurnManager. Receives Commands from the parser, validates them
    against the World Model, executes the appropriate handler, and writes
    every state change through WorldModel's write interface.

    No other module may call World Model write methods.

    Blueprint Reference: Chapter 15.4 — Game Engine module responsibilities.
    """

    def __init__(self, world_model: WorldModel, debug_mode: bool = False) -> None:
        self.world_model = world_model
        self.parser = CommandParser(debug_mode=debug_mode)
        self.turn_manager = TurnManager()
        self._debug_mode = debug_mode

    # ------------------------------------------------------------------
    # Primary entry point
    # ------------------------------------------------------------------

    def process_input(self, raw_input: str) -> GameResult:
        """
        Full pipeline: parse raw player text → validate → execute → return result.

        This is the single method the UI (or test) calls per player action.
        Always returns a GameResult — never raises.
        """
        # Step 1 — Parse
        parse_result = self.parser.parse(raw_input)
        if not parse_result.success:
            return GameResult.invalid(parse_result.error_message)

        command = parse_result.command
        return self.execute(command)

    def execute(self, command: Command) -> GameResult:
        """
        Execute a pre-parsed Command against the current World Model.

        Validates, runs the appropriate handler, records history, advances turn.
        Returns a GameResult describing the outcome.
        """
        wm = self.world_model

        # --- Record the raw input in player command history ---
        wm._record_command(command.raw_input or str(command))

        # --- Dispatch to category handler ---
        result = self._dispatch(command)

        # --- Advance turn and sync World Model on any meaningful action ---
        if result.status in (ResultStatus.SUCCESS, ResultStatus.FAILURE):
            new_turn = self.turn_manager.advance()
            wm._increment_turn()
            result.turn = new_turn

            # Update world phase from turn manager
            wm.world.temple_phase = self.turn_manager.get_phase()

            # Record history entry
            entry = HistoryEntry(
                turn=new_turn,
                event_id=f"{command.action.value}_{new_turn}",
                category=HISTORY_PLAYER_ACTION,
                description=self._history_description(command, result),
                room_id=wm.player.current_room,
            )
            wm._append_history(entry)
        else:
            result.turn = self.turn_manager.current_turn

        return result

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def _dispatch(self, command: Command) -> GameResult:
        """Route command to its category handler."""
        category = command.category

        if category == CommandCategory.OBSERVATION:
            return self._handle_observation(command)
        if category == CommandCategory.MOVEMENT:
            return self._handle_movement(command)
        if category == CommandCategory.INVENTORY:
            return self._handle_inventory(command)
        if category == CommandCategory.PUZZLE:
            return self._handle_puzzle(command)
        if category == CommandCategory.KNOWLEDGE:
            return self._handle_knowledge(command)
        if category == CommandCategory.AI:
            return self._handle_ai(command)
        if category == CommandCategory.SYSTEM:
            return self._handle_system(command)
        if category == CommandCategory.DEBUG:
            return self._handle_debug(command)
        if category == CommandCategory.HIDDEN:
            return self._handle_hidden(command)

        return GameResult.invalid(
            "That intention doesn't translate into any action the temple recognises.",
            command=command,
        )

    # ------------------------------------------------------------------
    # Observation handler
    # ------------------------------------------------------------------

    def _handle_observation(self, command: Command) -> GameResult:
        wm = self.world_model
        action = command.action
        target = command.target
        turn = self.turn_manager.current_turn

        # LOOK / LOOK AROUND — describe current room
        if action == Action.LOOK:
            room = wm.get_current_room()
            if room is None:
                return GameResult.failure(
                    "You stand in an undefined space. Something has gone wrong.",
                    command=command,
                )

            # Try to get a description from the room definition
            from src.world.rooms import ROOM_DEFINITIONS
            rd = ROOM_DEFINITIONS.get(room.room_id)
            description = rd.description if rd else (
                f"You survey {wm.player.current_room.replace('_', ' ')}."
            )

            # List visible objects in the room
            visible_objects = [
                wm.objects[oid].name
                for oid in room.object_ids_present
                if oid in wm.objects and wm.objects[oid].visible
            ]

            # List accessible exits
            exits = list(room.accessible_exits.keys())

            wm._update_evaluation(EVAL_CURIOSITY, EVAL_DELTA_OBSERVE,
                                   "looked around room", turn)
            room.times_inspected += 1

            # Mark room as visited
            if not room.visited:
                room.visited = True
                room.first_visited_turn = turn + 1

            obj_line = ""
            if visible_objects:
                obj_line = " You can see: " + ", ".join(visible_objects) + "."
            exit_line = ""
            if exits:
                exit_line = " Exits: " + ", ".join(exits) + "."

            return GameResult.success(
                description + obj_line + exit_line,
                command=command,
                actions_taken=["room_inspected", "curiosity+"],
                data={
                    "room_id": room.room_id,
                    "exits": exits,
                    "objects_present": [
                        oid for oid in room.object_ids_present
                        if oid in wm.objects and wm.objects[oid].visible
                    ],
                },
            )

        # INSPECT / READ / LISTEN / TOUCH / SMELL — target required
        if target is None:
            return GameResult.failure(
                "What would you like to inspect? "
                "The temple offers many things worthy of attention.",
                command=command,
            )

        # Check if target object exists in current room or inventory
        obj = self._find_object_by_name(target)

        if obj is not None:
            # Use the object definition description if available
            from src.world.objects import OBJECT_DEFINITIONS
            od = OBJECT_DEFINITIONS.get(obj.object_id)
            obj_description = od.description if od else f"The {target}."

            obj.usage_history.append(f"observed_turn_{turn}")
            if not hasattr(obj, "times_inspected"):
                obj.times_inspected = 1
            else:
                obj.times_inspected = getattr(obj, "times_inspected", 0) + 1
            wm._update_evaluation(EVAL_OBSERVATION, EVAL_DELTA_OBSERVE,
                                   f"inspected {target}", turn)

            # Mark story objects as discovered
            if obj.state == "undiscovered":
                wm._update_object_state(obj.object_id, state="discovered")
                if obj.object_id.startswith("inscription_"):
                    wm.story.entrance_inscription_read = True

            return GameResult.success(
                obj_description,
                command=command,
                actions_taken=[f"object_observed:{obj.object_id}", "observation+"],
                data={"object_id": obj.object_id, "object_state": obj.state},
            )

        # Target not found — in-world response (blueprint 8.7)
        return GameResult.failure(
            f"You see nothing here that could be described as '{target}'.",
            command=command,
        )

    # ------------------------------------------------------------------
    # Movement handler
    # ------------------------------------------------------------------

    def _handle_movement(self, command: Command) -> GameResult:
        wm = self.world_model
        turn = self.turn_manager.current_turn

        action = command.action
        target = command.target

        # LEAVE / EXIT — move to previous room if available
        if action == Action.LEAVE:
            if wm.player.previous_room and wm.player.previous_room in wm.rooms:
                return self._move_to(wm.player.previous_room, command, turn)
            return GameResult.failure(
                "There is no obvious way back from here.", command=command
            )

        # Resolve direction from target or action
        direction = self._resolve_direction(action, target)

        if direction is None:
            return GameResult.failure(
                "Which direction? The temple stretches in many directions.",
                command=command,
            )

        # Check current room exits
        current_room = wm.get_current_room()
        if current_room is None:
            return GameResult.failure(
                "You are nowhere. The world model has no record of your location.",
                command=command,
            )

        # Check accessibility
        destination_id = current_room.accessible_exits.get(direction)
        if destination_id is None or destination_id is False:
            return GameResult.failure(
                f"You cannot go {direction} from here. "
                "The way is blocked, sealed, or simply does not exist.",
                command=command,
            )

        # destination_id might be a bool True (direction exists but no room mapped)
        if not isinstance(destination_id, str):
            return GameResult.failure(
                f"The passage {direction} leads nowhere yet.", command=command
            )

        if destination_id not in wm.rooms:
            return GameResult.failure(
                f"The passage {direction} leads into darkness. "
                "That room has not been built yet.",
                command=command,
            )

        return self._move_to(destination_id, command, turn)

    def _move_to(self, room_id: str, command: Command, turn: int) -> GameResult:
        wm = self.world_model
        first_visit = room_id not in wm.player.visited_rooms
        wm._update_player_room(room_id, turn + 1)  # +1 because turn advances after
        if first_visit:
            wm._update_evaluation(EVAL_CURIOSITY, EVAL_DELTA_EXPLORE,
                                   f"entered new room {room_id}", turn)
        return GameResult.success(
            f"You move to {room_id.replace('_', ' ')}.",
            command=command,
            actions_taken=[f"moved_to:{room_id}", "curiosity+" if first_visit else "moved"],
        )

    def _resolve_direction(
        self, action: Action, target: Optional[str]
    ) -> Optional[str]:
        """Resolve a canonical direction string from action + target."""
        from .command_registry import DIRECTION_MAP

        # Bare direction words parsed as GO with target = direction
        if target:
            resolved = DIRECTION_MAP.get(target.lower())
            if resolved:
                return resolved

        # Action itself is a direction (e.g. bare "north" → Action.GO target="north")
        if target in (DIR_NORTH, DIR_SOUTH, DIR_EAST, DIR_WEST, "up", "down"):
            return target

        return None

    # ------------------------------------------------------------------
    # Inventory handler
    # ------------------------------------------------------------------

    def _handle_inventory(self, command: Command) -> GameResult:
        wm = self.world_model
        action = command.action
        target = command.target
        turn = self.turn_manager.current_turn

        # INVENTORY — list contents
        if action == Action.INVENTORY:
            items = wm.player.inventory
            if not items:
                return GameResult.info(
                    "You carry nothing. Your hands are empty.",
                    command=command,
                    data={"inventory": []},
                )
            names = [wm.objects[oid].name if oid in wm.objects else oid
                     for oid in items]
            return GameResult.info(
                "You are carrying: " + ", ".join(names) + ".",
                command=command,
                data={"inventory": items},
            )

        if target is None:
            return GameResult.failure(
                "What would you like to interact with?", command=command
            )

        # TAKE — pick up an object from current room
        if action == Action.TAKE:
            obj = self._find_object_in_room(target)
            if obj is None:
                return GameResult.failure(
                    f"You see no '{target}' here that can be taken.",
                    command=command,
                )
            # Enforce: only COLLECTIBLE objects may enter inventory
            if obj.category != ObjectCategory.COLLECTIBLE:
                return GameResult.failure(
                    f"The {target} cannot be carried. "
                    "Some things belong to the temple.",
                    command=command,
                )
            if not obj.interactable:
                return GameResult.failure(
                    f"The {target} cannot be moved.", command=command
                )
            if obj.object_id in wm.player.inventory:
                return GameResult.failure(
                    f"You are already carrying the {target}.", command=command
                )
            wm._add_to_inventory(obj.object_id)
            wm._update_evaluation(EVAL_CURIOSITY, 0.5,
                                   f"collected {target}", turn)
            return GameResult.success(
                f"You pick up the {target}.",
                command=command,
                actions_taken=[f"took:{obj.object_id}", "inventory_updated"],
            )

        # DROP — place object in current room
        if action == Action.DROP:
            obj = self._find_object_in_inventory(target)
            if obj is None:
                return GameResult.failure(
                    f"You are not carrying any '{target}'.", command=command
                )
            wm._remove_from_inventory(obj.object_id, wm.player.current_room)
            return GameResult.success(
                f"You set down the {target}.",
                command=command,
                actions_taken=[f"dropped:{obj.object_id}", "inventory_updated"],
            )

        # USE
        if action == Action.USE:
            obj = self._find_object_by_name(target)
            if obj is None:
                return GameResult.failure(
                    f"You don't have a '{target}' to use.", command=command
                )
            return GameResult.success(
                f"You use the {target}. "
                "(Specific use effects will be implemented in later phases.)",
                command=command,
                actions_taken=[f"used:{obj.object_id}"],
            )

        # LIGHT
        if action == Action.LIGHT:
            obj = self._find_object_by_name(target)
            if obj is None:
                return GameResult.failure(
                    f"There is nothing called '{target}' to light.", command=command
                )
            wm._update_object_state(obj.object_id, state="lit", activated=True)
            if target in ("torch", "torches") or "torch" in obj.name.lower():
                wm.player.torch.state = "lit"
                wm.player.torch.last_lit_turn = self.turn_manager.current_turn
            return GameResult.success(
                f"You light the {target}. Warm light spills across the ancient stone.",
                command=command,
                actions_taken=[f"lit:{obj.object_id}"],
            )

        # EXTINGUISH
        if action == Action.EXTINGUISH:
            obj = self._find_object_by_name(target)
            if obj is None:
                return GameResult.failure(
                    f"There is no '{target}' to extinguish.", command=command
                )
            wm._update_object_state(obj.object_id, state="extinguished", activated=False)
            return GameResult.success(
                f"You extinguish the {target}. Darkness presses in.",
                command=command,
                actions_taken=[f"extinguished:{obj.object_id}"],
            )

        return GameResult.failure(
            f"You are unsure how to do that with '{target}'.", command=command
        )

    # ------------------------------------------------------------------
    # Puzzle handler (stub — Phase 7)
    # ------------------------------------------------------------------

    def _handle_puzzle(self, command: Command) -> GameResult:
        target = command.target or "that"
        wm = self.world_model
        turn = self.turn_manager.current_turn

        # Track reckless interaction (acting without observing)
        obj = self._find_object_by_name(target) if command.target else None
        if obj is not None:
            observed = any(
                f"observed_turn_" in h for h in obj.usage_history
            )
            if not observed:
                wm._update_evaluation(
                    EVAL_RECKLESSNESS, 0.5,
                    f"puzzle action on {target} without observing first", turn
                )

        return GameResult.success(
            f"You attempt to {command.action.value} the {target}. "
            "(Puzzle logic will be implemented in Phase 7.)",
            command=command,
            actions_taken=[f"puzzle_action:{command.action.value}:{target}"],
        )

    # ------------------------------------------------------------------
    # Knowledge handler
    # ------------------------------------------------------------------

    def _handle_knowledge(self, command: Command) -> GameResult:
        wm = self.world_model
        target = command.target or "that"
        turn = self.turn_manager.current_turn

        obj = self._find_object_by_name(target) if command.target else None
        if obj is not None:
            obj.usage_history.append(f"knowledge_action_turn_{turn}")
            wm._update_evaluation(EVAL_OBSERVATION, EVAL_DELTA_OBSERVE,
                                   f"knowledge action on {target}", turn)

        return GameResult.success(
            f"You {command.action.value} the {target}. "
            "(Deep knowledge processing will be implemented in Phase 11.)",
            command=command,
            actions_taken=[f"knowledge:{command.action.value}:{target}", "observation+"],
        )

    # ------------------------------------------------------------------
    # AI handler (stub — Phase 11/12)
    # ------------------------------------------------------------------

    def _handle_ai(self, command: Command) -> GameResult:
        if command.action == Action.STATUS:
            wm = self.world_model
            return GameResult.info(
                f"Turn: {self.turn_manager.current_turn} | "
                f"Phase: {self.turn_manager.get_phase().name} | "
                f"Room: {wm.player.current_room} | "
                f"Inventory: {len(wm.player.inventory)} item(s)",
                command=command,
                data={
                    "turn": self.turn_manager.current_turn,
                    "phase": self.turn_manager.get_phase().name,
                    "room": wm.player.current_room,
                    "inventory_count": len(wm.player.inventory),
                },
            )
        return GameResult.info(
            "The temple's intelligence is not yet fully awakened. "
            "(AI integration arrives in Phase 11.)",
            command=command,
        )

    # ------------------------------------------------------------------
    # System handler
    # ------------------------------------------------------------------

    def _handle_system(self, command: Command) -> GameResult:
        action = command.action

        if action == Action.HELP:
            return GameResult.system(
                "Commands: look, inspect <object>, go <direction>, "
                "take <object>, drop <object>, inventory, use <object>, "
                "rotate <object>, read <object>, status, hint, mission, "
                "save, load, quit.",
                command=command,
            )

        if action == Action.MISSION:
            wm = self.world_model
            return GameResult.info(
                f"Current objective: {wm.mission.current_goal_description}",
                command=command,
                data={"mission": wm.mission.current_goal_description},
            )

        if action == Action.JOURNAL:
            wm = self.world_model
            discovered = wm.story.lore_ids_discovered
            return GameResult.info(
                f"Journal entries: {len(discovered)} discovered.",
                command=command,
                data={"lore_discovered": discovered},
            )

        if action == Action.HISTORY:
            wm = self.world_model
            last = wm.history.get_last_n_entries(5)
            lines = [f"Turn {e.turn}: {e.description}" for e in last]
            return GameResult.info(
                "\n".join(lines) if lines else "No history yet.",
                command=command,
                data={"entries": [e.description for e in last]},
            )

        if action == Action.QUIT:
            return GameResult.system("Farewell, explorer.", command=command)

        if action == Action.RESTART:
            return GameResult.system(
                "Restart is not yet wired to the UI. (Phase 10.)",
                command=command,
            )

        if action in (Action.SAVE, Action.LOAD):
            return GameResult.system(
                "Save and Load will be implemented in Phase 9.",
                command=command,
            )

        return GameResult.info(
            f"System command '{command.action.value}' acknowledged.",
            command=command,
        )

    # ------------------------------------------------------------------
    # Debug handler
    # ------------------------------------------------------------------

    def _handle_debug(self, command: Command) -> GameResult:
        if not self._debug_mode:
            return GameResult.invalid("Debug commands are not available.", command=command)

        wm = self.world_model
        action = command.action

        if action == Action.DEBUG_WORLD:
            return GameResult.info(
                str(wm.world), command=command,
                data={"world": wm.world.__dict__},
            )
        if action == Action.DEBUG_ROOM:
            room = wm.get_current_room()
            return GameResult.info(
                str(room) if room else "No room data.",
                command=command,
                data={"room": room.__dict__ if room else {}},
            )
        if action == Action.DEBUG_OBJECTS:
            return GameResult.info(
                f"{len(wm.objects)} objects in world model.",
                command=command,
                data={"objects": list(wm.objects.keys())},
            )
        if action == Action.DEBUG_EVAL:
            scores = {
                attr: round(getattr(wm.evaluation, attr).score, 1)
                for attr in (
                    "observation", "curiosity", "wisdom", "patience",
                    "adaptation", "integrity", "responsibility",
                    "understanding", "greed", "recklessness",
                )
            }
            return GameResult.info(str(scores), command=command, data=scores)
        if action == Action.DEBUG_EVENTS:
            return GameResult.info(
                f"Active events: {wm.dynamic_events.active_events}",
                command=command,
                data={"active": wm.dynamic_events.active_events},
            )

        return GameResult.info("Unknown debug command.", command=command)

    # ------------------------------------------------------------------
    # Hidden command handler
    # ------------------------------------------------------------------

    def _handle_hidden(self, command: Command) -> GameResult:
        wm = self.world_model
        turn = self.turn_manager.current_turn

        messages = {
            Action.PRAY: (
                "You close your eyes and bow your head. "
                "The temple grows very still.",
                "patience",
            ),
            Action.MEDITATE: (
                "You sit in silence. Ancient dust settles around you. "
                "Something in the temple shifts.",
                "wisdom",
            ),
            Action.WAIT: (
                "You stand motionless. Time passes. "
                "The temple continues its ancient rhythms.",
                "patience",
            ),
            Action.KNEEL: (
                "You kneel before the ancient stonework. "
                "A faint resonance passes through the floor.",
                "integrity",
            ),
            Action.SILENCE: (
                "You remain perfectly still and silent. "
                "The temple seems to breathe.",
                "understanding",
            ),
        }

        msg_pair = messages.get(command.action)
        if msg_pair:
            message, eval_attr = msg_pair
            wm._update_evaluation(eval_attr, 1.0,
                                   f"hidden action: {command.action.value}", turn)
            return GameResult.success(
                message, command=command,
                actions_taken=[f"hidden:{command.action.value}", f"{eval_attr}+"],
            )

        return GameResult.info("Nothing happens.", command=command)

    # ------------------------------------------------------------------
    # Object lookup helpers (read-only — no World Model writes)
    # ------------------------------------------------------------------

    def _find_object_by_name(self, name: str):
        """
        Find an object by name in the current room OR in the player's inventory.
        Returns ObjectState or None.
        Case-insensitive partial match on object name.
        """
        wm = self.world_model
        name_lower = name.lower()

        # Check inventory first
        for oid in wm.player.inventory:
            obj = wm.objects.get(oid)
            if obj and name_lower in obj.name.lower():
                return obj

        # Check current room
        room = wm.get_current_room()
        if room:
            for oid in room.object_ids_present:
                obj = wm.objects.get(oid)
                if obj and name_lower in obj.name.lower():
                    return obj

        return None

    def _find_object_in_room(self, name: str):
        """Find an object by name only in the current room (not inventory)."""
        wm = self.world_model
        name_lower = name.lower()
        room = wm.get_current_room()
        if room:
            for oid in room.object_ids_present:
                obj = wm.objects.get(oid)
                if obj and name_lower in obj.name.lower() and obj.visible:
                    return obj
        return None

    def _find_object_in_inventory(self, name: str):
        """Find an object by name only in the player's inventory."""
        wm = self.world_model
        name_lower = name.lower()
        for oid in wm.player.inventory:
            obj = wm.objects.get(oid)
            if obj and name_lower in obj.name.lower():
                return obj
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _history_description(command: Command, result: GameResult) -> str:
        """Build a concise history log string from command + result."""
        base = f"{command.action.value.capitalize()}"
        if command.target:
            base += f" {command.target}"
        if result.status == ResultStatus.FAILURE:
            base += " (failed)"
        return base
