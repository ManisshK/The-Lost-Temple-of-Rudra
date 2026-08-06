"""
test_phase7.py — The Lost Temple of Rudra

Comprehensive tests for Phase 7: UI Framework, Save System, State Manager,
Audio Engine, and packaging components.

All tests are headless-safe:
  - tkinter.Tk root is created with root.withdraw() (hidden, no display needed)
  - A single module-level root is shared; each test class tears down its own widgets
  - No real file I/O for save tests (uses tmp_path fixture)
  - No audio hardware required (AudioEngine is feature-flagged)
  - No mainloop() calls in any test
"""
from __future__ import annotations

import json
import os
import sys
import tkinter as tk
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# ---------------------------------------------------------------------------
# Shared headless tk root (module-level)
# ---------------------------------------------------------------------------
_root: tk.Tk = None


def _get_root() -> tk.Tk:
    global _root
    if _root is None or not _root.winfo_exists():
        _root = tk.Tk()
        _root.withdraw()
    return _root


@pytest.fixture(scope="module", autouse=True)
def tk_root():
    """Provide a hidden Tk root for the entire module, destroy at end."""
    root = _get_root()
    yield root
    try:
        root.destroy()
    except Exception:
        pass

# ---------------------------------------------------------------------------
# World-model helpers (reuse across tests)
# ---------------------------------------------------------------------------
from world.world_model import WorldModel
from world.room_state import RoomState, RoomRegion
from world.object_state import ObjectState, ObjectCategory
from world.puzzle_state import PuzzleState, PuzzleStatus, PuzzleCategory
from world.player_state import TorchStatus


def _simple_wm(room_id: str = "temple_entrance") -> WorldModel:
    wm = WorldModel()
    wm.rooms[room_id] = RoomState(
        room_id=room_id,
        region=RoomRegion.OUTER_TEMPLE,
        accessible_exits={"north": "hall_of_echoes"},
    )
    wm.player.current_room = room_id
    wm.player.torch = TorchStatus(state="lit", fuel=75, brightness=70)
    return wm


# ===========================================================================
# ThemeManager
# ===========================================================================
from ui.theme import ThemeManager, WindowConfig, FontConfig, ThemeColors


class TestThemeManager:
    def test_default_theme_loads(self):
        t = ThemeManager()
        assert isinstance(t.window, WindowConfig)
        assert isinstance(t.fonts, FontConfig)
        assert isinstance(t.colors, ThemeColors)

    def test_default_colours_are_valid_hex(self):
        t = ThemeManager()
        for attr in ("background", "text", "accent", "panel", "border"):
            val = getattr(t.colors, attr)
            assert val.startswith("#"), f"{attr} not a hex colour: {val}"
            assert len(val) == 7, f"{attr} hex length wrong: {val}"

    def test_window_dimensions_positive(self):
        t = ThemeManager()
        assert t.window.width > 0
        assert t.window.height > 0

    def test_font_sizes_positive(self):
        t = ThemeManager()
        assert t.fonts.size_normal > 0
        assert t.fonts.size_large > t.fonts.size_normal
        assert t.fonts.size_title > t.fonts.size_large

    def test_load_from_custom_config(self, tmp_path):
        cfg = tmp_path / "graphics.json"
        cfg.write_text(json.dumps({
            "window": {"title": "Test", "width": 800, "height": 600,
                       "resizable": True, "fullscreen": False},
            "fonts": {"size_normal": 12, "size_large": 16, "size_title": 28},
            "theme": {"background_color": "#111111", "text_color": "#ffffff",
                      "accent_color": "#ff0000", "panel_color": "#222222",
                      "border_color": "#333333"},
            "panels": {"narrative_width_percent": 65, "sidebar_width_percent": 35},
        }))
        t = ThemeManager(config_path=str(cfg))
        assert t.window.width == 800
        assert t.window.title == "Test"
        assert t.colors.background == "#111111"
        assert t.fonts.size_normal == 12

    def test_fallback_on_missing_config(self):
        t = ThemeManager(config_path="/nonexistent/path.json")
        assert t.window.width > 0

    def test_font_tuples_are_tuples(self):
        t = ThemeManager()
        assert isinstance(t.font_normal(), tuple)
        assert isinstance(t.font_large(), tuple)
        assert isinstance(t.font_title(), tuple)
        assert isinstance(t.font_mono(), tuple)
        assert isinstance(t.font_small(), tuple)

    def test_width_percentages_sum_to_one(self):
        t = ThemeManager()
        assert abs(t.narrative_width_pct + t.sidebar_width_pct - 1.0) < 0.01


# ===========================================================================
# Animations
# ===========================================================================
from ui.animations import TypewriterEffect, FadeEffect, FlickerEffect, SmoothScrollEffect, _lerp_color


