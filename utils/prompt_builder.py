"""Prompt builder utilities for the Discord bot.

Constructs a token-budgeted system prompt for the AI DM with prioritized
context sections and concise tag instructions.
"""

import logging
from typing import Optional, Callable, List, Tuple

from utils.character_manager import load_character

# Context source imports — fail at startup, not silently at runtime
from utils.npc_manager import get_nearby_npcs, get_faction_context_for_ai
from utils.quest_manager import get_quest_context_for_ai
from utils.environment_manager import get_environment_context_for_ai
from utils.encounter_manager import get_travel_context_for_ai
from utils.world_generator import get_world_context_for_ai
from utils.world_map import get_world_context_for_ai as get_map_context
from utils.session_manager import get_pacing_context_for_ai
from utils.inventory_manager import get_party_inventory_context

logger = logging.getLogger(__name__)

# ~1500 tokens ≈ 6000 characters
MAX_CONTEXT_CHARS = 6000

DIFFICULTY_GUIDE = {
    "easy": "Be generous with successes and helpful hints. Most DCs 10-12.",
    "normal": "Standard D&D 5e difficulty. DCs 10-18 based on task.",
    "hard": "Be challenging. DCs 15-22, real consequences.",
}


# =============================================================================
# Context getters — each returns a (name, text) or empty string
# =============================================================================

def _combat_context(state: dict, channel_id: str) -> str:
    """If in combat, that's the #1 context."""
    combat = state.get("combat") or state.get("in_combat")
    if not combat:
        return ""
    # Compact summary of who's in the fight
    combatants = state.get("combat", {}).get("combatants", [])
    if not combatants:
        return ""
    lines = ["**Active Combat:**"]
    for c in combatants:
        hp = f"{c.get('hp', '?')}/{c.get('max_hp', c.get('hp', '?'))}"
        lines.append(f"- {c['name']} HP:{hp} AC:{c.get('ac', '?')}")
    return "\n".join(lines)


def _campaign_summary_context(state: dict, _channel_id: str) -> str:
    summary = state.get("campaign_summary", "")
    if summary:
        return f"**Story So Far:** {summary}"
    return ""


def _quest_context(_state: dict, channel_id: str) -> str:
    return get_quest_context_for_ai(channel_id) or ""


def _npc_context(state: dict, channel_id: str) -> str:
    location = state.get("location", "")
    nearby = get_nearby_npcs(channel_id, location)
    if not nearby:
        return ""
    disp_map = {-2: "hostile", -1: "unfriendly", 0: "neutral", 1: "friendly", 2: "allied"}
    lines = ["**Nearby NPCs:**"]
    for npc in nearby[:5]:
        disp = disp_map.get(npc.disposition, "neutral")
        lines.append(f"- {npc.name} ({npc.race} {npc.role}): {disp}")
    faction = get_faction_context_for_ai(channel_id)
    if faction:
        lines.append(faction)
    return "\n".join(lines)


def _environment_context(_state: dict, channel_id: str) -> str:
    return get_environment_context_for_ai(channel_id) or ""


def _world_context(_state: dict, channel_id: str) -> str:
    return get_world_context_for_ai(channel_id) or ""


def _travel_context(_state: dict, channel_id: str) -> str:
    return get_travel_context_for_ai(channel_id) or ""


def _pacing_context(_state: dict, channel_id: str) -> str:
    return get_pacing_context_for_ai(channel_id) or ""


def _map_context(_state: dict, channel_id: str) -> str:
    return get_map_context(channel_id) or ""


def _inventory_context(state: dict, _channel_id: str) -> str:
    players = state.get("players", [])
    if players:
        return get_party_inventory_context(players) or ""
    return ""


# Priority order — combat & campaign summary first, polish last
CONTEXT_PRIORITY: List[Tuple[str, Callable]] = [
    ("combat", _combat_context),
    ("campaign_summary", _campaign_summary_context),
    ("quests", _quest_context),
    ("npcs", _npc_context),
    ("environment", _environment_context),
    ("world", _world_context),
    ("travel", _travel_context),
    ("pacing", _pacing_context),
    ("map", _map_context),
    ("inventory", _inventory_context),
]


def _build_context_sections(state: dict, channel_id: Optional[str]) -> str:
    """Gather context sections in priority order, stopping at the token budget."""
    if not channel_id:
        return ""

    sections: list[str] = []
    total = 0

    for name, getter in CONTEXT_PRIORITY:
        try:
            section = getter(state, channel_id)
            if section and total + len(section) < MAX_CONTEXT_CHARS:
                sections.append(section)
                total += len(section)
        except Exception:
            logger.debug("Context source '%s' failed, skipping", name)
            continue

    return "\n\n".join(sections)


