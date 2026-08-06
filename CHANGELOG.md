# CHANGELOG — The Lost Temple of Rudra

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.1.0] — Phase 7 (UI Framework + Release Foundation)

### Added
- **Main Window** — Full tkinter GUI: narrative panel, command input, sidebar panels.
- **Theme Manager** — Dark temple colour scheme loaded from `config/graphics.json`.
- **Animation Engine** — TypewriterEffect, FadeEffect, FlickerEffect, SmoothScrollEffect.
- **Audio Engine** — Feature-flagged pygame audio (ambience, SFX, music). Silently disabled when pygame absent.
- **NarrativePanel** — Scrollable typewriter narration with skip-on-click.
- **CommandInput** — Command entry with history navigation (↑/↓).
- **TempleAIPanel** — Displays Temple AI atmospheric observations.
- **ExplorerAIPanel** — Displays Explorer AI recommendations.
- **InventoryPanel** — Item list with torch fuel bar.
- **ObjectivesPanel** — Current mission + completed objectives.
- **JournalPanel** — Discovered lore, symbols, and resolved puzzles.
- **StatusPanel** — Turn, phase, torch, flood, stability status bar.
- **EvaluationPanel** — Guardian evaluation score bars.
- **MapPanel** — Mini-map with fog of war and room grid.
- **TitleScreen** — Opening title with New Game / Continue / Load / Settings / Quit.
- **PauseMenu** — In-game pause overlay (F11 = fullscreen, Esc = pause).
- **SaveLoadDialog** — 5-slot save/load interface.
- **SettingsDialog** — Text speed, fullscreen, AI model display.
- **LoadingScreen** — Animated loading overlay.
- **ExitConfirmDialog** — Exit confirmation prompt.
- **SaveManager** — Save/load World Model to `data/saves/slot_N.json`. Autosave every 10 turns.
- **StateManager** — Macro game-state machine (LOADING → TITLE → PLAYING → JUDGMENT → ENDING).
- Keyboard shortcuts: F5 quick-save, F9 quick-load, F11 fullscreen, Esc pause.
- GUI entry point in `src/main.py` (`--cli` flag for terminal fallback).

---

## [0.0.6] — Phase 6 (Temple AI + Explorer AI)

### Added
- **TempleAI** — Observes player behaviour across 10 evaluation attributes. Generates atmospheric narration. Computes final worthiness judgment.
- **ExplorerAI** — Rule-based recommendation pipeline. History recall. Room analysis. Lore Q&A.
- **AIManager** — Central dispatch for all AI requests. 11 request types. Never raises.
- **AIMemory** — Session-scoped persistent memory shared by both AIs.
- **ContextBuilder** — Sanitised read-only context snapshots (no puzzle solutions, no hidden passages).
- **PromptManager** — 10 prompt templates for LLM integration.
- **BaseProvider / OllamaProvider** — Configurable LLM provider abstraction. Disabled by default.
- **Game Engine wiring** — `hint`, `recommend`, `think`, `analyze`, `status` commands live.
- **CLI AI commands** — `hint`, `recommend`, `ask <question>`, `summary`, `think`.

---

## [0.0.5] — Phase 5 (Puzzle System + Dynamic Event Engine)

### Added
- Guardian Statues puzzle (Hall of Guardians)
- Flood Control puzzle
- Bridge Integrity puzzle
- Dynamic Event Engine: torch decay, flood progression, bridge decay, statue reset, dust accumulation, hidden passage activation, temple collapse
- Puzzle registry and validator pattern

---

## [0.0.4] — Phase 4 (Room System + Object System + Inventory)

### Added
- 24 canonically-defined rooms with descriptions and connections
- 40+ object definitions (collectibles, story objects, puzzle objects, interactive objects)
- TAKE / DROP / USE / INVENTORY / LIGHT / EXTINGUISH commands
- Temple loader — full world initialisation from definitions

---

## [0.0.3] — Phase 3 (Command Parser + Game Engine)

### Added
- Natural language command parser with 150+ verb synonyms
- Game Engine execution pipeline
- Dynamic event post-processing
- Turn manager and phase transitions

---

## [0.0.2] — Phase 2 (Persistent World Model)

### Added
- 11-section World Model dataclass hierarchy
- Full JSON serialisation / deserialisation
- World Model validation
- Guardian evaluation system (10 attributes)

---

## [0.0.1] — Phase 1 (Foundation)

### Added
- Project structure, Python package layout
- Configuration files
- pytest suite baseline
