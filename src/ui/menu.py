"""
menu.py — The Lost Temple of Rudra

Title screen, pause menu, save/load dialog, settings, and exit confirmation.

All screens are pure tkinter frames.
Game actions (new game, save, load, quit) use callbacks — never touch World Model directly.
"""

from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional, TYPE_CHECKING

from .theme import ThemeManager

if TYPE_CHECKING:
    pass

_SETTINGS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "game_settings.json")
)


# ---------------------------------------------------------------------------
# Helper — themed button
# ---------------------------------------------------------------------------

def _make_button(
    parent: tk.Widget,
    text: str,
    command: Callable,
    theme: ThemeManager,
    width: int = 22,
) -> tk.Button:
    t = theme
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=t.colors.panel,
        fg=t.colors.text,
        activebackground=t.colors.accent,
        activeforeground=t.colors.highlight,
        relief="flat",
        bd=0,
        font=t.font_normal(),
        width=width,
        pady=8,
        cursor="hand2",
    )
    btn.bind("<Enter>", lambda _: btn.configure(fg=t.colors.highlight))
    btn.bind("<Leave>", lambda _: btn.configure(fg=t.colors.text))
    return btn


# ---------------------------------------------------------------------------
# TitleScreen
# ---------------------------------------------------------------------------

class TitleScreen(tk.Frame):
    """
    Opening title screen.
    Callbacks: on_new_game, on_continue, on_load, on_settings, on_quit.
    """

    def __init__(
        self,
        parent: tk.Widget,
        theme: ThemeManager,
        on_new_game: Callable,
        on_continue: Optional[Callable] = None,
        on_load: Optional[Callable] = None,
        on_settings: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
        has_save: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=theme.colors.background, **kwargs)
        self._theme = theme
        self._build(on_new_game, on_continue, on_load, on_settings, on_quit, has_save)

    def _build(
        self,
        on_new_game, on_continue, on_load, on_settings, on_quit, has_save
    ) -> None:
        t = self._theme
        self.columnconfigure(0, weight=1)

        # Spacer
        tk.Frame(self, bg=t.colors.background, height=80).pack()

        # Title
        tk.Label(
            self,
            text="THE LOST TEMPLE OF RUDRA",
            fg=t.colors.accent,
            bg=t.colors.background,
            font=t.font_title(),
        ).pack(pady=4)

        # Subtitle
        tk.Label(
            self,
            text="The temple does not remember your name.\nIt remembers your choices.",
            fg=t.colors.dim,
            bg=t.colors.background,
            font=(t.fonts.family_secondary, t.fonts.size_large),
            justify="center",
        ).pack(pady=16)

        sep = tk.Frame(self, bg=t.colors.border, height=1, width=300)
        sep.pack(pady=12)

        btn_frame = tk.Frame(self, bg=t.colors.background)
        btn_frame.pack()

        _make_button(btn_frame, "Begin the Journey", on_new_game, t).pack(pady=4)

        if has_save and on_continue:
            _make_button(btn_frame, "Continue", on_continue, t).pack(pady=4)

        if on_load:
            _make_button(btn_frame, "Load Game", on_load, t).pack(pady=4)

        if on_settings:
            _make_button(btn_frame, "Settings", on_settings, t).pack(pady=4)

        if on_quit:
            _make_button(btn_frame, "Quit", on_quit, t).pack(pady=4)

        # Version footer
        tk.Label(
            self,
            text="v0.1.0 — Phase 7",
            fg=t.colors.border,
            bg=t.colors.background,
            font=t.font_small(),
        ).pack(side="bottom", pady=8)


# ---------------------------------------------------------------------------
# PauseMenu
# ---------------------------------------------------------------------------

