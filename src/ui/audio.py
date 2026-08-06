"""
audio.py — The Lost Temple of Rudra

Audio engine. Feature-flagged — silently disabled when pygame is absent.

Sound categories:
  - Ambience: looping background atmosphere per room/phase
  - SFX: one-shot interaction sounds (pickup, door, puzzle, footstep)
  - Music: adaptive background tracks (exploration, tension, judgment, ending)

All sounds are loaded from assets/audio/.
File references come from the audio manifest (config/audio_manifest.json)
or fall back to safe defaults when files are missing.

Rules:
  - Never write to the World Model.
  - Graceful no-op when pygame.mixer is unavailable.
  - Volume levels are configurable (0.0 – 1.0).
"""

from __future__ import annotations

import json
import os
from typing import Optional

# ---------------------------------------------------------------------------
# Pygame availability guard
# ---------------------------------------------------------------------------
try:
    import pygame
    _PYGAME_AVAILABLE = True
except ImportError:
    _PYGAME_AVAILABLE = False

_AUDIO_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "audio")
)
_MANIFEST_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "audio_manifest.json")
)


def _load_manifest() -> dict:
    try:
        with open(_MANIFEST_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# AudioEngine
# ---------------------------------------------------------------------------

class AudioEngine:
    """
    Manages background music, ambience, and sound effects.

    Silently disabled (all methods are no-ops) when pygame is unavailable
    or when audio initialisation fails.
    """

    def __init__(
        self,
        sfx_volume: float = 0.7,
        music_volume: float = 0.4,
        ambience_volume: float = 0.3,
        enabled: bool = True,
    ) -> None:
        self._enabled = enabled and _PYGAME_AVAILABLE
        self._sfx_vol = max(0.0, min(1.0, sfx_volume))
        self._music_vol = max(0.0, min(1.0, music_volume))
        self._ambience_vol = max(0.0, min(1.0, ambience_volume))
        self._manifest: dict = _load_manifest()
        self._sfx_cache: dict[str, object] = {}
        self._current_music: Optional[str] = None
        self._current_ambience: Optional[str] = None

        if self._enabled:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                pygame.mixer.set_num_channels(16)
            except Exception:
                self._enabled = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        return self._enabled

    def play_sfx(self, sound_id: str) -> None:
        """Play a one-shot sound effect by ID (e.g. 'pickup', 'door_unlock')."""
        if not self._enabled:
            return
        sound = self._get_sfx(sound_id)
        if sound:
            try:
                sound.set_volume(self._sfx_vol)
                sound.play()
            except Exception:
                pass

    def play_music(self, track_id: str, loop: bool = True) -> None:
        """Start a background music track by ID (e.g. 'exploration', 'tension')."""
        if not self._enabled or track_id == self._current_music:
            return
        path = self._resolve("music", track_id)
        if not path:
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self._music_vol)
            pygame.mixer.music.play(-1 if loop else 0)
            self._current_music = track_id
        except Exception:
            pass

    def play_ambience(self, ambience_id: str) -> None:
        """Start a looping ambience track (e.g. 'temple', 'water', 'wind')."""
        if not self._enabled or ambience_id == self._current_ambience:
            return
        path = self._resolve("ambience", ambience_id)
        if not path:
            return
        try:
            # Use channel 0 for ambience
            ch = pygame.mixer.Channel(0)
            sound = pygame.mixer.Sound(path)
            sound.set_volume(self._ambience_vol)
            ch.play(sound, loops=-1)
            self._current_ambience = ambience_id
        except Exception:
            pass

    def stop_music(self, fade_ms: int = 1000) -> None:
        if not self._enabled:
            return
        try:
            pygame.mixer.music.fadeout(fade_ms)
            self._current_music = None
        except Exception:
            pass

    def stop_ambience(self) -> None:
        if not self._enabled:
            return
        try:
            pygame.mixer.Channel(0).stop()
            self._current_ambience = None
        except Exception:
            pass

    def set_sfx_volume(self, v: float) -> None:
        self._sfx_vol = max(0.0, min(1.0, v))

    def set_music_volume(self, v: float) -> None:
        self._music_vol = max(0.0, min(1.0, v))
        if self._enabled:
            try:
                pygame.mixer.music.set_volume(self._music_vol)
            except Exception:
                pass

    def set_ambience_volume(self, v: float) -> None:
        self._ambience_vol = max(0.0, min(1.0, v))

    def shutdown(self) -> None:
        if self._enabled:
            try:
                pygame.mixer.quit()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, category: str, sound_id: str) -> Optional[str]:
        """Return the filesystem path for a sound ID, or None."""
        manifest_path = (
            self._manifest
            .get(category, {})
            .get(sound_id, "")
        )
        if manifest_path:
            full = os.path.join(_AUDIO_DIR, manifest_path)
            if os.path.isfile(full):
                return full
        # Auto-discover: try common extensions
        for ext in (".ogg", ".wav", ".mp3"):
            candidate = os.path.join(_AUDIO_DIR, category, f"{sound_id}{ext}")
            if os.path.isfile(candidate):
                return candidate
        return None

    def _get_sfx(self, sound_id: str):
        if sound_id in self._sfx_cache:
            return self._sfx_cache[sound_id]
        path = self._resolve("sfx", sound_id)
        if not path:
            return None
        try:
            sound = pygame.mixer.Sound(path)
            self._sfx_cache[sound_id] = sound
            return sound
        except Exception:
            return None
