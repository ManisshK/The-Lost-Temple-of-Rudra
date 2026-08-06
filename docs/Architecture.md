# Architecture — The Lost Temple of Rudra

## Core Rule

The World Model is the single source of truth.
Only the Game Engine may write to it.
All other systems access it in read-only mode through defined interfaces.

## System Layers

| Layer   | Modules                                               |
|---------|-------------------------------------------------------|
| World   | world_model, rooms, objects, puzzles, events, evaluation |
| Engine  | game_engine, command_parser, turn_manager, state_manager, save_manager |
| AI      | temple_ai, explorer_ai, prompt_manager, context_builder, ollama_client |
| UI      | main_window, menu, inventory, journal, dialogue       |
| Utils   | logger, constants                                     |

## Data Flow

```
Player Input → Parser → Game Engine → World Model (write)
                                    → Dynamic Event Engine
                                    → Temple AI (read-only) → Narration
                                    → Explorer AI (read-only) → Recommendation
                                    → UI Output
```

## Module Responsibilities

_Expanded in each implementation phase._