class TestAnimations:
    def _text_widget(self) -> tk.Text:
        w = tk.Text(_get_root(), state="disabled")
        return w

    def _canvas(self) -> tk.Canvas:
        return tk.Canvas(_get_root(), width=50, height=50, bg="#000000")

    def test_lerp_color_endpoints(self):
        assert _lerp_color("#000000", "#ffffff", 0.0) == "#000000"
        assert _lerp_color("#000000", "#ffffff", 1.0) == "#ffffff"

    def test_lerp_color_midpoint(self):
        result = _lerp_color("#000000", "#ffffff", 0.5)
        assert result.startswith("#")
        assert len(result) == 7

    def test_typewriter_cancel_flushes_text(self):
        w = self._text_widget()
        tw = TypewriterEffect(w, "hello world", speed_ms=10000, tag="normal")
        tw.start()
        tw.cancel()
        w.configure(state="normal")
        content = w.get("1.0", tk.END).strip()
        assert "hello world" in content
        w.destroy()

    def test_typewriter_on_complete_called_after_cancel(self):
        w = self._text_widget()
        called = []
        tw = TypewriterEffect(w, "test", speed_ms=10000, on_complete=lambda: called.append(1))
        tw.start()
        tw.cancel()
        assert called == [1]
        w.destroy()

    def test_typewriter_zero_speed_instant(self):
        w = self._text_widget()
        completed = []
        tw = TypewriterEffect(w, "instant", speed_ms=0, on_complete=lambda: completed.append(1))
        tw.start()
        # With speed=0, scheduling fires but we cancel immediately
        tw.cancel()
        w.configure(state="normal")
        content = w.get("1.0", tk.END)
        assert "instant" in content
        w.destroy()

    def test_fade_effect_cancel_does_not_raise(self):
        w = self._text_widget()
        w.tag_configure("t", foreground="#ffffff")
        fade = FadeEffect(w, "t", "#000000", "#ffffff", duration_ms=1000)
        fade.start()
        fade.cancel()
        w.destroy()

    def test_flicker_effect_start_stop(self):
        c = self._canvas()
        item = c.create_oval(5, 5, 45, 45, fill="#e8920a")
        flick = FlickerEffect(c, item, interval_ms=10000)
        flick.start()
        assert flick._running
        flick.stop()
        assert not flick._running
        c.destroy()

    def test_smooth_scroll_cancel_does_not_raise(self):
        w = self._text_widget()
        ss = SmoothScrollEffect(w, target=1.0, steps=5, interval_ms=1000)
        ss.start()
        ss.cancel()
        w.destroy()


# ===========================================================================
# Audio Engine
# ===========================================================================
from ui.audio import AudioEngine, _PYGAME_AVAILABLE


class TestAudioEngine:
    def test_instantiates_without_pygame(self):
        audio = AudioEngine()
        # Must not raise even when pygame is absent
        assert isinstance(audio, AudioEngine)

    def test_is_available_false_without_pygame(self):
        audio = AudioEngine()
        if not _PYGAME_AVAILABLE:
            assert audio.is_available is False

    def test_play_sfx_noop_when_disabled(self):
        audio = AudioEngine(enabled=False)
        audio.play_sfx("pickup")  # Must not raise

    def test_play_music_noop_when_disabled(self):
        audio = AudioEngine(enabled=False)
        audio.play_music("exploration")  # Must not raise

    def test_play_ambience_noop_when_disabled(self):
        audio = AudioEngine(enabled=False)
        audio.play_ambience("temple")  # Must not raise

    def test_stop_music_noop_when_disabled(self):
        audio = AudioEngine(enabled=False)
        audio.stop_music()  # Must not raise

    def test_volume_clamped(self):
        audio = AudioEngine(sfx_volume=2.0, music_volume=-1.0)
        assert audio._sfx_vol == 1.0
        assert audio._music_vol == 0.0

    def test_set_sfx_volume(self):
        audio = AudioEngine(enabled=False)
        audio.set_sfx_volume(0.5)
        assert audio._sfx_vol == 0.5

    def test_set_music_volume(self):
        audio = AudioEngine(enabled=False)
        audio.set_music_volume(0.3)
        assert audio._music_vol == 0.3

    def test_shutdown_noop_when_disabled(self):
        audio = AudioEngine(enabled=False)
        audio.shutdown()  # Must not raise

    def test_manifest_load_missing_file(self):
        audio = AudioEngine(enabled=False)
        assert isinstance(audio._manifest, dict)  # Empty dict on missing file


# ===========================================================================
# NarrativePanel
# ===========================================================================
from ui.dialogue import NarrativePanel, CommandInput, TempleAIPanel, ExplorerAIPanel


class TestNarrativePanel:
    def _panel(self) -> NarrativePanel:
        return NarrativePanel(_get_root(), ThemeManager(), typewriter_speed_ms=0)

    def test_instantiates(self):
        p = self._panel()
        assert p is not None
        p.destroy()

    def test_append_inserts_text(self):
        p = self._panel()
        p.append("Hello temple", typewriter=False)
        p._text.configure(state="normal")
        content = p._text.get("1.0", tk.END)
        assert "Hello temple" in content
        p.destroy()

    def test_append_room_title(self):
        p = self._panel()
        p.append_room_title("Hall of Guardians")
        p._text.configure(state="normal")
        content = p._text.get("1.0", tk.END)
        assert "HALL OF GUARDIANS" in content
        p.destroy()

    def test_clear_empties_content(self):
        p = self._panel()
        p.append("some text", typewriter=False)
        p.clear()
        p._text.configure(state="normal")
        content = p._text.get("1.0", tk.END).strip()
        assert content == ""
        p.destroy()

    def test_all_tags_configured(self):
        p = self._panel()
        for tag in ("normal", "temple", "explorer", "hint",
                    "warning", "success", "dim", "highlight", "title", "system"):
            # Tag configuration should exist without raising
            p._text.tag_configure(tag)
        p.destroy()

    def test_set_typewriter_speed(self):
        p = self._panel()
        p.set_typewriter_speed(50)
        assert p._speed == 50
        p.destroy()

    def test_set_typewriter_speed_clamped_at_zero(self):
        p = self._panel()
        p.set_typewriter_speed(-10)
        assert p._speed == 0
        p.destroy()

    def test_multiple_appends(self):
        p = self._panel()
        for i in range(5):
            p.append(f"Line {i}", typewriter=False)
        p._text.configure(state="normal")
        content = p._text.get("1.0", tk.END)
        assert "Line 4" in content
        p.destroy()

    def test_append_with_on_complete_callback(self):
        p = self._panel()
        called = []
        p.append("text", typewriter=False, on_complete=lambda: called.append(1))
        assert called == [1]
        p.destroy()

