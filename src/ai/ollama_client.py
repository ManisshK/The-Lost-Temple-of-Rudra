"""
ollama_client.py — The Lost Temple of Rudra

HTTP client for communicating with a locally running Ollama instance.
Sends formatted prompts to the configured LLM model (Qwen) and returns responses.

If Ollama is unavailable, returns None so AI systems can fall back gracefully
to rule-based responses without crashing the game.

TODO: Implement send_prompt(prompt: str) -> str | None
TODO: Implement is_available() -> bool (health check against Ollama host)
TODO: Load host, model, temperature, max_tokens from config/ai_settings.json
TODO: Implement configurable timeout and basic retry logic.
TODO: Handle all connection and HTTP errors without raising to the game layer.
"""
