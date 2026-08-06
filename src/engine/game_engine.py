"""
game_engine.py — The Lost Temple of Rudra

THE ONLY SYSTEM PERMITTED TO WRITE TO THE WORLD MODEL.

Execution pipeline (every command, every turn):
    1. Receive Command from CommandParser.
    2. Validate against current World Model state.
    3. Execute the command handler.
    4. Update World Model via write interface.
    5. Process puzzle logic (if applicable).
    6. Process dynamic events (evaluate_events → apply EventEffects).
    7. Advance turn counter.
    8. Record history entry.
    9. Return GameResult.

Blueprint Reference:
    Chapter 8  - Command System & Natural Language Parser
    Chapter 13 - Dynamic Event Engine
    Chapter 15 - Software Architecture
    Chapter 20 - Development Roadmap
"""

from __future__ import annotations

from typing import Optional

from src.world.world_model import WorldModel
from src.world.history_state import HistoryEntry
from src.world.object_state import ObjectCategory, StatueDirection
from src.world.puzzle_state import PuzzleStatus
from src.world.story_state import EndingEligibility
from src.world.events import evaluate_events, EventEffect
from src.world.events import (
    EFFECT_SET_FLOOD_LEVEL, EFFECT_SET_FLOOD_ACTIVE, EFFECT_SET_COLLAPSE_STAGE,
    EFFECT_SET_DUST_DENSITY, EFFECT_SET_WORLD_STABILITY,
    EFFECT_SET_ROOM_WATER, EFFECT_SET_ROOM_DUST,
    EFFECT_OPEN_EXIT, EFFECT_CLOSE_EXIT, EFFECT_REVEAL_HIDDEN_PASSAGE,
    EFFECT_UPDATE_OBJECT, EFFECT_UPDATE_BRIDGE,
    EFFECT_UPDATE_TORCH, EFFECT_UPDATE_EVALUATION,
    EFFECT_APPEND_HISTORY, EFFECT_MARK_EVENT_ACTIVE, EFFECT_MARK_EVENT_COMPLETE,
    EFFECT_RESET_STATUE, EFFECT_SET_FLOOD_STATE,
)
from src.utils.constants import (
    HISTORY_PLAYER_ACTION, HISTORY_ENVIRONMENTAL,
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

    def __init__(
        self,
        world_model: WorldModel,
        debug_mode: bool = False,
        ai_manager=None,
    ) -> None:
        self.world_model = world_model
        self.parser = CommandParser(debug_mode=debug_mode)
        self.turn_manager = TurnManager()
        self._debug_mode = debug_mode
        # AI Manager — optional; lazy-initialised on first AI command if None
        self._ai_manager = ai_manager

    # ------------------------------------------------------------------
    # Primary entry point
    # ------------------------------------------------------------------

    def _get_ai_manager(self):
        """Lazy-initialise AI Manager on first use."""
        if self._ai_manager is None:
            try:
                from src.ai.ai_manager import AIManager
                self._ai_manager = AIManager()
            except Exception:  # noqa: BLE001
                self._ai_manager = None
        return self._ai_manager

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

            # Record player history entry
            entry = HistoryEntry(
                turn=new_turn,
                event_id=f"{command.action.value}_{new_turn}",
                category=HISTORY_PLAYER_ACTION,
                description=self._history_description(command, result),
                room_id=wm.player.current_room,
            )
            wm._append_history(entry)

            # Process dynamic events after every successful/failed player turn
            event_effects = evaluate_events(wm, new_turn)
            for effect in event_effects:
                self._apply_event_effect(effect, new_turn)

            # Notify Temple AI of the action (read-only evaluation)
            self._notify_temple_ai(command, result, new_turn)
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
    # Puzzle handler — Phase 5
    # ------------------------------------------------------------------

    def _handle_puzzle(self, command: Command) -> GameResult:
        """
        Execute a puzzle interaction command.

        Pipeline:
            1. Find the puzzle associated with the current room.
            2. Delegate to PuzzleRegistry.attempt() for validation.
            3. Apply all world_effects from the result.
            4. Update PuzzleState.
            5. Apply evaluation impacts.
            6. Return GameResult.
        """
        from src.world.puzzles import PuzzleRegistry, PuzzleAttemptResult

        wm = self.world_model
        turn = self.turn_manager.current_turn
        target = command.target or ""
        action_str = command.action.value

        # Determine which puzzle governs this room
        current_room = wm.get_current_room()
        puzzle_id: Optional[str] = None
        if current_room:
            puzzle_id = current_room.puzzle_id

        # Allow targeting a specific puzzle object regardless of room
        # (player may be adjacent or the object has a puzzle_id)
        if puzzle_id is None and target:
            obj = self._find_object_by_name(target)
            if obj and obj.puzzle_id:
                puzzle_id = obj.puzzle_id

        if puzzle_id is None:
            # No puzzle in room — track recklessness for puzzle action in wrong place
            wm._update_evaluation(EVAL_RECKLESSNESS, 0.5,
                                   f"puzzle action with no puzzle present: {action_str}", turn)
            return GameResult.failure(
                "There is no puzzle mechanism here that responds to that.",
                command=command,
            )

        puzzle_state = wm.puzzles.get(puzzle_id)
        if puzzle_state is None:
            return GameResult.failure(
                "The puzzle mechanism seems disconnected from the rest of the temple.",
                command=command,
            )

        # Record first attempt turn
        if puzzle_state.first_attempted_turn is None:
            wm._update_puzzle_state(puzzle_id, first_attempted_turn=turn + 1)

        # Increment attempt count
        wm._update_puzzle_state(
            puzzle_id,
            attempt_count=puzzle_state.attempt_count + 1,
            status=PuzzleStatus.IN_PROGRESS if puzzle_state.status == PuzzleStatus.AVAILABLE
            else puzzle_state.status,
        )

        # Track recklessness: acting on puzzle without prior observation
        obj = self._find_object_by_name(target) if target else None
        if obj is not None:
            observed = any("observed_turn" in h for h in obj.usage_history)
            if not observed:
                wm._update_evaluation(
                    EVAL_RECKLESSNESS, 0.5,
                    f"puzzle action on {target} without observing first", turn
                )
                wm._update_puzzle_state(puzzle_id, observation_before_action=False)

        # Delegate to registry
        attempt = PuzzleRegistry.attempt(puzzle_id, action_str, target, wm, puzzle_state)

        # Apply world effects
        self._apply_puzzle_effects(attempt, puzzle_id, turn)

        # Apply evaluation impacts
        for attr, delta in attempt.eval_impacts.items():
            if delta != 0.0:
                wm._update_evaluation(attr, delta, f"puzzle:{puzzle_id}", turn)

        # Update puzzle status on success
        if attempt.success:
            solved_in = (turn + 1) - (puzzle_state.first_attempted_turn or turn + 1)
            wm._update_puzzle_state(
                puzzle_id,
                status=PuzzleStatus.SOLVED,
                solved_turn=turn + 1,
                reward_given=True,
                time_to_solve_turns=max(1, solved_in),
                solved_without_hints=(puzzle_state.hint_count == 0),
            )
            # Mark room as puzzle-solved
            if current_room and current_room.puzzle_id == puzzle_id:
                current_room.puzzle_solved = True
            # Record in history
            wm._append_history(HistoryEntry(
                turn=turn + 1,
                event_id=f"puzzle_solved_{puzzle_id}_{turn + 1}",
                category="puzzle",
                description=f"Puzzle solved: {puzzle_id}",
                room_id=wm.player.current_room,
            ))
            return GameResult.success(
                attempt.message,
                command=command,
                actions_taken=[f"puzzle_solved:{puzzle_id}"],
                data={"puzzle_id": puzzle_id, "solved": True},
            )

        # Failure
        if not attempt.partial:
            wm._update_puzzle_state(
                puzzle_id,
                failure_count=puzzle_state.failure_count + 1,
                failure_history=[
                    *puzzle_state.failure_history,
                    f"{action_str}_{target}_turn_{turn}",
                ],
            )

        return GameResult.failure(
            attempt.message,
            command=command,
        ) if not attempt.partial else GameResult.success(
            attempt.message,
            command=command,
            actions_taken=[f"puzzle_progress:{puzzle_id}"],
            data={"puzzle_id": puzzle_id, "partial": True},
        )

    def _apply_puzzle_effects(
        self,
        attempt: "PuzzleAttemptResult",  # type: ignore[name-defined]
        puzzle_id: str,
        turn: int,
    ) -> None:
        """Apply world_effects from a PuzzleAttemptResult to the World Model."""
        from src.world.object_state import StatueDirection

        wm = self.world_model
        effects = attempt.world_effects

        for key, value in effects.items():
            if key == "rotate_statue":
                statue_id, direction_str = value
                try:
                    new_dir = StatueDirection(direction_str)
                except ValueError:
                    continue
                wm._update_object_state(
                    statue_id,
                    facing_direction=new_dir,
                    state=f"facing_{direction_str}",
                    rotation_count=(wm.objects[statue_id].rotation_count + 1
                                    if statue_id in wm.objects else 1),
                    last_rotated_turn=turn + 1,
                )
                # Record in statue reset tracker
                wm.dynamic_events.statues.last_rotated[statue_id] = turn + 1

            elif key == "open_exit":
                room_id, direction, destination = value
                room = wm.rooms.get(room_id)
                if room:
                    room.accessible_exits[direction] = destination

            elif key == "close_exit":
                room_id, direction = value
                room = wm.rooms.get(room_id)
                if room and direction in room.accessible_exits:
                    del room.accessible_exits[direction]

            elif key == "update_object_state":
                obj_id, obj_kwargs = value
                wm._update_object_state(obj_id, **obj_kwargs)

            elif key == "update_object_state_2":
                obj_id, obj_kwargs = value
                wm._update_object_state(obj_id, **obj_kwargs)

            elif key == "update_puzzle_progress":
                wm._update_puzzle_state(puzzle_id, current_progress=value)

            elif key == "trigger_flood":
                wm.dynamic_events.flood.active = True
                wm.dynamic_events.flood.start_turn = turn + 1

            elif key == "activate_water_wheel":
                wm.dynamic_events.flood.water_wheel_active = True

            elif key == "reveal_hidden_passage":
                room_id, direction = value
                room = wm.rooms.get(room_id)
                if room:
                    room.hidden_passages[direction] = True

            elif key == "update_event_state":
                # ("water_gates", gate_id, state)
                sub_key, gate_id, gate_state = value
                if sub_key == "water_gates":
                    wm.dynamic_events.water_gates[gate_id] = gate_state
                    if gate_state:
                        wm.dynamic_events.flood.flood_gates_open.append(gate_id)

            elif key == "consume_object":
                obj_id = value
                if obj_id in wm.player.inventory:
                    wm._remove_from_inventory(obj_id, wm.player.current_room)
                    wm._update_object_state(obj_id, state="used", condition=0.0,
                                            interactable=False)

            elif key == "set_ending_eligibility":
                try:
                    wm.story.ending_eligibility = EndingEligibility(value)
                except ValueError:
                    pass

    # ------------------------------------------------------------------
    # Event effect applicator
    # ------------------------------------------------------------------

    def _apply_event_effect(self, effect: EventEffect, turn: int) -> None:
        """
        Apply a single EventEffect to the World Model.

        Called after every player turn to process dynamic events.
        All writes go through the World Model's write interface.

        Blueprint Reference: Chapter 13 — Dynamic Event Engine.
        """
        wm = self.world_model
        p = effect.payload

        try:
            etype = effect.effect_type

            if etype == EFFECT_UPDATE_TORCH:
                wm.player.torch.fuel = p["fuel"]
                wm.player.torch.state = p["state"]
                wm.player.torch.brightness = p["brightness"]

            elif etype == EFFECT_SET_FLOOD_LEVEL:
                wm.world.flood_level = p["flood_level"]

            elif etype == EFFECT_SET_FLOOD_ACTIVE:
                wm.dynamic_events.flood.active = p["active"]
                if "start_turn" in p:
                    wm.dynamic_events.flood.start_turn = p["start_turn"]

            elif etype == EFFECT_SET_FLOOD_STATE:
                state = wm.dynamic_events.flood
                state.current_stage = p.get("current_stage", state.current_stage)
                for room_id in p.get("affected_rooms", []):
                    if room_id not in state.affected_rooms:
                        state.affected_rooms.append(room_id)
                if not wm.dynamic_events.active_events.__contains__("flood"):
                    wm.dynamic_events.active_events.append("flood")

            elif etype == EFFECT_SET_COLLAPSE_STAGE:
                wm.world.collapse_stage = p["collapse_stage"]
                wm.dynamic_events.collapse.current_stage = p["stage"]
                if not wm.dynamic_events.collapse.active:
                    wm.dynamic_events.collapse.active = True
                    wm.dynamic_events.collapse.start_turn = turn
                if not wm.story.collapse_sequence_started:
                    wm.story.collapse_sequence_started = True

            elif etype == EFFECT_SET_DUST_DENSITY:
                wm.dynamic_events.dust.global_density = p["global_density"]
                wm.world.dust_density = p["global_density"]

            elif etype == EFFECT_SET_WORLD_STABILITY:
                wm.world.world_stability = max(0.0, min(100.0, p["world_stability"]))

            elif etype == EFFECT_SET_ROOM_WATER:
                room = wm.rooms.get(p["room_id"])
                if room:
                    room.water_level = min(100.0, p["water_level"])

            elif etype == EFFECT_SET_ROOM_DUST:
                room = wm.rooms.get(p["room_id"])
                if room:
                    room.dust_level = min(100.0, p["dust_level"])

            elif etype == EFFECT_OPEN_EXIT:
                room = wm.rooms.get(p["room_id"])
                if room:
                    room.accessible_exits[p["direction"]] = p["destination"]

            elif etype == EFFECT_CLOSE_EXIT:
                room = wm.rooms.get(p["room_id"])
                if room and p["direction"] in room.accessible_exits:
                    del room.accessible_exits[p["direction"]]

            elif etype == EFFECT_REVEAL_HIDDEN_PASSAGE:
                room = wm.rooms.get(p["room_id"])
                if room:
                    room.hidden_passages[p["direction"]] = True

            elif etype == EFFECT_UPDATE_OBJECT:
                obj_id = p.pop("object_id", None)
                if obj_id:
                    wm._update_object_state(obj_id, **p)

            elif etype == EFFECT_UPDATE_BRIDGE:
                bridge_id = p["bridge_id"]
                new_integrity = p["integrity"]
                wm.dynamic_events.bridge.integrity[bridge_id] = new_integrity
                if new_integrity <= 0.0:
                    if bridge_id not in wm.dynamic_events.bridge.collapsed_bridges:
                        wm.dynamic_events.bridge.collapsed_bridges.append(bridge_id)

            elif etype == EFFECT_RESET_STATUE:
                from src.world.object_state import StatueDirection
                statue_id = p["statue_id"]
                direction_str = p["direction"]
                try:
                    original_dir = StatueDirection(direction_str)
                except ValueError:
                    return
                wm._update_object_state(
                    statue_id,
                    facing_direction=original_dir,
                    state=f"facing_{direction_str}",
                )
                # Reset puzzle progress
                puzzle = wm.puzzles.get("puzzle_guardian_statues")
                if puzzle:
                    progress = puzzle.current_progress.copy()
                    progress["statues_correct"] = 0
                    wm._update_puzzle_state(
                        "puzzle_guardian_statues",
                        current_progress=progress,
                        status=PuzzleStatus.AVAILABLE,
                    )

            elif etype == EFFECT_UPDATE_EVALUATION:
                attr = p.get("attribute")
                delta = p.get("delta", 0.0)
                reason = p.get("reason", "event")
                if attr:
                    wm._update_evaluation(attr, delta, reason, turn)

            elif etype == EFFECT_APPEND_HISTORY:
                entry = HistoryEntry(
                    turn=p.get("turn", turn),
                    event_id=p.get("event_id", effect.event_id),
                    category=p.get("category", HISTORY_ENVIRONMENTAL),
                    description=p.get("description", effect.description),
                    room_id=p.get("room_id", wm.player.current_room),
                )
                wm._append_history(entry)

            elif etype == EFFECT_MARK_EVENT_ACTIVE:
                event_id = p.get("event_id", effect.event_id)
                if event_id and event_id not in wm.dynamic_events.active_events:
                    wm.dynamic_events.active_events.append(event_id)

            elif etype == EFFECT_MARK_EVENT_COMPLETE:
                event_id = p.get("event_id", effect.event_id)
                if event_id in wm.dynamic_events.active_events:
                    wm.dynamic_events.active_events.remove(event_id)
                if event_id and event_id not in wm.dynamic_events.completed_events:
                    wm.dynamic_events.completed_events.append(event_id)

        except Exception:  # noqa: BLE001
            # Event effects must never crash the game
            pass

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
    # AI handler — Phase 6
    # ------------------------------------------------------------------

    def _handle_ai(self, command: Command) -> GameResult:
        """
        Route AI commands (hint, recommend, analyze, think, status)
        through the AI Manager.
        """
        from src.ai.ai_manager import AIRequest

        wm = self.world_model
        action = command.action
        target = command.target or ""
        ai = self._get_ai_manager()

        # STATUS — always available, no AI needed
        if action == Action.STATUS:
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

        if ai is None:
            return GameResult.info(
                "The temple's intelligence stirs but does not yet respond.",
                command=command,
            )

        # HINT
        if action == Action.HINT:
            response = ai.handle(AIRequest("hint"), wm)
            puzzle = wm.get_current_room()
            if puzzle and puzzle.puzzle_id:
                ps = wm.puzzles.get(puzzle.puzzle_id)
                if ps:
                    wm._update_puzzle_state(
                        puzzle.puzzle_id,
                        hint_count=ps.hint_count + 1,
                        hint_level=min(2, ps.hint_level + 1),
                        solved_without_hints=False,
                    )
            text = response.text or "The temple offers no guidance here."
            return GameResult.info(text, command=command)

        # RECOMMEND
        if action == Action.RECOMMEND:
            response = ai.handle(AIRequest("recommend"), wm)
            text = response.text or "No recommendation available at this time."
            return GameResult.info(text, command=command)

        # ANALYZE
        if action == Action.ANALYZE:
            response = ai.handle(AIRequest("analyze"), wm)
            text = response.text or "Nothing stands out for analysis right now."
            return GameResult.info(text, command=command)

        # THINK (history/reflection)
        if action == Action.THINK:
            response = ai.handle(AIRequest("reflect"), wm)
            text = response.text or "No discoveries to reflect upon yet."
            return GameResult.info(text, command=command)

        return GameResult.info(
            "The temple's intelligence stirs but does not yet respond.",
            command=command,
        )

    def _notify_temple_ai(
        self, command: Command, result, turn: int
    ) -> None:
        """
        Notify the Temple AI of a completed player action.
        Applies any returned evaluation deltas to the World Model.
        This is called AFTER events — it never raises.
        """
        try:
            from src.ai.ai_manager import AIRequest
            ai = self._get_ai_manager()
            if ai is None:
                return
            req = AIRequest(
                request_type="observe_action",
                action_str=command.action.value,
                target=command.target or "",
                result_success=result.status.value == "success",
            )
            response = ai.handle(req, self.world_model)
            # Apply evaluation deltas returned by Temple AI
            for attr, delta in response.eval_deltas.items():
                if delta != 0.0:
                    try:
                        self.world_model._update_evaluation(
                            attr, delta,
                            f"temple_ai:{command.action.value}", turn
                        )
                    except Exception:
                        pass
        except Exception:  # noqa: BLE001 — AI must never crash the game
            pass

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
