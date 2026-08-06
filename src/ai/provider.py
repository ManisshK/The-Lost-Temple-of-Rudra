"""
provider.py — The Lost Temple of Rudra

Abstract base class for AI model providers.
Defines the contract that every provider must satisfy.

Providers:
    OllamaProvider  — Local Ollama instance (see ollama_client.py)
    MockProvider    — Deterministic stub used during tests

All concrete providers must inherit from BaseProvider and implement
send_prompt() and is_available(). The rest of the AI stack never
imports a concrete provider directly — it always works through
this interface.

Blueprint Reference: Chapter 15 — Software Architecture
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Provider response
# ---------------------------------------------------------------------------

@dataclass
class ProviderResponse:
    """
    Typed wrapper returned by every provider call.

    Fields:
        text        — The model's response text, or "" on failure.
        success     — True when the provider returned a usable response.
        error       — Human-readable error string when success is False.
        model       — Name of the model that produced the response.
        latency_ms  — Round-trip time in milliseconds (0 when unavailable).
    """
    text: str = ""
    success: bool = False
    error: str = ""
    model: str = ""
    latency_ms: int = 0


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseProvider(ABC):
    """
    Abstract AI model provider.

    Implementors must provide send_prompt() and is_available().
    All exceptions must be caught internally — callers receive a
    ProviderResponse with success=False rather than a raised exception.
    """

    @abstractmethod
    def send_prompt(self, prompt: str, system: str = "") -> ProviderResponse:
        """
        Send a prompt to the model and return the response.

        Args:
            prompt  — The user-facing prompt text.
            system  — Optional system instruction prepended to the request.

        Returns:
            ProviderResponse — always returned, never raises.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """
        Returns True when the provider is ready to accept requests.
        Fast check — must not block for more than ~1 second.
        """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The name of the underlying model (e.g. 'qwen', 'llama3')."""
