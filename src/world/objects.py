"""
objects.py — The Lost Temple of Rudra

Defines every object in the temple and the factory that populates the World Model.

Object categories (Blueprint Chapter 7.3):
    COLLECTIBLE   — Can enter the player's inventory (torch, key, scroll…)
    INTERACTIVE   — Stays in room, changes state  (lever, door, flood gate…)
    STORY         — Communicates lore; read-only  (inscription, mural, tablet…)
    ENVIRONMENTAL — Participates in simulation    (bridge, rubble, water…)
    PUZZLE        — Required for puzzle logic     (statue, orrery, relief…)
    SYMBOLIC      — Reinforces philosophy         (mirror, plaque, seat…)
    GUARDIAN      — Final chamber only; never collectible

Blueprint Reference:
    Chapter 7  — Object System
    Chapter 10 — Section 10.4.4 — Object State
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .object_state import ObjectState, ObjectCategory, StatueDirection


# ---------------------------------------------------------------------------
# ObjectDefinition — static blueprint (never stored in World Model)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ObjectDefinition:
    """
    Immutable description of an object's static properties.

    The dynamic runtime state (location, condition, state string, usage
    history…) lives in ObjectState inside the World Model.
    """
    object_id: str
    name: str
    category: ObjectCategory
    room_id: Optional[str]              # Starting room (None = starts in inventory)
    description: str
    initial_state: str = ""
    initial_condition: float = 100.0
    visible: bool = True
    discoverable: bool = True
    interactable: bool = True
    collectible: bool = False            # True only for COLLECTIBLE category objects
    puzzle_id: Optional[str] = None
    story_importance: str = ""
    facing_direction: Optional[StatueDirection] = None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

OBJECT_DEFINITIONS: dict[str, ObjectDefinition] = {}


def _obj(
    object_id: str,
    name: str,
    category: ObjectCategory,
    room_id: Optional[str],
    description: str,
    state: str = "",
    condition: float = 100.0,
    visible: bool = True,
    discoverable: bool = True,
    interactable: bool = True,
    collectible: bool = False,
    puzzle_id: Optional[str] = None,
    story_importance: str = "",
    facing: Optional[StatueDirection] = None,
) -> ObjectDefinition:
    od = ObjectDefinition(
        object_id=object_id,
        name=name,
        category=category,
        room_id=room_id,
        description=description,
        initial_state=state,
        initial_condition=condition,
        visible=visible,
        discoverable=discoverable,
        interactable=interactable,
        collectible=collectible,
        puzzle_id=puzzle_id,
        story_importance=story_importance,
        facing_direction=facing,
    )
    OBJECT_DEFINITIONS[object_id] = od
    return od


# ── Collectible objects ───────────────────────────────────────────────────────

_obj("torch_entrance", "Ancient Torch", ObjectCategory.COLLECTIBLE,
     "temple_entrance",
     "A wall-mounted torch bracket holds a torch that, remarkably, still seems "
     "usable. The fuel is old but dry. If you had a way to light it, it would "
     "provide light for a while.",
     state="unlit", collectible=True,
     story_importance="Primary light source — critical for dark regions.")

_obj("key_archive", "Archive Key", ObjectCategory.COLLECTIBLE,
     "archive_vault",
     "A heavy iron key, surface mottled with age but the mechanism still sound. "
     "A small tag attached to it reads: 'Lower Vault'. "
     "It might open something in the deeper levels of the temple.",
     state="unused", collectible=True,
     story_importance="Opens a locked chamber in the lower temple.")

_obj("ancient_key_reservoir", "Reservoir Key", ObjectCategory.COLLECTIBLE,
     "underground_reservoir",
     "A corroded bronze key half-buried in silt near the water's edge. "
     "It is etched with a river symbol.",
     state="unused", collectible=True,
     story_importance="Opens the sealed passage in the Water Channel Network.")

_obj("ancient_key_collapsed", "Collapsed Passage Key", ObjectCategory.COLLECTIBLE,
     "collapsed_hallway",
     "A flat iron key wedged into a crack in the rubble. "
     "The teeth look like they match a lock you haven't found yet.",
     state="unused", collectible=True,
     story_importance="May unlock something in the Guardian Core.")

_obj("tool_wrench", "Stone Wrench", ObjectCategory.COLLECTIBLE,
     "water_channel_network",
     "A heavy wrench carved from a single piece of dark stone. "
     "It fits the bolt pattern on the channel sluice gates.",
     state="clean", collectible=True,
     story_importance="Required for operating the flood control mechanisms.")

_obj("tool_chisel", "Iron Chisel", ObjectCategory.COLLECTIBLE,
     "hidden_maintenance_tunnel",
     "A small iron chisel, its edge still sharp despite centuries of disuse. "
     "Someone left it here mid-task.",
     state="clean", collectible=True,
     story_importance="Can be used to clear inscriptions obscured by sediment.")

# ── Story objects (read-only lore carriers) ──────────────────────────────────

_obj("inscription_entrance", "Entrance Inscription", ObjectCategory.STORY,
     "temple_entrance",
     "Carved above the inner lintel in deep, sure strokes: "
     "'The temple does not remember your name. It remembers your choices.' "
     "Below that, in smaller script: 'Enter in curiosity. Leave in understanding.'",
     state="unread",
     story_importance="The temple's first and most important lore reveal.")

_obj("scroll_hall_of_echoes", "Echoing Scroll", ObjectCategory.STORY,
     "hall_of_echoes",
     (
         "A partially unrolled scroll, the clay hardened in place. "
         "The visible text reads: 'In the age before memory, the builders asked: "
         "what outlasts stone? They concluded: only choices.'"
     ),
     state="undiscovered", story_importance="Chapter 1 lore entry.")

_obj("tablet_inscriptions_01", "Stone Tablet I", ObjectCategory.STORY,
     "chamber_of_inscriptions",
     "The first of two large tablets leaning against the eastern wall. "
     "The text describes the founding of the temple and its true purpose: "
     "not to house a god, but to evaluate those who would understand one.",
     state="undiscovered", story_importance="Chapter 2 lore entry.")

_obj("tablet_inscriptions_02", "Stone Tablet II", ObjectCategory.STORY,
     "chamber_of_inscriptions",
     "The second tablet continues the narrative. It describes the Guardian — "
     "not as a creature but as a principle. 'The Guardian does not judge. "
     "The Guardian reflects.'",
     state="undiscovered", story_importance="Chapter 3 lore entry.")

_obj("mural_meditation_01", "Meditation Mural", ObjectCategory.STORY,
     "first_meditation_hall",
     "A painted mural, faded but legible, showing a figure seated in the "
     "meditation hall — this very room — surrounded by the five symbols. "
     "The figure's eyes are open but looking inward.",
     state="undiscovered", story_importance="Teaches the significance of the five symbols.")

_obj("scroll_ancient_library_01", "Library Scroll I", ObjectCategory.STORY,
     "ancient_library",
     "A fragile scroll detailing the original purpose of the Knowledge Sanctum: "
     "a repository for everything the builders had learned, preserved for "
     "whoever came after. 'We did not build this for ourselves.'",
     state="undiscovered", story_importance="Chapter 4 lore.")

_obj("scroll_ancient_library_02", "Library Scroll II", ObjectCategory.STORY,
     "ancient_library",
     "A second scroll, this one technical — a partial index of the library's "
     "original contents. Most of the listed items are missing.",
     state="undiscovered", story_importance="Provides hints about what scrolls exist elsewhere.")

_obj("tablet_library_index", "Library Index Tablet", ObjectCategory.STORY,
     "ancient_library",
     "A clay tablet that served as the library's catalogue. "
     "Cross-referencing it with found scrolls might reveal what knowledge "
     "the builders considered most essential.",
     state="undiscovered", story_importance="Meta-document: reveals the structure of the lore.")

_obj("scroll_vault_01", "Archive Vault Scroll", ObjectCategory.STORY,
     "archive_vault",
     "The best-preserved document in the temple — sealed in a protective niche. "
     "It is a first-person account from one of the original builders, describing "
     "their doubt, their purpose, and their hope for whoever finds this.",
     state="undiscovered", story_importance="Core lore: first-person builder account.")

_obj("mural_symbol_gallery", "Symbol Gallery Mural", ObjectCategory.STORY,
     "symbol_gallery",
     "A panoramic mural that connects the five symbols into a single narrative. "
     "The Eye sees. The Flame illuminates. The River persists. "
     "The Circle returns. The Throne waits.",
     state="undiscovered", story_importance="Unified symbol mythology.")

_obj("scroll_astronomy", "Astronomy Scroll", ObjectCategory.STORY,
     "astronomers_chamber",
     "A technical document about the celestial alignments used to calibrate "
     "the orrery. Contains encrypted references to underground water levels.",
     state="undiscovered", story_importance="Connects celestial and hydrological systems.")

_obj("plaque_choices", "Plaque: These Are Not Gods", ObjectCategory.STORY,
     "statue_gallery",
     "The entrance plaque reads: 'These are not gods. These are choices.' "
     "Each statue is labelled with an abstract virtue: Patience, Curiosity, "
     "Integrity, Wisdom, and eight others.",
     state="read", story_importance="Reinforces the evaluation theme.")

_obj("map_temple_full", "Temple Map", ObjectCategory.STORY,
     "chamber_of_maps",
     "A large relief map carved directly into the central plinth. "
     "It shows the complete layout of the temple — all four regions, "
     "with passages marked and the water system indicated in blue-painted grooves.",
     state="undiscovered", story_importance="Navigation aid; reveals full temple structure.")

_obj("tablet_water_system", "Water System Tablet", ObjectCategory.STORY,
     "chamber_of_maps",
     "A technical diagram of the underground water system — reservoir, "
     "channels, flood gates, and overflow routes.",
     state="undiscovered", story_importance="Essential for understanding the flood puzzle.")

_obj("chalk_inscription_01", "Chalk Inscription", ObjectCategory.STORY,
     "forgotten_classroom",
     "Fragments of chalk writing on the teaching wall. A partial equation "
     "and the five symbols arranged in a specific order — different from "
     "the Symbol Gallery arrangement.",
     state="undiscovered", story_importance="Puzzle hint for symbol alignment.")

_obj("scroll_lesson", "Teaching Scroll", ObjectCategory.STORY,
     "forgotten_classroom",
     "A teaching scroll laying out the principles of the temple's evaluation "
     "system, written as if for students. 'Observation precedes action. "
     "Understanding precedes judgment.'",
     state="undiscovered", story_importance="Directly describes the evaluation system.")

_obj("plaque_bridge", "Bridge Plaque", ObjectCategory.STORY,
     "bridge_of_echoes",
     (
         "A small plaque mounted at the bridge entrance: "
         "'What echoes from below is older than the bridge. "
         "What echoes from above is older than memory.'"
     ),
     state="read", story_importance="Hints at the reservoir below.")

_obj("tablet_hydraulics", "Hydraulics Tablet", ObjectCategory.STORY,
     "flood_control_room",
     "A technical specification tablet for the flood control machinery. "
     "It lists the sequence of operations required to safely manage the "
     "reservoir water level.",
     state="undiscovered", story_importance="Instructions for the flood control puzzle.")

_obj("tablet_reservoir", "Reservoir Tablet", ObjectCategory.STORY,
     "underground_reservoir",
     "A waterlogged tablet, its text nearly gone. "
     "One phrase survives: 'The river remembers everything you pour into it.'",
     state="undiscovered", story_importance="Chapter 5 lore entry.")

_obj("tablet_channel_system", "Channel System Tablet", ObjectCategory.STORY,
     "water_channel_network",
     "Etched maintenance notes listing every sluice gate and its function. "
     "Some gates are marked 'sealed' — they were deliberately closed.",
     state="undiscovered", story_importance="Provides context for the flood control puzzle.")

_obj("tablet_maintenance", "Maintenance Record", ObjectCategory.STORY,
     "hidden_maintenance_tunnel",
     "A record of maintenance visits carved directly into the tunnel wall. "
     "The most recent entry, far older than any living memory, reads: "
     "'All channels nominal. The flood will not come in my lifetime.'",
     state="undiscovered", story_importance="Ironic lore; establishes timeline.")

_obj("scroll_engineering", "Engineering Scroll", ObjectCategory.STORY,
     "ancient_machinery_chamber",
     "Technical documentation for the counterweight systems. "
     "A footnote reads: 'This machinery was never meant to run forever. "
     "It was meant to run long enough.'",
     state="undiscovered", story_importance="Reveals the intended lifecycle of the temple.")

_obj("mural_reflection_01", "Reflection Mural", ObjectCategory.STORY,
     "chamber_of_reflection",
     "A mural showing the history of the temple compressed into a spiral — "
     "beginning, middle, and the uncertain end. "
     "At the spiral's centre: a blank space, waiting to be filled.",
     state="undiscovered", story_importance="Meta-narrative: the story is unfinished.")

_obj("tablet_judgment_criteria", "Judgment Criteria Tablet", ObjectCategory.STORY,
     "hall_of_judgment",
     "A formal document listing the ten attributes by which the Guardian "
     "evaluates those who seek the Eye: Observation, Curiosity, Wisdom, "
     "Patience, Adaptation, Integrity, Responsibility, Understanding, "
     "and — with rare honesty — Greed and Recklessness as things to minimise.",
     state="undiscovered", story_importance="Explicitly describes the evaluation system.")

_obj("scroll_guardian_records", "Guardian's Records", ObjectCategory.STORY,
     "guardian_archive",
     (
         "A scroll recording evaluations of previous explorers. "
         "Most entries are brief: 'Arrived. Sought treasure. Did not understand. "
         "Departed.' One entry, longer than the others, is annotated: "
         "'Close. Very close.'"
     ),
     state="undiscovered", story_importance="Creates context and raises stakes.")

_obj("tablet_prior_explorers", "Tablet of Prior Explorers", ObjectCategory.STORY,
     "guardian_archive",
     "A list of names — explorers who have entered the temple over the "
     "centuries. None are marked as having reached the Final Chamber.",
     state="undiscovered", story_importance="Historical context; player is unique.")

_obj("plaque_threshold", "Threshold Plaque", ObjectCategory.STORY,
     "throne_approach",
     (
         "A plaque at the approach to the Final Chamber reads: "
         "'Beyond here lies the Eye of Rudra. "
         "But know this: you will not find it. "
         "You will become it — or you will not.'"
     ),
     state="read", story_importance="Final lore reveal before the chamber.")

# ── Interactive objects ───────────────────────────────────────────────────────

_obj("lever_flood_control", "Flood Control Lever", ObjectCategory.INTERACTIVE,
     "flood_control_room",
     "A large iron lever connected to the main sluice gate system. "
     "Pulling it should engage the flood prevention sequence — "
     "if the machinery is still functional.",
     state="idle", puzzle_id="puzzle_flood_control",
     story_importance="Key mechanism in the flood control puzzle.")

_obj("door_guardian_chamber", "Guardian Chamber Door", ObjectCategory.INTERACTIVE,
     "hall_of_guardians",
     "A heavy stone door bearing all four guardian faces. "
     "It will not move by force — the locking mechanism is bound to the "
     "positions of the four guardian statues.",
     state="locked", puzzle_id="puzzle_guardian_statues",
     story_importance="Progression gate between regions I and II.")

_obj("arch_seal", "Sealed Arch", ObjectCategory.INTERACTIVE,
     "throne_approach",
     "A large stone arch whose keystone is engraved with all five symbols. "
     "The arch is sealed — the stone itself seems to refuse passage. "
     "Perhaps the seal responds not to force but to worthiness.",
     state="sealed", puzzle_id="puzzle_final_judgment",
     story_importance="The final gate before the conclusion.")

# ── Environmental objects ────────────────────────────────────────────────────

_obj("flood_gate_main", "Main Flood Gate", ObjectCategory.ENVIRONMENTAL,
     "flood_control_room",
     "A massive sluice gate controlling water flow from the reservoir. "
     "It is currently closed. Opening it without engaging the overflow "
     "bypass would flood the lower chambers.",
     state="closed", puzzle_id="puzzle_flood_control",
     story_importance="Central to the flood simulation system.")

_obj("flood_gate_secondary", "Secondary Flood Gate", ObjectCategory.ENVIRONMENTAL,
     "flood_control_room",
     "A secondary gate controlling overflow. "
     "It should be opened first, before the main gate, to prevent flooding.",
     state="closed", puzzle_id="puzzle_flood_control",
     story_importance="Part of the flood control sequence.")

_obj("water_wheel", "Ancient Water Wheel", ObjectCategory.ENVIRONMENTAL,
     "flood_control_room",
     "A large wooden and stone wheel, its paddles still intact despite the "
     "centuries. When the water flows correctly, this wheel should turn — "
     "generating mechanical power for the temple's internal systems.",
     state="idle", puzzle_id="puzzle_flood_control",
     story_importance="Powers the temple's mechanical systems.")

_obj("bridge_rope", "Bridge Rope", ObjectCategory.ENVIRONMENTAL,
     "bridge_of_echoes",
     "A weathered rope attached to the bridge railing. "
     "Looking down, you see it descends toward the reservoir far below. "
     "It might bear weight — or it might not.",
     state="intact", condition=60.0,
     puzzle_id="puzzle_bridge_integrity",
     story_importance="Provides access to the underground reservoir.")

_obj("rubble_pile", "Collapsed Rubble", ObjectCategory.ENVIRONMENTAL,
     "collapsed_hallway",
     "A mass of fallen stone blocking the northern passage. "
     "Some pieces are large; others are loose. "
     "The gap near the floor might be widened with the right tools.",
     state="blocking", condition=100.0,
     puzzle_id="puzzle_clear_rubble",
     story_importance="Barrier requiring tool use to clear.")

_obj("pool_reflection", "Reflection Pool", ObjectCategory.ENVIRONMENTAL,
     "chamber_of_reflection",
     "A perfectly still pool of dark water filling a basin at the room's centre. "
     "The surface is like polished obsidian — every detail of the room above "
     "it is reflected with perfect clarity. Including you.",
     state="still", puzzle_id="puzzle_reflection_pool",
     story_importance="The mirror puzzle mechanism.")

_obj("gear_system", "Ancient Gear System", ObjectCategory.ENVIRONMENTAL,
     "ancient_machinery_chamber",
     "An enormous array of interlocking gears — some the size of cartwheel, "
     "others no larger than a coin. Most are seized with rust. "
     "The whole system connects somehow to the flood control mechanisms.",
     state="seized", puzzle_id="puzzle_machinery",
     story_importance="Connected to the flood control system.")

_obj("counterweight", "Stone Counterweight", ObjectCategory.ENVIRONMENTAL,
     "ancient_machinery_chamber",
     "A massive stone block suspended on a pulley system. "
     "If released, it would drive the gear system for a limited time.",
     state="suspended", puzzle_id="puzzle_machinery",
     story_importance="Provides temporary mechanical power.")

# ── Puzzle objects ───────────────────────────────────────────────────────────

_obj("statue_guardian_n", "Northern Guardian Statue", ObjectCategory.PUZZLE,
     "hall_of_guardians",
     "One of four identical guardian statues. This one faces north. "
     "The correct facing direction is inscribed, in code, on the Hall of "
     "Guardians floor.",
     state="incorrect", facing=StatueDirection.NORTH,
     puzzle_id="puzzle_guardian_statues",
     story_importance="Part of the guardian statue puzzle.")

_obj("statue_guardian_e", "Eastern Guardian Statue", ObjectCategory.PUZZLE,
     "hall_of_guardians",
     "One of four identical guardian statues. This one faces east. "
     "You sense it is not in the correct position.",
     state="incorrect", facing=StatueDirection.EAST,
     puzzle_id="puzzle_guardian_statues",
     story_importance="Part of the guardian statue puzzle.")

_obj("statue_guardian_s", "Southern Guardian Statue", ObjectCategory.PUZZLE,
     "hall_of_guardians",
     "One of four identical guardian statues. This one faces south.",
     state="incorrect", facing=StatueDirection.SOUTH,
     puzzle_id="puzzle_guardian_statues",
     story_importance="Part of the guardian statue puzzle.")

_obj("statue_guardian_w", "Western Guardian Statue", ObjectCategory.PUZZLE,
     "hall_of_guardians",
     "One of four identical guardian statues. This one faces west.",
     state="incorrect", facing=StatueDirection.WEST,
     puzzle_id="puzzle_guardian_statues",
     story_importance="Part of the guardian statue puzzle.")

_obj("orrery", "Stone Orrery", ObjectCategory.PUZZLE,
     "astronomers_chamber",
     "A hanging model of the known celestial bodies. Several spheres are "
     "missing or displaced. Restoring them to their correct positions might "
     "reveal something about the temple's astronomical calendar.",
     state="incomplete", puzzle_id="puzzle_orrery",
     story_importance="Celestial puzzle; connects to water system timing.")

# ── Symbolic objects ─────────────────────────────────────────────────────────

_obj("relief_eye", "Eye Relief", ObjectCategory.SYMBOLIC,
     "symbol_gallery",
     (
         "A stone relief of the Eye symbol — an open eye with rays extending "
         "from it like a sun. Beside it, text reads: 'See clearly. "
         "The Eye is not merely sight — it is understanding what you see.'"
     ),
     state="intact", story_importance="Defines the Eye symbol's meaning.")

_obj("relief_flame", "Flame Relief", ObjectCategory.SYMBOLIC,
     "symbol_gallery",
     "A carved flame, detailed enough to suggest motion. "
     "'The Flame does not ask for fuel. It transforms what it touches.'",
     state="intact", story_importance="Defines the Flame symbol's meaning.")

_obj("relief_river", "River Relief", ObjectCategory.SYMBOLIC,
     "symbol_gallery",
     "A carving of flowing water, the lines suggesting both movement and memory. "
     "'The River does not forget the stone it has passed over.'",
     state="intact", story_importance="Defines the River symbol's meaning.")

_obj("relief_circle", "Circle Relief", ObjectCategory.SYMBOLIC,
     "symbol_gallery",
     "A perfect circle, carved with mathematical precision. "
     "'The Circle does not end. It returns. What is completed is not finished.'",
     state="intact", story_importance="Defines the Circle symbol's meaning.")

_obj("relief_throne", "Throne Relief", ObjectCategory.SYMBOLIC,
     "symbol_gallery",
     (
         "A carved throne, empty. 'The Throne is not for sitting. "
         "It is for understanding who should not sit on it.'"
     ),
     state="intact", story_importance="Defines the Throne symbol's meaning.")

_obj("guardian_seat", "Guardian's Seat", ObjectCategory.SYMBOLIC,
     "hall_of_judgment",
     "The raised seat at the far end of the Hall of Judgment. "
     "It is empty. Has always been empty. "
     "The Guardian evaluates — but does not occupy space.",
     state="empty", interactable=False,
     story_importance="Symbolic: the Guardian is not a physical presence.")

_obj("statue_gallery_01", "Gallery Statue: Patience", ObjectCategory.SYMBOLIC,
     "statue_gallery",
     "One of twelve statues representing abstract virtues. "
     "This figure is seated, eyes closed, hands open in the lap. "
     "The label reads: 'Patience is not waiting. It is understanding why.'",
     state="intact", story_importance="Reinforces evaluation themes.")

_obj("relief_judgment_01", "Judgment Relief I", ObjectCategory.SYMBOLIC,
     "hall_of_judgment",
     "A relief showing a figure approaching a mirror and seeing not their "
     "face but their history of choices.",
     state="intact", story_importance="Visual representation of the judgment process.")

_obj("relief_judgment_02", "Judgment Relief II", ObjectCategory.SYMBOLIC,
     "hall_of_judgment",
     "A relief showing three outcomes after judgment — "
     "one figure leaving unchanged, one leaving wiser, one leaving transformed.",
     state="intact", story_importance="Shows the three possible judgment outcomes.")

# ── Guardian / Ending objects ─────────────────────────────────────────────────

_obj("guardian_mirror", "The Guardian", ObjectCategory.GUARDIAN,
     "final_chamber",
     "The Guardian of the Lost Temple — not a creature, not a weapon, "
     "not a treasure chest. It is a mirror, floor to ceiling, "
     "framed in all five sacred symbols. "
     "It shows you as you are: every choice recorded, every moment of "
     "curiosity or fear or wisdom or recklessness reflected back. "
     "It does not speak. It does not need to.",
     state="active", interactable=False,
     story_importance="The final revelation: the Guardian is self-knowledge.")

_obj("eye_of_rudra", "The Eye of Rudra", ObjectCategory.GUARDIAN,
     "final_chamber",
     "The Eye of Rudra is not an object. It never was. "
     "It is the capacity to see yourself with perfect clarity — "
     "to know what you have done, what it cost, and what it meant. "
     "You feel it, now, looking at the mirror. "
     "You cannot pick it up. You can only earn it.",
     state="present", interactable=False, visible=False,
     story_importance="The game's ultimate revelation and ending trigger.",
     collectible=False)


# ---------------------------------------------------------------------------
# Convenience lookup
# ---------------------------------------------------------------------------

ALL_OBJECT_IDS: frozenset[str] = frozenset(OBJECT_DEFINITIONS.keys())


def get_object_definition(object_id: str) -> Optional[ObjectDefinition]:
    """Return the static ObjectDefinition for an object ID, or None."""
    return OBJECT_DEFINITIONS.get(object_id)


def get_objects_for_room(room_id: str) -> list[ObjectDefinition]:
    """Return all objects whose starting room is room_id."""
    return [od for od in OBJECT_DEFINITIONS.values() if od.room_id == room_id]


def get_collectible_objects() -> list[ObjectDefinition]:
    """Return all collectible object definitions."""
    return [od for od in OBJECT_DEFINITIONS.values()
            if od.category == ObjectCategory.COLLECTIBLE]


# ---------------------------------------------------------------------------
# Factory — build ObjectState instances for the World Model
# ---------------------------------------------------------------------------

def build_world_objects() -> dict[str, ObjectState]:
    """
    Instantiate a fresh ObjectState for every canonical object.

    Called once at game startup to populate WorldModel.objects.
    """
    objects: dict[str, ObjectState] = {}
    for od in OBJECT_DEFINITIONS.values():
        obj = ObjectState(
            object_id=od.object_id,
            name=od.name,
            category=od.category,
            current_room=od.room_id,
            current_owner=None,
            condition=od.initial_condition,
            state=od.initial_state,
            visible=od.visible,
            discoverable=od.discoverable,
            interactable=od.interactable,
            puzzle_id=od.puzzle_id,
            story_importance=od.story_importance,
            facing_direction=od.facing_direction,
        )
        objects[od.object_id] = obj
    return objects
