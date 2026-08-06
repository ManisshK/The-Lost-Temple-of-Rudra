"""
animations.py — The Lost Temple of Rudra

Pure-tkinter animation primitives.
All animations are scheduled via widget.after() — no threads, no blocking.

Animations:
  TypewriterEffect  — reveals text character by character
  FadeEffect        — fades a widget's foreground colour in/out
  FlickerEffect     — simulates torch flicker on a canvas item
  ScrollEffect      — smooth-scrolls a Text widget to a position

Rules:
  - Never write to the World Model.
  - All animations are cancellable (cancel() method).
  - Animations are fire-and-forget; caller gets an object to cancel early.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# TypewriterEffect
# ---------------------------------------------------------------------------

class TypewriterEffect:
    """
    Reveals text in a tk.Text widget character by character.

    Usage:
        tw = TypewriterEffect(text_widget, "Hello, temple.", speed_ms=30)
        tw.start()
        # Cancel early:
        tw.cancel()
    """

    def __init__(
        self,
        widget: tk.Text,
        text: str,
        speed_ms: int = 25,
        tag: str = "default",
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        self._widget = widget
        self._text = text
        self._speed = speed_ms
        self._tag = tag
        self._on_complete = on_complete
        self._index = 0
        self._job: Optional[str] = None
        self._cancelled = False

    def start(self) -> None:
        """Begin the typewriter animation."""
        self._cancelled = False
        self._index = 0
        self._tick()

    def cancel(self) -> None:
        """Stop animation and insert remaining text immediately."""
        self._cancelled = True
        if self._job:
            try:
                self._widget.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        # Flush remaining text
        remaining = self._text[self._index:]
        if remaining:
            try:
                self._widget.configure(state="normal")
                self._widget.insert(tk.END, remaining, self._tag)
                self._widget.configure(state="disabled")
                self._widget.see(tk.END)
            except Exception:
                pass
        if self._on_complete:
            self._on_complete()

    def _tick(self) -> None:
        if self._cancelled:
            return
        if self._index >= len(self._text):
            if self._on_complete:
                self._on_complete()
            return
        chunk = self._text[self._index]
        self._index += 1
        try:
            self._widget.configure(state="normal")
            self._widget.insert(tk.END, chunk, self._tag)
            self._widget.configure(state="disabled")
            self._widget.see(tk.END)
        except Exception:
            return
        self._job = self._widget.after(self._speed, self._tick)


# ---------------------------------------------------------------------------
# FadeEffect
# ---------------------------------------------------------------------------

_HEX_PAIRS = [(i * 2, i * 2 + 2) for i in range(3)]


def _lerp_color(c1: str, c2: str, t: float) -> str:
    """Linear interpolation between two #rrggbb colours."""
    def _parse(c: str) -> tuple[int, int, int]:
        c = c.lstrip("#")
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        return r, g, b

    r1, g1, b1 = _parse(c1)
    r2, g2, b2 = _parse(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


class FadeEffect:
    """
    Fades a tk.Text tag foreground colour from dim to bright (fade-in)
    or bright to dim (fade-out).
    """

    def __init__(
        self,
        widget: tk.Text,
        tag: str,
        start_color: str,
        end_color: str,
        duration_ms: int = 500,
        steps: int = 20,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        self._widget = widget
        self._tag = tag
        self._start = start_color
        self._end = end_color
        self._duration = duration_ms
        self._steps = steps
        self._on_complete = on_complete
        self._step = 0
        self._job: Optional[str] = None

    def start(self) -> None:
        self._step = 0
        self._tick()

    def cancel(self) -> None:
        if self._job:
            try:
                self._widget.after_cancel(self._job)
            except Exception:
                pass
        self._job = None

    def _tick(self) -> None:
        if self._step > self._steps:
            try:
                self._widget.tag_configure(self._tag, foreground=self._end)
            except Exception:
                pass
            if self._on_complete:
                self._on_complete()
            return
        t = self._step / self._steps
        color = _lerp_color(self._start, self._end, t)
        try:
            self._widget.tag_configure(self._tag, foreground=color)
        except Exception:
            return
        self._step += 1
        interval = self._duration // self._steps
        self._job = self._widget.after(interval, self._tick)


# ---------------------------------------------------------------------------
# FlickerEffect
# ---------------------------------------------------------------------------

class FlickerEffect:
    """
    Simulates torch flicker by rapidly cycling a Canvas item's fill colour.
    """

    _FLICKER_COLORS = [
        "#e8920a", "#f0a020", "#c87000", "#f5b030",
        "#d4800a", "#ffb040", "#cc6a00", "#f0a820",
    ]

    def __init__(
        self,
        canvas: tk.Canvas,
        item_id: int,
        interval_ms: int = 80,
    ) -> None:
        self._canvas = canvas
        self._item = item_id
        self._interval = interval_ms
        self._running = False
        self._job: Optional[str] = None
        self._idx = 0

    def start(self) -> None:
        self._running = True
        self._tick()

    def stop(self) -> None:
        self._running = False
        if self._job:
            try:
                self._canvas.after_cancel(self._job)
            except Exception:
                pass
        self._job = None

    def _tick(self) -> None:
        if not self._running:
            return
        color = self._FLICKER_COLORS[self._idx % len(self._FLICKER_COLORS)]
        self._idx += 1
        try:
            self._canvas.itemconfig(self._item, fill=color)
        except Exception:
            return
        # Vary interval slightly for organic feel
        jitter = (self._idx * 37) % 40 - 20
        self._job = self._canvas.after(
            max(30, self._interval + jitter), self._tick
        )


# ---------------------------------------------------------------------------
# SmoothScrollEffect
# ---------------------------------------------------------------------------

class SmoothScrollEffect:
    """
    Smoothly scrolls a tk.Text widget to a target position.
    """

    def __init__(
        self,
        widget: tk.Text,
        target: float = 1.0,
        steps: int = 10,
        interval_ms: int = 16,
    ) -> None:
        self._widget = widget
        self._target = target
        self._steps = steps
        self._interval = interval_ms
        self._step = 0
        self._job: Optional[str] = None

    def start(self) -> None:
        self._step = 0
        self._tick()

    def cancel(self) -> None:
        if self._job:
            try:
                self._widget.after_cancel(self._job)
            except Exception:
                pass

    def _tick(self) -> None:
        if self._step >= self._steps:
            try:
                self._widget.yview_moveto(self._target)
            except Exception:
                pass
            return
        t = (self._step + 1) / self._steps
        pos = self._target * t
        try:
            self._widget.yview_moveto(pos)
        except Exception:
            return
        self._step += 1
        self._job = self._widget.after(self._interval, self._tick)