# ===========================================================================
# CommandInput
# ===========================================================================

class TestCommandInput:
    def _input(self, on_submit=None) -> CommandInput:
        submitted = []
        cb = on_submit or (lambda t: submitted.append(t))
        return CommandInput(_get_root(), ThemeManager(), on_submit=cb)

    def test_instantiates(self):
        ci = self._input()
        assert ci is not None
        ci.destroy()

    def test_focus_does_not_raise(self):
        ci = self._input()
        ci.focus()
        ci.destroy()

    def test_set_enabled_disables_entry(self):
        ci = self._input()
        ci.set_enabled(False)
        assert str(ci._entry.cget("state")) == "disabled"
        ci.destroy()

    def test_set_enabled_re_enables(self):
        ci = self._input()
        ci.set_enabled(False)
        ci.set_enabled(True)
        assert str(ci._entry.cget("state")) == "normal"
        ci.destroy()

    def test_submit_calls_callback(self):
        received = []
        ci = self._input(on_submit=lambda t: received.append(t))
        ci._var.set("go north")
        ci._submit()
        assert received == ["go north"]
        ci.destroy()

    def test_empty_submit_ignored(self):
        received = []
        ci = self._input(on_submit=lambda t: received.append(t))
        ci._var.set("   ")
        ci._submit()
        assert received == []
        ci.destroy()

    def test_history_recorded_after_submit(self):
        ci = self._input()
        ci._var.set("look")
        ci._submit()
        assert "look" in ci._history
        ci.destroy()

    def test_history_no_duplicate_consecutive(self):
        ci = self._input()
        for _ in range(3):
            ci._var.set("look")
            ci._submit()
        assert ci._history.count("look") == 1
        ci.destroy()

    def test_history_back_restores_command(self):
        ci = self._input()
        ci._var.set("look"); ci._submit()
        ci._var.set("go north"); ci._submit()
        ci._history_back()
        assert ci._var.get() == "go north"
        ci.destroy()

    def test_history_forward_clears_on_end(self):
        ci = self._input()
        ci._var.set("look"); ci._submit()
        ci._history_back()
        ci._history_forward()
        assert ci._var.get() == ""
        ci.destroy()

    def test_var_cleared_after_submit(self):
        ci = self._input()
        ci._var.set("inspect")
        ci._submit()
        assert ci._var.get() == ""
        ci.destroy()


# ===========================================================================
# Temple AI Panel & Explorer AI Panel
# ===========================================================================

class TestAIPanels:
    def test_temple_panel_instantiates(self):
        p = TempleAIPanel(_get_root(), ThemeManager())
        assert p is not None
        p.destroy()

    def test_temple_panel_set_message(self):
        p = TempleAIPanel(_get_root(), ThemeManager())
        p.set_message("The temple watches.")
        content = p._text.get("1.0", tk.END).strip()
        assert "temple watches" in content
        p.destroy()

    def test_temple_panel_clear(self):
        p = TempleAIPanel(_get_root(), ThemeManager())
        p.set_message("something")
        p.clear()
        content = p._text.get("1.0", tk.END).strip()
        assert content == "The temple watches in silence..."
        p.destroy()

    def test_explorer_panel_instantiates(self):
        p = ExplorerAIPanel(_get_root(), ThemeManager())
        assert p is not None
        p.destroy()

    def test_explorer_panel_set_message(self):
        p = ExplorerAIPanel(_get_root(), ThemeManager())
        p.set_message("Go north.")
        content = p._text.get("1.0", tk.END).strip()
        assert "Go north" in content
        p.destroy()

    def test_explorer_panel_clear(self):
        p = ExplorerAIPanel(_get_root(), ThemeManager())
        p.set_message("some hint")
        p.clear()
        content = p._text.get("1.0", tk.END).strip()
        assert content == ""
        p.destroy()

    def test_temple_panel_text_is_read_only(self):
        p = TempleAIPanel(_get_root(), ThemeManager())
        # Underlying text widget should be disabled (read-only)
        assert str(p._text.cget("state")) == "disabled"
        p.destroy()


# ===========================================================================
# Inventory Panel
# ===========================================================================
from ui.inventory import InventoryPanel


