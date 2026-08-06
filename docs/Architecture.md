# Architecture — The Lost Temple of Rudra

## Core Rule

The World Model is the single source of truth.
Only the Game Engine may write to it.
All other systems access it in read-only mode through defined interfaces.

## System Layers

| Layer   | Modules                                                                           |
|---------|-----------------------------------------------------------------------------------|
| World   | world_model, rooms, objects, puzzles, events, evaluation                          |
| Engine  | game_engine, command_parser, turn_manager, state_manager, save_manager            |
| AI      | ai_manager, temple_ai, explorer_ai, prompt_manager, context_builder, ai_memory, provider, ollama_client |
| UI      | main_window, menu, inventory, journal, dialogue                                   |
| Utils   | logger, constants                                                                 |

## Data Flow

```
Player Input → Parser → Game Engine → World Model (write)
                                    → Dynamic Event Engine
                                    → AI Manager → Temple AI (read-only) → TempleObservation
                                                 → Explorer AI (read-only) → Recommendation
                                    → UI Output
```

## AI Layer (Phase 6)

### Access Rule
The AI layer is **strictly read-only** with respect to the World Model.

- `ContextBuilder` reads the World Model and returns plain dicts (never live references).
- `TempleAI` and `ExplorerAI` receive only these sanitised dicts.
- `AIManager.handle()` returns `AIResponse` carrying eval deltas.
- The **Game Engine** applies those deltas via `wm._update_evaluation()` — the only write path.

### Component Responsibilities

| Component | Responsibility |
|---|---|
| `AIManager` | Single dispatch point between Game Engine and AI subsystems. Never raises. |
| `TempleAI` | Observes player behaviour, tracks patterns, generates atmospheric narration, computes final judgment. |
| `ExplorerAI` | Rule-based recommendation pipeline, history recall, room analysis, lore Q&A. |
| `AIMemory` | Session-scoped, append-only memory store shared by both AIs. |
| `ContextBuilder` | Builds sanitised read-only context dicts. Filters puzzle solutions, hidden passages, judgment thresholds. |
| `PromptManager` | 10 prompt templates (system + user). Never invents content beyond provided context. |
| `BaseProvider` | Abstract provider interface (`send_prompt`, `is_available`, `model_name`). |
| `OllamaProvider` | HTTP client for local Ollama instance. Config-driven, no hardcoded values, disabled by default. |

### AI Request Types

| Request Type | Handler | Description |
|---|---|---|
| `observe_action` | TempleAI | After every player turn — returns eval deltas |
| `hint` | TempleAI | Redirect hint for current puzzle (never reveals solution) |
| `recommend` | ExplorerAI | Single best next-action suggestion |
| `analyze` | ExplorerAI | Room analysis |
| `reflect` | ExplorerAI | Journey discovery summary |
| `narrate_event` | TempleAI | Atmospheric narration for dynamic events |
| `puzzle_solved` | TempleAI | Eval deltas on puzzle completion |
| `lore_discovered` | TempleAI | Eval deltas on lore discovery |
| `judgment` | TempleAI | Final worthiness judgment narrative |
| `ask` | ExplorerAI | Lore question (based only on discovered content) |
| `mission` | ExplorerAI | Current mission objective summary |

### Provider Fallback Chain

```
LLM available? → send_prompt() → ProviderResponse.success?
    Yes → use LLM response
    No  → rule-based fallback (always available, never raises)
```

## Module Responsibilities

### World Layer
- `world_model.py` — Aggregates all 11 state sections. Single write interface.
- `rooms.py` / `room_state.py` — Room definitions and runtime state.
- `objects.py` / `object_state.py` — Object definitions and runtime state.
- `puzzles.py` / `puzzle_state.py` — Puzzle validators, definitions, runtime state.
- `events.py` / `event_state.py` — Dynamic event evaluators and state.
- `evaluation_state.py` — Ten Guardian evaluation attributes (silent accumulation).
- `serializer.py` — JSON serialisation / deserialisation.
- `validator.py` — World Model integrity checks.
- `temple_loader.py` — Initialises the full World Model at game start.

### Engine Layer
- `game_engine.py` — Central authority. Only system that writes to World Model.
- `command_parser.py` — Parses raw input to `Command` objects.
- `command_registry.py` — Verb synonym map.
- `turn_manager.py` — Turn counter and phase transitions.
- `command_result.py` — `GameResult` type returned after every command.

### AI Layer
- See AI Layer section above.

### Utils Layer
- `constants.py` — All magic strings, room IDs, evaluation keys, delta values.
- `logger.py` — Logging utilities.
