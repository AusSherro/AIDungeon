"""
NPC Memory & Dialogue System for AI Dungeon Master.

This module provides:
- NPC relationship tracking (what they know, player reputation)
- Faction standing system with numerical values
- Quest giver state (offered quests, completed quests, available rewards)
- Shop/merchant persistent inventory
- Auto-voice assignment for newly introduced NPCs
- NPC mood/disposition based on interaction history

Phase 5 Implementation
"""

import os
import json
import random
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

# =============================================================================
# DATA CLASSES AND ENUMS
# =============================================================================

class Disposition(Enum):
    """NPC disposition toward the party."""
    HOSTILE = -2
    UNFRIENDLY = -1
    NEUTRAL = 0
    FRIENDLY = 1
    ALLIED = 2


class NPCRole(Enum):
    """NPC functional roles."""
    GENERIC = "generic"
    QUEST_GIVER = "quest_giver"
    MERCHANT = "merchant"
    INNKEEPER = "innkeeper"
    GUARD = "guard"
    NOBLE = "noble"
    VILLAIN = "villain"
    ALLY = "ally"
    INFORMANT = "informant"


@dataclass
class NPCMemory:
    """What an NPC knows and remembers about the party."""
    first_met: str = ""  # When/where first encountered
    last_seen: str = ""  # Last interaction timestamp
    knows_names: List[str] = field(default_factory=list)  # Player names known
    knows_facts: List[str] = field(default_factory=list)  # Facts NPC learned
    interaction_count: int = 0
    trust_level: int = 0  # -100 to 100
    owes_favor: bool = False
    owed_favor: bool = False
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NPCMemory':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class NPCDialogueState:
    """Tracks conversation state with an NPC."""
    current_topic: str = ""
    offered_quests: List[str] = field(default_factory=list)
    completed_quests: List[str] = field(default_factory=list)
    available_rewards: List[dict] = field(default_factory=list)
    secrets_revealed: List[str] = field(default_factory=list)
    rumors_shared: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NPCDialogueState':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ShopInventory:
    """Merchant inventory with stock tracking."""
    shop_name: str = ""
    shop_type: str = "general"  # general, weapons, armor, magic, potions, etc.
    gold_reserve: int = 100
    items: List[dict] = field(default_factory=list)  # [{name, price, quantity, description}]
    restock_interval: str = "weekly"  # daily, weekly, monthly, never
    last_restock: str = ""
    buy_rate: float = 0.5  # Multiplier for buying items from players
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ShopInventory':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class NPC:
    """Complete NPC data structure."""
    name: str
    description: str = ""
    role: str = "generic"
    race: str = "human"
    gender: str = "unknown"
    location: str = ""
    status: str = "alive"  # alive, dead, missing, unknown
    
    # Disposition and mood
    disposition: int = 0  # -2 to 2 (Hostile to Allied)
    current_mood: str = "neutral"  # happy, angry, sad, scared, suspicious, etc.
    personality_traits: List[str] = field(default_factory=list)
    
    # Memory and dialogue
    memory: NPCMemory = field(default_factory=NPCMemory)
    dialogue_state: NPCDialogueState = field(default_factory=NPCDialogueState)
    
    # Shop inventory (for merchants)
    shop: Optional[ShopInventory] = None
    
    # Faction affiliations
    factions: Dict[str, int] = field(default_factory=dict)  # {faction_name: standing}
    
    # Voice assignment
    voice_id: str = ""
    voice_archetype: str = ""
    
    # Timestamps
    created_at: str = ""
    updated_at: str = ""
    
    def to_dict(self) -> dict:
        data = {
            'name': self.name,
            'description': self.description,
            'role': self.role,
            'race': self.race,
            'gender': self.gender,
            'location': self.location,
            'status': self.status,
            'disposition': self.disposition,
            'current_mood': self.current_mood,
            'personality_traits': self.personality_traits,
            'memory': self.memory.to_dict() if self.memory else {},
            'dialogue_state': self.dialogue_state.to_dict() if self.dialogue_state else {},
            'shop': self.shop.to_dict() if self.shop else None,
            'factions': self.factions,
            'voice_id': self.voice_id,
            'voice_archetype': self.voice_archetype,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NPC':
        memory = NPCMemory.from_dict(data.get('memory', {}))
        dialogue_state = NPCDialogueState.from_dict(data.get('dialogue_state', {}))
        shop = ShopInventory.from_dict(data['shop']) if data.get('shop') else None
        
        return cls(
            name=data.get('name', 'Unknown'),
            description=data.get('description', ''),
            role=data.get('role', 'generic'),
            race=data.get('race', 'human'),
            gender=data.get('gender', 'unknown'),
            location=data.get('location', ''),
            status=data.get('status', 'alive'),
            disposition=data.get('disposition', 0),
            current_mood=data.get('current_mood', 'neutral'),
            personality_traits=data.get('personality_traits', []),
            memory=memory,
            dialogue_state=dialogue_state,
            shop=shop,
            factions=data.get('factions', {}),
            voice_id=data.get('voice_id', ''),
            voice_archetype=data.get('voice_archetype', ''),
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
        )


@dataclass
class Faction:
    """Faction data structure."""
    name: str
    description: str = ""
    alignment: str = "neutral"  # lawful good, chaotic evil, etc.
    headquarters: str = ""
    leader: str = ""
    
    # Party standing with this faction
    party_standing: int = 0  # -100 to 100
    standing_title: str = "Unknown"  # Based on standing level
    
    # Faction relationships with other factions
    allies: List[str] = field(default_factory=list)
    enemies: List[str] = field(default_factory=list)
    
    # Benefits at different standing levels
    benefits: Dict[int, List[str]] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Faction':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# =============================================================================
# FACTION STANDING TITLES
# =============================================================================

STANDING_TITLES = {
    -100: "Hunted Enemy",
    -75: "Sworn Enemy",
    -50: "Hostile",
    -25: "Unfriendly",
    -10: "Suspicious",
    0: "Unknown",
    10: "Known",
    25: "Friendly",
    50: "Trusted",
    75: "Honored",
    100: "Exalted Champion",
}


def get_standing_title(standing: int) -> str:
    """Get the title for a faction standing value."""
    for threshold in sorted(STANDING_TITLES.keys(), reverse=True):
        if standing >= threshold:
            return STANDING_TITLES[threshold]
    return "Unknown"


# =============================================================================
# NPC DETECTION PATTERNS
# =============================================================================

# Patterns to detect NPC introductions in AI narration
NPC_INTRODUCTION_PATTERNS = [
    r'\[Voice:\s*([^\]]+)\]',  # [Voice: Character Name]
    r'(?:introduces?\s+(?:himself|herself|themselves)\s+as\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
    r'"(?:I\s+am|My\s+name\s+is|Call\s+me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"',
    r'(?:a|an|the)\s+([a-z]+\s+)?(?:named|called)\s+([A-Z][a-z]+)',
]

# Role detection from description
ROLE_KEYWORDS = {
    NPCRole.MERCHANT: ['merchant', 'shopkeeper', 'vendor', 'trader', 'seller', 'peddler', 'store owner'],
    NPCRole.INNKEEPER: ['innkeeper', 'bartender', 'barkeep', 'tavern keeper', 'tavern owner'],
    NPCRole.QUEST_GIVER: ['lord', 'lady', 'mayor', 'elder', 'chieftain', 'king', 'queen', 'noble', 'advisor'],
    NPCRole.GUARD: ['guard', 'soldier', 'watchman', 'sentry', 'knight', 'warrior', 'captain'],
    NPCRole.NOBLE: ['noble', 'lord', 'lady', 'duke', 'duchess', 'baron', 'baroness', 'count', 'countess'],
    NPCRole.VILLAIN: ['villain', 'bandit', 'thief', 'assassin', 'cultist', 'necromancer', 'dark'],
    NPCRole.INFORMANT: ['informant', 'spy', 'scout', 'messenger', 'courier'],
}

# Race detection from description
RACE_KEYWORDS = {
    'dwarf': ['dwarf', 'dwarven', 'dwarfish'],
    'elf': ['elf', 'elven', 'elvish', 'high elf', 'wood elf', 'dark elf', 'drow'],
    'halfling': ['halfling', 'hobbit'],
    'human': ['human', 'man', 'woman'],
    'orc': ['orc', 'orcish', 'half-orc'],
    'gnome': ['gnome', 'gnomish'],
    'tiefling': ['tiefling', 'devil-touched'],
    'dragonborn': ['dragonborn', 'dragon-kin'],
    'goblin': ['goblin'],
    'kobold': ['kobold'],
}

# Gender detection from description
GENDER_KEYWORDS = {
    'male': ['he', 'him', 'his', 'man', 'male', 'gentleman', 'lord', 'king', 'prince', 'boy', 'father', 'son', 'husband'],
    'female': ['she', 'her', 'hers', 'woman', 'female', 'lady', 'queen', 'princess', 'girl', 'mother', 'daughter', 'wife'],
}

# Mood keywords
MOOD_KEYWORDS = {
    'happy': ['happy', 'cheerful', 'joyful', 'delighted', 'pleased', 'smiling', 'grinning'],
    'angry': ['angry', 'furious', 'enraged', 'livid', 'seething', 'scowling', 'glaring'],
    'sad': ['sad', 'sorrowful', 'melancholy', 'depressed', 'gloomy', 'tearful', 'weeping'],
    'scared': ['scared', 'frightened', 'terrified', 'nervous', 'anxious', 'trembling'],
    'suspicious': ['suspicious', 'wary', 'distrustful', 'skeptical', 'guarded'],
    'friendly': ['friendly', 'warm', 'welcoming', 'hospitable'],
    'hostile': ['hostile', 'aggressive', 'threatening', 'menacing'],
    'neutral': ['neutral', 'impassive', 'stoic', 'calm'],
}


# =============================================================================
# NPC DETECTION AND EXTRACTION
# =============================================================================

import re

def detect_npc_from_narration(narration: str) -> Optional[Dict[str, Any]]:
    """
    Detect and extract NPC information from AI narration.
    
    Args:
        narration: The AI-generated narration text
        
    Returns:
        Dict with NPC data if detected, None otherwise
    """
    # Check for voice tags first
    voice_match = re.search(r'\[Voice:\s*([^\]]+)\]', narration)
    if voice_match:
        voice_tag = voice_match.group(1).strip()
        
        # Parse voice tag for name and description
        if ':' in voice_tag:
            parts = voice_tag.split(':', 1)
            name = parts[0].strip()
            description = parts[1].strip()
        else:
            name = voice_tag
            description = ""
        
        # Extract additional info from narration context
        npc_data = {
            'name': name,
            'description': description,
            'role': detect_role(description + " " + narration),
            'race': detect_race(description + " " + narration),
            'gender': detect_gender(description + " " + narration, npc_name=name),
            'mood': detect_mood(narration),
        }
        
        return npc_data
    
    return None


def detect_role(text: str) -> str:
    """Detect NPC role from text."""
    text_lower = text.lower()
    for role, keywords in ROLE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return role.value
    return NPCRole.GENERIC.value


def detect_race(text: str) -> str:
    """Detect NPC race from text."""
    text_lower = text.lower()
    for race, keywords in RACE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return race
    return 'human'


def detect_gender(text: str, npc_name: str = "") -> str:
    """Detect NPC gender from text, scoped to sentences mentioning the NPC."""
    if npc_name:
        sentences = re.split(r'[.!?]', text)
        relevant = [s for s in sentences if npc_name.lower() in s.lower()]
        if not relevant:
            return 'unknown'
        text = " ".join(relevant)
    
    text_lower = text.lower()
    
    # Use word-boundary matching to avoid 'he' matching inside 'her'
    male_count = sum(len(re.findall(rf'\b{re.escape(kw)}\b', text_lower)) for kw in GENDER_KEYWORDS['male'])
    female_count = sum(len(re.findall(rf'\b{re.escape(kw)}\b', text_lower)) for kw in GENDER_KEYWORDS['female'])
    
    if female_count > male_count:
        return 'female'
    elif male_count > female_count:
        return 'male'
    return 'unknown'


def detect_mood(text: str) -> str:
    """Detect NPC mood from text."""
    text_lower = text.lower()
    for mood, keywords in MOOD_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return mood
    return 'neutral'


# =============================================================================
# NPC STORAGE AND MANAGEMENT
# =============================================================================

def get_npc_storage_path(channel_id: str) -> str:
    """Get the path to the NPC storage file for a channel."""
    state_dir = os.path.join(os.path.dirname(__file__), '..', 'state')
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, f'{channel_id}_npcs.json')


