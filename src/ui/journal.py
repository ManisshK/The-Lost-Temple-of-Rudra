"""
journal.py — The Lost Temple of Rudra

Journal, objectives, and status panels.
Reads from World Model — never writes.

Panels:
  ObjectivesPanel  — current mission + completed objectives
  JournalPanel     — discovered lore, symbols, puzzle history
  StatusPanel      — temple phase, flood, stability, torch, turn
  EvaluationPanel  — silent evaluation scores (display-only)
  MapPanel         — mini-map with fog of war (room grid)
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from .theme import ThemeManager

if TYPE_CHECKING:
    from src.world.world_model import WorldModel


# ---------------------------------------------------------------------------
# ObjectivesPanel
# ---------------------------------------------------------------------------

class ObjectivesPanel(tk.Frame):
    """Current mission objective and completed objectives."""

    def __init__(self, parent: tk.Widget, theme: ThemeManager, **kwargs) -> None:
        super().__init__(parent, bg=theme.colors.panel, **kwargs)
        self._theme = theme
        self._build()

    def _build(self) -> None:
        t = self._theme
        tk.Label(
            self, text="◎  OBJECTIVES",
            fg=t.colors.highlight, bg=t.colors.panel,
            font=t.font_small(), anchor="w", padx=8, pady=4,
        ).pack(fill="x")
        tk.Frame(self, bg=t.colors.border, height=1).pack(fill="x", padx=4)

        self._primary = tk.Label(
            self, text="", fg=t.colors.text, bg=t.colors.panel,
            font=t.font_small(), anchor="w", padx=8, pady=2, wraplength=300,
        )
        self._primary.pack(fill="x")

        self._completed_frame = tk.Frame(self, bg=t.colors.panel)
        self._completed_frame.pack(fill="x", padx=4)

    def refresh(self, world_model: "WorldModel") -> None:
        self._primary.configure(
            text=world_model.mission.current_goal_description or "Explore the temple."
        )
        for w in self._completed_frame.winfo_children():
            w.destroy()
        t = self._theme
        for obj_id in world_model.mission.completed_objectives[-5:]:
            tk.Label(
                self._completed_frame,
                text=f"✓ {obj_id.replace('_', ' ')}",
                fg=t.colors.success, bg=t.colors.panel,
                font=t.font_small(), anchor="w", padx=12,
            ).pack(fill="x")


# ---------------------------------------------------------------------------
# JournalPanel
# ---------------------------------------------------------------------------

class JournalPanel(tk.Frame):
    """Discovered lore entries, symbols, and puzzle notes."""

    def __init__(self, parent: tk.Widget, theme: ThemeManager, **kwargs) -> None:
        super().__init__(parent, bg=theme.colors.panel, **kwargs)
        self._theme = theme
        self._build()

    def _build(self) -> None:
        t = self._theme
        tk.Label(
            self, text="✦  JOURNAL",
            fg=t.colors.highlight, bg=t.colors.panel,
            font=t.font_small(), anchor="w", padx=8, pady=4,
        ).pack(fill="x")
        tk.Frame(self, bg=t.colors.border, height=1).pack(fill="x", padx=4)

        self._text = tk.Text(
            self, bg=t.colors.panel, fg=t.colors.text,
            font=t.font_small(), wrap=tk.WORD, state="disabled",
            relief="flat", bd=0, height=6, padx=8, pady=4,
        )
        self._text.pack(fill="both", expand=True)

    def refresh(self, world_model: "WorldModel") -> None:
        t = self._theme
        self._text.configure(state="normal")
        self._text.delete("1.0", tk.END)

        lore = world_model.story.lore_ids_discovered
        symbols = world_model.story.symbols_encountered
        solved = [pid for pid, ps in world_model.puzzles.items()
                  if ps.status.value == "solved"]

        if lore:
            self._text.insert(tk.END, "Lore discovered:\n", "header")
            for lid in lore[-5:]:
                self._text.insert(tk.END, f"  • {lid.replace('_', ' ')}\n")

        if symbols:
            self._text.insert(tk.END, "\nSymbols known:\n", "header")
            self._text.insert(tk.END, f"  {', '.join(str(s) for s in symbols)}\n")

        if solved:
            self._text.insert(tk.END, "\nMechanisms resolved:\n", "header")
            for pid in solved:
                self._text.insert(tk.END, f"  ✓ {pid.replace('puzzle_', '').replace('_', ' ')}\n")

        if not lore and not symbols and not solved:
            self._text.insert(tk.END, "(nothing recorded yet)")

        self._text.tag_configure(
            "header", foreground=t.colors.accent,
            font=(t.fonts.family_primary, t.fonts.size_normal, "bold"),
        )
        self._text.configure(state="disabled")


# ---------------------------------------------------------------------------
# StatusPanel
# ---------------------------------------------------------------------------

class StatusPanel(tk.Frame):
    """
    Temple phase, turn, flood, stability, torch state.
    Compact single-row status bar.
    """

    def __init__(self, parent: tk.Widget, theme: ThemeManager, **kwargs) -> None:
        super().__init__(parent, bg=theme.colors.background, **kwargs)
        self._theme = theme
        self._labels: dict[str, tk.Label] = {}
        self._build()

    def _build(self) -> None:
        t = self._theme
        fields = [
            ("turn", "Turn 0"),
            ("phase", "Discovery"),
            ("torch", "Torch: unlit"),
            ("flood", "Flood: dry"),
            ("stability", "Stability: 100%"),
        ]
        for i, (key, default) in enumerate(fields):
            lbl = tk.Label(
                self, text=default,
                fg=t.colors.dim, bg=t.colors.background,
                font=t.font_small(), padx=8,
            )
            lbl.grid(row=0, column=i, sticky="w")
            self._labels[key] = lbl

            if i < len(fields) - 1:
                tk.Label(
                    self, text="│",
                    fg=t.colors.border, bg=t.colors.background,
                    font=t.font_small(),
                ).grid(row=0, column=i * 2 + 1)

    def refresh(self, world_model: "WorldModel") -> None:
        t = self._theme
        turn = world_model.world.current_turn
        phase = world_model.world.temple_phase.name.replace("_", " ").title()
        torch = world_model.player.torch.state
        fuel = world_model.player.torch.fuel
        flood = world_model.world.flood_level.name.replace("_", " ").title()
        stability = int(world_model.world.world_stability)

        torch_color = t.colors.text
        if fuel < 30:
            torch_color = t.colors.warning
        elif fuel < 60:
            torch_color = "#e8920a"

        flood_color = t.colors.dim
        if flood.lower() not in ("dry", "none"):
            flood_color = t.colors.warning

        self._labels["turn"].configure(text=f"Turn {turn}", fg=t.colors.dim)
        self._labels["phase"].configure(text=phase, fg=t.colors.accent)
        self._labels["torch"].configure(
            text=f"Torch: {torch} ({fuel}%)", fg=torch_color
        )
        self._labels["flood"].configure(
            text=f"Flood: {flood}", fg=flood_color
        )
        self._labels["stability"].configure(
            text=f"Stability: {stability}%",
            fg=t.colors.warning if stability < 50 else t.colors.dim,
        )


# ---------------------------------------------------------------------------
# EvaluationPanel
# ---------------------------------------------------------------------------

class EvaluationPanel(tk.Frame):
    """
    Displays the Temple's evaluation of the explorer (read-only).
    Shows attribute scores as compact bars.
    The player is aware scores exist but never sees the judgment thresholds.
    """

    _POSITIVE = [
        ("observation", "Obs"),
        ("curiosity", "Cur"),
        ("wisdom", "Wis"),
        ("patience", "Pat"),
        ("adaptation", "Ada"),
    ]
    _NEGATIVE = [
        ("greed", "Grd"),
        ("recklessness", "Rck"),
    ]

    def __init__(self, parent: tk.Widget, theme: ThemeManager, **kwargs) -> None:
        super().__init__(parent, bg=theme.colors.panel, **kwargs)
        self._theme = theme
        self._bars: dict[str, tk.Canvas] = {}
        self._build()

    def _build(self) -> None:
        t = self._theme
        tk.Label(
            self, text="◈  TEMPLE EVALUATION",
            fg=t.colors.ai_temple, bg=t.colors.panel,
            font=t.font_small(), anchor="w", padx=8, pady=4,
        ).pack(fill="x")
        tk.Frame(self, bg=t.colors.border, height=1).pack(fill="x", padx=4)

        grid = tk.Frame(self, bg=t.colors.panel)
        grid.pack(fill="x", padx=8, pady=4)

        for i, (attr, short) in enumerate(self._POSITIVE + self._NEGATIVE):
            row, col = divmod(i, 2)
            frame = tk.Frame(grid, bg=t.colors.panel)
            frame.grid(row=row, column=col, padx=4, pady=1, sticky="ew")

            is_neg = attr in ("greed", "recklessness")
            bar_color = t.colors.warning if is_neg else t.colors.success

            tk.Label(
                frame, text=f"{short}:",
                fg=t.colors.dim, bg=t.colors.panel, font=t.font_small(), width=4,
            ).pack(side="left")

            canvas = tk.Canvas(
                frame, width=60, height=8,
                bg=t.colors.background, highlightthickness=0,
            )
            canvas.pack(side="left", padx=2)
            self._bars[attr] = canvas

        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

    def refresh(self, world_model: "WorldModel") -> None:
        t = self._theme
        eval_ = world_model.evaluation
        for attr, _ in self._POSITIVE + self._NEGATIVE:
            canvas = self._bars.get(attr)
            if not canvas:
                continue
            score = getattr(eval_, attr).score
            fill_w = int(60 * min(100, max(0, score)) / 100)
            is_neg = attr in ("greed", "recklessness")
            color = t.colors.warning if is_neg else t.colors.success
            if not is_neg and score < 30:
                color = t.colors.dim
            canvas.delete("all")
            canvas.create_rectangle(0, 0, fill_w, 8, fill=color, outline="")


# ---------------------------------------------------------------------------
# MapPanel
# ---------------------------------------------------------------------------

class MapPanel(tk.Frame):
    """
    Mini-map with fog of war.
    Shows a grid of known rooms, current position, and connections.
    Rooms the player hasn't visited are hidden (fog of war).
    """

    # Room layout grid positions (col, row) — manually positioned
    _ROOM_GRID: dict[str, tuple[int, int]] = {
        "temple_entrance": (3, 6),
        "hall_of_echoes": (3, 5),
        "hall_of_guardians": (3, 4),
        "chamber_of_inscriptions": (3, 3),
        "first_meditation_hall": (2, 3),
        "ancient_library": (4, 3),
        "archive_vault": (4, 2),
        "symbol_gallery": (2, 2),
        "astronomers_chamber": (3, 2),
        "statue_gallery": (5, 3),
        "chamber_of_maps": (1, 3),
        "forgotten_classroom": (1, 2),
        "bridge_of_echoes": (3, 7),
        "flood_control_room": (2, 7),
        "underground_reservoir": (1, 7),
        "water_channel_network": (2, 8),
        "collapsed_hallway": (4, 7),
        "ancient_machinery_chamber": (4, 8),
        "hidden_maintenance_tunnel": (3, 8),
        "chamber_of_reflection": (2, 9),
        "hall_of_judgment": (3, 1),
        "guardian_archive": (4, 1),
        "throne_approach": (3, 0),
        "final_chamber": (3, -1),
    }

    _CELL = 18   # pixels per cell
    _PADDING = 8

    def __init__(self, parent: tk.Widget, theme: ThemeManager, **kwargs) -> None:
        super().__init__(parent, bg=theme.colors.panel, **kwargs)
        self._theme = theme
        self._build()

    def _build(self) -> None:
        t = self._theme
        tk.Label(
            self, text="⊕  MAP",
            fg=t.colors.highlight, bg=t.colors.panel,
            font=t.font_small(), anchor="w", padx=8, pady=4,
        ).pack(fill="x")
        tk.Frame(self, bg=t.colors.border, height=1).pack(fill="x", padx=4)

        # Calculate canvas size
        all_pos = list(self._ROOM_GRID.values())
        max_col = max(c for c, r in all_pos)
        max_row = max(r for c, r in all_pos)
        min_row = min(r for c, r in all_pos)
        self._row_offset = -min_row

        w = (max_col + 1) * self._CELL + self._PADDING * 2
        h = (max_row - min_row + 1) * self._CELL + self._PADDING * 2

        self._canvas = tk.Canvas(
            self, width=min(w, 200), height=min(h, 180),
            bg=t.colors.background, highlightthickness=0,
        )
        self._canvas.pack(padx=4, pady=4)

    def refresh(self, world_model: "WorldModel") -> None:
        t = self._theme
        self._canvas.delete("all")
        visited = set(world_model.player.visited_rooms)
        current = world_model.player.current_room
        c = self._CELL
        pad = self._PADDING

        for room_id, (col, row) in self._ROOM_GRID.items():
            x = col * c + pad
            y = (row + self._row_offset) * c + pad

            if room_id not in visited:
                # Fog of war
                self._canvas.create_rectangle(
                    x, y, x + c - 2, y + c - 2,
                    fill=t.colors.background, outline=t.colors.border, width=1,
                )
                continue

            # Visited room
            fill = t.colors.accent if room_id == current else t.colors.panel
            outline = t.colors.highlight if room_id == current else t.colors.dim

            self._canvas.create_rectangle(
                x, y, x + c - 2, y + c - 2,
                fill=fill, outline=outline, width=1,
            )

            if room_id == current:
                # Player marker
                cx, cy = x + c // 2 - 1, y + c // 2 - 1
                self._canvas.create_oval(
                    cx - 3, cy - 3, cx + 3, cy + 3,
                    fill=t.colors.highlight, outline="",
                )
