"""
rooms.py — The Lost Temple of Rudra

Defines the complete static room graph for all 24 canonical temple rooms.

The physical layout never changes. Only room state (accessibility, flood,
dust, objects present) changes via the World Model.

Each room definition captures:
    - Canonical ID, display name, and region
    - Static neighbour connections (graph edges, always present)
    - Default accessible exits (dynamic — changed by puzzles / events)
    - Object IDs initially present
    - Room description (for LOOK command)
    - Lore symbols present
    - Puzzle ID (if any)

Blueprint Reference:
    Chapter 5  — Temple Layout & World Design
    Chapter 6  — Room Design Bible
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .room_state import RoomState, RoomRegion, LightLevel


# ---------------------------------------------------------------------------
# RoomDefinition — static blueprint; never stored in World Model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoomDefinition:
    """
    Immutable blueprint for a single temple room.

    static_connections: all physical neighbour links (direction → room_id).
                        These never change.
    default_accessible: subset of static_connections accessible at game start.
                        Puzzle/event logic may open or close these at runtime
                        by writing to RoomState.accessible_exits.
    """
    room_id: str
    name: str
    region: RoomRegion
    description: str
    static_connections: dict[str, str] = field(default_factory=dict)
    default_accessible: dict[str, str] = field(default_factory=dict)
    initial_objects: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    puzzle_id: Optional[str] = None
    light_level: LightLevel = LightLevel.NORMAL
    hidden_passages: dict[str, str] = field(default_factory=dict)
    # hidden_passages: direction → room_id (all start inaccessible)


# ---------------------------------------------------------------------------
# Canonical room definitions — all 24 rooms
# Blueprint Chapter 5 — Temple Layout
# ---------------------------------------------------------------------------

ROOM_DEFINITIONS: dict[str, RoomDefinition] = {}


def _room(
    room_id: str,
    name: str,
    region: RoomRegion,
    description: str,
    connections: dict[str, str],
    accessible: dict[str, str],
    objects: list[str] = (),
    symbols: list[str] = (),
    puzzle_id: Optional[str] = None,
    light: LightLevel = LightLevel.NORMAL,
    hidden: dict[str, str] = (),
) -> RoomDefinition:
    """Helper to build and register a RoomDefinition."""
    rd = RoomDefinition(
        room_id=room_id,
        name=name,
        region=region,
        description=description,
        static_connections=dict(connections),
        default_accessible=dict(accessible),
        initial_objects=list(objects),
        symbols=list(symbols),
        puzzle_id=puzzle_id,
        light_level=light,
        hidden_passages=dict(hidden) if hidden else {},
    )
    ROOM_DEFINITIONS[room_id] = rd
    return rd


# ── Region I: Outer Temple ───────────────────────────────────────────────────

_room(
    "temple_entrance",
    "Temple Entrance",
    RoomRegion.OUTER_TEMPLE,
    (
        "You stand at the threshold of the Lost Temple of Rudra. "
        "Massive stone doors frame a passage leading north into darkness. "
        "Carved above the lintel, an ancient inscription catches the flickering "
        "light: 'The temple does not remember your name. It remembers your choices.' "
        "Dust lies thick on the floor, undisturbed for centuries. "
        "A weathered torch bracket juts from the eastern wall."
    ),
    connections={"north": "hall_of_echoes"},
    accessible={"north": "hall_of_echoes"},
    objects=["torch_entrance", "inscription_entrance"],
    symbols=["eye"],
    puzzle_id=None,
    light=LightLevel.DIM,
)

_room(
    "hall_of_echoes",
    "Hall of Echoes",
    RoomRegion.OUTER_TEMPLE,
    (
        "A long vaulted corridor stretches before you, its walls lined with "
        "shallow alcoves. Every footstep rings back at you doubled, tripled — "
        "as if the temple itself is counting your steps. "
        "Passages lead south back to the entrance, east toward the Hall of "
        "Guardians, and west into the Chamber of Inscriptions. "
        "High above, a narrow slit window admits a thread of pale light."
    ),
    connections={
        "south": "temple_entrance",
        "east": "hall_of_guardians",
        "west": "chamber_of_inscriptions",
        "north": "first_meditation_hall",
    },
    accessible={
        "south": "temple_entrance",
        "east": "hall_of_guardians",
        "west": "chamber_of_inscriptions",
        "north": "first_meditation_hall",
    },
    objects=["scroll_hall_of_echoes"],
    symbols=["flame"],
)

_room(
    "hall_of_guardians",
    "Hall of Guardians",
    RoomRegion.OUTER_TEMPLE,
    (
        "Four colossal stone guardians stand sentinel, one at each corner of the "
        "chamber. Their blank faces all face inward, as if watching you. "
        "The room smells of old stone and something faintly metallic. "
        "The western passage leads back to the Hall of Echoes. "
        "A heavy stone door stands sealed to the north — its locking mechanism "
        "seems tied to the statues."
    ),
    connections={
        "west": "hall_of_echoes",
        "north": "chamber_of_inscriptions",
    },
    accessible={
        "west": "hall_of_echoes",
        # north sealed until guardian puzzle solved
    },
    objects=["statue_guardian_n", "statue_guardian_e", "statue_guardian_s", "statue_guardian_w",
             "door_guardian_chamber"],
    symbols=["eye", "throne"],
    puzzle_id="puzzle_guardian_statues",
)

_room(
    "chamber_of_inscriptions",
    "Chamber of Inscriptions",
    RoomRegion.OUTER_TEMPLE,
    (
        "Every surface of this chamber is covered in tightly carved script — "
        "floor to ceiling, column to column. The inscriptions appear to be a "
        "continuous narrative, spiralling inward from the outer walls. "
        "The air is cold and still. Passages lead east back to the Hall of "
        "Echoes, and north toward the First Meditation Hall."
    ),
    connections={
        "east": "hall_of_echoes",
        "north": "first_meditation_hall",
        "west": "hall_of_guardians",
    },
    accessible={
        "east": "hall_of_echoes",
        "north": "first_meditation_hall",
        "west": "hall_of_guardians",
    },
    objects=["tablet_inscriptions_01", "tablet_inscriptions_02"],
    symbols=["river", "circle"],
)

_room(
    "first_meditation_hall",
    "First Meditation Hall",
    RoomRegion.OUTER_TEMPLE,
    (
        "A circular chamber, bare save for a low stone dais at its centre. "
        "The ceiling is domed, and a circular opening at its apex frames a "
        "patch of sky — or darkness, depending on the hour. "
        "The silence here is of a different quality: intentional, expectant. "
        "Passages lead south to the Hall of Echoes, east to the Symbol Gallery, "
        "and north deeper into the temple."
    ),
    connections={
        "south": "hall_of_echoes",
        "east": "symbol_gallery",
        "north": "ancient_library",
        "west": "chamber_of_inscriptions",
    },
    accessible={
        "south": "hall_of_echoes",
        "east": "symbol_gallery",
        "north": "ancient_library",
        "west": "chamber_of_inscriptions",
    },
    objects=["mural_meditation_01"],
    symbols=["circle"],
)

# ── Region II: Knowledge Sanctum ────────────────────────────────────────────

_room(
    "ancient_library",
    "Ancient Library",
    RoomRegion.KNOWLEDGE_SANCTUM,
    (
        "Row upon row of stone shelves line this vast library, most now empty "
        "but for dust. A handful of clay tablets and rolled scrolls survive "
        "in niches protected from the worst of the decay. "
        "At the far end, a reading lectern still stands. "
        "The southern passage leads back to the First Meditation Hall. "
        "Stairs lead up to the Archive Vault. A narrow doorway opens east "
        "into the Astronomer's Chamber."
    ),
    connections={
        "south": "first_meditation_hall",
        "up": "archive_vault",
        "east": "astronomers_chamber",
        "west": "forgotten_classroom",
    },
    accessible={
        "south": "first_meditation_hall",
        "up": "archive_vault",
        "east": "astronomers_chamber",
        "west": "forgotten_classroom",
    },
    objects=["scroll_ancient_library_01", "scroll_ancient_library_02",
             "tablet_library_index"],
    symbols=["flame", "eye"],
    light=LightLevel.DIM,
)

_room(
    "archive_vault",
    "Archive Vault",
    RoomRegion.KNOWLEDGE_SANCTUM,
    (
        "A smaller chamber above the library, sealed with a stone door now "
        "wedged open by a collapsed shelf. The most protected scrolls were "
        "kept here — and several have survived. "
        "A scholar's writing table occupies the centre, its surface scored "
        "with calculations no longer legible. "
        "Stairs lead back down to the Ancient Library."
    ),
    connections={"down": "ancient_library"},
    accessible={"down": "ancient_library"},
    objects=["scroll_vault_01", "key_archive"],
    symbols=["circle", "throne"],
    light=LightLevel.DIM,
)

_room(
    "symbol_gallery",
    "Symbol Gallery",
    RoomRegion.KNOWLEDGE_SANCTUM,
    (
        "Five alcoves, one for each of the five sacred symbols, ring this "
        "gallery. Each alcove is carved with a single enormous glyph and "
        "contains a stone relief depicting scenes of the symbol's significance. "
        "The Eye. The Flame. The River. The Circle. The Throne. "
        "The western passage leads back to the First Meditation Hall. "
        "A passage north leads into the Chamber of Maps."
    ),
    connections={
        "west": "first_meditation_hall",
        "north": "chamber_of_maps",
    },
    accessible={
        "west": "first_meditation_hall",
        "north": "chamber_of_maps",
    },
    objects=["relief_eye", "relief_flame", "relief_river", "relief_circle", "relief_throne",
             "mural_symbol_gallery"],
    symbols=["eye", "flame", "river", "circle", "throne"],
    puzzle_id="puzzle_symbol_alignment",
)

_room(
    "astronomers_chamber",
    "Astronomer's Chamber",
    RoomRegion.KNOWLEDGE_SANCTUM,
    (
        "A circular room dominated by a large stone orrery — a model of the "
        "celestial bodies — suspended from the ceiling by corroded chains. "
        "Several of the spheres have fallen and lie on the floor. "
        "The walls are covered with astronomical charts, most faded beyond "
        "reading. A crack in the ceiling admits a thin beam of light that "
        "moves across the floor over the course of a day. "
        "Passages west lead back to the Ancient Library and east to the "
        "Statue Gallery."
    ),
    connections={
        "west": "ancient_library",
        "east": "statue_gallery",
    },
    accessible={
        "west": "ancient_library",
        "east": "statue_gallery",
    },
    objects=["orrery", "scroll_astronomy"],
    symbols=["circle", "eye"],
    puzzle_id="puzzle_orrery",
)

_room(
    "statue_gallery",
    "Statue Gallery",
    RoomRegion.KNOWLEDGE_SANCTUM,
    (
        "A gallery of twelve stone figures arranged in two facing rows, each "
        "representing a different posture of supplication or wisdom. "
        "Their expressions are surprisingly detailed — sorrow, wonder, "
        "determination. A plaque at the entrance reads: 'These are not gods. "
        "These are choices.' "
        "Passages lead west back to the Astronomer's Chamber and north to the "
        "Chamber of Maps."
    ),
    connections={
        "west": "astronomers_chamber",
        "north": "chamber_of_maps",
        "south": "bridge_of_echoes",
    },
    accessible={
        "west": "astronomers_chamber",
        "north": "chamber_of_maps",
        "south": "bridge_of_echoes",
    },
    objects=["statue_gallery_01", "plaque_choices"],
    symbols=["throne", "river"],
)

_room(
    "chamber_of_maps",
    "Chamber of Maps",
    RoomRegion.KNOWLEDGE_SANCTUM,
    (
        "Carved relief maps cover every wall — topographic surveys of the "
        "temple's surroundings, diagrams of the water system beneath the "
        "floors, architectural cross-sections. Most are too eroded to read "
        "clearly, but one large central map of the full temple layout is "
        "still decipherable. "
        "Passages lead south to the Symbol Gallery and Statue Gallery. "
        "A passage east leads toward the bridge."
    ),
    connections={
        "south": "symbol_gallery",
        "east": "bridge_of_echoes",
        "west": "forgotten_classroom",
        "north": "collapsed_hallway",
    },
    accessible={
        "south": "symbol_gallery",
        "east": "bridge_of_echoes",
        "west": "forgotten_classroom",
        # north blocked by collapse
    },
    objects=["map_temple_full", "tablet_water_system"],
    symbols=["river"],
    puzzle_id="puzzle_map_reading",
)

_room(
    "forgotten_classroom",
    "Forgotten Classroom",
    RoomRegion.KNOWLEDGE_SANCTUM,
    (
        "Rows of low stone benches face a blank teaching wall. A few "
        "fragments of chalk inscription remain — partial equations, symbol "
        "sequences, an incomplete diagram. "
        "It feels like something interrupted a lesson and no one ever returned. "
        "Passages lead east to the Ancient Library and north to the Chamber of Maps."
    ),
    connections={
        "east": "ancient_library",
        "north": "chamber_of_maps",
    },
    accessible={
        "east": "ancient_library",
        "north": "chamber_of_maps",
    },
    objects=["chalk_inscription_01", "scroll_lesson"],
    symbols=["circle"],
)

# ── Region III: The Living Temple ────────────────────────────────────────────

_room(
    "bridge_of_echoes",
    "Bridge of Echoes",
    RoomRegion.LIVING_TEMPLE,
    (
        "A narrow stone bridge spans a deep shaft. Looking down, you can hear "
        "the distant sound of running water far below. "
        "The bridge is solid for now, though weathered. A crack runs along its "
        "eastern edge. "
        "Passages lead west back toward the chamber network and east to the "
        "Flood Control Room. North leads to the Statue Gallery."
    ),
    connections={
        "west": "chamber_of_maps",
        "east": "flood_control_room",
        "north": "statue_gallery",
        "down": "underground_reservoir",
    },
    accessible={
        "west": "chamber_of_maps",
        "east": "flood_control_room",
        "north": "statue_gallery",
        # down: only accessible after bridge rope discovered
    },
    objects=["bridge_rope", "plaque_bridge"],
    symbols=["river"],
    puzzle_id="puzzle_bridge_integrity",
    light=LightLevel.DIM,
    hidden={"down": "underground_reservoir"},
)

_room(
    "flood_control_room",
    "Flood Control Room",
    RoomRegion.LIVING_TEMPLE,
    (
        "Ancient hydraulic machinery fills this room — wheels, levers, sluice "
        "gates connected by corroded chains. The floor is damp; "
        "a thin film of water seeps through the western wall. "
        "The whole system is designed to manage the underground reservoir "
        "and prevent flooding of the lower chambers. "
        "Passage west leads back across the bridge. "
        "A reinforced door leads north to the Ancient Machinery Chamber. "
        "Stairs lead down to the Water Channel Network."
    ),
    connections={
        "west": "bridge_of_echoes",
        "north": "ancient_machinery_chamber",
        "down": "water_channel_network",
    },
    accessible={
        "west": "bridge_of_echoes",
        "north": "ancient_machinery_chamber",
        "down": "water_channel_network",
    },
    objects=["flood_gate_main", "flood_gate_secondary", "water_wheel",
             "lever_flood_control", "tablet_hydraulics"],
    symbols=["river"],
    puzzle_id="puzzle_flood_control",
    light=LightLevel.DIM,
)

_room(
    "underground_reservoir",
    "Underground Reservoir",
    RoomRegion.LIVING_TEMPLE,
    (
        "A vast underground cistern, partially filled with dark still water. "
        "The ceiling is lost in shadow far above. Stone walkways run along "
        "the edges of the reservoir, slick with moisture. "
        "The water's surface is perfectly flat and mirror-like. "
        "You can hear your own breathing echoing back from every direction. "
        "A rope ladder leads back up to the Bridge of Echoes. "
        "A narrow passage leads east to the Water Channel Network."
    ),
    connections={
        "up": "bridge_of_echoes",
        "east": "water_channel_network",
    },
    accessible={
        "up": "bridge_of_echoes",
        "east": "water_channel_network",
    },
    objects=["ancient_key_reservoir", "tablet_reservoir"],
    symbols=["river", "eye"],
    puzzle_id="puzzle_reservoir",
    light=LightLevel.DARK,
)

_room(
    "water_channel_network",
    "Water Channel Network",
    RoomRegion.LIVING_TEMPLE,
    (
        "A labyrinth of carved stone channels, most still carrying trickling "
        "water toward the reservoir. The sound of water is constant here — "
        "a low, patient murmur. "
        "Maintenance alcoves line the walls, some still containing tools. "
        "Passages lead west to the Reservoir, up to the Flood Control Room, "
        "and east to the Hidden Maintenance Tunnel."
    ),
    connections={
        "west": "underground_reservoir",
        "up": "flood_control_room",
        "east": "hidden_maintenance_tunnel",
    },
    accessible={
        "west": "underground_reservoir",
        "up": "flood_control_room",
        # east sealed until specific puzzle
    },
    objects=["tool_wrench", "tablet_channel_system"],
    symbols=["river"],
    hidden={"east": "hidden_maintenance_tunnel"},
)

_room(
    "collapsed_hallway",
    "Collapsed Hallway",
    RoomRegion.LIVING_TEMPLE,
    (
        "Part of the ceiling has come down here, blocking what was once a "
        "direct passage. Rubble is piled high. A narrow gap near the floor "
        "might be passable if you crouch low. "
        "The passage south leads back to the Chamber of Maps. "
        "The way north was once a direct route to the Chamber of Reflection, "
        "but the collapse may have blocked it completely."
    ),
    connections={
        "south": "chamber_of_maps",
        "north": "chamber_of_reflection",
    },
    accessible={
        "south": "chamber_of_maps",
        # north: accessible only after clearing rubble (puzzle)
    },
    objects=["rubble_pile", "ancient_key_collapsed"],
    symbols=["river"],
    puzzle_id="puzzle_clear_rubble",
)

_room(
    "ancient_machinery_chamber",
    "Ancient Machinery Chamber",
    RoomRegion.LIVING_TEMPLE,
    (
        "A cathedral-sized space filled with the remnants of extraordinary "
        "engineering. Enormous gear systems, counterweight mechanisms, and "
        "pulley arrays fill the room. Most are frozen with rust and age, "
        "but a few still move when the flood control system operates. "
        "Passages lead south back to the Flood Control Room. "
        "A sealed passage north leads toward the Chamber of Reflection."
    ),
    connections={
        "south": "flood_control_room",
        "north": "chamber_of_reflection",
    },
    accessible={
        "south": "flood_control_room",
        "north": "chamber_of_reflection",
    },
    objects=["gear_system", "counterweight", "scroll_engineering"],
    symbols=["flame", "circle"],
    puzzle_id="puzzle_machinery",
)

_room(
    "hidden_maintenance_tunnel",
    "Hidden Maintenance Tunnel",
    RoomRegion.LIVING_TEMPLE,
    (
        "A narrow service tunnel, barely wide enough to move through sideways. "
        "The walls are rough — this was never meant for ceremony, only function. "
        "Maintenance markings are scratched into the stone at intervals. "
        "It connects back west to the Water Channel Network and, at its far end, "
        "opens into a hidden alcove behind the Chamber of Reflection."
    ),
    connections={
        "west": "water_channel_network",
        "east": "chamber_of_reflection",
    },
    accessible={
        "west": "water_channel_network",
        "east": "chamber_of_reflection",
    },
    objects=["tablet_maintenance", "tool_chisel"],
    symbols=["river"],
    light=LightLevel.DARK,
)

# ── Region IV: Guardian Core ─────────────────────────────────────────────────

_room(
    "chamber_of_reflection",
    "Chamber of Reflection",
    RoomRegion.GUARDIAN_CORE,
    (
        "A perfectly square chamber, its walls polished to a high sheen so "
        "that you see yourself reflected from every angle at once. "
        "At the centre, a still pool of dark water mirrors the ceiling. "
        "The room feels charged — as if the air itself is paying attention. "
        "Passages lead south to the Collapsed Hallway or the Machinery Chamber, "
        "and north toward the Hall of Judgment."
    ),
    connections={
        "south": "ancient_machinery_chamber",
        "north": "hall_of_judgment",
        "west": "collapsed_hallway",
        "east": "hidden_maintenance_tunnel",
    },
    accessible={
        "south": "ancient_machinery_chamber",
        "north": "hall_of_judgment",
        "west": "collapsed_hallway",
        "east": "hidden_maintenance_tunnel",
    },
    objects=["pool_reflection", "mural_reflection_01"],
    symbols=["eye", "circle", "throne"],
    puzzle_id="puzzle_reflection_pool",
    light=LightLevel.BRIGHT,
)

_room(
    "hall_of_judgment",
    "Hall of Judgment",
    RoomRegion.GUARDIAN_CORE,
    (
        "An immense hall, impossibly tall, with an arched ceiling lost in "
        "shadow. The walls are lined with carved reliefs depicting moments "
        "of judgment — not punishment, but evaluation. Every scene shows a "
        "figure standing before the Guardian, offering something of themselves. "
        "A raised dais at the far end holds the Guardian's seat — empty. "
        "The passage south leads back. The passage north leads to the "
        "Guardian Archive. The Throne Approach lies east."
    ),
    connections={
        "south": "chamber_of_reflection",
        "north": "guardian_archive",
        "east": "throne_approach",
    },
    accessible={
        "south": "chamber_of_reflection",
        "north": "guardian_archive",
        "east": "throne_approach",
    },
    objects=["relief_judgment_01", "relief_judgment_02",
             "tablet_judgment_criteria", "guardian_seat"],
    symbols=["eye", "throne"],
    light=LightLevel.DIM,
)

_room(
    "guardian_archive",
    "Guardian Archive",
    RoomRegion.GUARDIAN_CORE,
    (
        "A small chamber attached to the Hall of Judgment, containing the "
        "records of every explorer who has ever been evaluated by the Guardian. "
        "Most entries record failure — not of ability, but of understanding. "
        "One shelf holds a single scroll, more recent than the others, "
        "partially translated by some earlier visitor."
    ),
    connections={"south": "hall_of_judgment"},
    accessible={"south": "hall_of_judgment"},
    objects=["scroll_guardian_records", "tablet_prior_explorers"],
    symbols=["eye", "circle"],
)

_room(
    "throne_approach",
    "Throne Approach",
    RoomRegion.GUARDIAN_CORE,
    (
        "A broad ceremonial corridor leading toward the Final Chamber. "
        "The floor is inlaid with all five sacred symbols in sequence: "
        "eye, flame, river, circle, throne. "
        "Torches in wall brackets still burn — lit by mechanisms unknown, "
        "fuelled by something older than memory. "
        "The passage west leads back to the Hall of Judgment. "
        "The sealed arch ahead leads to the Final Chamber."
    ),
    connections={
        "west": "hall_of_judgment",
        "north": "final_chamber",
    },
    accessible={
        "west": "hall_of_judgment",
        # north sealed until player is worthy
    },
    objects=["arch_seal", "plaque_threshold"],
    symbols=["eye", "flame", "river", "circle", "throne"],
    light=LightLevel.BRIGHT,
)

_room(
    "final_chamber",
    "Final Chamber",
    RoomRegion.GUARDIAN_CORE,
    (
        "You have reached the heart of the Lost Temple of Rudra. "
        "The chamber is circular, its walls bare polished stone. "
        "At the centre stands the Guardian — not a creature, not a weapon, "
        "not a treasure. The Guardian is a mirror, floor to ceiling, "
        "framed in five sacred symbols. "
        "It shows you as you are: every choice recorded, every moment of "
        "curiosity or fear or wisdom or recklessness. "
        "The Eye of Rudra is not an object. It was never an object. "
        "It is this — the capacity to see yourself clearly. "
        "The chamber is silent. The temple is waiting."
    ),
    connections={"south": "throne_approach"},
    accessible={"south": "throne_approach"},
    objects=["guardian_mirror", "eye_of_rudra"],
    symbols=["eye", "flame", "river", "circle", "throne"],
    light=LightLevel.BRIGHT,
)

# ---------------------------------------------------------------------------
# Convenience lookup
# ---------------------------------------------------------------------------

ALL_ROOM_IDS: frozenset[str] = frozenset(ROOM_DEFINITIONS.keys())


def get_room_definition(room_id: str) -> Optional[RoomDefinition]:
    """Return the static RoomDefinition for a room ID, or None."""
    return ROOM_DEFINITIONS.get(room_id)


def get_connected_rooms(room_id: str) -> dict[str, str]:
    """Return the static connections (direction → room_id) for a room."""
    rd = ROOM_DEFINITIONS.get(room_id)
    return dict(rd.static_connections) if rd else {}


# ---------------------------------------------------------------------------
# Factory — build all RoomState instances for the World Model
# ---------------------------------------------------------------------------

def build_world_rooms() -> dict[str, RoomState]:
    """
    Instantiate a fresh RoomState for every canonical room.

    The initial accessible_exits are taken from default_accessible in the
    RoomDefinition. The Game Engine may open/close exits at runtime.
    Called once at game startup to populate WorldModel.rooms.
    """
    rooms: dict[str, RoomState] = {}
    for rd in ROOM_DEFINITIONS.values():
        rooms[rd.room_id] = RoomState(
            room_id=rd.room_id,
            region=rd.region,
            light_level=rd.light_level,
            object_ids_present=list(rd.initial_objects),
            accessible_exits=dict(rd.default_accessible),
            hidden_passages={k: False for k in rd.hidden_passages},
            puzzle_id=rd.puzzle_id,
        )
    return rooms
