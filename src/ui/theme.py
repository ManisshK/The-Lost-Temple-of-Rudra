"""
theme.py — The Lost Temple of Rudra

Dark temple theme manager.
Loads colours, fonts, and spacing from config/graphics.json.
Provides a single ThemeManager instance that all UI components reference.

Rules:
  - Never writes to the World Model.
  - Falls back gracefully when config is missing or fonts are unavailable.
  - All colour values are valid tkinter colour strings (#rrggbb).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

_DEFAULT_CONFIG = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "graphics.json")
)

# ---------------------------------------------------------------------------
# Default theme — applied when config is absent
# ---------------------------------------------------------------------------
_DEFAULTS = {
    "window": {
        "title": "The Lost Temple of Rudra",
        "width": 1280,
        "height": 800,
        "resizable": True,
        "fullscreen": False,
    },
    "fonts": {
        "primary": "",
        "secondary": "",
        "size_normal": 13,
        "size_large": 18,
        "size_title": 32,
    },
    "theme": {
        "background_color": "#0a0a0a",
        "text_color": "#d4b896",
        "accent_color": "#8b4513",
        "panel_color": "#1a1208",
        "border_color": "#5c3d1e",
        "hint_color": "#7a9e7e",
        "warning_color": "#c0392b",
        "success_color": "#7fb069",
        "dim_color": "#6b5a45",
        "highlight_color": "#e8c98a",
        "ai_temple_color": "#9b59b6",
        "ai_explorer_color": "#2980b9",
        "cursor_color": "#d4b896",
        "input_bg": "#120e06",
        "scrollbar_color": "#3d2b14",
    },
    "panels": {
        "narrative_width_percent": 60,
        "sidebar_width_percent": 40,
    },
}


@dataclass
class WindowConfig:
    title: str = "The Lost Temple of Rudra"
    width: int = 1280
    height: int = 800
    resizable: bool = True
    fullscreen: bool = False


@dataclass
class FontConfig:
    family_primary: str = "Consolas"
    family_secondary: str = "Georgia"
    size_normal: int = 13
    size_large: int = 18
    size_title: int = 32


@dataclass
class ThemeColors:
    background: str = "#0a0a0a"
    text: str = "#d4b896"
    accent: str = "#8b4513"
    panel: str = "#1a1208"
    border: str = "#5c3d1e"
    hint: str = "#7a9e7e"
    warning: str = "#c0392b"
    success: str = "#7fb069"
    dim: str = "#6b5a45"
    highlight: str = "#e8c98a"
    ai_temple: str = "#9b59b6"
    ai_explorer: str = "#2980b9"
    cursor: str = "#d4b896"
    input_bg: str = "#120e06"
    scrollbar: str = "#3d2b14"


class ThemeManager:
    """
    Singleton-style theme manager.
    Load once at startup; all panels read from it.
    """

    def __init__(self, config_path: str = _DEFAULT_CONFIG) -> None:
        data = self._load(config_path)
        w = data.get("window", _DEFAULTS["window"])
        f = data.get("fonts", _DEFAULTS["fonts"])
        t = data.get("theme", _DEFAULTS["theme"])
        p = data.get("panels", _DEFAULTS["panels"])

        self.window = WindowConfig(
            title=w.get("title", _DEFAULTS["window"]["title"]),
            width=int(w.get("width", 1280)),
            height=int(w.get("height", 800)),
            resizable=bool(w.get("resizable", True)),
            fullscreen=bool(w.get("fullscreen", False)),
        )

        # Resolve font family — fall back to Consolas / Georgia (always available on Windows)
        self.fonts = FontConfig(
            family_primary=self._resolve_font(f.get("primary", "")),
            family_secondary=self._resolve_font(f.get("secondary", ""), secondary=True),
            size_normal=int(f.get("size_normal", 13)),
            size_large=int(f.get("size_large", 18)),
            size_title=int(f.get("size_title", 32)),
        )

        self.colors = ThemeColors(
            background=t.get("background_color", "#0a0a0a"),
            text=t.get("text_color", "#d4b896"),
            accent=t.get("accent_color", "#8b4513"),
            panel=t.get("panel_color", "#1a1208"),
            border=t.get("border_color", "#5c3d1e"),
            hint=t.get("hint_color", "#7a9e7e"),
            warning=t.get("warning_color", "#c0392b"),
            success=t.get("success_color", "#7fb069"),
            dim=t.get("dim_color", "#6b5a45"),
            highlight=t.get("highlight_color", "#e8c98a"),
            ai_temple=t.get("ai_temple_color", "#9b59b6"),
            ai_explorer=t.get("ai_explorer_color", "#2980b9"),
            cursor=t.get("cursor_color", "#d4b896"),
            input_bg=t.get("input_bg", "#120e06"),
            scrollbar=t.get("scrollbar_color", "#3d2b14"),
        )

        self.narrative_width_pct: float = float(
            p.get("narrative_width_percent", 60)
        ) / 100.0
        self.sidebar_width_pct: float = float(
            p.get("sidebar_width_percent", 40)
        ) / 100.0

    # ------------------------------------------------------------------

    @staticmethod
    def _load(path: str) -> dict:
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    @staticmethod
    def _resolve_font(path_or_name: str, secondary: bool = False) -> str:
        """Return a usable tkinter font family name."""
        if not path_or_name:
            return "Georgia" if secondary else "Consolas"
        # If it's a .ttf path, extract stem as a hint (tkinter uses family names)
        if path_or_name.endswith(".ttf"):
            stem = os.path.splitext(os.path.basename(path_or_name))[0]
            return stem if stem else ("Georgia" if secondary else "Consolas")
        return path_or_name

    def font_normal(self) -> tuple:
        return (self.fonts.family_primary, self.fonts.size_normal)

    def font_large(self) -> tuple:
        return (self.fonts.family_secondary, self.fonts.size_large)

    def font_title(self) -> tuple:
        return (self.fonts.family_secondary, self.fonts.size_title, "bold")

    def font_mono(self) -> tuple:
        return (self.fonts.family_primary, self.fonts.size_normal)

    def font_small(self) -> tuple:
        return (self.fonts.family_primary, max(10, self.fonts.size_normal - 2))