class TestInventoryPanel:
    def _panel(self) -> InventoryPanel:
        return InventoryPanel(_get_root(), ThemeManager())

    def test_instantiates(self):
        p = self._panel()
        assert p is not None
        p.destroy()

    def test_refresh_empty_inventory(self):
        p = self._panel()
        wm = _simple_wm()
        p.refresh(wm)   # No items — must not raise
        p.destroy()

    def test_refresh_with_item(self):
        p = self._panel()
        wm = _simple_wm()
        wm.objects["torch_e"] = ObjectState(
            object_id="torch_e", name="Ancient Torch",
            category=ObjectCategory.COLLECTIBLE, current_room=None,
            state="lit", condition=80.0,
        )
        wm.player.inventory.append("torch_e")
        p.refresh(wm)
        # Collect all label text recursively — Canvas and Frame have no -text
        def collect_text(widget):
            parts = []
            try:
                parts.append(str(widget.cget("text")))
            except Exception:
                pass
            for child in widget.winfo_children():
                parts.extend(collect_text(child))
            return parts
        flat = " ".join(collect_text(p._container))
        assert "Ancient Torch" in flat
        p.destroy()

    def test_refresh_multiple_items(self):
        p = self._panel()
        wm = _simple_wm()
        for i in range(3):
            oid = f"item_{i}"
            wm.objects[oid] = ObjectState(
                object_id=oid, name=f"Item {i}",
                category=ObjectCategory.COLLECTIBLE,
                current_room=None, condition=100.0,
            )
            wm.player.inventory.append(oid)
        p.refresh(wm)
        assert len(p._item_frames) == 3
        p.destroy()

    def test_refresh_clears_previous_items(self):
        p = self._panel()
        wm = _simple_wm()
        wm.objects["a"] = ObjectState(
            object_id="a", name="Stone Key",
            category=ObjectCategory.COLLECTIBLE,
            current_room=None, condition=100.0,
        )
        wm.player.inventory.append("a")
        p.refresh(wm)
        assert len(p._item_frames) == 1
        # Now clear inventory and refresh again
        wm.player.inventory.clear()
        p.refresh(wm)
        assert len(p._item_frames) == 0
        p.destroy()

    def test_refresh_does_not_modify_world_model(self):
        p = self._panel()
        wm = _simple_wm()
        before = len(wm.player.inventory)
        p.refresh(wm)
        assert len(wm.player.inventory) == before
        p.destroy()


# ===========================================================================
# Sidebar Panels: Objectives, Journal, Status, Evaluation, Map
# ===========================================================================
from ui.journal import ObjectivesPanel, JournalPanel, StatusPanel, EvaluationPanel, MapPanel


class TestObjectivesPanel:
    def test_instantiates(self):
        p = ObjectivesPanel(_get_root(), ThemeManager())
        assert p is not None
        p.destroy()

    def test_refresh_shows_mission(self):
        p = ObjectivesPanel(_get_root(), ThemeManager())
        wm = _simple_wm()
        wm.mission.current_goal_description = "Find the ancient scroll."
        p.refresh(wm)
        assert "ancient scroll" in p._primary.cget("text").lower()
        p.destroy()

    def test_refresh_completed_objectives(self):
        p = ObjectivesPanel(_get_root(), ThemeManager())
        wm = _simple_wm()
        wm.mission.completed_objectives = ["obj_read_entrance", "obj_reach_library"]
        p.refresh(wm)
        p.destroy()

    def test_refresh_does_not_modify_wm(self):
        p = ObjectivesPanel(_get_root(), ThemeManager())
        wm = _simple_wm()
        goal = wm.mission.current_goal_description
        p.refresh(wm)
        assert wm.mission.current_goal_description == goal
        p.destroy()


class TestJournalPanel:
    def test_instantiates(self):
        p = JournalPanel(_get_root(), ThemeManager())
        assert p is not None
        p.destroy()

    def test_refresh_empty(self):
        p = JournalPanel(_get_root(), ThemeManager())
        wm = _simple_wm()
        p.refresh(wm)
        p._text.configure(state="normal")
        content = p._text.get("1.0", tk.END).strip()
        assert "nothing recorded" in content.lower()
        p.destroy()

    def test_refresh_with_lore(self):
        p = JournalPanel(_get_root(), ThemeManager())
        wm = _simple_wm()
        wm.story.lore_ids_discovered = ["lore_entrance_warning"]
        p.refresh(wm)
        p._text.configure(state="normal")
        content = p._text.get("1.0", tk.END)
        assert "entrance warning" in content.lower()
        p.destroy()

    def test_refresh_with_solved_puzzle(self):
        p = JournalPanel(_get_root(), ThemeManager())
        wm = _simple_wm()
        from world.puzzle_state import PuzzleState, PuzzleStatus, PuzzleCategory
        wm.puzzles["puzzle_x"] = PuzzleState(
            puzzle_id="puzzle_x", room_id="temple_entrance",
            status=PuzzleStatus.SOLVED, category=PuzzleCategory.OBSERVATION,
        )
        p.refresh(wm)
        p._text.configure(state="normal")
        content = p._text.get("1.0", tk.END)
        assert "x" in content.lower()
        p.destroy()


