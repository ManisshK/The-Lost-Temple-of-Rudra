"""
main_window.py — The Lost Temple of Rudra

Main application window.  Root tkinter container for the entire game UI.

Layout
──────
  ┌──────────────────────────────┬──────────────────────┐
  │  NarrativePanel (60%)        │  InventoryPanel       │
  │  ─ room title                │  ─ item list          │
  │  ─ typewriter narration      │  ObjectivesPanel      │
  │  ─ Temple AI bar             │  ─ current mission    │
  │  ─ Explorer AI bar           │  JournalPanel         │
  │  ─ CommandInput              │  EvaluationPanel      │
  ├──────────────────────────────│  MapPanel             │
  │  StatusPanel (full width)    │                       │
  └──────────────────────────────┴──────────────────────┘

Rules
──────
  - Never writes to the World Model.
  - All player commands go through GameEngine.process_input().
  - All AI requests go through AIManager via GameEngine.
  - Refresh all panels after every command that alters game state.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable, Optional, TYPE_CHECKING

from .theme import ThemeManager
from .animations import FlickerEffect
from .dialogue import NarrativePanel, CommandInput, TempleAIPanel, ExplorerAIPanel
from .inventory import InventoryPanel
from .journal import ObjectivesPanel, JournalPanel, StatusPanel, EvaluationPanel, MapPanel
from .menu import (
    TitleScreen, PauseMenu, SaveLoadDialog,
    SettingsDialog, ExitConfirmDialog, LoadingScreen,
)

if TYPE_CHECKING:
    from src.world.world_model import WorldModel
    from src.engine.game_engine import GameEngine
    from src.ai.ai_manager import AIManager


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_APP_TITLE = "The Lost Temple of Rudra"
_MIN_W, _MIN_H = 800, 600


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow:
    """
    Root application window.

    Owns the tkinter.Tk root.
    Owns the ThemeManager.
    Coordinates all panels.
    Dispatches commands through the Game Engine.
    Refreshes all panels after state changes.

    Usage::

        from src.ui.main_window import MainWindow
        window = MainWindow()
        window.start(engine, world_model, ai_manager)
        window.run()        # enters the tk mainloop
    """

    def __init__(self, config_path: str = "") -> None:
        self._theme = ThemeManager(config_path) if config_path else ThemeManager()
        self._root: Optional[tk.Tk] = None
        self._engine: Optional["GameEngine"] = None
        self._world_model: Optional["WorldModel"] = None
        self._ai_manager: Optional["AIManager"] = None
        self._panels_built = False
        self._typewriter_speed = 20   # ms per character
        self._flicker: Optional[FlickerEffect] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(
        self,
        engine: "GameEngine",
        world_model: "WorldModel",
        ai_manager: Optional["AIManager"] = None,
    ) -> None:
        """Wire the game systems into the window."""
        self._engine = engine
        self._world_model = world_model
        self._ai_manager = ai_manager

    def run(self) -> None:
        """
        Build the window and enter the tkinter mainloop.
        Blocks until the window is closed.
        """
        self._build_root()
        self._build_title_screen()
        self._root.mainloop()

    def run_game_directly(self) -> None:
        """
        Build the window and jump straight to the game layout
        (skipping the title screen).  Used for development / testing.
        """
        self._build_root()
        self._build_game_layout()
        self._show_room()
        self._root.mainloop()

    def destroy(self) -> None:
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Root window
    # ------------------------------------------------------------------

    def _build_root(self) -> None:
        t = self._theme
        self._root = tk.Tk()
        self._root.title(t.window.title or _APP_TITLE)
        self._root.configure(bg=t.colors.background)
        self._root.minsize(_MIN_W, _MIN_H)
        self._root.geometry(f"{t.window.width}x{t.window.height}")

        if t.window.resizable:
            self._root.resizable(True, True)
        else:
            self._root.resizable(False, False)

        if t.window.fullscreen:
            self._root.attributes("-fullscreen", True)

        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.bind("<F11>", self._toggle_fullscreen)
        self._root.bind("<Escape>", self._on_escape)
        self._root.bind("<F5>", lambda _: self._quick_save())
        self._root.bind("<F9>", lambda _: self._quick_load())

        # Centre on screen
        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x = (sw - t.window.width) // 2
        y = (sh - t.window.height) // 2
        self._root.geometry(f"{t.window.width}x{t.window.height}+{x}+{y}")

    # ------------------------------------------------------------------
    # Title screen
    # ------------------------------------------------------------------

    def _build_title_screen(self) -> None:
        from src.engine.save_manager import SaveManager
        has_save = bool(SaveManager.list_saves())

        self._title_frame = TitleScreen(
            self._root,
            self._theme,
            on_new_game=self._on_new_game,
            on_continue=self._on_continue if has_save else None,
            on_load=self._on_load_game,
            on_settings=self._on_settings,
            on_quit=self._on_close,
            has_save=has_save,
        )
        self._title_frame.pack(fill="both", expand=True)

    def _on_new_game(self) -> None:
        self._title_frame.destroy()
        self._show_loading("Awakening the temple...", 0.1)
        # Engine + world model should already be wired via start()
        self._build_game_layout()
        self._show_room()

    def _on_continue(self) -> None:
        from src.engine.save_manager import SaveManager
        saves = SaveManager.list_saves()
        if saves:
            self._load_slot(0)   # most recent
        else:
            self._on_new_game()

    def _on_load_game(self) -> None:
        from src.engine.save_manager import SaveManager
        saves = SaveManager.list_saves()
        slot_info = [
            {"label": s["label"]} if isinstance(s, dict) else {"label": str(s)}
            for s in saves
        ] + [None] * (5 - len(saves))

        dlg = SaveLoadDialog(
            self._root, self._theme, mode="load",
            slots=slot_info[:5],
            on_confirm=self._load_slot,
        )

    # ------------------------------------------------------------------
    # Game layout
    # ------------------------------------------------------------------

    def _build_game_layout(self) -> None:
        if self._panels_built:
            return
        self._panels_built = True
        t = self._theme

        # ── Main container ────────────────────────────────────────────
        self._game_frame = tk.Frame(self._root, bg=t.colors.background)
        self._game_frame.pack(fill="both", expand=True)
        self._game_frame.columnconfigure(0, weight=int(t.narrative_width_pct * 10))
        self._game_frame.columnconfigure(1, weight=int(t.sidebar_width_pct * 10))
        self._game_frame.rowconfigure(0, weight=1)
        self._game_frame.rowconfigure(1, weight=0)

        # ── Left column: narrative + AI bars + input ──────────────────
        left = tk.Frame(self._game_frame, bg=t.colors.background)
        left.grid(row=0, column=0, sticky="nsew", padx=(4, 2), pady=4)
        left.rowconfigure(0, weight=1)
        left.rowconfigure(1, weight=0)
        left.rowconfigure(2, weight=0)
        left.rowconfigure(3, weight=0)
        left.columnconfigure(0, weight=1)

        self._narrative = NarrativePanel(
            left, t, typewriter_speed_ms=self._typewriter_speed,
        )
        self._narrative.grid(row=0, column=0, sticky="nsew")

        # Thin border
        tk.Frame(left, bg=t.colors.border, height=1).grid(
            row=1, column=0, sticky="ew"
        )

        self._temple_ai_panel = TempleAIPanel(left, t)
        self._temple_ai_panel.grid(row=2, column=0, sticky="ew")

        self._explorer_ai_panel = ExplorerAIPanel(left, t)
        self._explorer_ai_panel.grid(row=3, column=0, sticky="ew")

        # Command input
        self._command_input = CommandInput(left, t, on_submit=self._on_command)
        self._command_input.grid(row=4, column=0, sticky="ew", pady=(2, 0))

        # ── Right column: sidebar panels ──────────────────────────────
        right = tk.Frame(self._game_frame, bg=t.colors.background)
        right.grid(row=0, column=1, sticky="nsew", padx=(2, 4), pady=4)
        right.columnconfigure(0, weight=1)
        for r in range(6):
            right.rowconfigure(r, weight=1)

        self._inventory_panel = InventoryPanel(right, t)
        self._inventory_panel.grid(row=0, column=0, sticky="nsew", pady=2)

        tk.Frame(right, bg=t.colors.border, height=1).grid(
            row=1, column=0, sticky="ew"
        )

        self._objectives_panel = ObjectivesPanel(right, t)
        self._objectives_panel.grid(row=2, column=0, sticky="nsew", pady=2)

        self._journal_panel = JournalPanel(right, t)
        self._journal_panel.grid(row=3, column=0, sticky="nsew", pady=2)

        self._eval_panel = EvaluationPanel(right, t)
        self._eval_panel.grid(row=4, column=0, sticky="nsew", pady=2)

        self._map_panel = MapPanel(right, t)
        self._map_panel.grid(row=5, column=0, sticky="nsew", pady=2)

        # ── Status bar (bottom, full width) ──────────────────────────
        self._status_bar = StatusPanel(self._game_frame, t)
        self._status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 2))

        # Focus input
        self._command_input.focus()

    # ------------------------------------------------------------------
    # Loading screen
    # ------------------------------------------------------------------

    def _show_loading(self, message: str, progress: float = 0.0) -> None:
        if not self._root:
            return
        loading = LoadingScreen(self._root, self._theme)
        loading.place(relx=0, rely=0, relwidth=1, relheight=1)
        loading.set_status(message, progress)
        self._root.update_idletasks()
        # Auto-dismiss after a short delay
        self._root.after(400, loading.destroy)

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def _on_command(self, raw: str) -> None:
        """
        Called when the player presses Enter on the command input.
        Dispatches through the Game Engine, then refreshes all panels.
        """
        if self._engine is None:
            return

        # Disable input during processing
        self._command_input.set_enabled(False)

        try:
            result = self._engine.process_input(raw)
            self._display_result(result)
            self._refresh_panels()
        finally:
            self._command_input.set_enabled(True)
            self._command_input.focus()

    def _display_result(self, result) -> None:
        """Route a GameResult to the appropriate narrative display."""
        from src.engine.command_result import ResultStatus

        msg = result.message or ""
        if not msg:
            return

        # Choose tag based on result status
        tag_map = {
            ResultStatus.SUCCESS: "normal",
            ResultStatus.FAILURE: "warning",
            ResultStatus.INFO:    "highlight",
            ResultStatus.SYSTEM:  "system",
            ResultStatus.INVALID: "dim",
        }
        tag = tag_map.get(result.status, "normal")

        # Check if player moved rooms — show room header
        actions = getattr(result, "actions_taken", []) or []
        moved = any(a.startswith("moved_to:") for a in actions)
        if moved and self._world_model:
            room_id = self._world_model.player.current_room
            room_name = room_id.replace("_", " ").title()
            self._narrative.append_room_title(room_name)

        self._narrative.append(msg, tag=tag)

        # Temple AI narration (if any was generated this turn)
        if self._ai_manager and self._world_model:
            self._refresh_ai_panels()

    # ------------------------------------------------------------------
    # Panel refresh
    # ------------------------------------------------------------------

    def _refresh_panels(self) -> None:
        wm = self._world_model
        if wm is None:
            return
        self._inventory_panel.refresh(wm)
        self._objectives_panel.refresh(wm)
        self._journal_panel.refresh(wm)
        self._eval_panel.refresh(wm)
        self._map_panel.refresh(wm)
        self._status_bar.refresh(wm)

    def _refresh_ai_panels(self) -> None:
        if not self._ai_manager or not self._world_model:
            return
        try:
            from src.ai.ai_manager import AIRequest
            # Temple AI — brief atmospheric observation
            t_resp = self._ai_manager.handle(
                AIRequest("observe_action", action_str="look"), self._world_model
            )
            if t_resp.text:
                self._temple_ai_panel.set_message(t_resp.text)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Initial room display
    # ------------------------------------------------------------------

    def _show_room(self) -> None:
        if self._engine is None:
            return
        result = self._engine.process_input("look")
        self._display_result(result)
        self._refresh_panels()

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def _quick_save(self) -> None:
        from src.engine.save_manager import SaveManager
        if self._world_model:
            SaveManager.save(self._world_model, slot=0)
            self._narrative.append("Game saved.", tag="system", typewriter=False)

    def _quick_load(self) -> None:
        self._on_load_game()

    def _load_slot(self, slot: int) -> None:
        from src.engine.save_manager import SaveManager
        from src.world.temple_loader import load_temple
        from src.engine.game_engine import GameEngine

        try:
            wm = SaveManager.load(slot=slot)
            if wm is None:
                return
            self._world_model = wm
            self._engine = GameEngine(wm)
            if not self._panels_built:
                self._build_game_layout()
            self._refresh_panels()
            self._show_room()
        except Exception as exc:
            self._narrative.append(
                f"Failed to load save: {exc}", tag="warning", typewriter=False
            )

    def _save_slot(self, slot: int) -> None:
        from src.engine.save_manager import SaveManager
        if self._world_model:
            SaveManager.save(self._world_model, slot=slot)

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------

    def _on_settings(self) -> None:
        SettingsDialog(
            self._root, self._theme,
            on_apply=self._apply_settings,
        )

    def _apply_settings(self, settings: dict) -> None:
        speed = settings.get("text_speed_ms", self._typewriter_speed)
        if isinstance(speed, int):
            self._typewriter_speed = speed
            if hasattr(self, "_narrative"):
                self._narrative.set_typewriter_speed(speed)

        fullscreen = settings.get("fullscreen", False)
        if self._root:
            self._root.attributes("-fullscreen", bool(fullscreen))

    def _on_pause(self) -> None:
        def resume():
            pause.destroy()
            self._command_input.focus()

        pause = PauseMenu(
            self._root, self._theme,
            on_resume=resume,
            on_save=lambda: (self._quick_save(), resume()),
            on_load=lambda: (resume(), self._on_load_game()),
            on_settings=lambda: SettingsDialog(
                self._root, self._theme, on_apply=self._apply_settings
            ),
            on_quit_title=self._on_quit_to_title,
        )

    def _on_quit_to_title(self) -> None:
        if self._game_frame:
            self._game_frame.destroy()
        self._panels_built = False
        self._build_title_screen()

    # ------------------------------------------------------------------
    # Window events
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        if ExitConfirmDialog.ask(self._root):
            if self._world_model:
                try:
                    from src.engine.save_manager import SaveManager
                    SaveManager.save(self._world_model, slot=0, label="autosave")
                except Exception:
                    pass
            self.destroy()

    def _on_escape(self, _event=None) -> None:
        if self._panels_built:
            self._on_pause()

    def _toggle_fullscreen(self, _event=None) -> None:
        if self._root:
            current = self._root.attributes("-fullscreen")
            self._root.attributes("-fullscreen", not current)
