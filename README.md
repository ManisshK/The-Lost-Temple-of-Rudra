# THE LOST TEMPLE OF RUDRA

An AI-powered text adventure with a persistent world model, adaptive Temple AI,
and a full graphical interface built on tkinter.

---

## Overview

The player explores an ancient temple searching for the legendary Eye of Rudra.
Unknown to them, the temple itself evaluates whether they are worthy of becoming
the next Guardian Consciousness — silently, across ten behavioural attributes.

**The Eye of Rudra is not a treasure. It is a responsibility.**

---

## Quick Start

```bash
# GUI mode (default)
python -m src.main

# CLI / terminal mode
python -m src.main --cli
```

Requirements: Python 3.11+. No external dependencies for core gameplay.  
Optional: `pygame>=2.5` for audio. `pyinstaller>=6.0` to build an executable.

---

## Project Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Foundation — project structure, config, stubs | ✅ Complete |
| 2 | Persistent World Model — 11-section dataclass hierarchy, serialisation, validation | ✅ Complete |
| 3 | Command Parser + Game Engine — 150+ verb synonyms, full execution pipeline | ✅ Complete |
| 4 | Room System + Object System + Inventory | ✅ Complete |
| 4.5 | CLI Entry Point | ✅ Complete |
| 5 | Puzzle System + Dynamic Event Engine | ✅ Complete |
| 6 | Temple AI + Explorer AI + AI Manager + Ollama provider | ✅ Complete |
| 7 | UI Framework — tkinter GUI, animations, save/load, state machine, packaging | ✅ Complete |

**Test suite: 936 tests, 0 failing.**

---

## Architecture

```
Player Input ──► CommandParser ──► GameEngine ──► WorldModel (write)
                                        │
                                        ├──► DynamicEventEngine (events.py)
                                        ├──► AIManager ──► TempleAI (read-only)
                                        │               └──► ExplorerAI (read-only)
                                        └──► UI (read-only refresh)
```

The **World Model** is the single source of truth.
Only the **Game Engine** writes to it.
All other systems — AI, UI, Save Manager — read through defined interfaces.

---

## Project Structure

```
src/
  world/          Persistent World Model (11 sections)
  engine/         Game Engine, Parser, Turn Manager, Save Manager, State Manager
  ai/             Temple AI, Explorer AI, AI Manager, Memory, Prompts, Ollama provider
  ui/             Main Window, Panels, Animations, Audio, Menu, Theme
  utils/          Constants, Logger
  main.py         Entry point (GUI + CLI)

tests/            936 tests across all phases
config/           graphics.json, ai_settings.json, game_settings.json, audio_manifest.json
assets/           images/, audio/, fonts/, icons/, animations/
data/saves/       Save slot files (slot_0.json … slot_4.json)
docs/             Architecture.md, API.md, Development_Log.md
```

---

## Features

### World Model
- 11-section persistent state: rooms, objects, inventory, puzzles, story, evaluation, events, history
- Full JSON serialisation / deserialisation
- World Model validation with integrity checks

### Game Engine
- Natural language parser with 150+ verb synonyms
- Full command pipeline: parse → validate → execute → events → AI → return
- 24 canonical rooms, 40+ objects, 6 puzzle types

### Puzzle System
- Guardian Statues (logic), Flood Control (environmental), Bridge Integrity
- Every puzzle remembers attempts, hints used, time to solve, observation before action

### Dynamic Event Engine
- Torch decay with flood modifier
- Flood progression through 5 stages
- Bridge integrity decay and collapse
- Dust accumulation, statue auto-reset, temple collapse warning
- Hidden passage activation

### Temple AI
- Observes every player action
- Tracks 10 Guardian evaluation attributes silently
- Generates atmospheric narration (rule-based + optional Ollama LLM)
- Computes final worthiness judgment: WORTHY / NEARLY WORTHY / UNWORTHY
- Redirect hints that never reveal puzzle solutions

### Explorer AI
- Rule-based recommendation pipeline (6 priority levels)
- History recall and journey reflection
- Room analysis and lore Q&A
- Optional LLM overlay via Ollama

### Graphical UI
- Dark temple theme loaded from `config/graphics.json`
- Typewriter narration with skip-on-click
- Inventory panel with torch fuel bar
- Mini-map with fog of war
- Guardian evaluation score bars
- Temple AI and Explorer AI panels
- Save/load dialog (5 slots), autosave every 10 turns
- Fullscreen (F11), pause menu (Esc), quick-save (F5), quick-load (F9)
- Settings: text speed, fullscreen, AI model display

### Audio (optional — requires pygame)
- Ambient loops: temple, water, wind, machinery
- SFX: pickup, puzzle solved, door unlock, stone move, footstep, torch
- Music: exploration, tension, judgment, ending, title

---

## Configuration

| File | Purpose |
|------|---------|
| `config/graphics.json` | Window size, theme colours, fonts, panel ratios |
| `config/ai_settings.json` | Ollama host/model, enable/disable AI |
| `config/game_settings.json` | Torch burn rate, autosave interval, debug mode |
| `config/audio_manifest.json` | Maps sound IDs to asset file paths |

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## Building a Windows Executable

```bash
pip install pyinstaller
pyinstaller temple.spec
```

The executable lands in `dist/TheLostTempleOfRudra.exe`.

---

## Enabling the LLM (optional)

1. Install [Ollama](https://ollama.ai) locally.
2. Pull a model: `ollama pull qwen`
3. Edit `config/ai_settings.json`:
   ```json
   { "ollama": { "enabled": true, "model": "qwen" } }
   ```
4. Restart the game. The AI panels will use LLM responses instead of rule-based fallbacks.

---

## License

MIT — see [LICENSE](LICENSE).