class TestStatusPanel:
    def test_instantiates(self):
        p = StatusPanel(_get_root(), ThemeManager())
        assert p is not None
        p.destroy()

    def test_refresh_shows_turn(self):
        p = StatusPanel(_get_root(), ThemeManager())
        wm = _simple_wm()
        wm.world.current_turn = 42
        p.refresh(wm)
        assert "42" in p._labels["turn"].cget("text")
        p.destroy()

    def test_refresh_shows_torch_state(self):
        p = StatusPanel(_get_root(), ThemeManager())
        wm = _simple_wm()
        wm.player.torch.state = "dim"
        wm.player.torch.fuel = 25
        p.refresh(wm)
        assert "dim" in p._labels["torch"].cget("text").lower()
        p.destroy()

    def test_low_fuel_uses_warning_colour(self):
        t = ThemeManager()
        p = StatusPanel(_get_root(), t)
        wm = _simple_wm()
        wm.player.torch.fuel = 10
        wm.player.torch.state = "almost_out"
        p.refresh(wm)
        assert p._labels["torch"].cget("fg") == t.colors.warning
        p.destroy()

    def test_refresh_does_not_mutate_wm(self):
        p = StatusPanel(_get_root(), ThemeManager())
        wm = _simple_wm()
        turn_before = wm.world.current_turn
        p.refresh(wm)
        assert wm.world.current_turn == turn_before
        p.destroy()


class TestEvaluationPanel:
    def test_instantiates(self):
        p = EvaluationPanel(_get_root(), ThemeManager())
        assert p is not None
        p.destroy()

    def test_refresh_creates_bars(self):
        p = EvaluationPanel(_get_root(), ThemeManager())
        wm = _simple_wm()
        p.refresh(wm)
        assert len(p._bars) > 0
        p.destroy()

    def test_all_attributes_have_bars(self):
        p = EvaluationPanel(_get_root(), ThemeManager())
        wm = _simple_wm()
        p.refresh(wm)
        for attr in ("observation", "curiosity", "wisdom", "patience",
                     "greed", "recklessness"):
            assert attr in p._bars
        p.destroy()

    def test_refresh_does_not_mutate_scores(self):
        p = EvaluationPanel(_get_root(), ThemeManager())
        wm = _simple_wm()
        wm.evaluation.observation.score = 55.0
        p.refresh(wm)
        assert wm.evaluation.observation.score == 55.0
        p.destroy()


class TestMapPanel:
    def test_instantiates(self):
        p = MapPanel(_get_root(), ThemeManager())
        assert p is not None
        p.destroy()

    def test_refresh_with_no_visited_rooms(self):
        p = MapPanel(_get_root(), ThemeManager())
        wm = _simple_wm()
        wm.player.visited_rooms = []
        p.refresh(wm)   # Should draw fog — no raises
        p.destroy()

    def test_refresh_with_visited_rooms(self):
        p = MapPanel(_get_root(), ThemeManager())
        wm = _simple_wm()
        wm.player.visited_rooms = ["temple_entrance", "hall_of_echoes"]
        p.refresh(wm)
        # Canvas should have items drawn
        items = p._canvas.find_all()
        assert len(items) > 0
        p.destroy()

    def test_refresh_marks_current_room(self):
        p = MapPanel(_get_root(), ThemeManager())
        wm = _simple_wm("temple_entrance")
        wm.player.visited_rooms = ["temple_entrance"]
        wm.player.current_room = "temple_entrance"
        p.refresh(wm)
        # Multiple items drawn (room rect + player marker oval)
        items = p._canvas.find_all()
        assert len(items) >= 2
        p.destroy()


# ===========================================================================
# StateManager
# ===========================================================================
from engine.state_manager import StateManager, GameState


class TestStateManager:
    def test_initial_state_is_loading(self):
        sm = StateManager()
        assert sm.state == GameState.LOADING

    def test_valid_transition_succeeds(self):
        sm = StateManager()
        ok = sm.transition(GameState.TITLE)
        assert ok is True
        assert sm.state == GameState.TITLE

    def test_invalid_transition_fails(self):
        sm = StateManager()
        # LOADING → PLAYING is valid, LOADING → ENDING is not
        ok = sm.transition(GameState.ENDING)
        assert ok is False
        assert sm.state == GameState.LOADING

    def test_is_playing(self):
        sm = StateManager()
        sm.transition(GameState.TITLE)
        sm.transition(GameState.PLAYING)
        assert sm.is_playing()

    def test_is_paused(self):
        sm = StateManager()
        sm.transition(GameState.TITLE)
        sm.transition(GameState.PLAYING)
        sm.transition(GameState.PAUSED)
        assert sm.is_paused()

    def test_observer_called_on_transition(self):
        sm = StateManager()
        events = []
        sm.add_observer(lambda f, t: events.append((f, t)))
        sm.transition(GameState.TITLE)
        assert events == [(GameState.LOADING, GameState.TITLE)]

    def test_observer_not_called_on_invalid_transition(self):
        sm = StateManager()
        events = []
        sm.add_observer(lambda f, t: events.append((f, t)))
        sm.transition(GameState.ENDING)   # invalid
        assert events == []

    def test_multiple_observers(self):
        sm = StateManager()
        a, b = [], []
        sm.add_observer(lambda f, t: a.append(t))
        sm.add_observer(lambda f, t: b.append(t))
        sm.transition(GameState.TITLE)
        assert a == [GameState.TITLE]
        assert b == [GameState.TITLE]

    def test_remove_observer(self):
        sm = StateManager()
        called = []
        fn = lambda f, t: called.append(t)
        sm.add_observer(fn)
        sm.remove_observer(fn)
        sm.transition(GameState.TITLE)
        assert called == []

    def test_force_ignores_validity(self):
        sm = StateManager()
        sm.force(GameState.ENDING)
        assert sm.state == GameState.ENDING

    def test_observer_exception_does_not_crash(self):
        sm = StateManager()
        sm.add_observer(lambda f, t: (_ for _ in ()).throw(RuntimeError("oops")))
        sm.transition(GameState.TITLE)   # Must not raise
        assert sm.state == GameState.TITLE

    def test_full_play_session_transitions(self):
        sm = StateManager()
        assert sm.transition(GameState.TITLE)
        assert sm.transition(GameState.PLAYING)
        assert sm.transition(GameState.PAUSED)
        assert sm.transition(GameState.PLAYING)
        assert sm.transition(GameState.JUDGMENT)
        assert sm.transition(GameState.ENDING)
        assert sm.transition(GameState.CREDITS)
        assert sm.transition(GameState.TITLE)


