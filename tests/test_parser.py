"""
test_parser.py — The Lost Temple of Rudra

Tests for Phase 3: CommandParser and Command dataclasses.

Covers:
    - Synonym resolution (many inputs → one canonical action)
    - All nine command categories
    - Target extraction
    - Secondary target extraction
    - Direction normalisation
    - Bare direction words
    - Article/preposition stripping
    - Empty / whitespace input
    - Invalid input handling
    - Debug gate (disabled by default)
    - Hidden commands
    - ParseResult structure
"""

import pytest
from src.engine.command import Action, CommandCategory, Command
from src.engine.command_parser import CommandParser, ParseResult


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def parser():
    return CommandParser(debug_mode=False)

@pytest.fixture
def debug_parser():
    return CommandParser(debug_mode=True)


# ---------------------------------------------------------------------------
# ParseResult structure
# ---------------------------------------------------------------------------

class TestParseResult:
    def test_ok_sets_success(self):
        cmd = Command(action=Action.LOOK)
        r = ParseResult.ok(cmd)
        assert r.success is True
        assert r.command is cmd
        assert r.error_message == ""

    def test_fail_sets_failure(self):
        r = ParseResult.fail("You cannot do that.")
        assert r.success is False
        assert r.command is None
        assert "You cannot" in r.error_message


# ---------------------------------------------------------------------------
# Empty / whitespace input
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_empty_string(self, parser):
        r = parser.parse("")
        assert not r.success
        assert r.error_message

    def test_whitespace_only(self, parser):
        r = parser.parse("   ")
        assert not r.success

    def test_none_equivalent_empty(self, parser):
        r = parser.parse("")
        assert not r.success


# ---------------------------------------------------------------------------
# Observation synonyms → INSPECT / LOOK / READ / LISTEN
# ---------------------------------------------------------------------------

class TestObservationSynonyms:
    @pytest.mark.parametrize("phrase", [
        "look", "l", "look around",
    ])
    def test_look_synonyms(self, parser, phrase):
        r = parser.parse(phrase)
        assert r.success
        assert r.command.action == Action.LOOK

    @pytest.mark.parametrize("phrase", [
        "inspect statue",
        "examine statue",
        "observe statue",
        "check statue",
        "view statue",
        "watch statue",
    ])
    def test_inspect_synonyms(self, parser, phrase):
        r = parser.parse(phrase)
        assert r.success
        assert r.command.action == Action.INSPECT
        assert r.command.target == "statue"

    def test_read_inscription(self, parser):
        r = parser.parse("read inscription")
        assert r.success
        assert r.command.action == Action.READ
        assert r.command.target == "inscription"

    def test_listen(self, parser):
        r = parser.parse("listen")
        assert r.success
        assert r.command.action == Action.LISTEN

    def test_listen_to_bells(self, parser):
        r = parser.parse("listen to the bells")
        assert r.success
        assert r.command.action == Action.LISTEN

    def test_touch_wall(self, parser):
        r = parser.parse("touch wall")
        assert r.success
        assert r.command.action == Action.TOUCH
        assert r.command.target == "wall"

    def test_smell(self, parser):
        r = parser.parse("smell air")
        assert r.success
        assert r.command.action == Action.SMELL


# ---------------------------------------------------------------------------
# Movement synonyms → GO / ENTER / LEAVE / CROSS / CLIMB / DESCEND
# ---------------------------------------------------------------------------

class TestMovementSynonyms:
    @pytest.mark.parametrize("phrase,expected_target", [
        ("go north",   "north"),
        ("north",      "north"),
        ("n",          "north"),
        ("go south",   "south"),
        ("south",      "south"),
        ("go east",    "east"),
        ("east",       "east"),
        ("go west",    "west"),
        ("west",       "west"),
        ("walk north", "north"),
        ("move north", "north"),
        ("head north", "north"),
    ])
    def test_movement_directions(self, parser, phrase, expected_target):
        r = parser.parse(phrase)
        assert r.success, f"Failed to parse: '{phrase}'"
        assert r.command.action == Action.GO
        assert r.command.target == expected_target

    def test_enter(self, parser):
        r = parser.parse("enter tunnel")
        assert r.success
        assert r.command.action == Action.ENTER

    def test_leave(self, parser):
        r = parser.parse("leave")
        assert r.success
        assert r.command.action == Action.LEAVE

    def test_cross_bridge(self, parser):
        r = parser.parse("cross bridge")
        assert r.success
        assert r.command.action == Action.CROSS

    def test_climb_ladder(self, parser):
        r = parser.parse("climb ladder")
        assert r.success
        assert r.command.action == Action.CLIMB

    def test_descend(self, parser):
        r = parser.parse("descend stairs")
        assert r.success
        assert r.command.action == Action.DESCEND


