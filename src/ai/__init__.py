"""
ai/__init__.py — The Lost Temple of Rudra

AI subsystem package.

Exports:
    AIManager       — Central coordinator (primary interface for Game Engine)
    AIRequest       — Request type for AI Manager dispatch
    AIResponse      — Response type from AI Manager
    TempleAI        — Guardian consciousness (Temple AI)
    TempleObservation — Observation result from Temple AI
    ExplorerAI      — Player advisor (Explorer AI)
    Recommendation  — Recommendation result from Explorer AI
    AIMemory        — Persistent session memory
    MemoryEntry     — Single memory record
    BaseProvider    — Abstract provider interface
    OllamaProvider  — Ollama HTTP provider
    ProviderResponse — Typed provider response
"""

from .ai_manager import AIManager, AIRequest, AIResponse
from .temple_ai import TempleAI, TempleObservation
from .explorer_ai import ExplorerAI, Recommendation
from .ai_memory import AIMemory, MemoryEntry
from .provider import BaseProvider, ProviderResponse
from .ollama_client import OllamaProvider

__all__ = [
    "AIManager",
    "AIRequest",
    "AIResponse",
    "TempleAI",
    "TempleObservation",
    "ExplorerAI",
    "Recommendation",
    "AIMemory",
    "MemoryEntry",
    "BaseProvider",
    "ProviderResponse",
    "OllamaProvider",
]
