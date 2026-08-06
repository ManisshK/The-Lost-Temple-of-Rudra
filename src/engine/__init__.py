"""
engine/__init__.py — The Lost Temple of Rudra

Game engine package.
Contains the core execution pipeline: game engine, command parser,
turn manager, state manager, and save manager.

The Game Engine is the ONLY system permitted to write to the World Model.
"""

from .save_manager import SaveManager
from .state_manager import StateManager, GameState

__all__ = ["SaveManager", "StateManager", "GameState"]
