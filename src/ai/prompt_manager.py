"""
prompt_manager.py — The Lost Temple of Rudra

Manages all ten prompt templates used by the Temple AI and Explorer AI.
Loads templates, injects World Model context, and returns formatted prompts
ready to be sent to the LLM via OllamaClient.

Templates:
    1.  Explorer AI action recommendation
    2.  Temple AI consequence narration
    3.  World Model interpreter (human-readable state summary)
    4.  Dynamic event generator narration
    5.  Hint generator (redirect attention, never reveal answer)
    6.  Lore narrator (atmospheric room descriptions)
    7.  Judgment AI (final evaluation narrative)
    8.  Explorer reflection (discovery summary)
    9.  Mission generator (current objective)
    10. AI recommendation display

TODO: Implement all ten prompt builder methods.
TODO: Enforce constraints: no invented rooms, no future spoilers, no hallucination.
TODO: Inject sanitised World Model context from ContextBuilder into each prompt.
"""
