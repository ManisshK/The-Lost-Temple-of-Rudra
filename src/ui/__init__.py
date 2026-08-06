"""
ui/__init__.py — The Lost Temple of Rudra

UI subsystem package.  Presentation layer only.

Exports:
    MainWindow         — Root application window
    ThemeManager       — Dark-temple colour / font config
    NarrativePanel     — Typewriter narration display
    CommandInput       — Player command entry field
    TempleAIPanel      — Temple AI atmospheric observations
    ExplorerAIPanel    — Explorer AI recommendations
    InventoryPanel     — Player inventory display
    ObjectivesPanel    — Mission objectives display
    JournalPanel       — Lore / symbol / puzzle notes
    StatusPanel        — Compact status bar
    EvaluationPanel    — Guardian evaluation score bars
    MapPanel           — Mini-map with fog of war
    TitleScreen        — Opening title screen
    PauseMenu          — In-game pause overlay
    SaveLoadDialog     — Save / load slot selector
    SettingsDialog     — Settings panel
    LoadingScreen      — Loading overlay
    AudioEngine        — Audio engine (pygame, feature-flagged)
    TypewriterEffect   — Character-by-character text animation
    FadeEffect         — Colour fade animation
    FlickerEffect      — Torch flicker canvas animation

Rules:
    - UI components NEVER write to the World Model.
    - All commands route through GameEngine.process_input().
    - All AI requests route through AIManager.handle().
"""

from .theme import ThemeManager
from .animations import TypewriterEffect, FadeEffect, FlickerEffect, SmoothScrollEffect
from .audio import AudioEngine
from .dialogue import NarrativePanel, CommandInput, TempleAIPanel, ExplorerAIPanel
from .inventory import InventoryPanel
from .journal import ObjectivesPanel, JournalPanel, StatusPanel, EvaluationPanel, MapPanel
from .menu import (
    TitleScreen, PauseMenu, SaveLoadDialog,
    SettingsDialog, ExitConfirmDialog, LoadingScreen,
)
from .main_window import MainWindow

__all__ = [
    "MainWindow",
    "ThemeManager",
    "NarrativePanel",
    "CommandInput",
    "TempleAIPanel",
    "ExplorerAIPanel",
    "InventoryPanel",
    "ObjectivesPanel",
    "JournalPanel",
    "StatusPanel",
    "EvaluationPanel",
    "MapPanel",
    "TitleScreen",
    "PauseMenu",
    "SaveLoadDialog",
    "SettingsDialog",
    "ExitConfirmDialog",
    "LoadingScreen",
    "AudioEngine",
    "TypewriterEffect",
    "FadeEffect",
    "FlickerEffect",
    "SmoothScrollEffect",
]