def load_npcs(channel_id: str) -> Dict[str, NPC]:
    """Load all NPCs for a channel."""
    path = get_npc_storage_path(channel_id)
    if not os.path.exists(path):
        return {}
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {name: NPC.from_dict(npc_data) for name, npc_data in data.items()}
    except Exception as e:
        logger.error(f"Failed to load NPCs: {e}")
        return {}


def save_npcs(channel_id: str, npcs: Dict[str, NPC]):
    """Save all NPCs for a channel."""
    path = get_npc_storage_path(channel_id)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            data = {name: npc.to_dict() for name, npc in npcs.items()}
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save NPCs: {e}")


def get_npc(channel_id: str, name: str) -> Optional[NPC]:
    """Get a specific NPC by name."""
    npcs = load_npcs(channel_id)
    # Case-insensitive lookup
    for npc_name, npc in npcs.items():
        if npc_name.lower() == name.lower():
            return npc
    return None


def create_npc(channel_id: str, name: str, description: str = "", **kwargs) -> NPC:
    """Create a new NPC or update existing one."""
    npcs = load_npcs(channel_id)
    
    now = datetime.now().isoformat()
    
    # Check if NPC exists (case-insensitive)
    existing_key = None
    for npc_name in npcs:
        if npc_name.lower() == name.lower():
            existing_key = npc_name
            break
    
    if existing_key:
        # Update existing NPC
        npc = npcs[existing_key]
        if description:
            npc.description = description
        for key, value in kwargs.items():
            if hasattr(npc, key):
                setattr(npc, key, value)
        npc.updated_at = now
    else:
        # Create new NPC
        npc = NPC(
            name=name,
            description=description,
            role=kwargs.get('role', detect_role(description)),
            race=kwargs.get('race', detect_race(description)),
            gender=kwargs.get('gender', detect_gender(description, npc_name=name)),
            location=kwargs.get('location', ''),
            created_at=now,
            updated_at=now,
            **{k: v for k, v in kwargs.items() if k not in ['role', 'race', 'gender', 'location']}
        )
        
        # Auto-assign voice
        npc.voice_id, npc.voice_archetype = assign_voice_to_npc(npc)
        
        npcs[name] = npc
    
    save_npcs(channel_id, npcs)
    return npc


