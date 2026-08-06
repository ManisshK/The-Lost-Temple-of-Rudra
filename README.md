# THE LOST TEMPLE OF RUDRA

An AI-powered text adventure demonstrating a Persistent World Model through a dynamic, living environment.

---

## Overview

The Lost Temple of Rudra is a modern text adventure inspired by classic interactive fiction such as Zork,
combined with an AI-driven world model and a cinematic interface.

The player explores an ancient temple searching for the legendary Eye of Rudra.
Unknown to them, the temple itself is continuously evaluating whether they are worthy
of becoming the next Guardian Consciousness.

The Eye of Rudra is not a treasure. It is a responsibility.

---

## Current Development Phase

**Phase 1 — Project Scaffold**
Project structure created. Module stubs in place. No gameplay logic implemented.

---

## Planned Architecture

```
Player Input
    ↓
Command Parser
    ↓
Game Engine  ←── sole writer to World Model
    ↓
World Model  ←── single source of truth
    ↓
Dynamic Event Engine
    ↓
Temple AI (read-only)   Explorer AI (read-only)
    ↓                         ↓
Narration              Recommendation
    ↓
UI Output
```

---

## Folder Structure

```
/
├── assets/         Audio, fonts, images, icons, animations, videos
├── config/         Game, AI, and graphics configuration
├── data/           Room, puzzle, object, lore, event, and save data
├── docs/           Architecture, API, and development documentation
├── src/
│   ├── ai/         Temple AI, Explorer AI, prompts, Ollama client
│   ├── engine/     Game engine, parser, turn manager, save manager
│   ├── world/      World model, rooms, objects, puzzles, events, evaluation
│   ├── ui/         Main window, menus, inventory, journal, dialogue
│   └── utils/      Logger and constants
├── tests/          Test suite
├── BLUEPRINT/      Master Blueprint documents (all phases)
├── requirements.txt
└── README.md
```

---

## Technologies

- Python 3.11+
- Ollama (local LLM — Qwen model) for AI reasoning
- UI framework TBD (pygame / tkinter / customtkinter)
- JSON for configuration and World Model persistence

---

## Installation

_Installation instructions will be added once dependencies are finalised._

---

## License

_License to be determined._