# ---------------------------------------------------------------------------
# Inventory synonyms → TAKE / DROP / INVENTORY / USE / LIGHT / EXTINGUISH
# ---------------------------------------------------------------------------

class TestInventorySynonyms:
    @pytest.mark.parametrize("phrase", [
        "take torch",
        "grab torch",
        "pick up torch",
        "collect torch",
        "get torch",
    ])
    def test_take_synonyms(self, parser, phrase):
        r = parser.parse(phrase)
        assert r.success
        assert r.command.action == Action.TAKE
        assert r.command.target == "torch"

    @pytest.mark.parametrize("phrase", [
        "drop torch",
        "put down torch",
    ])
    def test_drop_synonyms(self, parser, phrase):
        r = parser.parse(phrase)
        assert r.success
        assert r.command.action == Action.DROP
        assert r.command.target == "torch"

    @pytest.mark.parametrize("phrase", [
        "inventory", "i", "inv", "items",
    ])
    def test_inventory_synonyms(self, parser, phrase):
        r = parser.parse(phrase)
        assert r.success
        assert r.command.action == Action.INVENTORY

    def test_light_torch(self, parser):
        r = parser.parse("light torch")
        assert r.success
        assert r.command.action == Action.LIGHT
        assert r.command.target == "torch"

    @pytest.mark.parametrize("phrase", [
        "extinguish torch",
        "put out torch",
        "douse torch",
    ])
    def test_extinguish_synonyms(self, parser, phrase):
        r = parser.parse(phrase)
        assert r.success
        assert r.command.action == Action.EXTINGUISH
        assert r.command.target == "torch"


# ---------------------------------------------------------------------------
# Puzzle synonyms → ROTATE / PUSH / PULL / INSERT / OPEN / CLOSE / etc.
# ---------------------------------------------------------------------------

class TestPuzzleSynonyms:
    @pytest.mark.parametrize("phrase", [
        "rotate statue",
        "turn statue",
        "spin statue",
    ])
    def test_rotate_synonyms(self, parser, phrase):
        r = parser.parse(phrase)
        assert r.success
        assert r.command.action == Action.ROTATE
        assert r.command.target == "statue"

    @pytest.mark.parametrize("phrase", [
        "push lever",
        "press lever",
    ])
    def test_push_synonyms(self, parser, phrase):
        r = parser.parse(phrase)
        assert r.success
        assert r.command.action == Action.PUSH

    @pytest.mark.parametrize("phrase", [
        "pull lever",
        "yank lever",
        "tug lever",
    ])
    def test_pull_synonyms(self, parser, phrase):
        r = parser.parse(phrase)
        assert r.success
        assert r.command.action == Action.PULL

    def test_open_door(self, parser):
        r = parser.parse("open door")
        assert r.success
        assert r.command.action == Action.OPEN

    def test_close_gate(self, parser):
        r = parser.parse("close gate")
        assert r.success
        assert r.command.action == Action.CLOSE

    def test_activate(self, parser):
        r = parser.parse("activate wheel")
        assert r.success
        assert r.command.action == Action.ACTIVATE


# ---------------------------------------------------------------------------
# Knowledge commands → TRANSLATE / STUDY / REMEMBER / COMPARE
# ---------------------------------------------------------------------------