def update_npc_disposition(channel_id: str, npc_name: str, change: int) -> Optional[NPC]:
    """Update an NPC's disposition toward the party."""
    npc = get_npc(channel_id, npc_name)
    if not npc:
        return None
    
    npc.disposition = max(-2, min(2, npc.disposition + change))
    npc.updated_at = datetime.now().isoformat()
    
    npcs = load_npcs(channel_id)
    npcs[npc.name] = npc
    save_npcs(channel_id, npcs)
    
    return npc


def update_npc_mood(channel_id: str, npc_name: str, mood: str) -> Optional[NPC]:
    """Update an NPC's current mood."""
    npc = get_npc(channel_id, npc_name)
    if not npc:
        return None
    
    npc.current_mood = mood
    npc.updated_at = datetime.now().isoformat()
    
    npcs = load_npcs(channel_id)
    npcs[npc.name] = npc
    save_npcs(channel_id, npcs)
    
    return npc


def record_npc_interaction(
    channel_id: str, 
    npc_name: str, 
    player_names: List[str], 
    facts_learned: List[str] = None
) -> Optional[NPC]:
    """Record an interaction with an NPC."""
    npc = get_npc(channel_id, npc_name)
    if not npc:
        return None
    
    now = datetime.now().isoformat()
    
    npc.memory.last_seen = now
    npc.memory.interaction_count += 1
    
    # Add player names the NPC now knows
    for name in player_names:
        if name not in npc.memory.knows_names:
            npc.memory.knows_names.append(name)
    
    # Add facts the NPC learned
    if facts_learned:
        npc.memory.knows_facts.extend(facts_learned)
        # Cap memory to prevent bloat
        from config import MAX_NPC_MEMORY_FACTS
        if len(npc.memory.knows_facts) > MAX_NPC_MEMORY_FACTS:
            npc.memory.knows_facts = npc.memory.knows_facts[-MAX_NPC_MEMORY_FACTS:]
    
    npc.updated_at = now
    
    npcs = load_npcs(channel_id)
    npcs[npc.name] = npc
    save_npcs(channel_id, npcs)
    
    return npc


