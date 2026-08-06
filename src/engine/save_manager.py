"""
save_manager.py — The Lost Temple of Rudra

Saves and loads game state by serialising / deserialising the World Model.

Save format: JSON files in data/saves/
  slot_0.json … slot_4.json   (manual + autosave slots)
  Each file is the complete WorldModel.to_json() output plus a metadata header.

Slot 0 is reserved for autosave.

Blueprint Reference: Chapter 10.7 — Save & Load Architecture
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.world.world_model import WorldModel

_SAVE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "saves")
)
_NUM_SLOTS = 5
_AUTOSAVE_INTERVAL = 10   # turns between autosaves


def _slot_path(slot: int) -> str:
    return os.path.join(_SAVE_DIR, f"slot_{slot}.json")


def _ensure_dir() -> None:
    os.makedirs(_SAVE_DIR, exist_ok=True)


class SaveManager:
    """
    Static save/load interface.  All methods are classmethods.

    Usage::

        SaveManager.save(world_model, slot=1, label="Turn 42")
        wm = SaveManager.load(slot=1)
        saves = SaveManager.list_saves()
    """

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    @classmethod
    def save(
        cls,
        world_model: "WorldModel",
        slot: int = 0,
        label: Optional[str] = None,
    ) -> str:
        """
        Serialise world_model and write to slot.

        Returns the path written.
        Raises OSError on disk failure.
        """
        _ensure_dir()
        path = _slot_path(slot)

        wm_dict = world_model.to_dict()
        turn = world_model.world.current_turn
        ts = time.strftime("%Y-%m-%d %H:%M")
        slot_label = label or f"Turn {turn}  —  {ts}"

        envelope = {
            "_save_meta": {
                "slot": slot,
                "label": slot_label,
                "turn": turn,
                "saved_at": ts,
                "version": "0.1.0",
            },
            "world_model": wm_dict,
        }

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(envelope, fh, indent=2, ensure_ascii=False)

        return path

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, slot: int = 0) -> Optional["WorldModel"]:
        """
        Load and deserialise the World Model from a slot.

        Returns None if the slot is empty or the file is corrupt.
        """
        from src.world.world_model import WorldModel

        path = _slot_path(slot)
        if not os.path.isfile(path):
            return None

        try:
            with open(path, encoding="utf-8") as fh:
                envelope = json.load(fh)

            wm_dict = envelope.get("world_model") or envelope
            return WorldModel.from_dict(wm_dict)

        except Exception:
            return None

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    @classmethod
    def list_saves(cls) -> list[dict]:
        """
        Return a list of slot metadata dicts for occupied slots.
        Each dict has keys: slot, label, turn, saved_at.
        Slots are returned newest-first.
        """
        results = []
        for slot in range(_NUM_SLOTS):
            path = _slot_path(slot)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8") as fh:
                    envelope = json.load(fh)
                meta = envelope.get("_save_meta", {})
                results.append({
                    "slot": slot,
                    "label": meta.get("label", f"Slot {slot}"),
                    "turn": meta.get("turn", 0),
                    "saved_at": meta.get("saved_at", ""),
                })
            except Exception:
                continue
        results.sort(key=lambda d: d.get("turn", 0), reverse=True)
        return results

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    @classmethod
    def delete(cls, slot: int) -> bool:
        """Remove a save slot file. Returns True if deleted."""
        path = _slot_path(slot)
        if os.path.isfile(path):
            os.remove(path)
            return True
        return False

    # ------------------------------------------------------------------
    # Autosave helper
    # ------------------------------------------------------------------

    @classmethod
    def maybe_autosave(
        cls,
        world_model: "WorldModel",
        autosave_interval: int = _AUTOSAVE_INTERVAL,
    ) -> bool:
        """
        Save to slot 0 if the current turn is a multiple of autosave_interval.
        Returns True if an autosave was written.
        """
        turn = world_model.world.current_turn
        if turn > 0 and turn % autosave_interval == 0:
            try:
                cls.save(world_model, slot=0, label=f"Autosave — Turn {turn}")
                return True
            except Exception:
                pass
        return False