class TestKnowledgeSynonyms:
    def test_translate(self, parser):
        r = parser.parse("translate inscription")
        assert r.success
        assert r.command.action == Action.TRANSLATE

    def test_decipher_synonym(self, parser):
        r = parser.parse("decipher inscription")
        assert r.success
        assert r.command.action == Action.TRANSLATE

    def test_study(self, parser):
        r = parser.parse("study mural")
        assert r.success
        assert r.command.action == Action.STUDY

    def test_remember(self, parser):
        r = parser.parse("remember clue")
        assert r.success
        assert r.command.action == Action.REMEMBER

    def test_compare(self, parser):
        r = parser.parse("compare symbols")
        assert r.success
        assert r.command.action == Action.COMPARE


# ---------------------------------------------------------------------------
# AI commands
# ---------------------------------------------------------------------------

class TestAICommands:
    def test_recommend(self, parser):
        r = parser.parse("recommend")
        assert r.success
        assert r.command.action == Action.RECOMMEND

    def test_suggest_synonym(self, parser):
        r = parser.parse("suggest")
        assert r.success
        assert r.command.action == Action.RECOMMEND

    def test_hint(self, parser):
        r = parser.parse("hint")
        assert r.success
        assert r.command.action == Action.HINT

    def test_status(self, parser):
        r = parser.parse("status")
        assert r.success
        assert r.command.action == Action.STATUS

    def test_think(self, parser):
        r = parser.parse("think")
        assert r.success
        assert r.command.action == Action.THINK


# ---------------------------------------------------------------------------
# System commands
# ---------------------------------------------------------------------------

class TestSystemCommands:
    def test_help(self, parser):
        r = parser.parse("help")
        assert r.success
        assert r.command.action == Action.HELP

    def test_question_mark(self, parser):
        r = parser.parse("?")
        assert r.success
        assert r.command.action == Action.HELP

    def test_mission(self, parser):
        r = parser.parse("mission")
        assert r.success
        assert r.command.action == Action.MISSION

    def test_objective_synonym(self, parser):
        r = parser.parse("objective")
        assert r.success
        assert r.command.action == Action.MISSION

    def test_quit(self, parser):
        r = parser.parse("quit")
        assert r.success
        assert r.command.action == Action.QUIT

    def test_save(self, parser):
        r = parser.parse("save")
        assert r.success
        assert r.command.action == Action.SAVE


# ---------------------------------------------------------------------------
# Debug commands — gating
# ---------------------------------------------------------------------------

class TestDebugCommands:
    def test_debug_blocked_without_flag(self, parser):
        r = parser.parse("worldmodel")
        assert not r.success
        assert "not available" in r.error_message.lower()

    def test_debug_allowed_with_flag(self, debug_parser):
        r = debug_parser.parse("worldmodel")
        assert r.success
        assert r.command.action == Action.DEBUG_WORLD

    def test_debug_evaluation(self, debug_parser):
        r = debug_parser.parse("evaluation")
        assert r.success
        assert r.command.action == Action.DEBUG_EVAL

    def test_debug_room(self, debug_parser):
        r = debug_parser.parse("roomstate")
        assert r.success
        assert r.command.action == Action.DEBUG_ROOM


# ---------------------------------------------------------------------------
# Hidden commands (always enabled, not documented)
# ---------------------------------------------------------------------------

class TestHiddenCommands:
    def test_pray(self, parser):
        r = parser.parse("pray")
        assert r.success
        assert r.command.action == Action.PRAY

    def test_meditate(self, parser):
        r = parser.parse("meditate")
        assert r.success
        assert r.command.action == Action.MEDITATE

    def test_wait(self, parser):
        r = parser.parse("wait")
        assert r.success
        assert r.command.action == Action.WAIT

    def test_observe_silence(self, parser):
        r = parser.parse("observe silence")
        assert r.success
        assert r.command.action == Action.SILENCE

    def test_remain_silent(self, parser):
        r = parser.parse("remain silent")
        assert r.success
        assert r.command.action == Action.SILENCE


# ---------------------------------------------------------------------------
# Target extraction
# ---------------------------------------------------------------------------