def get_npc_context_for_ai(channel_id: str, npc_name: str) -> str:
    """
    Build context about an NPC for the AI to use.
    
    Returns a formatted string describing the NPC's memory,
    disposition, and relevant history.
    """
    npc = get_npc(channel_id, npc_name)
    if not npc:
        return ""
    
    lines = [f"**NPC: {npc.name}**"]
    
    if npc.description:
        lines.append(f"Description: {npc.description}")
    
    lines.append(f"Role: {npc.role.replace('_', ' ').title()}")
    lines.append(f"Race: {npc.race.title()}")
    
    # Disposition
    disp_names = {-2: "Hostile", -1: "Unfriendly", 0: "Neutral", 1: "Friendly", 2: "Allied"}
    lines.append(f"Disposition: {disp_names.get(npc.disposition, 'Neutral')}")
    lines.append(f"Current Mood: {npc.current_mood.title()}")
    
    # Memory
    if npc.memory.knows_names:
        lines.append(f"Knows Players: {', '.join(npc.memory.knows_names)}")
    
    if npc.memory.knows_facts:
        lines.append(f"Knows: {'; '.join(npc.memory.knows_facts[-5:])}")  # Last 5 facts
    
    if npc.memory.interaction_count > 0:
        lines.append(f"Previous Interactions: {npc.memory.interaction_count}")
    
    # Faction affiliations
    if npc.factions:
        faction_info = [f"{f}: {s}" for f, s in npc.factions.items()]
        lines.append(f"Faction Affiliations: {', '.join(faction_info)}")
    
    # Quest state
    if npc.dialogue_state.offered_quests:
        lines.append(f"Offered Quests: {', '.join(npc.dialogue_state.offered_quests)}")
    
    if npc.dialogue_state.completed_quests:
        lines.append(f"Completed Quests: {', '.join(npc.dialogue_state.completed_quests)}")
    
    return "\n".join(lines)