# ===========================================================================
# SaveManager
# ===========================================================================
from engine.save_manager import SaveManager


class TestSaveManager:
    def test_save_creates_file(self, tmp_path):
        import engine.save_manager as sm_mod
        original = sm_mod._SAVE_DIR
        sm_mod._SAVE_DIR = str(tmp_path)
        try:
            wm = _simple_wm()
            path = SaveManager.save(wm, slot=0)
            assert os.path.isfile(path)
        finally:
            sm_mod._SAVE_DIR = original

    def test_save_file_contains_world_model(self, tmp_path):
        import engine.save_manager as sm_mod
        original = sm_mod._SAVE_DIR
        sm_mod._SAVE_DIR = str(tmp_path)
        try:
            wm = _simple_wm()
            wm.world.current_turn = 17
            path = SaveManager.save(wm, slot=1)
            with open(path) as f:
                data = json.load(f)
            assert "world_model" in data
            assert data["_save_meta"]["turn"] == 17
        finally:
            sm_mod._SAVE_DIR = original

    def test_load_returns_world_model(self, tmp_path):
        import engine.save_manager as sm_mod
        original = sm_mod._SAVE_DIR
        sm_mod._SAVE_DIR = str(tmp_path)
        try:
            wm = _simple_wm()
            wm.world.current_turn = 5
            SaveManager.save(wm, slot=2)
            restored = SaveManager.load(slot=2)
            assert restored is not None
            assert restored.world.current_turn == 5
        finally:
            sm_mod._SAVE_DIR = original

    def test_load_missing_slot_returns_none(self, tmp_path):
        import engine.save_manager as sm_mod
        original = sm_mod._SAVE_DIR
        sm_mod._SAVE_DIR = str(tmp_path)
        try:
            result = SaveManager.load(slot=3)
            assert result is None
        finally:
            sm_mod._SAVE_DIR = original

    def test_load_corrupt_file_returns_none(self, tmp_path):
        import engine.save_manager as sm_mod
        original = sm_mod._SAVE_DIR
        sm_mod._SAVE_DIR = str(tmp_path)
        try:
            p = tmp_path / "slot_4.json"
            p.write_text("not valid json{{{")
            result = SaveManager.load(slot=4)
            assert result is None
        finally:
            sm_mod._SAVE_DIR = original

    def test_list_saves_empty_dir(self, tmp_path):
        import engine.save_manager as sm_mod
        original = sm_mod._SAVE_DIR
        sm_mod._SAVE_DIR = str(tmp_path)
        try:
            saves = SaveManager.list_saves()
            assert saves == []
        finally:
            sm_mod._SAVE_DIR = original

    def test_list_saves_returns_metadata(self, tmp_path):
        import engine.save_manager as sm_mod
        original = sm_mod._SAVE_DIR
        sm_mod._SAVE_DIR = str(tmp_path)
        try:
            wm = _simple_wm()
            wm.world.current_turn = 10
            SaveManager.save(wm, slot=0, label="Test Save")
            saves = SaveManager.list_saves()
            assert len(saves) == 1
            assert saves[0]["label"] == "Test Save"
            assert saves[0]["turn"] == 10
        finally:
            sm_mod._SAVE_DIR = original

    def test_delete_removes_file(self, tmp_path):
        import engine.save_manager as sm_mod
        original = sm_mod._SAVE_DIR
        sm_mod._SAVE_DIR = str(tmp_path)
        try:
            wm = _simple_wm()
            SaveManager.save(wm, slot=0)
            assert SaveManager.delete(slot=0)
            assert SaveManager.load(slot=0) is None
        finally:
            sm_mod._SAVE_DIR = original

    def test_delete_nonexistent_returns_false(self, tmp_path):
        import engine.save_manager as sm_mod
        original = sm_mod._SAVE_DIR
        sm_mod._SAVE_DIR = str(tmp_path)
        try:
            assert SaveManager.delete(slot=0) is False
        finally:
            sm_mod._SAVE_DIR = original

    def test_save_round_trip_preserves_room(self, tmp_path):
        import engine.save_manager as sm_mod
        original = sm_mod._SAVE_DIR
        sm_mod._SAVE_DIR = str(tmp_path)
        try:
            wm = _simple_wm("hall_of_guardians")
            wm.player.current_room = "hall_of_guardians"
            SaveManager.save(wm, slot=0)
            restored = SaveManager.load(slot=0)
            assert restored.player.current_room == "hall_of_guardians"
        finally:
            sm_mod._SAVE_DIR = original

    def test_autosave_triggers_on_interval(self, tmp_path):
        import engine.save_manager as sm_mod
        original = sm_mod._SAVE_DIR
        sm_mod._SAVE_DIR = str(tmp_path)
        try:
            wm = _simple_wm()
            wm.world.current_turn = 10
            saved = SaveManager.maybe_autosave(wm, autosave_interval=10)
            assert saved is True
        finally:
            sm_mod._SAVE_DIR = original

    def test_autosave_skips_non_interval_turn(self, tmp_path):
        import engine.save_manager as sm_mod
        original = sm_mod._SAVE_DIR
        sm_mod._SAVE_DIR = str(tmp_path)
        try:
            wm = _simple_wm()
            wm.world.current_turn = 7
            saved = SaveManager.maybe_autosave(wm, autosave_interval=10)
            assert saved is False
        finally:
            sm_mod._SAVE_DIR = original