class TestTargetExtraction:
    def test_simple_target(self, parser):
        r = parser.parse("inspect statue")
        assert r.command.target == "statue"

    def test_article_stripped(self, parser):
        r = parser.parse("inspect the statue")
        assert r.command.target == "statue"

    def test_multi_word_target(self, parser):
        r = parser.parse("inspect ancient tablet")
        assert r.command.target == "ancient tablet"

    def test_no_target_for_look(self, parser):
        r = parser.parse("look")
        assert r.command.target is None

    def test_secondary_target_with_into(self, parser):
        r = parser.parse("insert disc into pedestal")
        assert r.command.target == "disc"
        assert r.command.secondary_target == "pedestal"

    def test_secondary_target_with_with(self, parser):
        r = parser.parse("use key with door")
        assert r.command.target == "key"
        assert r.command.secondary_target == "door"

    def test_no_secondary_target(self, parser):
        r = parser.parse("take torch")
        assert r.command.secondary_target is None


# ---------------------------------------------------------------------------
# Command category derivation
# ---------------------------------------------------------------------------

class TestCommandCategory:
    def test_observation_category(self, parser):
        r = parser.parse("inspect statue")
        assert r.command.category == CommandCategory.OBSERVATION

    def test_movement_category(self, parser):
        r = parser.parse("go north")
        assert r.command.category == CommandCategory.MOVEMENT

    def test_inventory_category(self, parser):
        r = parser.parse("take torch")
        assert r.command.category == CommandCategory.INVENTORY

    def test_puzzle_category(self, parser):
        r = parser.parse("rotate statue")
        assert r.command.category == CommandCategory.PUZZLE

    def test_system_category(self, parser):
        r = parser.parse("help")
        assert r.command.category == CommandCategory.SYSTEM

    def test_hidden_category(self, parser):
        r = parser.parse("pray")
        assert r.command.category == CommandCategory.HIDDEN


# ---------------------------------------------------------------------------
# Input normalisation
# ---------------------------------------------------------------------------

class TestNormalisation:
    def test_uppercase_normalised(self, parser):
        r = parser.parse("INSPECT STATUE")
        assert r.success
        assert r.command.action == Action.INSPECT

    def test_mixed_case(self, parser):
        r = parser.parse("Inspect The Ancient Statue")
        assert r.success
        assert r.command.action == Action.INSPECT

    def test_extra_whitespace(self, parser):
        r = parser.parse("  inspect   statue  ")
        assert r.success
        assert r.command.target == "statue"

    def test_raw_input_preserved(self, parser):
        raw = "Inspect the Ancient Statue"
        r = parser.parse(raw)
        assert r.command.raw_input == raw

    def test_punctuation_stripped(self, parser):
        r = parser.parse("inspect statue!")
        assert r.success
        assert r.command.target == "statue"


# ---------------------------------------------------------------------------
# Unknown / unrecognised inputs
# ---------------------------------------------------------------------------

class TestUnknownInput:
    def test_completely_unknown_verb(self, parser):
        r = parser.parse("xyzzy")
        assert not r.success
        assert r.error_message  # always a message

    def test_error_message_is_natural(self, parser):
        r = parser.parse("xyzzy statue")
        assert not r.success
        # Must not contain raw technical language
        assert "error" not in r.error_message.lower()
        assert "exception" not in r.error_message.lower()
        assert "traceback" not in r.error_message.lower()

    def test_partial_match_does_not_crash(self, parser):
        r = parser.parse("goo north")
        # "goo" is not a valid verb — should fail gracefully
        assert not r.success

    def test_never_raises(self, parser):
        for bad_input in ["", "   ", "!@#$%", "a" * 500, "go", "take"]:
            result = parser.parse(bad_input)
            assert isinstance(result, ParseResult)


# ---------------------------------------------------------------------------
# Command __str__ representation
# ---------------------------------------------------------------------------

class TestCommandStr:
    def test_str_with_target(self):
        cmd = Command(action=Action.INSPECT, target="statue", raw_input="inspect statue")
        assert "inspect" in str(cmd)
        assert "statue" in str(cmd)

    def test_str_with_secondary(self):
        cmd = Command(action=Action.INSERT, target="disc",
                      secondary_target="pedestal", raw_input="insert disc into pedestal")
        s = str(cmd)
        assert "disc" in s
        assert "pedestal" in s