# =============================================================================
# FACTION MANAGEMENT
# =============================================================================

def get_faction_storage_path(channel_id: str) -> str:
    """Get the path to the faction storage file for a channel."""
    state_dir = os.path.join(os.path.dirname(__file__), '..', 'state')
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, f'{channel_id}_factions.json')


def load_factions(channel_id: str) -> Dict[str, Faction]:
    """Load all factions for a channel."""
    path = get_faction_storage_path(channel_id)
    if not os.path.exists(path):
        return {}
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {name: Faction.from_dict(faction_data) for name, faction_data in data.items()}
    except Exception as e:
        logger.error(f"Failed to load factions: {e}")
        return {}


def save_factions(channel_id: str, factions: Dict[str, Faction]):
    """Save all factions for a channel."""
    path = get_faction_storage_path(channel_id)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            data = {name: faction.to_dict() for name, faction in factions.items()}
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save factions: {e}")


def get_faction(channel_id: str, name: str) -> Optional[Faction]:
    """Get a specific faction by name."""
    factions = load_factions(channel_id)
    for faction_name, faction in factions.items():
        if faction_name.lower() == name.lower():
            return faction
    return None


def create_faction(channel_id: str, name: str, description: str = "", **kwargs) -> Faction:
    """Create a new faction."""
    factions = load_factions(channel_id)
    
    faction = Faction(
        name=name,
        description=description,
        **kwargs
    )
    faction.standing_title = get_standing_title(faction.party_standing)
    
    factions[name] = faction
    save_factions(channel_id, factions)
    
    return faction


def modify_faction_standing(channel_id: str, faction_name: str, change: int, reason: str = "") -> Optional[Tuple[Faction, str]]:
    """
    Modify the party's standing with a faction.
    
    Args:
        channel_id: Discord channel ID
        faction_name: Name of the faction
        change: Amount to change standing (+/-)
        reason: Optional reason for the change
        
    Returns:
        Tuple of (updated faction, notification message) or None
    """
    faction = get_faction(channel_id, faction_name)
    if not faction:
        return None
    
    old_standing = faction.party_standing
    old_title = faction.standing_title
    
    faction.party_standing = max(-100, min(100, faction.party_standing + change))
    faction.standing_title = get_standing_title(faction.party_standing)
    
    factions = load_factions(channel_id)
    factions[faction.name] = faction
    save_factions(channel_id, factions)
    
    # Generate notification
    direction = "increased" if change > 0 else "decreased"
    message = f"Your standing with **{faction.name}** has {direction} by {abs(change)}."
    
    if old_title != faction.standing_title:
        message += f"\nYou are now **{faction.standing_title}** with {faction.name}!"
    
    if reason:
        message = f"{reason}\n{message}"
    
    return (faction, message)


