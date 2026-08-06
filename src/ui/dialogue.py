"""
dialogue.py — The Lost Temple of Rudra

Narrative display panel and AI response panels.

Components:
  NarrativePanel   — scrollable story/narration text area with typewriter effect
  TempleAIPanel    — Temple AI atmospheric observations
  ExplorerAIPanel  — Explorer AI recommendations and responses
  CommandInput     — text entry field that dispatches through the Game Engine

Rules:
  - Never writes to the World Model.
  - All commands go through the Game Engine.
  - AI requests go through the AI Manager via the Game Engine.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, TYPE_CHECKING

from .theme import ThemeManager
from .animations import TypewriterEffect, FadeEffect

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# NarrativePanel
# ---------------------------------------------------------------------------

class NarrativePanel(tk.Frame):
    """
    Main story/narration display.
    Append text with category tags (normal, temple, explorer, hint, warning, success).
    Supports typewriter effect and skip-animation on click/Enter.
    """

    # Tag names and their semantic colours (resolved from theme at build time)
    _TAGS = {
        "normal":    None,           # uses theme text colour
        "temple":    "ai_temple",    # purple — temple consciousness
        "explorer":  "ai_explorer",  # blue   — explorer guide
        "hint":      "hint",         # green  — redirect hints
        "warning":   "warning",      # red    — danger / event narration
        "success":   "success",      # green  — puzzle solved
        "dim":       "dim",          # muted  — past / inactive text
        "highlight": "highlight",    # gold   — lore / important
        "title":     "accent",       # brown  — room titles
        "system":    "dim",          # muted  — system messages
    }

    def __init__(
        self,
        parent: tk.Widget,
        theme: ThemeManager,
        typewriter_speed_ms: int = 20,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=theme.colors.background, **kwargs)
        self._theme = theme
        self._speed = typewriter_speed_ms
        self._active_tw: Optional[TypewriterEffect] = None
        self._build()

    def _build(self) -> None:
        t = self._theme
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Scrollable text area
        self._text = tk.Text(
            self,
            bg=t.colors.panel,
            fg=t.colors.text,
            font=t.font_normal(),
            wrap=tk.WORD,
            state="disabled",
            relief="flat",
            bd=0,
            padx=16,
            pady=12,
            cursor="arrow",
            insertbackground=t.colors.cursor,
            selectbackground=t.colors.accent,
            selectforeground=t.colors.text,
            spacing3=4,
        )
        self._text.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        self._scroll = tk.Scrollbar(
            self,
            command=self._text.yview,
            bg=t.colors.scrollbar,
            troughcolor=t.colors.panel,
            relief="flat",
            bd=0,
            width=10,
        )
        self._scroll.grid(row=0, column=1, sticky="ns")
        self._text.configure(yscrollcommand=self._scroll.set)

        # Configure semantic tags
        self._configure_tags()

        # Click anywhere to skip typewriter
        self._text.bind("<Button-1>", self._skip_animation)
        self._text.bind("<Return>", self._skip_animation)

    def _configure_tags(self) -> None:
        t = self._theme
        color_map = {
            "ai_temple": t.colors.ai_temple,
            "ai_explorer": t.colors.ai_explorer,
            "hint": t.colors.hint,
            "warning": t.colors.warning,
            "success": t.colors.success,
            "dim": t.colors.dim,
            "highlight": t.colors.highlight,
            "accent": t.colors.accent,
        }
        for tag, color_key in self._TAGS.items():
            color = color_map.get(color_key, t.colors.text) if color_key else t.colors.text
            self._text.tag_configure(
                tag,
                foreground=color,
                font=t.font_normal(),
            )
        # Title tag uses larger bold font
        self._text.tag_configure(
            "title",
            foreground=t.colors.accent,
            font=(t.fonts.family_secondary, t.fonts.size_large, "bold"),
        )

    def _skip_animation(self, _event=None) -> None:
        if self._active_tw:
            self._active_tw.cancel()
            self._active_tw = None

    def append(
        self,
        text: str,
        tag: str = "normal",
        typewriter: bool = True,
        newline: bool = True,
        on_complete: Optional[Callable] = None,
    ) -> None:
        """
        Append text to the narrative display.
        If typewriter=True, reveals character by character.
        """
        # Cancel any in-progress animation
        self._skip_animation()

        full_text = text + ("\n" if newline else "")

        if typewriter and self._speed > 0:
            self._text.configure(state="normal")
            self._text.insert(tk.END, "\n", "dim")  # spacing before
            self._text.configure(state="disabled")

            self._active_tw = TypewriterEffect(
                self._text, full_text,
                speed_ms=self._speed,
                tag=tag,
                on_complete=on_complete,
            )
            self._active_tw.start()
        else:
            self._text.configure(state="normal")
            self._text.insert(tk.END, "\n", "dim")
            self._text.insert(tk.END, full_text, tag)
            self._text.configure(state="disabled")
            self._text.see(tk.END)
            if on_complete:
                on_complete()

    def append_room_title(self, title: str) -> None:
        """Display a room title prominently."""
        self._skip_animation()
        sep = "─" * 50
        self._text.configure(state="normal")
        self._text.insert(tk.END, f"\n{sep}\n", "dim")
        self._text.insert(tk.END, f"  {title.upper()}\n", "title")
        self._text.insert(tk.END, f"{sep}\n", "dim")
        self._text.configure(state="disabled")
        self._text.see(tk.END)

    def clear(self) -> None:
        self._skip_animation()
        self._text.configure(state="normal")
        self._text.delete("1.0", tk.END)
        self._text.configure(state="disabled")

    def set_typewriter_speed(self, speed_ms: int) -> None:
        self._speed = max(0, speed_ms)


# ---------------------------------------------------------------------------
# CommandInput
# ---------------------------------------------------------------------------

class CommandInput(tk.Frame):
    """
    Single-line command entry field.
    Dispatches commands via the on_submit callback.
    Maintains a command history (up/down arrow navigation).
    """

    _HISTORY_LIMIT = 100

    def __init__(
        self,
        parent: tk.Widget,
        theme: ThemeManager,
        on_submit: Callable[[str], None],
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=theme.colors.background, **kwargs)
        self._theme = theme
        self._on_submit = on_submit
        self._history: list[str] = []
        self._history_idx: int = -1
        self._build()

    def _build(self) -> None:
        t = self._theme
        self.columnconfigure(1, weight=1)

        # Prompt label
        self._prompt = tk.Label(
            self,
            text=">",
            fg=t.colors.accent,
            bg=t.colors.input_bg,
            font=t.font_mono(),
            padx=8,
            pady=6,
        )
        self._prompt.grid(row=0, column=0, sticky="ew")

        # Entry field
        self._var = tk.StringVar()
        self._entry = tk.Entry(
            self,
            textvariable=self._var,
            bg=t.colors.input_bg,
            fg=t.colors.text,
            font=t.font_mono(),
            relief="flat",
            bd=0,
            insertbackground=t.colors.cursor,
            selectbackground=t.colors.accent,
            selectforeground=t.colors.text,
        )
        self._entry.grid(row=0, column=1, sticky="ew", ipady=6, padx=(0, 8))

        self._entry.bind("<Return>", self._submit)
        self._entry.bind("<Up>", self._history_back)
        self._entry.bind("<Down>", self._history_forward)
        self._entry.bind("<Escape>", lambda _: self._entry.delete(0, tk.END))

    def _submit(self, _event=None) -> None:
        raw = self._var.get().strip()
        if not raw:
            return
        self._var.set("")
        self._history_idx = -1
        if not self._history or self._history[-1] != raw:
            self._history.append(raw)
            if len(self._history) > self._HISTORY_LIMIT:
                self._history.pop(0)
        self._on_submit(raw)

    def _history_back(self, _event=None) -> None:
        if not self._history:
            return
        if self._history_idx == -1:
            self._history_idx = len(self._history) - 1
        else:
            self._history_idx = max(0, self._history_idx - 1)
        self._var.set(self._history[self._history_idx])
        self._entry.icursor(tk.END)

    def _history_forward(self, _event=None) -> None:
        if self._history_idx == -1:
            return
        self._history_idx += 1
        if self._history_idx >= len(self._history):
            self._history_idx = -1
            self._var.set("")
        else:
            self._var.set(self._history[self._history_idx])
        self._entry.icursor(tk.END)

    def focus(self) -> None:
        self._entry.focus_set()

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self._entry.configure(state=state)


# ---------------------------------------------------------------------------
# TempleAIPanel
# ---------------------------------------------------------------------------

class TempleAIPanel(tk.Frame):
    """
    Displays Temple AI atmospheric observations.
    Shows: "The Temple watches..." and evolving judgements.
    """

    def __init__(
        self,
        parent: tk.Widget,
        theme: ThemeManager,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=theme.colors.panel, **kwargs)
        self._theme = theme
        self._build()

    def _build(self) -> None:
        t = self._theme

        header = tk.Label(
            self,
            text="◈  TEMPLE CONSCIOUSNESS",
            fg=t.colors.ai_temple,
            bg=t.colors.panel,
            font=t.font_small(),
            anchor="w",
            padx=8,
            pady=4,
        )
        header.pack(fill="x")

        sep = tk.Frame(self, bg=t.colors.border, height=1)
        sep.pack(fill="x", padx=4)

        self._text = tk.Text(
            self,
            bg=t.colors.panel,
            fg=t.colors.ai_temple,
            font=t.font_small(),
            wrap=tk.WORD,
            state="disabled",
            relief="flat",
            bd=0,
            height=4,
            padx=8,
            pady=6,
        )
        self._text.pack(fill="both", expand=True)

    def set_message(self, message: str) -> None:
        """Display a new Temple AI message."""
        self._text.configure(state="normal")
        self._text.delete("1.0", tk.END)
        self._text.insert(tk.END, message)
        self._text.configure(state="disabled")

    def clear(self) -> None:
        self.set_message("The temple watches in silence...")


# ---------------------------------------------------------------------------
# ExplorerAIPanel
# ---------------------------------------------------------------------------

class ExplorerAIPanel(tk.Frame):
    """
    Displays Explorer AI recommendations and lore answers.
    """

    def __init__(
        self,
        parent: tk.Widget,
        theme: ThemeManager,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=theme.colors.panel, **kwargs)
        self._theme = theme
        self._build()

    def _build(self) -> None:
        t = self._theme

        header = tk.Label(
            self,
            text="◉  EXPLORER GUIDE",
            fg=t.colors.ai_explorer,
            bg=t.colors.panel,
            font=t.font_small(),
            anchor="w",
            padx=8,
            pady=4,
        )
        header.pack(fill="x")

        sep = tk.Frame(self, bg=t.colors.border, height=1)
        sep.pack(fill="x", padx=4)

        self._text = tk.Text(
            self,
            bg=t.colors.panel,
            fg=t.colors.ai_explorer,
            font=t.font_small(),
            wrap=tk.WORD,
            state="disabled",
            relief="flat",
            bd=0,
            height=4,
            padx=8,
            pady=6,
        )
        self._text.pack(fill="both", expand=True)

    def set_message(self, message: str) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", tk.END)
        self._text.insert(tk.END, message)
        self._text.configure(state="disabled")

    def clear(self) -> None:
        self.set_message("")