# ===========================================================================
# Menu Components (headless — no mainloop needed)
# ===========================================================================
from ui.menu import TitleScreen, LoadingScreen, ExitConfirmDialog


class TestTitleScreen:
    def test_instantiates(self):
        ts = TitleScreen(
            _get_root(), ThemeManager(),
            on_new_game=lambda: None,
            on_quit=lambda: None,
            has_save=False,
        )
        assert ts is not None
        ts.destroy()

    def test_new_game_button_exists(self):
        ts = TitleScreen(
            _get_root(), ThemeManager(),
            on_new_game=lambda: None,
        )
        # Title text appears somewhere in widget hierarchy
        all_text = []
        def collect(w):
            try:
                t = str(w.cget("text"))
                if t:
                    all_text.append(t.lower())
            except Exception:
                pass
            for child in w.winfo_children():
                collect(child)
        collect(ts)
        assert any("journey" in t or "begin" in t for t in all_text)
        ts.destroy()

    def test_continue_button_only_when_has_save(self):
        called = []
        ts = TitleScreen(
            _get_root(), ThemeManager(),
            on_new_game=lambda: None,
            on_continue=lambda: called.append(1),
            has_save=True,
        )
        all_text = []
        def collect(w):
            try:
                t = str(w.cget("text"))
                if t:
                    all_text.append(t.lower())
            except Exception:
                pass
            for child in w.winfo_children():
                collect(child)
        collect(ts)
        assert any("continue" in t for t in all_text)
        ts.destroy()


class TestLoadingScreen:
    def test_instantiates(self):
        ls = LoadingScreen(_get_root(), ThemeManager())
        assert ls is not None
        ls.destroy()

    def test_set_status_does_not_raise(self):
        ls = LoadingScreen(_get_root(), ThemeManager())
        ls.set_status("Loading rooms...", 0.5)
        ls.destroy()

    def test_progress_clamped(self):
        ls = LoadingScreen(_get_root(), ThemeManager())
        ls.set_status("done", 1.5)   # over 1.0 — should not crash
        ls.set_status("done", -0.5)  # negative — should not crash
        ls.destroy()


# ===========================================================================
# Settings Dialog
# ===========================================================================
from ui.menu import SettingsDialog


class TestSettingsDialog:
    def test_instantiates(self):
        d = SettingsDialog(_get_root(), ThemeManager())
        assert d is not None
        d.destroy()

    def test_apply_calls_callback(self):
        received = []
        d = SettingsDialog(
            _get_root(), ThemeManager(),
            on_apply=lambda s: received.append(s),
        )
        d._apply()
        assert len(received) == 1
        assert isinstance(received[0], dict)

    def test_apply_returns_text_speed(self):
        received = []
        d = SettingsDialog(
            _get_root(), ThemeManager(),
            on_apply=lambda s: received.append(s),
        )
        d._vars["text_speed_ms"].set(40)
        d._apply()
        assert received[0]["text_speed_ms"] == 40


# ===========================================================================
# UI Integration: command routing through engine
# ===========================================================================
from engine.game_engine import GameEngine
from engine.command_result import ResultStatus


