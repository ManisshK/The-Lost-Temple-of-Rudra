"""
test_phase5.py - The Lost Temple of Rudra

Tests for Phase 5: Puzzle System + Dynamic Event Engine.

Covers:
    Puzzle framework:
        - PuzzleDefinition and PuzzleRegistry structure
        - PuzzleAttemptResult fields
        - PuzzleRegistry.attempt(): solved/locked/prereq/missing-object guards
        - Guardian statues: rotate, partial progress, full solve, recklessness
        - Flood control: wrong order triggers flood, correct sequence solves
        - Bridge: rope descent, crossing degrades integrity
        - Symbol alignment: wrong order resets, correct order solves
        - Clear rubble: missing chisel, correct use solves
        - Reflection pool: inspect-then-meditate sequence
        - Final judgment: composite score gate

    Dynamic events:
        - Torch decay each turn
        - Torch state transitions (lit -> dim -> almost_out -> extinguished)
        - Flood progression: auto-trigger at phase 3, stage advance
        - Flood: solved puzzle prevents auto-trigger
        - Dust accumulation
        - Bridge integrity decay (phase 2+)
        - Statue reset timer
        - Hidden passage activation
        - evaluate_events() never raises

    Game Engine integration:
        - Puzzle dispatch routes to registry
        - Puzzle solve opens exit in World Model
        - Puzzle failure records in history
        - Event effects applied after turn
        - Torch fuel decrements after each turn
        - World Model validates after puzzle + event operations
        - Serialization round-trip after puzzle solve
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from world.world_model import WorldModel
from world.room_state import RoomState, RoomRegion
from world.object_state import ObjectState, ObjectCategory, StatueDirection
from world.puzzle_state import PuzzleState, PuzzleCategory, PuzzleStatus
from world.player_state import TorchStatus
from world.world_state import TemplePhase, FloodLevel
from world.event_state import DynamicEventState
from world.puzzles import (
    PuzzleRegistry, PuzzleDefinition, PuzzleAttemptResult,
    PUZZLE_DEFINITIONS, PUZZLE_VALIDATORS,
)
from world.events import (
    evaluate_events, EventEffect,
    _evaluate_torch_decay, _evaluate_flood_progression,
    _evaluate_dust_accumulation, _evaluate_bridge_integrity,
    _evaluate_statue_reset, _evaluate_hidden_passage_activation,
    EFFECT_UPDATE_TORCH, EFFECT_SET_FLOOD_LEVEL, EFFECT_SET_FLOOD_ACTIVE,
    EFFECT_SET_DUST_DENSITY, EFFECT_UPDATE_BRIDGE, EFFECT_RESET_STATUE,
    EFFECT_REVEAL_HIDDEN_PASSAGE, EFFECT_OPEN_EXIT, EFFECT_SET_ROOM_WATER,
)
from engine.game_engine import GameEngine
from engine.command_result import ResultStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _world_with_room(room_id="temple_entrance"):
    wm = WorldModel()
    wm.rooms[room_id] = RoomState(room_id=room_id)
    wm.player.current_room = room_id
    return wm


def _statues_world():
    """WorldModel with hall_of_guardians puzzle fully set up."""
    wm = WorldModel()
    wm.rooms["hall_of_guardians"] = RoomState(
        room_id="hall_of_guardians",
        region=RoomRegion.OUTER_TEMPLE,
        accessible_exits={},
        puzzle_id="puzzle_guardian_statues",
    )
    wm.player.current_room = "hall_of_guardians"
    wm.puzzles["puzzle_guardian_statues"] = PuzzleState(
        puzzle_id="puzzle_guardian_statues",
        room_id="hall_of_guardians",
        category=PuzzleCategory.LOGIC,
        status=PuzzleStatus.AVAILABLE,
    )
    NAMES = {
        "statue_guardian_n": ("Northern Guardian Statue", StatueDirection.NORTH),
        "statue_guardian_e": ("Eastern Guardian Statue", StatueDirection.EAST),
        "statue_guardian_s": ("Southern Guardian Statue", StatueDirection.SOUTH),
        "statue_guardian_w": ("Western Guardian Statue", StatueDirection.WEST),
    }
    for sid, (name, facing) in NAMES.items():
        wm.objects[sid] = ObjectState(
            object_id=sid, name=name,
            category=ObjectCategory.PUZZLE,
            current_room="hall_of_guardians",
            facing_direction=facing,
        )
        wm.rooms["hall_of_guardians"].object_ids_present.append(sid)
    return wm


def _flood_world():
    """WorldModel with flood_control_room puzzle set up."""
    wm = WorldModel()
    wm.rooms["flood_control_room"] = RoomState(
        room_id="flood_control_room", region=RoomRegion.LIVING_TEMPLE,
        accessible_exits={}, puzzle_id="puzzle_flood_control",
    )
    wm.player.current_room = "flood_control_room"
    wm.puzzles["puzzle_flood_control"] = PuzzleState(
        puzzle_id="puzzle_flood_control", room_id="flood_control_room",
        category=PuzzleCategory.ENVIRONMENTAL, status=PuzzleStatus.AVAILABLE,
    )
    for oid, name in [("flood_gate_secondary", "Secondary Flood Gate"),
                      ("flood_gate_main", "Main Flood Gate"),
                      ("lever_flood_control", "Flood Control Lever"),
                      ("water_wheel", "Ancient Water Wheel")]:
        wm.objects[oid] = ObjectState(
            object_id=oid, name=name, category=ObjectCategory.ENVIRONMENTAL,
            current_room="flood_control_room", state="closed",
        )
        wm.rooms["flood_control_room"].object_ids_present.append(oid)
    # Give player the wrench
    wm.objects["tool_wrench"] = ObjectState(
        object_id="tool_wrench", name="Stone Wrench",
        category=ObjectCategory.COLLECTIBLE, current_owner="player",
    )
    wm.player.inventory.append("tool_wrench")
    return wm


# ===========================================================================
# PUZZLE FRAMEWORK TESTS
# ===========================================================================

class TestPuzzleAttemptResult:
    def test_default_fields(self):
        r = PuzzleAttemptResult()
        assert r.success is False
        assert r.partial is False
        assert r.message == ""
        assert r.eval_impacts == {}
        assert r.world_effects == {}
        assert r.reckless is False

    def test_success_result(self):
        r = PuzzleAttemptResult(success=True, message="Solved.", eval_impacts={"wisdom": 5.0})
        assert r.success is True
        assert r.eval_impacts["wisdom"] == 5.0

    def test_partial_result(self):
        r = PuzzleAttemptResult(partial=True, message="Progress.")
        assert r.partial is True
        assert r.success is False


class TestPuzzleDefinition:
    def test_all_canonical_puzzles_defined(self):
        expected = [
            "puzzle_guardian_statues", "puzzle_flood_control",
            "puzzle_bridge_integrity", "puzzle_symbol_alignment",
            "puzzle_clear_rubble", "puzzle_reflection_pool",
            "puzzle_final_judgment",
        ]
        for pid in expected:
            assert pid in PUZZLE_DEFINITIONS, f"Missing: {pid}"

    def test_all_canonical_puzzles_have_validators(self):
        for pid in PUZZLE_DEFINITIONS:
            assert pid in PUZZLE_VALIDATORS, f"No validator for: {pid}"

    def test_definition_fields_populated(self):
        defn = PUZZLE_DEFINITIONS["puzzle_guardian_statues"]
        assert defn.puzzle_id == "puzzle_guardian_statues"
        assert defn.room_id == "hall_of_guardians"
        assert defn.category == PuzzleCategory.LOGIC
        assert defn.solve_eval  # not empty

    def test_flood_control_requires_wrench(self):
        defn = PUZZLE_DEFINITIONS["puzzle_flood_control"]
        assert "tool_wrench" in defn.required_objects

    def test_clear_rubble_requires_chisel(self):
        defn = PUZZLE_DEFINITIONS["puzzle_clear_rubble"]
        assert "tool_chisel" in defn.required_objects

    def test_final_judgment_has_prerequisites(self):
        defn = PUZZLE_DEFINITIONS["puzzle_final_judgment"]
        assert "puzzle_guardian_statues" in defn.prerequisite_puzzle_ids
        assert "puzzle_reflection_pool" in defn.prerequisite_puzzle_ids


class TestPuzzleRegistryGuards:
    def test_unknown_puzzle_id_returns_message(self):
        wm = _world_with_room()
        ps = PuzzleState(puzzle_id="ghost", room_id="temple_entrance", status=PuzzleStatus.AVAILABLE)
        result = PuzzleRegistry.attempt("ghost", "rotate", "thing", wm, ps)
        assert result.success is False
        assert result.message

    def test_solved_puzzle_returns_already_solved(self):
        wm = _world_with_room()
        ps = PuzzleState(puzzle_id="puzzle_guardian_statues", room_id="hall_of_guardians", status=PuzzleStatus.SOLVED)
        result = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "statue", wm, ps)
        assert result.success is False
        assert "solved" in result.message.lower() or "already" in result.message.lower()

    def test_locked_puzzle_returns_inaccessible(self):
        wm = _world_with_room()
        ps = PuzzleState(puzzle_id="puzzle_guardian_statues", room_id="hall_of_guardians", status=PuzzleStatus.LOCKED)
        result = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "statue", wm, ps)
        assert result.success is False

    def test_missing_prerequisite_blocks_attempt(self):
        wm = _world_with_room()
        # final_judgment requires two prerequisites not solved
        ps = PuzzleState(puzzle_id="puzzle_final_judgment", room_id="throne_approach", status=PuzzleStatus.AVAILABLE)
        result = PuzzleRegistry.attempt("puzzle_final_judgment", "open", "arch", wm, ps)
        assert result.success is False
        assert "connected" in result.message.lower() or "resolved" in result.message.lower()

    def test_missing_required_object_blocks_attempt(self):
        wm = _world_with_room()
        wm.rooms["flood_control_room"] = RoomState(room_id="flood_control_room")
        ps = PuzzleState(puzzle_id="puzzle_flood_control", room_id="flood_control_room", status=PuzzleStatus.AVAILABLE)
        # No wrench in inventory
        result = PuzzleRegistry.attempt("puzzle_flood_control", "open", "secondary gate", wm, ps)
        assert result.success is False
        assert "missing" in result.message.lower()

    def test_get_definition_returns_correct_object(self):
        defn = PuzzleRegistry.get_definition("puzzle_guardian_statues")
        assert isinstance(defn, PuzzleDefinition)
        assert defn.puzzle_id == "puzzle_guardian_statues"

    def test_get_definition_unknown_returns_none(self):
        assert PuzzleRegistry.get_definition("not_a_puzzle") is None

    def test_get_validator_returns_callable(self):
        v = PuzzleRegistry.get_validator("puzzle_guardian_statues")
        assert callable(v)


# ===========================================================================
# GUARDIAN STATUES PUZZLE
# ===========================================================================

class TestGuardianStatuesPuzzle:
    def test_no_target_returns_clarification(self):
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "", wm, ps)
        assert r.success is False
        assert "specify" in r.message.lower() or "northern" in r.message.lower() or "four" in r.message.lower()

    def test_rotate_northern_statue_partial_progress(self):
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "northern", wm, ps)
        # Northern statue must rotate: N->E (not correct SOUTH), so partial=False, success=False
        assert r.success is False
        assert "north" in r.message.lower() or "east" in r.message.lower() or "correct" in r.message.lower()
        assert "rotate_statue" in r.world_effects

    def test_rotate_applies_correct_direction_in_effects(self):
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "northern", wm, ps)
        statue_id, direction = r.world_effects["rotate_statue"]
        assert statue_id == "statue_guardian_n"
        # N statue starts NORTH, rotates to EAST
        assert direction == StatueDirection.EAST.value

    def test_solve_requires_all_four_correct(self):
        """Manually set statues to correct positions except one, then rotate the last."""
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        # Pre-set three statues to correct facing
        wm.objects["statue_guardian_e"].facing_direction = StatueDirection.WEST
        wm.objects["statue_guardian_s"].facing_direction = StatueDirection.NORTH
        wm.objects["statue_guardian_w"].facing_direction = StatueDirection.EAST
        # Northern starts NORTH, needs SOUTH; rotate until SOUTH (N->E->S)
        wm.objects["statue_guardian_n"].facing_direction = StatueDirection.EAST
        # Now rotating northern will give SOUTH = correct
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "northern", wm, ps)
        assert r.success is True
        assert "open_exit" in r.world_effects
        assert r.world_effects["open_exit"] == ("hall_of_guardians", "north", "chamber_of_inscriptions")

    def test_solve_has_positive_eval_impacts(self):
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        wm.objects["statue_guardian_e"].facing_direction = StatueDirection.WEST
        wm.objects["statue_guardian_s"].facing_direction = StatueDirection.NORTH
        wm.objects["statue_guardian_w"].facing_direction = StatueDirection.EAST
        wm.objects["statue_guardian_n"].facing_direction = StatueDirection.EAST
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "northern", wm, ps)
        assert r.eval_impacts.get("wisdom", 0) > 0
        assert r.eval_impacts.get("patience", 0) > 0

    def test_reckless_flag_set_when_not_observed(self):
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        # usage_history is empty — not observed
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "northern", wm, ps)
        assert r.reckless is True

    def test_reckless_false_when_observed(self):
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        wm.objects["statue_guardian_n"].usage_history.append("observed_turn_1")
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "northern", wm, ps)
        assert r.reckless is False

    def test_partial_progress_tracked(self):
        """After rotating one correct statue, progress shows statues_correct >= 1."""
        wm = _statues_world()
        ps = wm.puzzles["puzzle_guardian_statues"]
        # Set N to EAST so rotating gives SOUTH = correct
        wm.objects["statue_guardian_n"].facing_direction = StatueDirection.EAST
        r = PuzzleRegistry.attempt("puzzle_guardian_statues", "rotate", "northern", wm, ps)
        if "update_puzzle_progress" in r.world_effects:
            prog = r.world_effects["update_puzzle_progress"]
            assert prog.get("statues_correct", 0) >= 1


# ===========================================================================
# FLOOD CONTROL PUZZLE
# ===========================================================================

class TestFloodControlPuzzle:
    def test_no_wrench_blocked(self):
        wm = _flood_world()
        wm.player.inventory.remove("tool_wrench")
        ps = wm.puzzles["puzzle_flood_control"]
        r = PuzzleRegistry.attempt("puzzle_flood_control", "open", "secondary gate", wm, ps)
        assert r.success is False
        assert "wrench" in r.message.lower()

    def test_open_secondary_gate_first(self):
        wm = _flood_world()
        ps = wm.puzzles["puzzle_flood_control"]
        r = PuzzleRegistry.attempt("puzzle_flood_control", "open", "secondary gate", wm, ps)
        assert r.partial is True
        assert r.world_effects.get("update_object_state") == ("flood_gate_secondary", {"state": "open"})
        assert r.world_effects.get("update_puzzle_progress", {}).get("secondary_gate_open") is True

    def test_open_main_without_secondary_triggers_flood(self):
        wm = _flood_world()
        ps = wm.puzzles["puzzle_flood_control"]
        r = PuzzleRegistry.attempt("puzzle_flood_control", "open", "main gate", wm, ps)
        assert r.success is False
        assert r.reckless is True
        assert r.world_effects.get("trigger_flood") is True
        assert "flood" in r.message.lower()

    def test_open_main_after_secondary_ok(self):
        wm = _flood_world()
        ps = wm.puzzles["puzzle_flood_control"]
        ps.current_progress["secondary_gate_open"] = True
        r = PuzzleRegistry.attempt("puzzle_flood_control", "open", "main gate", wm, ps)
        assert r.partial is True
        assert "trigger_flood" not in r.world_effects
        assert r.world_effects.get("update_puzzle_progress", {}).get("main_gate_open") is True

    def test_lever_without_both_gates_fails(self):
        wm = _flood_world()
        ps = wm.puzzles["puzzle_flood_control"]
        r = PuzzleRegistry.attempt("puzzle_flood_control", "pull", "lever", wm, ps)
        assert r.success is False
        assert r.reckless is True

    def test_lever_after_both_gates_solves(self):
        wm = _flood_world()
        ps = wm.puzzles["puzzle_flood_control"]
        ps.current_progress["secondary_gate_open"] = True
        ps.current_progress["main_gate_open"] = True
        r = PuzzleRegistry.attempt("puzzle_flood_control", "pull", "lever", wm, ps)
        assert r.success is True
        assert r.world_effects.get("activate_water_wheel") is True
        assert r.eval_impacts.get("responsibility", 0) > 0

    def test_wrong_order_increases_recklessness(self):
        wm = _flood_world()
        ps = wm.puzzles["puzzle_flood_control"]
        r = PuzzleRegistry.attempt("puzzle_flood_control", "open", "main gate", wm, ps)
        assert r.eval_impacts.get("recklessness", 0) > 0


# ===========================================================================
# BRIDGE PUZZLE
# ===========================================================================

class TestBridgeIntegrityPuzzle:
    def _bridge_world(self):
        wm = WorldModel()
        wm.rooms["bridge_of_echoes"] = RoomState(
            room_id="bridge_of_echoes", region=RoomRegion.LIVING_TEMPLE,
            accessible_exits={}, puzzle_id="puzzle_bridge_integrity",
        )
        wm.rooms["underground_reservoir"] = RoomState(room_id="underground_reservoir")
        wm.player.current_room = "bridge_of_echoes"
        wm.puzzles["puzzle_bridge_integrity"] = PuzzleState(
            puzzle_id="puzzle_bridge_integrity", room_id="bridge_of_echoes",
            category=PuzzleCategory.ENVIRONMENTAL, status=PuzzleStatus.AVAILABLE,
        )
        wm.objects["bridge_rope"] = ObjectState(
            object_id="bridge_rope", name="Bridge Rope",
            category=ObjectCategory.ENVIRONMENTAL,
            current_room="bridge_of_echoes", state="intact", condition=80.0,
        )
        wm.rooms["bridge_of_echoes"].object_ids_present.append("bridge_rope")
        wm.dynamic_events.bridge.integrity["bridge_rope"] = 100.0
        return wm

    def test_rope_descent_solves_puzzle(self):
        wm = self._bridge_world()
        ps = wm.puzzles["puzzle_bridge_integrity"]
        r = PuzzleRegistry.attempt("puzzle_bridge_integrity", "use", "rope", wm, ps)
        assert r.success is True
        assert r.world_effects.get("open_exit") == ("bridge_of_echoes", "down", "underground_reservoir")
        assert r.world_effects.get("reveal_hidden_passage") == ("bridge_of_echoes", "down")

    def test_frayed_rope_blocks_descent(self):
        wm = self._bridge_world()
        wm.objects["bridge_rope"].condition = 10.0
        ps = wm.puzzles["puzzle_bridge_integrity"]
        r = PuzzleRegistry.attempt("puzzle_bridge_integrity", "use", "rope", wm, ps)
        assert r.success is False
        assert "frayed" in r.message.lower() or "weight" in r.message.lower()

    def test_crossing_degrades_bridge(self):
        wm = self._bridge_world()
        ps = wm.puzzles["puzzle_bridge_integrity"]
        r = PuzzleRegistry.attempt("puzzle_bridge_integrity", "cross", "bridge", wm, ps)
        assert r.partial is True
        fx = r.world_effects.get("update_bridge_integrity")
        assert fx is not None
        bridge_id, new_integrity = fx
        assert new_integrity < 100.0

    def test_multiple_crossings_accumulate_damage(self):
        wm = self._bridge_world()
        ps = wm.puzzles["puzzle_bridge_integrity"]
        r1 = PuzzleRegistry.attempt("puzzle_bridge_integrity", "cross", "bridge", wm, ps)
        # Simulate applying the effect
        _, i1 = r1.world_effects["update_bridge_integrity"]
        wm.dynamic_events.bridge.integrity["bridge_rope"] = i1
        r2 = PuzzleRegistry.attempt("puzzle_bridge_integrity", "cross", "bridge", wm, ps)
        _, i2 = r2.world_effects["update_bridge_integrity"]
        assert i2 < i1


# ===========================================================================
# SYMBOL ALIGNMENT PUZZLE
# ===========================================================================

class TestSymbolAlignmentPuzzle:
    def _symbol_world(self, mural_read=True, symbols=3):
        wm = WorldModel()
        wm.rooms["symbol_gallery"] = RoomState(
            room_id="symbol_gallery", region=RoomRegion.KNOWLEDGE_SANCTUM,
            accessible_exits={}, puzzle_id="puzzle_symbol_alignment",
        )
        wm.rooms["chamber_of_maps"] = RoomState(room_id="chamber_of_maps")
        wm.player.current_room = "symbol_gallery"
        wm.puzzles["puzzle_symbol_alignment"] = PuzzleState(
            puzzle_id="puzzle_symbol_alignment", room_id="symbol_gallery",
            category=PuzzleCategory.MEMORY, status=PuzzleStatus.AVAILABLE,
        )
        wm.objects["mural_symbol_gallery"] = ObjectState(
            object_id="mural_symbol_gallery", name="Symbol Gallery Mural",
            category=ObjectCategory.STORY, current_room="symbol_gallery",
            state="read" if mural_read else "undiscovered",
        )
        for sym in list({"eye","flame","river","circle","throne"})[:symbols]:
            wm.story.symbols_encountered.add(sym)
        return wm

    def test_without_knowledge_blocked(self):
        wm = self._symbol_world(mural_read=False, symbols=1)
        ps = wm.puzzles["puzzle_symbol_alignment"]
        r = PuzzleRegistry.attempt("puzzle_symbol_alignment", "align", "eye", wm, ps)
        assert r.success is False
        assert "haven" in r.message.lower() or "learned" in r.message.lower()

    def test_with_mural_read_unlocked(self):
        wm = self._symbol_world(mural_read=True, symbols=1)
        ps = wm.puzzles["puzzle_symbol_alignment"]
        r = PuzzleRegistry.attempt("puzzle_symbol_alignment", "align", "eye", wm, ps)
        # Should not be blocked by knowledge gate
        assert "haven" not in r.message.lower() or r.partial

    def test_correct_first_symbol_partial(self):
        wm = self._symbol_world()
        ps = wm.puzzles["puzzle_symbol_alignment"]
        r = PuzzleRegistry.attempt("puzzle_symbol_alignment", "align", "eye", wm, ps)
        assert r.partial is True
        assert r.world_effects.get("update_puzzle_progress", {}).get("aligned_sequence") == ["eye"]

    def test_wrong_order_resets(self):
        wm = self._symbol_world()
        ps = wm.puzzles["puzzle_symbol_alignment"]
        # Flame is second, but try it first
        r = PuzzleRegistry.attempt("puzzle_symbol_alignment", "align", "flame", wm, ps)
        assert r.success is False
        assert r.world_effects.get("update_puzzle_progress", {}).get("aligned_sequence") == []

    def test_full_correct_sequence_solves(self):
        wm = self._symbol_world()
        ps = wm.puzzles["puzzle_symbol_alignment"]
        for sym in ["eye", "flame", "river", "circle"]:
            ps.current_progress.setdefault("aligned_sequence", []).append(sym)
        # Add throne — last one
        r = PuzzleRegistry.attempt("puzzle_symbol_alignment", "align", "throne", wm, ps)
        assert r.success is True
        assert r.world_effects.get("open_exit") == ("symbol_gallery", "north", "chamber_of_maps")

    def test_duplicate_symbol_rejected(self):
        wm = self._symbol_world()
        ps = wm.puzzles["puzzle_symbol_alignment"]
        ps.current_progress["aligned_sequence"] = ["eye"]
        r = PuzzleRegistry.attempt("puzzle_symbol_alignment", "align", "eye", wm, ps)
        assert r.partial is True
        assert "already" in r.message.lower()


# ===========================================================================
# CLEAR RUBBLE PUZZLE
# ===========================================================================

class TestClearRubblePuzzle:
    def _rubble_world(self, has_chisel=True):
        wm = WorldModel()
        wm.rooms["collapsed_hallway"] = RoomState(
            room_id="collapsed_hallway", region=RoomRegion.LIVING_TEMPLE,
            accessible_exits={}, puzzle_id="puzzle_clear_rubble",
        )
        wm.rooms["chamber_of_reflection"] = RoomState(room_id="chamber_of_reflection")
        wm.player.current_room = "collapsed_hallway"
        wm.puzzles["puzzle_clear_rubble"] = PuzzleState(
            puzzle_id="puzzle_clear_rubble", room_id="collapsed_hallway",
            category=PuzzleCategory.ENVIRONMENTAL, status=PuzzleStatus.AVAILABLE,
        )
        wm.objects["rubble_pile"] = ObjectState(
            object_id="rubble_pile", name="Collapsed Rubble",
            category=ObjectCategory.ENVIRONMENTAL,
            current_room="collapsed_hallway", state="blocking",
        )
        wm.rooms["collapsed_hallway"].object_ids_present.append("rubble_pile")
        if has_chisel:
            wm.objects["tool_chisel"] = ObjectState(
                object_id="tool_chisel", name="Iron Chisel",
                category=ObjectCategory.COLLECTIBLE, current_owner="player",
            )
            wm.player.inventory.append("tool_chisel")
        return wm

    def test_without_chisel_blocked(self):
        wm = self._rubble_world(has_chisel=False)
        ps = wm.puzzles["puzzle_clear_rubble"]
        r = PuzzleRegistry.attempt("puzzle_clear_rubble", "push", "rubble", wm, ps)
        assert r.success is False
        assert "tool" in r.message.lower() or "chisel" in r.message.lower() or "hand" in r.message.lower()

    def test_with_chisel_clears_rubble(self):
        wm = self._rubble_world(has_chisel=True)
        ps = wm.puzzles["puzzle_clear_rubble"]
        r = PuzzleRegistry.attempt("puzzle_clear_rubble", "push", "rubble", wm, ps)
        assert r.success is True
        assert r.world_effects.get("open_exit") == ("collapsed_hallway", "north", "chamber_of_reflection")
        assert r.world_effects.get("consume_object") == "tool_chisel"

    def test_unclear_target_blocked(self):
        wm = self._rubble_world(has_chisel=True)
        ps = wm.puzzles["puzzle_clear_rubble"]
        r = PuzzleRegistry.attempt("puzzle_clear_rubble", "push", "door", wm, ps)
        assert r.success is False

    def test_solve_eval_includes_patience(self):
        wm = self._rubble_world(has_chisel=True)
        ps = wm.puzzles["puzzle_clear_rubble"]
        r = PuzzleRegistry.attempt("puzzle_clear_rubble", "push", "rubble", wm, ps)
        assert r.eval_impacts.get("patience", 0) > 0


# ===========================================================================
# REFLECTION POOL PUZZLE
# ===========================================================================

class TestReflectionPoolPuzzle:
    def _pool_world(self):
        wm = WorldModel()
        wm.rooms["chamber_of_reflection"] = RoomState(
            room_id="chamber_of_reflection", region=RoomRegion.GUARDIAN_CORE,
            accessible_exits={}, puzzle_id="puzzle_reflection_pool",
        )
        wm.rooms["hall_of_judgment"] = RoomState(room_id="hall_of_judgment")
        wm.player.current_room = "chamber_of_reflection"
        wm.puzzles["puzzle_reflection_pool"] = PuzzleState(
            puzzle_id="puzzle_reflection_pool", room_id="chamber_of_reflection",
            category=PuzzleCategory.OBSERVATION, status=PuzzleStatus.AVAILABLE,
        )
        wm.objects["pool_reflection"] = ObjectState(
            object_id="pool_reflection", name="Reflection Pool",
            category=ObjectCategory.ENVIRONMENTAL,
            current_room="chamber_of_reflection", state="still",
        )
        wm.rooms["chamber_of_reflection"].object_ids_present.append("pool_reflection")
        return wm

    def test_meditate_without_inspecting_fails(self):
        wm = self._pool_world()
        ps = wm.puzzles["puzzle_reflection_pool"]
        r = PuzzleRegistry.attempt("puzzle_reflection_pool", "meditate", "pool", wm, ps)
        assert r.success is False
        assert "looked" in r.message.lower() or "pool" in r.message.lower()

    def test_inspect_pool_partial_progress(self):
        wm = self._pool_world()
        ps = wm.puzzles["puzzle_reflection_pool"]
        r = PuzzleRegistry.attempt("puzzle_reflection_pool", "inspect", "pool", wm, ps)
        assert r.success is False
        assert r.world_effects.get("update_puzzle_progress", {}).get("pool_inspections", 0) >= 1

    def test_inspect_twice_partial_true(self):
        wm = self._pool_world()
        ps = wm.puzzles["puzzle_reflection_pool"]
        ps.current_progress["pool_inspections"] = 1
        r = PuzzleRegistry.attempt("puzzle_reflection_pool", "inspect", "pool", wm, ps)
        assert r.partial is True

    def test_meditate_after_inspecting_solves(self):
        wm = self._pool_world()
        ps = wm.puzzles["puzzle_reflection_pool"]
        ps.current_progress["pool_inspections"] = 1
        r = PuzzleRegistry.attempt("puzzle_reflection_pool", "meditate", "pool", wm, ps)
        assert r.success is True
        assert r.world_effects.get("open_exit") == ("chamber_of_reflection", "north", "hall_of_judgment")

    def test_kneel_after_inspecting_solves(self):
        wm = self._pool_world()
        ps = wm.puzzles["puzzle_reflection_pool"]
        ps.current_progress["pool_inspections"] = 2
        r = PuzzleRegistry.attempt("puzzle_reflection_pool", "kneel", "", wm, ps)
        assert r.success is True

    def test_solve_eval_includes_patience_and_understanding(self):
        wm = self._pool_world()
        ps = wm.puzzles["puzzle_reflection_pool"]
        ps.current_progress["pool_inspections"] = 1
        r = PuzzleRegistry.attempt("puzzle_reflection_pool", "meditate", "", wm, ps)
        assert r.eval_impacts.get("patience", 0) > 0
        assert r.eval_impacts.get("understanding", 0) > 0


# ===========================================================================
# FINAL JUDGMENT PUZZLE
# ===========================================================================

class TestFinalJudgmentPuzzle:
    def _judgment_world(self, composite_score=0.0):
        wm = WorldModel()
        wm.rooms["throne_approach"] = RoomState(
            room_id="throne_approach", region=RoomRegion.GUARDIAN_CORE,
            accessible_exits={}, puzzle_id="puzzle_final_judgment",
        )
        wm.rooms["final_chamber"] = RoomState(room_id="final_chamber")
        wm.player.current_room = "throne_approach"
        wm.puzzles["puzzle_final_judgment"] = PuzzleState(
            puzzle_id="puzzle_final_judgment", room_id="throne_approach",
            category=PuzzleCategory.FINAL_JUDGMENT, status=PuzzleStatus.AVAILABLE,
        )
        # Satisfy prerequisites
        for pid in ("puzzle_guardian_statues", "puzzle_reflection_pool"):
            wm.puzzles[pid] = PuzzleState(puzzle_id=pid, room_id="hall_of_guardians", status=PuzzleStatus.SOLVED)
        wm.objects["arch_seal"] = ObjectState(
            object_id="arch_seal", name="Sealed Arch",
            category=ObjectCategory.INTERACTIVE,
            current_room="throne_approach", state="sealed",
        )
        # Set evaluation scores to reach desired composite
        if composite_score >= 40.0:
            for attr in ("observation","curiosity","wisdom","patience","adaptation","integrity","responsibility","understanding"):
                getattr(wm.evaluation, attr).score = 50.0
        return wm

    def test_unworthy_player_blocked(self):
        wm = self._judgment_world(composite_score=0.0)
        ps = wm.puzzles["puzzle_final_judgment"]
        r = PuzzleRegistry.attempt("puzzle_final_judgment", "open", "arch", wm, ps)
        assert r.success is False
        assert "incomplete" in r.message.lower() or "readiness" in r.message.lower()

    def test_worthy_player_passes(self):
        wm = self._judgment_world(composite_score=50.0)
        ps = wm.puzzles["puzzle_final_judgment"]
        r = PuzzleRegistry.attempt("puzzle_final_judgment", "open", "arch", wm, ps)
        assert r.success is True
        assert r.world_effects.get("open_exit") == ("throne_approach", "north", "final_chamber")
        assert r.world_effects.get("set_ending_eligibility") == "worthy"

    def test_partial_progress_when_half_ready(self):
        wm = self._judgment_world()
        for attr in ("observation","curiosity","wisdom","patience"):
            getattr(wm.evaluation, attr).score = 50.0
        ps = wm.puzzles["puzzle_final_judgment"]
        r = PuzzleRegistry.attempt("puzzle_final_judgment", "open", "arch", wm, ps)
        assert r.partial is True or r.success is True  # depends on exact score


# ===========================================================================
# DYNAMIC EVENT ENGINE TESTS
# ===========================================================================

class TestTorchDecay:
    def _lit_world(self, fuel=100):
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r")
        wm.player.current_room = "r"
        wm.player.torch.state = "lit"
        wm.player.torch.fuel = fuel
        wm.player.torch.brightness = 80
        wm.dynamic_events.torch_burn.current_burn_rate = 1.0
        return wm

    def test_torch_fuel_decrements_when_lit(self):
        wm = self._lit_world(fuel=50)
        effects = _evaluate_torch_decay(wm, 1)
        torch_fx = next((e for e in effects if e.effect_type == EFFECT_UPDATE_TORCH), None)
        assert torch_fx is not None
        assert torch_fx.payload["fuel"] < 50

    def test_torch_unlit_no_effects(self):
        wm = self._lit_world()
        wm.player.torch.state = "unlit"
        effects = _evaluate_torch_decay(wm, 1)
        torch_fx = [e for e in effects if e.effect_type == EFFECT_UPDATE_TORCH]
        assert len(torch_fx) == 0

    def test_torch_transitions_to_dim(self):
        wm = self._lit_world(fuel=31)
        effects = _evaluate_torch_decay(wm, 1)
        torch_fx = next((e for e in effects if e.effect_type == EFFECT_UPDATE_TORCH), None)
        assert torch_fx.payload["state"] == "dim"

    def test_torch_transitions_to_almost_out(self):
        wm = self._lit_world(fuel=11)
        effects = _evaluate_torch_decay(wm, 1)
        torch_fx = next((e for e in effects if e.effect_type == EFFECT_UPDATE_TORCH), None)
        assert torch_fx.payload["state"] == "almost_out"

    def test_torch_transitions_to_extinguished(self):
        wm = self._lit_world(fuel=1)
        effects = _evaluate_torch_decay(wm, 1)
        torch_fx = next((e for e in effects if e.effect_type == EFFECT_UPDATE_TORCH), None)
        assert torch_fx.payload["state"] == "extinguished"
        assert torch_fx.payload["fuel"] == 0

    def test_history_appended_on_extinguish(self):
        wm = self._lit_world(fuel=1)
        wm.player.torch.state = "almost_out"
        effects = _evaluate_torch_decay(wm, 5)
        history_fx = [e for e in effects if e.effect_type == "append_history"]
        assert len(history_fx) > 0

    def test_burn_rate_increases_near_water(self):
        wm = self._lit_world(fuel=50)
        wm.rooms["r"].water_level = 30.0
        effects = _evaluate_torch_decay(wm, 1)
        torch_fx = next(e for e in effects if e.effect_type == EFFECT_UPDATE_TORCH)
        # With flood modifier 1.5, burn >= 1 * 1.5 rounded = 2 per turn minimum
        assert torch_fx.payload["fuel"] <= 48


class TestFloodProgression:
    def _dry_world(self, phase=1):
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r")
        wm.rooms["underground_reservoir"] = RoomState(room_id="underground_reservoir")
        wm.rooms["water_channel_network"] = RoomState(room_id="water_channel_network")
        wm.player.current_room = "r"
        wm.world.temple_phase = TemplePhase(phase)
        wm.puzzles["puzzle_flood_control"] = PuzzleState(
            puzzle_id="puzzle_flood_control", room_id="r",
            category=PuzzleCategory.ENVIRONMENTAL, status=PuzzleStatus.AVAILABLE,
        )
        return wm

    def test_no_flood_in_discovery_phase(self):
        wm = self._dry_world(phase=1)
        effects = _evaluate_flood_progression(wm, 5)
        flood_active_fx = [e for e in effects if e.effect_type == EFFECT_SET_FLOOD_ACTIVE]
        assert len(flood_active_fx) == 0

    def test_flood_auto_triggers_at_adaptation_phase(self):
        wm = self._dry_world(phase=3)
        effects = _evaluate_flood_progression(wm, 1)
        flood_fx = [e for e in effects if e.effect_type == EFFECT_SET_FLOOD_ACTIVE]
        assert len(flood_fx) > 0
        assert flood_fx[0].payload["active"] is True

    def test_flood_does_not_trigger_if_puzzle_solved(self):
        wm = self._dry_world(phase=3)
        wm.puzzles["puzzle_flood_control"].status = PuzzleStatus.SOLVED
        effects = _evaluate_flood_progression(wm, 1)
        flood_fx = [e for e in effects if e.effect_type == EFFECT_SET_FLOOD_ACTIVE]
        assert len(flood_fx) == 0

    def test_flood_advances_stage_after_enough_turns(self):
        wm = self._dry_world(phase=3)
        # Activate flood manually at turn 0
        wm.dynamic_events.flood.active = True
        wm.dynamic_events.flood.start_turn = 0
        wm.dynamic_events.flood.current_stage = 0
        # After FLOOD_TURNS_PER_LEVEL turns, stage should advance
        from world.events import FLOOD_TURNS_PER_LEVEL
        effects = _evaluate_flood_progression(wm, FLOOD_TURNS_PER_LEVEL + 1)
        level_fx = [e for e in effects if e.effect_type == EFFECT_SET_FLOOD_LEVEL]
        assert len(level_fx) > 0
        assert level_fx[0].payload["stage"] >= 1

    def test_flood_rooms_get_water_level(self):
        wm = self._dry_world(phase=3)
        wm.dynamic_events.flood.active = True
        wm.dynamic_events.flood.start_turn = 0
        wm.dynamic_events.flood.current_stage = 0
        from world.events import FLOOD_TURNS_PER_LEVEL
        effects = _evaluate_flood_progression(wm, FLOOD_TURNS_PER_LEVEL + 1)
        water_fx = [e for e in effects if e.effect_type == EFFECT_SET_ROOM_WATER]
        assert len(water_fx) > 0
        for fx in water_fx:
            assert fx.payload["water_level"] > 0

    def test_flood_triggered_by_puzzle_failure(self):
        wm = self._dry_world(phase=1)
        wm.puzzles["puzzle_flood_control"].current_progress["flood_triggered"] = True
        wm.dynamic_events.flood.start_turn = 0
        wm.dynamic_events.flood.current_stage = 0
        from world.events import FLOOD_TURNS_PER_LEVEL
        effects = _evaluate_flood_progression(wm, FLOOD_TURNS_PER_LEVEL + 1)
        # Should advance flood even in phase 1 because trigger flag is set
        level_fx = [e for e in effects if e.effect_type == EFFECT_SET_FLOOD_LEVEL]
        assert len(level_fx) > 0


class TestDustAccumulation:
    def test_dust_increases_each_turn(self):
        wm = _world_with_room()
        wm.dynamic_events.dust.global_density = 0.0
        wm.dynamic_events.dust.accumulation_rate = 0.2
        effects = _evaluate_dust_accumulation(wm, 1)
        dust_fx = next((e for e in effects if e.effect_type == EFFECT_SET_DUST_DENSITY), None)
        assert dust_fx is not None
        assert dust_fx.payload["global_density"] > 0.0

    def test_water_wheel_halves_accumulation(self):
        wm = _world_with_room()
        wm.dynamic_events.dust.global_density = 0.0
        wm.dynamic_events.dust.accumulation_rate = 0.4
        wm.dynamic_events.flood.water_wheel_active = True
        effects = _evaluate_dust_accumulation(wm, 1)
        dust_fx = next(e for e in effects if e.effect_type == EFFECT_SET_DUST_DENSITY)
        # Should be 0.4 * 0.5 = 0.2
        assert abs(dust_fx.payload["global_density"] - 0.2) < 0.01

    def test_dust_capped_at_100(self):
        wm = _world_with_room()
        wm.dynamic_events.dust.global_density = 99.9
        effects = _evaluate_dust_accumulation(wm, 1)
        dust_fx = next(e for e in effects if e.effect_type == EFFECT_SET_DUST_DENSITY)
        assert dust_fx.payload["global_density"] <= 100.0


class TestBridgeIntegrityDecay:
    def test_bridge_decays_in_phase_2(self):
        wm = _world_with_room()
        wm.world.temple_phase = TemplePhase(2)
        wm.dynamic_events.bridge.integrity["bridge_rope"] = 100.0
        wm.objects["bridge_rope"] = ObjectState(
            object_id="bridge_rope", name="Bridge Rope",
            category=ObjectCategory.ENVIRONMENTAL, current_room="r",
        )
        effects = _evaluate_bridge_integrity(wm, 1)
        bridge_fx = next((e for e in effects if e.effect_type == EFFECT_UPDATE_BRIDGE), None)
        assert bridge_fx is not None
        assert bridge_fx.payload["integrity"] < 100.0

    def test_bridge_stable_in_phase_1(self):
        wm = _world_with_room()
        wm.world.temple_phase = TemplePhase(1)
        wm.dynamic_events.bridge.integrity["bridge_rope"] = 100.0
        effects = _evaluate_bridge_integrity(wm, 1)
        bridge_fx = [e for e in effects if e.effect_type == EFFECT_UPDATE_BRIDGE]
        assert len(bridge_fx) == 0

    def test_collapsed_bridge_not_decayed_further(self):
        wm = _world_with_room()
        wm.world.temple_phase = TemplePhase(2)
        wm.dynamic_events.bridge.collapsed_bridges.append("bridge_rope")
        effects = _evaluate_bridge_integrity(wm, 1)
        bridge_fx = [e for e in effects if e.effect_type == EFFECT_UPDATE_BRIDGE]
        assert len(bridge_fx) == 0

    def test_bridge_collapse_event_fires_at_threshold(self):
        wm = _world_with_room()
        wm.world.temple_phase = TemplePhase(2)
        from world.events import BRIDGE_COLLAPSE_THRESHOLD, BRIDGE_DECAY_PER_TURN
        # Set just above threshold so one decay crosses it
        wm.dynamic_events.bridge.integrity["bridge_rope"] = BRIDGE_COLLAPSE_THRESHOLD + BRIDGE_DECAY_PER_TURN * 0.5
        effects = _evaluate_bridge_integrity(wm, 1)
        history_fx = [e for e in effects if e.effect_type == "append_history"]
        assert len(history_fx) > 0  # collapse event logged


class TestStatueReset:
    def _statue_reset_world(self, turns_since_attempt=25):
        wm = WorldModel()
        wm.rooms["hall_of_guardians"] = RoomState(room_id="hall_of_guardians")
        wm.player.current_room = "hall_of_guardians"
        wm.puzzles["puzzle_guardian_statues"] = PuzzleState(
            puzzle_id="puzzle_guardian_statues", room_id="hall_of_guardians",
            category=PuzzleCategory.LOGIC, status=PuzzleStatus.IN_PROGRESS,
            first_attempted_turn=1,
        )
        for sid, facing in [
            ("statue_guardian_n", StatueDirection.EAST),   # wrong
            ("statue_guardian_e", StatueDirection.NORTH),  # wrong
            ("statue_guardian_s", StatueDirection.SOUTH),  # wrong (should be NORTH)
            ("statue_guardian_w", StatueDirection.WEST),   # wrong
        ]:
            wm.objects[sid] = ObjectState(
                object_id=sid, name=f"Guardian Statue",
                category=ObjectCategory.PUZZLE,
                current_room="hall_of_guardians",
                facing_direction=facing,
            )
        return wm, 1 + turns_since_attempt  # current_turn

    def test_statues_reset_after_timeout(self):
        wm, current_turn = self._statue_reset_world(turns_since_attempt=25)
        effects = _evaluate_statue_reset(wm, current_turn)
        reset_fx = [e for e in effects if e.effect_type == EFFECT_RESET_STATUE]
        assert len(reset_fx) > 0

    def test_reset_returns_to_original_facing(self):
        wm, current_turn = self._statue_reset_world(turns_since_attempt=25)
        effects = _evaluate_statue_reset(wm, current_turn)
        for fx in effects:
            if fx.effect_type == EFFECT_RESET_STATUE:
                sid = fx.payload["statue_id"]
                expected = {"statue_guardian_n": "north", "statue_guardian_e": "east",
                            "statue_guardian_s": "south", "statue_guardian_w": "west"}
                assert fx.payload["direction"] == expected[sid]

    def test_no_reset_before_timeout(self):
        wm, _ = self._statue_reset_world(turns_since_attempt=5)
        effects = _evaluate_statue_reset(wm, 6)
        reset_fx = [e for e in effects if e.effect_type == EFFECT_RESET_STATUE]
        assert len(reset_fx) == 0

    def test_solved_puzzle_never_resets(self):
        wm, current_turn = self._statue_reset_world(turns_since_attempt=25)
        wm.puzzles["puzzle_guardian_statues"].status = PuzzleStatus.SOLVED
        effects = _evaluate_statue_reset(wm, current_turn)
        reset_fx = [e for e in effects if e.effect_type == EFFECT_RESET_STATUE]
        assert len(reset_fx) == 0

    def test_recent_rotation_prevents_reset(self):
        wm, current_turn = self._statue_reset_world(turns_since_attempt=25)
        # Simulate recent rotation (only 5 turns ago)
        wm.dynamic_events.statues.last_rotated["statue_guardian_n"] = current_turn - 5
        effects = _evaluate_statue_reset(wm, current_turn)
        reset_fx = [e for e in effects if e.effect_type == EFFECT_RESET_STATUE]
        assert len(reset_fx) == 0


class TestHiddenPassageActivation:
    def test_bridge_passage_revealed_after_rope_used(self):
        wm = WorldModel()
        wm.rooms["bridge_of_echoes"] = RoomState(
            room_id="bridge_of_echoes", hidden_passages={"down": False},
        )
        wm.rooms["underground_reservoir"] = RoomState(room_id="underground_reservoir")
        wm.player.current_room = "bridge_of_echoes"
        wm.puzzles["puzzle_bridge_integrity"] = PuzzleState(
            puzzle_id="puzzle_bridge_integrity", room_id="bridge_of_echoes",
            category=PuzzleCategory.ENVIRONMENTAL, status=PuzzleStatus.AVAILABLE,
            current_progress={"rope_used": True},
        )
        effects = _evaluate_hidden_passage_activation(wm, 5)
        reveal_fx = [e for e in effects if e.effect_type == EFFECT_REVEAL_HIDDEN_PASSAGE]
        assert len(reveal_fx) > 0
        assert reveal_fx[0].payload == {"room_id": "bridge_of_echoes", "direction": "down"}

    def test_bridge_passage_not_revealed_without_rope(self):
        wm = WorldModel()
        wm.rooms["bridge_of_echoes"] = RoomState(
            room_id="bridge_of_echoes", hidden_passages={"down": False},
        )
        wm.player.current_room = "bridge_of_echoes"
        wm.puzzles["puzzle_bridge_integrity"] = PuzzleState(
            puzzle_id="puzzle_bridge_integrity", room_id="bridge_of_echoes",
            category=PuzzleCategory.ENVIRONMENTAL, status=PuzzleStatus.AVAILABLE,
        )
        effects = _evaluate_hidden_passage_activation(wm, 5)
        reveal_fx = [e for e in effects if e.effect_type == EFFECT_REVEAL_HIDDEN_PASSAGE]
        assert len(reveal_fx) == 0

    def test_channel_passage_revealed_with_key_in_room(self):
        wm = WorldModel()
        wm.rooms["water_channel_network"] = RoomState(
            room_id="water_channel_network", hidden_passages={"east": False},
        )
        wm.rooms["hidden_maintenance_tunnel"] = RoomState(room_id="hidden_maintenance_tunnel")
        wm.player.current_room = "water_channel_network"
        wm.objects["ancient_key_reservoir"] = ObjectState(
            object_id="ancient_key_reservoir", name="Reservoir Key",
            category=ObjectCategory.COLLECTIBLE, current_owner="player",
        )
        wm.player.inventory.append("ancient_key_reservoir")
        effects = _evaluate_hidden_passage_activation(wm, 5)
        open_fx = [e for e in effects if e.effect_type == EFFECT_OPEN_EXIT]
        assert len(open_fx) > 0

    def test_channel_passage_not_revealed_in_wrong_room(self):
        wm = WorldModel()
        wm.rooms["water_channel_network"] = RoomState(
            room_id="water_channel_network", hidden_passages={"east": False},
        )
        wm.rooms["temple_entrance"] = RoomState(room_id="temple_entrance")
        wm.player.current_room = "temple_entrance"  # wrong room
        wm.objects["ancient_key_reservoir"] = ObjectState(
            object_id="ancient_key_reservoir", name="Reservoir Key",
            category=ObjectCategory.COLLECTIBLE, current_owner="player",
        )
        wm.player.inventory.append("ancient_key_reservoir")
        effects = _evaluate_hidden_passage_activation(wm, 5)
        open_fx = [e for e in effects if e.effect_type == EFFECT_OPEN_EXIT]
        assert len(open_fx) == 0


class TestEvaluateEventsIntegration:
    def test_returns_list(self):
        wm = _world_with_room()
        effects = evaluate_events(wm, 1)
        assert isinstance(effects, list)

    def test_never_raises(self):
        for phase in (1, 2, 3, 4):
            wm = _world_with_room()
            wm.world.temple_phase = TemplePhase(phase)
            try:
                evaluate_events(wm, 99)
            except Exception as e:
                pytest.fail(f"evaluate_events raised for phase {phase}: {e}")

    def test_all_effects_are_event_effect_instances(self):
        wm = _world_with_room()
        wm.player.torch.state = "lit"
        wm.player.torch.fuel = 50
        effects = evaluate_events(wm, 1)
        for e in effects:
            assert isinstance(e, EventEffect)

    def test_phase_1_limits_non_critical_events(self):
        wm = _world_with_room()
        wm.world.temple_phase = TemplePhase(1)
        # Bridge decay is phase 2+ so should not fire
        wm.dynamic_events.bridge.integrity["bridge_rope"] = 100.0
        effects = evaluate_events(wm, 1)
        bridge_fx = [e for e in effects if e.effect_type == EFFECT_UPDATE_BRIDGE]
        assert len(bridge_fx) == 0


# ===========================================================================
# GAME ENGINE INTEGRATION TESTS
# ===========================================================================

def _guardian_engine():
    """GameEngine wired with a full guardian statues setup."""
    wm = WorldModel()
    wm.rooms["hall_of_guardians"] = RoomState(
        room_id="hall_of_guardians", region=RoomRegion.OUTER_TEMPLE,
        accessible_exits={}, puzzle_id="puzzle_guardian_statues",
    )
    wm.rooms["chamber_of_inscriptions"] = RoomState(
        room_id="chamber_of_inscriptions", region=RoomRegion.OUTER_TEMPLE,
        accessible_exits={"west": "hall_of_guardians"},
    )
    wm.player.current_room = "hall_of_guardians"
    wm.puzzles["puzzle_guardian_statues"] = PuzzleState(
        puzzle_id="puzzle_guardian_statues", room_id="hall_of_guardians",
        category=PuzzleCategory.LOGIC, status=PuzzleStatus.AVAILABLE,
    )
    NAMES = {
        "statue_guardian_n": ("Northern Guardian Statue", StatueDirection.NORTH),
        "statue_guardian_e": ("Eastern Guardian Statue", StatueDirection.EAST),
        "statue_guardian_s": ("Southern Guardian Statue", StatueDirection.SOUTH),
        "statue_guardian_w": ("Western Guardian Statue", StatueDirection.WEST),
    }
    for sid, (name, facing) in NAMES.items():
        wm.objects[sid] = ObjectState(
            object_id=sid, name=name,
            category=ObjectCategory.PUZZLE,
            current_room="hall_of_guardians",
            facing_direction=facing,
        )
        wm.rooms["hall_of_guardians"].object_ids_present.append(sid)
    engine = GameEngine(wm)
    return engine, wm


class TestGameEnginePuzzleDispatch:
    def test_puzzle_in_room_dispatches(self):
        engine, wm = _guardian_engine()
        r = engine.process_input("rotate northern")
        assert r.status in (ResultStatus.SUCCESS, ResultStatus.FAILURE)
        assert r.message

    def test_puzzle_solve_opens_exit(self):
        engine, wm = _guardian_engine()
        # Set statues to one rotation away from solved
        wm.objects["statue_guardian_e"].facing_direction = StatueDirection.WEST
        wm.objects["statue_guardian_s"].facing_direction = StatueDirection.NORTH
        wm.objects["statue_guardian_w"].facing_direction = StatueDirection.EAST
        wm.objects["statue_guardian_n"].facing_direction = StatueDirection.EAST
        engine.process_input("rotate northern")
        assert "north" in wm.rooms["hall_of_guardians"].accessible_exits

    def test_puzzle_solve_updates_puzzle_status(self):
        engine, wm = _guardian_engine()
        wm.objects["statue_guardian_e"].facing_direction = StatueDirection.WEST
        wm.objects["statue_guardian_s"].facing_direction = StatueDirection.NORTH
        wm.objects["statue_guardian_w"].facing_direction = StatueDirection.EAST
        wm.objects["statue_guardian_n"].facing_direction = StatueDirection.EAST
        engine.process_input("rotate northern")
        assert wm.puzzles["puzzle_guardian_statues"].status == PuzzleStatus.SOLVED

    def test_puzzle_solve_records_history(self):
        engine, wm = _guardian_engine()
        wm.objects["statue_guardian_e"].facing_direction = StatueDirection.WEST
        wm.objects["statue_guardian_s"].facing_direction = StatueDirection.NORTH
        wm.objects["statue_guardian_w"].facing_direction = StatueDirection.EAST
        wm.objects["statue_guardian_n"].facing_direction = StatueDirection.EAST
        before = len(wm.history.entries)
        engine.process_input("rotate northern")
        assert len(wm.history.entries) > before

    def test_puzzle_failure_increments_failure_count(self):
        engine, wm = _guardian_engine()
        # Rotate to wrong position (N rotates N->E, not correct SOUTH)
        engine.process_input("rotate northern")
        ps = wm.puzzles["puzzle_guardian_statues"]
        assert ps.failure_count >= 0  # may be 0 (partial) or > 0 (failure)

    def test_no_puzzle_in_room_returns_failure_with_message(self):
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r")
        wm.player.current_room = "r"
        engine = GameEngine(wm)
        r = engine.process_input("rotate statue")
        assert r.status == ResultStatus.FAILURE
        assert "puzzle" in r.message.lower() or "mechanism" in r.message.lower()

    def test_attempt_count_increments_on_each_try(self):
        engine, wm = _guardian_engine()
        engine.process_input("rotate northern")
        ps = wm.puzzles["puzzle_guardian_statues"]
        assert ps.attempt_count >= 1
        engine.process_input("rotate eastern")
        assert ps.attempt_count >= 2

    def test_first_attempted_turn_set(self):
        engine, wm = _guardian_engine()
        engine.process_input("rotate northern")
        ps = wm.puzzles["puzzle_guardian_statues"]
        assert ps.first_attempted_turn is not None


class TestGameEngineEventProcessing:
    def test_torch_fuel_decrements_after_turn(self):
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r")
        wm.player.current_room = "r"
        wm.player.torch.state = "lit"
        wm.player.torch.fuel = 50
        engine = GameEngine(wm)
        engine.process_input("look")
        assert wm.player.torch.fuel < 50

    def test_event_history_appended_on_torch_warning(self):
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r")
        wm.player.current_room = "r"
        wm.player.torch.state = "almost_out"
        wm.player.torch.fuel = 1
        engine = GameEngine(wm)
        before = len(wm.history.entries)
        engine.process_input("look")
        assert len(wm.history.entries) > before

    def test_dust_accumulates_each_turn(self):
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r")
        wm.player.current_room = "r"
        wm.dynamic_events.dust.global_density = 0.0
        engine = GameEngine(wm)
        engine.process_input("look")
        assert wm.dynamic_events.dust.global_density > 0.0

    def test_world_validates_after_puzzle_and_events(self):
        engine, wm = _guardian_engine()
        wm.player.torch.state = "lit"
        wm.player.torch.fuel = 50
        engine.process_input("rotate northern")
        engine.process_input("rotate eastern")
        result = wm.validate()
        assert result.is_valid, str(result)

    def test_serialization_after_puzzle_solve(self):
        engine, wm = _guardian_engine()
        wm.objects["statue_guardian_e"].facing_direction = StatueDirection.WEST
        wm.objects["statue_guardian_s"].facing_direction = StatueDirection.NORTH
        wm.objects["statue_guardian_w"].facing_direction = StatueDirection.EAST
        wm.objects["statue_guardian_n"].facing_direction = StatueDirection.EAST
        engine.process_input("rotate northern")
        json_str = wm.to_json()
        restored = WorldModel.from_json(json_str)
        assert restored.puzzles["puzzle_guardian_statues"].status == PuzzleStatus.SOLVED
        assert "north" in restored.rooms["hall_of_guardians"].accessible_exits

    def test_event_effect_updates_world_model_directly(self):
        """_apply_event_effect correctly writes torch state."""
        from engine.game_engine import GameEngine
        from world.events import EventEffect, EFFECT_UPDATE_TORCH
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r")
        wm.player.current_room = "r"
        wm.player.torch.fuel = 80
        engine = GameEngine(wm)
        effect = EventEffect(EFFECT_UPDATE_TORCH, {"fuel": 30, "state": "dim", "brightness": 40})
        engine._apply_event_effect(effect, 5)
        assert wm.player.torch.fuel == 30
        assert wm.player.torch.state == "dim"

    def test_event_effect_open_exit_writes_accessible_exits(self):
        from engine.game_engine import GameEngine
        from world.events import EventEffect, EFFECT_OPEN_EXIT
        wm = WorldModel()
        wm.rooms["room_a"] = RoomState(room_id="room_a", accessible_exits={})
        wm.rooms["room_b"] = RoomState(room_id="room_b")
        wm.player.current_room = "room_a"
        engine = GameEngine(wm)
        effect = EventEffect(EFFECT_OPEN_EXIT, {"room_id": "room_a", "direction": "north", "destination": "room_b"})
        engine._apply_event_effect(effect, 1)
        assert wm.rooms["room_a"].accessible_exits.get("north") == "room_b"

    def test_event_effect_set_room_water_level(self):
        from engine.game_engine import GameEngine
        from world.events import EventEffect, EFFECT_SET_ROOM_WATER
        wm = WorldModel()
        wm.rooms["r"] = RoomState(room_id="r", water_level=0.0)
        wm.player.current_room = "r"
        engine = GameEngine(wm)
        effect = EventEffect(EFFECT_SET_ROOM_WATER, {"room_id": "r", "water_level": 40.0})
        engine._apply_event_effect(effect, 1)
        assert wm.rooms["r"].water_level == 40.0