def get_faction_context_for_ai(channel_id: str) -> str:
    """Build faction context for AI prompts."""
    factions = load_factions(channel_id)
    if not factions:
        return ""
    
    lines = ["**Faction Standings:**"]
    for name, faction in factions.items():
        lines.append(f"- {name}: {faction.standing_title} ({faction.party_standing})")
        if faction.description:
            lines.append(f"  {faction.description}")
    
    return "\n".join(lines)


# =============================================================================
# SHOP/MERCHANT SYSTEM
# =============================================================================

# Default shop inventories by type
DEFAULT_SHOP_INVENTORIES = {
    'general': [
        {'name': 'Torch', 'price': 1, 'quantity': 20, 'description': 'Provides light for 1 hour'},
        {'name': 'Rope (50 ft)', 'price': 1, 'quantity': 10, 'description': 'Hemp rope'},
        {'name': 'Rations (1 day)', 'price': 5, 'quantity': 50, 'description': 'Trail rations'},
        {'name': 'Waterskin', 'price': 2, 'quantity': 15, 'description': 'Holds water'},
        {'name': 'Backpack', 'price': 2, 'quantity': 8, 'description': 'Carries gear'},
        {'name': 'Bedroll', 'price': 1, 'quantity': 10, 'description': 'For camping'},
        {'name': 'Tinderbox', 'price': 5, 'quantity': 12, 'description': 'Start fires'},
    ],
    'weapons': [
        {'name': 'Dagger', 'price': 2, 'quantity': 10, 'description': '1d4 piercing'},
        {'name': 'Shortsword', 'price': 10, 'quantity': 5, 'description': '1d6 piercing'},
        {'name': 'Longsword', 'price': 15, 'quantity': 4, 'description': '1d8 slashing'},
        {'name': 'Longbow', 'price': 50, 'quantity': 3, 'description': '1d8 piercing, range 150/600'},
        {'name': 'Arrows (20)', 'price': 1, 'quantity': 30, 'description': 'Ammunition'},
        {'name': 'Handaxe', 'price': 5, 'quantity': 8, 'description': '1d6 slashing, thrown'},
        {'name': 'Battleaxe', 'price': 10, 'quantity': 3, 'description': '1d8 slashing'},
    ],
    'armor': [
        {'name': 'Leather Armor', 'price': 10, 'quantity': 5, 'description': 'AC 11 + DEX'},
        {'name': 'Studded Leather', 'price': 45, 'quantity': 3, 'description': 'AC 12 + DEX'},
        {'name': 'Chain Shirt', 'price': 50, 'quantity': 2, 'description': 'AC 13 + DEX (max 2)'},
        {'name': 'Scale Mail', 'price': 50, 'quantity': 2, 'description': 'AC 14 + DEX (max 2)'},
        {'name': 'Chain Mail', 'price': 75, 'quantity': 2, 'description': 'AC 16'},
        {'name': 'Shield', 'price': 10, 'quantity': 6, 'description': '+2 AC'},
    ],
    'potions': [
        {'name': 'Potion of Healing', 'price': 50, 'quantity': 8, 'description': 'Heals 2d4+2 HP'},
        {'name': 'Potion of Greater Healing', 'price': 150, 'quantity': 3, 'description': 'Heals 4d4+4 HP'},
        {'name': 'Antitoxin', 'price': 50, 'quantity': 5, 'description': 'Advantage on poison saves'},
        {'name': 'Potion of Resistance', 'price': 100, 'quantity': 2, 'description': 'Resistance to one damage type'},
    ],
    'magic': [
        {'name': 'Scroll of Identify', 'price': 75, 'quantity': 3, 'description': '1st level spell scroll'},
        {'name': 'Scroll of Detect Magic', 'price': 75, 'quantity': 3, 'description': '1st level spell scroll'},
        {'name': 'Scroll of Magic Missile', 'price': 75, 'quantity': 2, 'description': '1st level spell scroll'},
        {'name': 'Scroll of Shield', 'price': 75, 'quantity': 2, 'description': '1st level spell scroll'},
        {'name': 'Component Pouch', 'price': 25, 'quantity': 4, 'description': 'Spell components'},
        {'name': 'Arcane Focus', 'price': 10, 'quantity': 3, 'description': 'Spellcasting focus'},
    ],
}