# =============================================================================
# Tag instruction blocks — conditional on game state
# =============================================================================

_COMBAT_TAG_INSTRUCTIONS = """\
**Tags — Combat:**
[COMBAT: <count> <creature>, ...] — triggers combat. [SURPRISE: enemies|party] — ambush.
Do NOT ask for initiative rolls — the system handles that."""

_ENVIRONMENT_TAG_INSTRUCTIONS = """\
**Tags — Environment (optional, only on significant changes):**
[WEATHER: rain] · [LIGHTING: dim] · [LOCATION: Dark Cave] · [TIME: 3 hours pass] · [TRAP: pit trap] · [HAZARD: lava pool, 2d6 fire]"""

_QUEST_TAG_INSTRUCTIONS = """\
**Tags — Quests:**
[QUEST: name="...", type=rescue, difficulty=hard, giver="NPC"] · [QUEST_COMPLETE: "Name"] · [QUEST_PROGRESS: "Name", objective=1]
[RUMOR: "hint text"] · [QUEST_HOOK: name="...", description="..."] · [OBJECTIVE: "new objective"] · [QUEST_CHAIN: parent="A", child="B"]"""

_TRAVEL_TAG_INSTRUCTIONS = """\
**Tags — Travel:**
[TRAVEL: destination="Place", distance=15, terrain=forest] · [ARRIVAL: "Place"]
[LOCATION_DISCOVERED: name="Ruins", terrain=hills, type=ruins, poi=true] · [DISTANCE_REVEALED: from="A" to="B" miles=100]"""

_SKILL_CHECK_INSTRUCTIONS = """\
**Skill Checks:**
When the action is SPECIFIC and COMMITTED → ask for the check: "🎲 Roll [Skill] (DC [number])!" then STOP.
When the action is VAGUE → describe the situation and present 3 options, no roll yet."""


def _build_tag_instructions(state: dict) -> str:
    """Return concise tag instructions, conditional on game state."""
    parts: list[str] = []

    in_combat = state.get("in_combat", False)

    # Always include combat tags (unless already in combat)
    if not in_combat:
        parts.append(_COMBAT_TAG_INSTRUCTIONS)

    parts.append(_ENVIRONMENT_TAG_INSTRUCTIONS)
    parts.append(_QUEST_TAG_INSTRUCTIONS)

    # Only include travel tags when NOT actively traveling
    if not state.get("traveling"):
        parts.append(_TRAVEL_TAG_INSTRUCTIONS)

    parts.append(_SKILL_CHECK_INSTRUCTIONS)

    if not in_combat:
        parts.append(
            "**End with 3 short action suggestions** (only when NOT asking for a roll and NOT in combat):\n"
            "💡 **What will you do?**\n1. [Option] 2. [Option] 3. [Option]"
        )

    return "\n\n".join(parts)


# =============================================================================
# PUBLIC API
# =============================================================================

def build_system_prompt(state: dict, channel_id: str = None) -> str:
    """Return a system prompt describing the current campaign state."""
    title = state.get("campaign_title", "")
    realm = state.get("realm", "")
    location = state.get("location", "")
    plot = state.get("plot_hook", "")
    difficulty = state.get("difficulty", "normal")
    recent_actions = state.get("prompt_history", [])[-3:]
    party_comp = analyze_party_composition(state.get("players", []))
    actions_text = summarize_actions(recent_actions)

    diff_text = DIFFICULTY_GUIDE.get(difficulty, DIFFICULTY_GUIDE["normal"])

    # Build prioritised dynamic context
    dynamic_context = _build_context_sections(state, channel_id)

    # Build conditional tag instructions
    tag_instructions = _build_tag_instructions(state)

    system_prompt = f"""You are the Dungeon Master for a Discord-based D&D 5e campaign.

**Campaign:** {title} | **Realm:** {realm} | **Location:** {location}
**Plot:** {plot}
**Difficulty:** {difficulty} — {diff_text}
**Party:** {party_comp if party_comp else 'Unknown adventurers'}

**Recent Events:** {actions_text if actions_text else 'The adventure begins...'}

{dynamic_context}

**Response Style:**
1. Describe scene and NPC reactions vividly (2-3 sentences). Use [Voice: NPC Name] for dialogue.
2. Keep narration under 150 words. NPCs remember previous interactions.

{tag_instructions}
"""
    return system_prompt


def summarize_actions(actions):
    return "; ".join(a.get("content", "") for a in actions if a.get("role") == "user")


def analyze_party_composition(players):
    parts = []
    for pid in players:
        char = load_character(pid)
        if char:
            parts.append(f"{char.get('name')} (Lv {char.get('level',1)} {char.get('class','')})")
    return ", ".join(parts)
