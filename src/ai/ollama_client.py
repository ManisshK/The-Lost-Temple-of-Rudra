"""
ollama_client.py — The Lost Temple of Rudra

Concrete provider for a locally running Ollama instance.
Sends formatted prompts over HTTP and returns ProviderResponse objects.

If Ollama is unavailable the provider returns a failure response without
raising — the AI layer falls back to rule-based responses gracefully.

Configuration is loaded from config/ai_settings.json at construction time.
All fields (host, model, timeout, temperature, max_tokens) are configurable.
No values are hardcoded.

Blueprint Reference: Chapter 15 — Software Architecture
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

from .provider import BaseProvider, ProviderResponse


# ---------------------------------------------------------------------------
# Default config path
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "ai_settings.json")
)


def _load_ollama_config(config_path: str) -> dict:
    """Load the Ollama section from ai_settings.json, falling back to defaults."""
    defaults = {
        "host": "http://localhost:11434",
        "model": "qwen",
        "timeout_seconds": 30,
        "temperature": 0.7,
        "max_tokens": 512,
        "enabled": False,
    }
    try:
        with open(config_path, encoding="utf-8") as fh:
            data = json.load(fh)
        ollama = data.get("ollama", {})
        defaults.update({k: v for k, v in ollama.items() if k in defaults})
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return defaults


# ---------------------------------------------------------------------------
# OllamaProvider
# ---------------------------------------------------------------------------

class OllamaProvider(BaseProvider):
    """
    Sends prompts to a locally running Ollama instance via its HTTP API.

    Uses the /api/generate endpoint with stream=false.
    Falls back gracefully when Ollama is unavailable.
    """

    def __init__(self, config_path: str = _DEFAULT_CONFIG) -> None:
        cfg = _load_ollama_config(config_path)
        self._host: str = cfg["host"].rstrip("/")
        self._model: str = cfg["model"]
        self._timeout: int = int(cfg["timeout_seconds"])
        self._temperature: float = float(cfg["temperature"])
        self._max_tokens: int = int(cfg["max_tokens"])
        self._enabled: bool = bool(cfg["enabled"])

    # ------------------------------------------------------------------
    # BaseProvider interface
    # ------------------------------------------------------------------

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """
        Perform a lightweight health check against the Ollama host.
        Returns False immediately if the provider is disabled in config.
        """
        if not self._enabled:
            return False
        try:
            import urllib.request
            url = f"{self._host}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def send_prompt(self, prompt: str, system: str = "") -> ProviderResponse:
        """
        Send prompt to Ollama /api/generate (stream=false).
        Returns ProviderResponse with success=False if unavailable.
        """
        if not self._enabled:
            return ProviderResponse(
                success=False,
                error="Ollama provider is disabled in configuration.",
                model=self._model,
            )

        try:
            import urllib.request
            import urllib.error

            payload: dict = {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self._temperature,
                    "num_predict": self._max_tokens,
                },
            }
            if system:
                payload["system"] = system

            body = json.dumps(payload).encode("utf-8")
            url = f"{self._host}/api/generate"
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={"Content-Type": "application/json"},
            )

            t0 = time.monotonic()
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                latency_ms = int((time.monotonic() - t0) * 1000)
                raw = resp.read().decode("utf-8")

            data = json.loads(raw)
            text = data.get("response", "").strip()
            return ProviderResponse(
                text=text,
                success=bool(text),
                model=self._model,
                latency_ms=latency_ms,
            )

        except Exception as exc:  # noqa: BLE001
            return ProviderResponse(
                success=False,
                error=str(exc),
                model=self._model,
            )