def create_merchant_shop(
    channel_id: str, 
    npc_name: str, 
    shop_name: str = "", 
    shop_type: str = "general",
    gold_reserve: int = 200
) -> Optional[NPC]:
    """
    Create or update a merchant NPC with shop inventory.
    
    Args:
        channel_id: Discord channel ID
        npc_name: Name of the merchant NPC
        shop_name: Name of the shop
        shop_type: Type of shop (general, weapons, armor, potions, magic)
        gold_reserve: Amount of gold the shop has for buying
        
    Returns:
        Updated NPC or None
    """
    npc = get_npc(channel_id, npc_name)
    if not npc:
        npc = create_npc(channel_id, npc_name, role='merchant')
    
    # Get default inventory for shop type
    items = DEFAULT_SHOP_INVENTORIES.get(shop_type, DEFAULT_SHOP_INVENTORIES['general']).copy()
    
    npc.shop = ShopInventory(
        shop_name=shop_name or f"{npc_name}'s Shop",
        shop_type=shop_type,
        gold_reserve=gold_reserve,
        items=[dict(item) for item in items],  # Deep copy
        last_restock=datetime.now().isoformat(),
    )
    npc.role = 'merchant'
    npc.updated_at = datetime.now().isoformat()
    
    npcs = load_npcs(channel_id)
    npcs[npc.name] = npc
    save_npcs(channel_id, npcs)
    
    return npc


def get_shop_inventory(channel_id: str, npc_name: str) -> Optional[List[dict]]:
    """Get a merchant's current inventory."""
    npc = get_npc(channel_id, npc_name)
    if not npc or not npc.shop:
        return None
    return npc.shop.items


def buy_from_shop(
    channel_id: str, 
    npc_name: str, 
    item_name: str, 
    quantity: int = 1
) -> Optional[Tuple[dict, int]]:
    """
    Buy an item from a shop.
    
    Returns:
        Tuple of (item dict, total cost) or None if not available
    """
    npc = get_npc(channel_id, npc_name)
    if not npc or not npc.shop:
        return None
    
    for item in npc.shop.items:
        if item['name'].lower() == item_name.lower():
            if item['quantity'] >= quantity:
                item['quantity'] -= quantity
                total_cost = int(item['price'] * quantity * npc.shop.buy_rate)
                npc.shop.gold_reserve += total_cost
                
                # Save changes
                npcs = load_npcs(channel_id)
                npcs[npc.name] = npc
                save_npcs(channel_id, npcs)
                
                return (item, total_cost)
    
    return None


def sell_to_shop(
    channel_id: str, 
    npc_name: str, 
    item_name: str, 
    base_price: int, 
    quantity: int = 1
) -> Optional[int]:
    """
    Sell an item to a shop.
    
    Returns:
        Amount of gold received or None if shop can't afford it
    """
    npc = get_npc(channel_id, npc_name)
    if not npc or not npc.shop:
        return None
    
    sell_price = int(base_price * npc.shop.buy_rate * quantity)
    
    if npc.shop.gold_reserve >= sell_price:
        npc.shop.gold_reserve -= sell_price
        
        # Add item to shop inventory or increase quantity
        item_found = False
        for item in npc.shop.items:
            if item['name'].lower() == item_name.lower():
                item['quantity'] += quantity
                item_found = True
                break
        
        if not item_found:
            npc.shop.items.append({
                'name': item_name,
                'price': base_price,
                'quantity': quantity,
                'description': 'Player-sold item'
            })
        
        # Save changes
        npcs = load_npcs(channel_id)
        npcs[npc.name] = npc
        save_npcs(channel_id, npcs)
        
        return sell_price
    
    return None


def format_shop_inventory(npc: NPC) -> str:
    """Format shop inventory for display."""
    if not npc or not npc.shop:
        return "This NPC doesn't have a shop."
    
    lines = [
        f"🏪 **{npc.shop.shop_name}** ({npc.shop.shop_type.title()} Shop)",
        f"💰 Shop Gold: {npc.shop.gold_reserve} gp",
        f"📊 Buy Rate: {int(npc.shop.buy_rate * 100)}% of base price",
        "",
        "**Available Items:**"
    ]
    
    for item in npc.shop.items:
        if item['quantity'] > 0:
            lines.append(f"• {item['name']} - {item['price']} gp (x{item['quantity']})")
            if item.get('description'):
                lines.append(f"  *{item['description']}*")
    
    if not any(item['quantity'] > 0 for item in npc.shop.items):
        lines.append("*(Shop is currently out of stock)*")
    
    return "\n".join(lines)