class TestCommandRouting:
    """Commands typed in the UI must route correctly through the Game Engine."""

    def _engine(self):
        wm = _simple_wm()
        return GameEngine(wm), wm

    def test_look_command_returns_success(self):
        engine, wm = self._engine()
        result = engine.process_input("look")
        assert result.status == ResultStatus.SUCCESS

    def test_inventory_command_returns_info(self):
        engine, wm = self._engine()
        result = engine.process_input("inventory")
        assert result.status == ResultStatus.INFO

    def test_status_command_via_engine(self):
        engine, wm = self._engine()
        result = engine.process_input("status")
        assert result.status == ResultStatus.INFO
        assert "turn" in result.message.lower() or "Turn" in result.message

    def test_hint_command_via_engine(self):
        engine, wm = self._engine()
        result = engine.process_input("hint")
        assert result.status == ResultStatus.INFO
        assert len(result.message) > 0

    def test_recommend_command_via_engine(self):
        engine, wm = self._engine()
        result = engine.process_input("recommend")
        assert result.status == ResultStatus.INFO
        assert len(result.message) > 0

    def test_invalid_direction_returns_failure(self):
        engine, wm = self._engine()
        result = engine.process_input("go south")
        assert result.status == ResultStatus.FAILURE

    def test_ui_does_not_modify_wm_directly(self):
        """Simulate a UI refresh cycle — panels read WM, engine writes it."""
        engine, wm = self._engine()
        root = _get_root()
        t = ThemeManager()

        narrative = NarrativePanel(root, t, typewriter_speed_ms=0)
        inv = InventoryPanel(root, t)
        status = StatusPanel(root, t)

        before_turn = wm.world.current_turn

        # Simulate player action via engine
        result = engine.process_input("look")

        # Simulate UI refresh (read-only operations)
        narrative.append(result.message, typewriter=False)
        inv.refresh(wm)
        status.refresh(wm)

        # World model was only changed by engine, not by panels
        assert wm.world.current_turn > before_turn   # engine advanced turn

        narrative.destroy()
        inv.destroy()
        status.destroy()

    def test_multiple_commands_advance_turn(self):
        engine, wm = self._engine()
        start = wm.world.current_turn
        engine.process_input("look")
        engine.process_input("look")
        engine.process_input("look")
        assert wm.world.current_turn == start + 3


# ===========================================================================
# Theme switching
# ===========================================================================

class TestThemeSwitching:
    def test_panel_accepts_different_theme(self):
        t1 = ThemeManager()
        t2 = ThemeManager()
        # Mutate t2 colours to simulate a light theme
        t2.colors.background = "#ffffff"
        t2.colors.text = "#000000"

        p1 = NarrativePanel(_get_root(), t1, typewriter_speed_ms=0)
        p2 = NarrativePanel(_get_root(), t2, typewriter_speed_ms=0)
        # Both must instantiate without error
        p1.append("dark", typewriter=False)
        p2.append("light", typewriter=False)
        p1.destroy()
        p2.destroy()

    def test_status_panel_different_themes(self):
        t = ThemeManager()
        t.colors.warning = "#ff0000"
        p = StatusPanel(_get_root(), t)
        wm = _simple_wm()
        wm.player.torch.fuel = 5
        p.refresh(wm)
        assert p._labels["torch"].cget("fg") == "#ff0000"
        p.destroy()


# ===========================================================================
# UI Package exports
# ===========================================================================

class TestUIPackageExports:
    def test_all_exports_importable(self):
        from ui import (
            MainWindow, ThemeManager, NarrativePanel, CommandInput,
            TempleAIPanel, ExplorerAIPanel, InventoryPanel,
            ObjectivesPanel, JournalPanel, StatusPanel,
            EvaluationPanel, MapPanel,
            TitleScreen, LoadingScreen, AudioEngine,
            TypewriterEffect, FadeEffect, FlickerEffect,
        )

    def test_engine_exports_importable(self):
        from engine import SaveManager, StateManager, GameState
        assert SaveManager is not None
        assert StateManager is not None
        assert GameState is not None

    def test_save_manager_has_required_methods(self):
        from engine.save_manager import SaveManager
        assert callable(SaveManager.save)
        assert callable(SaveManager.load)
        assert callable(SaveManager.list_saves)
        assert callable(SaveManager.delete)
        assert callable(SaveManager.maybe_autosave)

    def test_state_manager_has_required_methods(self):
        from engine.state_manager import StateManager
        sm = StateManager()
        assert callable(sm.transition)
        assert callable(sm.force)
        assert callable(sm.add_observer)
        assert callable(sm.remove_observer)

    def test_audio_engine_is_feature_flagged(self):
        from ui.audio import AudioEngine, _PYGAME_AVAILABLE
        audio = AudioEngine()
        # If pygame absent, must be disabled
        if not _PYGAME_AVAILABLE:
            assert not audio.is_available


# ===========================================================================
# Packaging artifacts
# ===========================================================================

class TestPackagingArtifacts:
    _ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

    def test_requirements_txt_exists(self):
        assert os.path.isfile(os.path.join(self._ROOT, "requirements.txt"))

    def test_changelog_exists(self):
        assert os.path.isfile(os.path.join(self._ROOT, "CHANGELOG.md"))

    def test_license_exists(self):
        assert os.path.isfile(os.path.join(self._ROOT, "LICENSE"))

    def test_setup_py_exists(self):
        assert os.path.isfile(os.path.join(self._ROOT, "setup.py"))

    def test_pyinstaller_spec_exists(self):
        assert os.path.isfile(os.path.join(self._ROOT, "temple.spec"))

    def test_audio_manifest_exists(self):
        assert os.path.isfile(
            os.path.join(self._ROOT, "config", "audio_manifest.json")
        )

    def test_audio_manifest_valid_json(self):
        path = os.path.join(self._ROOT, "config", "audio_manifest.json")
        with open(path) as f:
            data = json.load(f)
        assert "sfx" in data
        assert "music" in data
        assert "ambience" in data

    def test_assets_directories_exist(self):
        for folder in ("images", "audio", "fonts", "icons", "animations"):
            p = os.path.join(self._ROOT, "assets", folder)
            assert os.path.isdir(p), f"Missing assets/{folder}"

    def test_config_graphics_json_exists(self):
        assert os.path.isfile(
            os.path.join(self._ROOT, "config", "graphics.json")
        )
