"""
inventory.py — The Lost Temple of Rudra

Inventory panel UI component.
Reads from World Model — never writes.
Refreshes when the calling code calls refresh().
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from .theme import ThemeManager

if TYPE_CHECKING:
    from src.world.world_model import WorldModel


class InventoryPanel(tk.Frame):
    """
    Displays the player's current inventory.
    Each item shows name, condition, and state.
    Torch shows a fuel bar.
    """

    def __init__(
        self,
        parent: tk.Widget,
        theme: ThemeManager,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=theme.colors.panel, **kwargs)
        self._theme = theme
        self._item_frames: list[tk.Frame] = []
        self._build()

    def _build(self) -> None:
        t = self._theme

        header = tk.Label(
            self,
            text="⊞  INVENTORY",
            fg=t.colors.highlight,
            bg=t.colors.panel,
            font=t.font_small(),
            anchor="w",
            padx=8,
            pady=4,
        )
        header.pack(fill="x")

        tk.Frame(self, bg=t.colors.border, height=1).pack(fill="x", padx=4)

        self._container = tk.Frame(self, bg=t.colors.panel)
        self._container.pack(fill="both", expand=True, padx=4, pady=4)

        self._empty_label = tk.Label(
            self._container,
            text="(empty)",
            fg=t.colors.dim,
            bg=t.colors.panel,
            font=t.font_small(),
        )
        self._empty_label.pack(pady=4)

    def refresh(self, world_model: "WorldModel") -> None:
        """Rebuild the inventory display from the current World Model state."""
        # Clear existing items
        for f in self._item_frames:
            f.destroy()
        self._item_frames.clear()

        t = self._theme
        items = world_model.player.inventory

        if not items:
            self._empty_label.pack(pady=4)
            return

        self._empty_label.pack_forget()

        for oid in items:
            obj = world_model.objects.get(oid)
            if obj is None:
                continue

            frame = tk.Frame(
                self._container,
                bg=t.colors.panel,
                pady=2,
            )
            frame.pack(fill="x", padx=4)
            self._item_frames.append(frame)

            # Item name
            name_color = t.colors.text
            if obj.state in ("lit", "active"):
                name_color = t.colors.success
            elif obj.state in ("extinguished", "broken", "used"):
                name_color = t.colors.dim

            tk.Label(
                frame,
                text=f"• {obj.name}",
                fg=name_color,
                bg=t.colors.panel,
                font=t.font_small(),
                anchor="w",
            ).pack(fill="x")

            # State / condition line
            state_text = self._describe_item(oid, obj, world_model)
            if state_text:
                tk.Label(
                    frame,
                    text=f"  {state_text}",
                    fg=t.colors.dim,
                    bg=t.colors.panel,
                    font=t.font_small(),
                    anchor="w",
                ).pack(fill="x")

            # Torch fuel bar
            if "torch" in oid.lower() or "torch" in obj.name.lower():
                self._add_fuel_bar(
                    frame, world_model.player.torch.fuel, t
                )

    def _describe_item(self, oid: str, obj, wm: "WorldModel") -> str:
        parts = []
        if obj.state and obj.state not in ("normal", "default", ""):
            parts.append(obj.state.replace("_", " "))
        if obj.condition < 30:
            parts.append("damaged")
        elif obj.condition < 70:
            parts.append("worn")
        return ", ".join(parts)

    def _add_fuel_bar(
        self, parent: tk.Frame, fuel: int, t: ThemeManager
    ) -> None:
        bar_frame = tk.Frame(parent, bg=t.colors.panel)
        bar_frame.pack(fill="x", padx=4, pady=1)

        tk.Label(
            bar_frame, text="fuel:", fg=t.colors.dim,
            bg=t.colors.panel, font=t.font_small(),
        ).pack(side="left")

        canvas = tk.Canvas(
            bar_frame,
            width=80, height=8,
            bg=t.colors.background,
            highlightthickness=0,
        )
        canvas.pack(side="left", padx=4)

        fill_w = int(80 * max(0, min(100, fuel)) / 100)
        color = t.colors.success
        if fuel < 30:
            color = t.colors.warning
        elif fuel < 60:
            color = "#e8920a"

        canvas.create_rectangle(0, 0, fill_w, 8, fill=color, outline="")

        tk.Label(
            bar_frame, text=f"{fuel}%", fg=t.colors.dim,
            bg=t.colors.panel, font=t.font_small(),
        ).pack(side="left")