# =============================================================================
# VOICE ASSIGNMENT
# =============================================================================

def assign_voice_to_npc(npc: NPC) -> Tuple[str, str]:
    """
    Assign a voice to an NPC based on their characteristics.
    
    Args:
        npc: NPC object
        
    Returns:
        Tuple of (voice_id, archetype)
    """
    try:
        from utils.voice_map import get_voice_for_npc, NPC_VOICE_ARCHETYPES
        
        # Build description string for voice matching
        description_parts = [npc.description, npc.race, npc.gender, npc.role]
        if npc.personality_traits:
            description_parts.extend(npc.personality_traits)
        
        full_description = " ".join(filter(None, description_parts))
        
        voice_id = get_voice_for_npc(full_description, npc.name)
        
        # Determine archetype
        archetype = 'narrator'
        for arch, voices in NPC_VOICE_ARCHETYPES.items():
            if voice_id in voices:
                archetype = arch
                break
        
        return (voice_id, archetype)
    except Exception:
        return (None, 'narrator')


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def list_all_npcs(channel_id: str) -> List[NPC]:
    """List all NPCs for a channel."""
    npcs = load_npcs(channel_id)
    return list(npcs.values())


def list_all_factions(channel_id: str) -> List[Faction]:
    """List all factions for a channel."""
    factions = load_factions(channel_id)
    return list(factions.values())


def get_nearby_npcs(channel_id: str, location: str) -> List[NPC]:
    """Get NPCs in a specific location."""
    npcs = load_npcs(channel_id)
    return [npc for npc in npcs.values() if npc.location.lower() == location.lower()]


def format_npc_summary(npc: NPC) -> str:
    """Format an NPC for display."""
    disp_names = {-2: "Hostile", -1: "Unfriendly", 0: "Neutral", 1: "Friendly", 2: "Allied"}
    
    lines = [
        f"**{npc.name}** ({npc.race.title()} {npc.role.replace('_', ' ').title()})",
    ]
    
    if npc.description:
        lines.append(f"*{npc.description}*")
    
    lines.append(f"📍 {npc.location or 'Unknown location'}")
    lines.append(f"💭 {disp_names.get(npc.disposition, 'Neutral')} • Mood: {npc.current_mood.title()}")
    
    if npc.memory.interaction_count > 0:
        lines.append(f"🤝 {npc.memory.interaction_count} interaction(s)")
    
    if npc.shop:
        lines.append(f"🏪 Runs {npc.shop.shop_name}")
    
    return "\n".join(lines)


def format_faction_summary(faction: Faction) -> str:
    """Format a faction for display."""
    lines = [
        f"**{faction.name}**",
    ]
    
    if faction.description:
        lines.append(f"*{faction.description}*")
    
    lines.append(f"📊 Standing: {faction.standing_title} ({faction.party_standing:+d})")
    
    if faction.leader:
        lines.append(f"👑 Leader: {faction.leader}")
    
    if faction.headquarters:
        lines.append(f"🏰 HQ: {faction.headquarters}")
    
    if faction.allies:
        lines.append(f"🤝 Allies: {', '.join(faction.allies)}")
    
    if faction.enemies:
        lines.append(f"⚔️ Enemies: {', '.join(faction.enemies)}")
    
    return "\n".join(lines)


def process_npc_from_narration(channel_id: str, narration: str, location: str = "") -> Optional[NPC]:
    """
    Process AI narration to detect and register new NPCs.
    
    Args:
        channel_id: Discord channel ID
        narration: AI-generated narration text
        location: Current location in the campaign
        
    Returns:
        NPC if one was detected and created/updated, None otherwise
    """
    npc_data = detect_npc_from_narration(narration)
    if not npc_data:
        return None
    
    # Check if this is a new NPC or existing one
    existing = get_npc(channel_id, npc_data['name'])
    
    if existing:
        # Update mood if detected
        if npc_data.get('mood') and npc_data['mood'] != 'neutral':
            update_npc_mood(channel_id, npc_data['name'], npc_data['mood'])
        return existing
    
    # Create new NPC
    npc = create_npc(
        channel_id,
        name=npc_data['name'],
        description=npc_data.get('description', ''),
        role=npc_data.get('role', 'generic'),
        race=npc_data.get('race', 'human'),
        gender=npc_data.get('gender', 'unknown'),
        location=location,
        current_mood=npc_data.get('mood', 'neutral'),
    )
    
    return npc