class PauseMenu(tk.Toplevel):
    """
    In-game pause menu overlay.
    """

    def __init__(
        self,
        parent: tk.Widget,
        theme: ThemeManager,
        on_resume: Callable,
        on_save: Callable,
        on_load: Callable,
        on_settings: Callable,
        on_quit_title: Callable,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        t = theme
        self.title("Paused")
        self.configure(bg=t.colors.background)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        tk.Label(
            self, text="— PAUSED —",
            fg=t.colors.accent, bg=t.colors.background,
            font=t.font_title(),
        ).pack(pady=20)

        for text, cmd in [
            ("Resume", on_resume),
            ("Save Game", on_save),
            ("Load Game", on_load),
            ("Settings", on_settings),
            ("Quit to Title", on_quit_title),
        ]:
            _make_button(self, text, cmd, t).pack(pady=3)

        tk.Frame(self, height=16, bg=t.colors.background).pack()
        self.bind("<Escape>", lambda _: on_resume())


# ---------------------------------------------------------------------------
# SaveLoadDialog
# ---------------------------------------------------------------------------

class SaveLoadDialog(tk.Toplevel):
    """
    Save / Load slot selector dialog.
    Shows up to 5 save slots with turn info.
    """

    _NUM_SLOTS = 5

    def __init__(
        self,
        parent: tk.Widget,
        theme: ThemeManager,
        mode: str,                         # "save" | "load"
        slots: list[Optional[dict]],       # list of slot info dicts or None
        on_confirm: Callable[[int], None], # called with slot index (0-based)
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        t = theme
        title_str = "Save Game" if mode == "save" else "Load Game"
        self.title(title_str)
        self.configure(bg=t.colors.background)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        tk.Label(
            self, text=title_str,
            fg=t.colors.accent, bg=t.colors.background,
            font=t.font_large(),
        ).pack(pady=12, padx=20)

        for i in range(self._NUM_SLOTS):
            slot = slots[i] if i < len(slots) else None
            label = slot.get("label", f"Slot {i + 1}") if slot else f"Slot {i + 1} — Empty"
            btn_text = label

            state = "normal" if (mode == "save" or slot is not None) else "disabled"
            btn = tk.Button(
                self,
                text=btn_text,
                command=lambda idx=i: (on_confirm(idx), self.destroy()),
                bg=t.colors.panel,
                fg=t.colors.text if slot else t.colors.dim,
                activebackground=t.colors.accent,
                activeforeground=t.colors.highlight,
                relief="flat", bd=0, font=t.font_normal(),
                width=28, pady=6, state=state,
            )
            btn.pack(pady=2, padx=20)

        _make_button(
            self, "Cancel", self.destroy, t, width=12
        ).pack(pady=8)


# ---------------------------------------------------------------------------
# SettingsDialog
# ---------------------------------------------------------------------------

class SettingsDialog(tk.Toplevel):
    """
    Settings dialog: graphics, audio, AI model, text speed, accessibility.
    Reads/writes config/game_settings.json.
    """

    def __init__(
        self,
        parent: tk.Widget,
        theme: ThemeManager,
        on_apply: Optional[Callable[[dict], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        t = theme
        self.title("Settings")
        self.configure(bg=t.colors.background)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self._theme = t
        self._on_apply = on_apply
        self._settings = self._load_settings()
        self._vars: dict[str, tk.Variable] = {}
        self._build()

    def _load_settings(self) -> dict:
        try:
            with open(_SETTINGS_PATH, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def _build(self) -> None:
        t = self._theme
        tk.Label(
            self, text="SETTINGS",
            fg=t.colors.accent, bg=t.colors.background,
            font=t.font_large(), pady=12,
        ).pack()

        notebook_frame = tk.Frame(self, bg=t.colors.background)
        notebook_frame.pack(padx=20, pady=4, fill="both")

        # Text speed
        self._add_slider(notebook_frame, "Text Speed (ms/char)", "text_speed_ms",
                         0, 80, self._settings.get("display", {}).get("text_speed", "normal"))

        # Fullscreen
        fs_var = tk.BooleanVar(value=False)
        self._vars["fullscreen"] = fs_var
        row = tk.Frame(notebook_frame, bg=t.colors.background)
        row.pack(fill="x", pady=3)
        tk.Label(row, text="Fullscreen:", fg=t.colors.text,
                 bg=t.colors.background, font=t.font_small(), width=20, anchor="w").pack(side="left")
        tk.Checkbutton(
            row, variable=fs_var,
            bg=t.colors.background, fg=t.colors.text,
            activebackground=t.colors.background,
            selectcolor=t.colors.panel,
        ).pack(side="left")

        # AI model label
        ai_model = (
            self._settings.get("ollama", {}).get("model", "qwen")
            if "ollama" in self._settings
            else self._settings.get("ai_model", "qwen")
        )
        row2 = tk.Frame(notebook_frame, bg=t.colors.background)
        row2.pack(fill="x", pady=3)
        tk.Label(row2, text="AI Model:", fg=t.colors.text,
                 bg=t.colors.background, font=t.font_small(), width=20, anchor="w").pack(side="left")
        tk.Label(row2, text=ai_model, fg=t.colors.dim,
                 bg=t.colors.background, font=t.font_small()).pack(side="left")

        btn_row = tk.Frame(self, bg=t.colors.background)
        btn_row.pack(pady=12)
        _make_button(btn_row, "Apply", self._apply, t, width=10).pack(side="left", padx=4)
        _make_button(btn_row, "Close", self.destroy, t, width=10).pack(side="left", padx=4)

    def _add_slider(
        self, parent: tk.Widget, label: str, key: str,
        min_val: int, max_val: int, current
    ) -> None:
        t = self._theme
        row = tk.Frame(parent, bg=t.colors.background)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=f"{label}:", fg=t.colors.text,
                 bg=t.colors.background, font=t.font_small(), width=20, anchor="w").pack(side="left")
        val = current if isinstance(current, int) else 25
        var = tk.IntVar(value=val)
        self._vars[key] = var
        tk.Scale(
            row, from_=min_val, to=max_val, orient="horizontal",
            variable=var, length=140,
            bg=t.colors.background, fg=t.colors.text,
            troughcolor=t.colors.panel,
            highlightthickness=0,
        ).pack(side="left")

    def _apply(self) -> None:
        settings = {k: v.get() for k, v in self._vars.items()}
        if self._on_apply:
            self._on_apply(settings)
        self.destroy()


# ---------------------------------------------------------------------------
# ExitConfirmDialog
# ---------------------------------------------------------------------------

class ExitConfirmDialog:
    """Simple exit confirmation. Returns True if user confirms."""

    @staticmethod
    def ask(parent: tk.Widget) -> bool:
        return messagebox.askyesno(
            "Quit",
            "The temple will remember your choices.\nAre you sure you want to leave?",
            icon="question",
            parent=parent,
        )


# ---------------------------------------------------------------------------
# LoadingScreen
# ---------------------------------------------------------------------------

class LoadingScreen(tk.Frame):
    """Brief loading overlay shown while the world model initialises."""

    def __init__(self, parent: tk.Widget, theme: ThemeManager, **kwargs) -> None:
        super().__init__(parent, bg=theme.colors.background, **kwargs)
        t = theme
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        inner = tk.Frame(self, bg=t.colors.background)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            inner,
            text="THE LOST TEMPLE OF RUDRA",
            fg=t.colors.accent, bg=t.colors.background,
            font=t.font_title(),
        ).pack()

        self._status = tk.Label(
            inner,
            text="Awakening the temple...",
            fg=t.colors.dim, bg=t.colors.background,
            font=t.font_normal(),
        )
        self._status.pack(pady=16)

        self._bar_canvas = tk.Canvas(
            inner, width=300, height=6,
            bg=t.colors.panel, highlightthickness=0,
        )
        self._bar_canvas.pack()
        self._progress = 0.0

    def set_status(self, text: str, progress: float = None) -> None:
        self._status.configure(text=text)
        if progress is not None:
            self._progress = max(0.0, min(1.0, progress))
            self._bar_canvas.delete("all")
            w = int(300 * self._progress)
            t = self._theme if hasattr(self, "_theme") else None
            color = "#8b4513"
            self._bar_canvas.create_rectangle(0, 0, w, 6, fill=color, outline="")
        self.update_idletasks()
