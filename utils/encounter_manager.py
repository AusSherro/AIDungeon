"""
Encounter Manager for AI Dungeon Master
Handles random encounters, travel, and non-combat events.
"""

import os
import json
import random
import math
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime
from threading import Lock


# ============================================================================
# ENUMS
# ============================================================================

class TerrainType(Enum):
    """Terrain types that affect encounter tables and travel."""
    ROAD = "road"
    FOREST = "forest"
    PLAINS = "plains"
    MOUNTAINS = "mountains"
    HILLS = "hills"
    SWAMP = "swamp"
    DESERT = "desert"
    ARCTIC = "arctic"
    COASTAL = "coastal"
    URBAN = "urban"
    UNDERGROUND = "underground"
    UNDERDARK = "underdark"
    JUNGLE = "jungle"
    RUINS = "ruins"


class EncounterDifficulty(Enum):
    """Encounter difficulty levels per DMG guidelines."""
    TRIVIAL = "trivial"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    DEADLY = "deadly"


class TravelPace(Enum):
    """Travel pace affecting speed and stealth."""
    SLOW = "slow"       # 2 miles/hour, can stealth
    NORMAL = "normal"   # 3 miles/hour
    FAST = "fast"       # 4 miles/hour, -5 passive perception


class EventType(Enum):
    """Types of random events."""
    COMBAT = "combat"
    SOCIAL = "social"
    DISCOVERY = "discovery"
    HAZARD = "hazard"
    WEATHER = "weather"
    REST_SITE = "rest_site"
    NOTHING = "nothing"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Monster:
    """Monster data for encounters."""
    name: str
    cr: float
    xp: int
    hp: int
    ac: int
    type: str = "beast"
    size: str = "medium"
    attacks: List[Dict] = field(default_factory=list)
    abilities: List[str] = field(default_factory=list)
    traits: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Monster':
        return cls(**data)


@dataclass
class Encounter:
    """A generated encounter."""
    name: str
    event_type: str
    difficulty: str
    monsters: List[Dict] = field(default_factory=list)
    description: str = ""
    xp_reward: int = 0
    loot_tier: str = "common"
    terrain: str = "plains"
    special_conditions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Encounter':
        return cls(**data)


@dataclass
class TravelState:
    """Tracks travel progress between locations."""
    origin: str = ""
    destination: str = ""
    terrain: str = "road"
    total_distance_miles: float = 0
    traveled_miles: float = 0
    pace: str = "normal"
    hours_traveled_today: float = 0
    days_traveled: int = 0
    encounters_today: int = 0
    last_encounter_check: str = ""
    is_resting: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TravelState':
        return cls(**data)


# ============================================================================
# CONSTANTS - XP THRESHOLDS (DMG pg. 82)
# ============================================================================

# XP thresholds by character level for difficulty calculation
XP_THRESHOLDS = {
    1:  {"easy": 25,   "medium": 50,   "hard": 75,    "deadly": 100},
    2:  {"easy": 50,   "medium": 100,  "hard": 150,   "deadly": 200},
    3:  {"easy": 75,   "medium": 150,  "hard": 225,   "deadly": 400},
    4:  {"easy": 125,  "medium": 250,  "hard": 375,   "deadly": 500},
    5:  {"easy": 250,  "medium": 500,  "hard": 750,   "deadly": 1100},
    6:  {"easy": 300,  "medium": 600,  "hard": 900,   "deadly": 1400},
    7:  {"easy": 350,  "medium": 750,  "hard": 1100,  "deadly": 1700},
    8:  {"easy": 450,  "medium": 900,  "hard": 1400,  "deadly": 2100},
    9:  {"easy": 550,  "medium": 1100, "hard": 1600,  "deadly": 2400},
    10: {"easy": 600,  "medium": 1200, "hard": 1900,  "deadly": 2800},
    11: {"easy": 800,  "medium": 1600, "hard": 2400,  "deadly": 3600},
    12: {"easy": 1000, "medium": 2000, "hard": 3000,  "deadly": 4500},
    13: {"easy": 1100, "medium": 2200, "hard": 3400,  "deadly": 5100},
    14: {"easy": 1250, "medium": 2500, "hard": 3800,  "deadly": 5700},
    15: {"easy": 1400, "medium": 2800, "hard": 4300,  "deadly": 6400},
    16: {"easy": 1600, "medium": 3200, "hard": 4800,  "deadly": 7200},
    17: {"easy": 2000, "medium": 3900, "hard": 5900,  "deadly": 8800},
    18: {"easy": 2100, "medium": 4200, "hard": 6300,  "deadly": 9500},
    19: {"easy": 2400, "medium": 4900, "hard": 7300,  "deadly": 10900},
    20: {"easy": 2800, "medium": 5700, "hard": 8500,  "deadly": 12700},
}

# CR to XP conversion (DMG pg. 275)
CR_TO_XP = {
    0: 10, 0.125: 25, 0.25: 50, 0.5: 100,
    1: 200, 2: 450, 3: 700, 4: 1100, 5: 1800,
    6: 2300, 7: 2900, 8: 3900, 9: 5000, 10: 5900,
    11: 7200, 12: 8400, 13: 10000, 14: 11500, 15: 13000,
    16: 15000, 17: 18000, 18: 20000, 19: 22000, 20: 25000,
    21: 33000, 22: 41000, 23: 50000, 24: 62000, 25: 75000,
    26: 90000, 27: 105000, 28: 120000, 29: 135000, 30: 155000,
}

# Encounter multipliers based on number of monsters (DMG pg. 82)
ENCOUNTER_MULTIPLIERS = {
    1: 1.0,
    2: 1.5,
    (3, 6): 2.0,
    (7, 10): 2.5,
    (11, 14): 3.0,
    15: 4.0,  # 15+
}

# Travel speeds
TRAVEL_SPEEDS = {
    "slow": {"miles_per_hour": 2, "miles_per_day": 18, "stealth_possible": True, "perception_mod": 0},
    "normal": {"miles_per_hour": 3, "miles_per_day": 24, "stealth_possible": False, "perception_mod": 0},
    "fast": {"miles_per_hour": 4, "miles_per_day": 30, "stealth_possible": False, "perception_mod": -5},
}

# Terrain modifiers for travel
TERRAIN_MODIFIERS = {
    "road": {"speed_mult": 1.0, "encounter_chance": 0.10},
    "plains": {"speed_mult": 1.0, "encounter_chance": 0.15},
    "forest": {"speed_mult": 0.5, "encounter_chance": 0.20},
    "hills": {"speed_mult": 0.5, "encounter_chance": 0.15},
    "mountains": {"speed_mult": 0.5, "encounter_chance": 0.20},
    "swamp": {"speed_mult": 0.5, "encounter_chance": 0.25},
    "desert": {"speed_mult": 0.5, "encounter_chance": 0.10},
    "arctic": {"speed_mult": 0.5, "encounter_chance": 0.15},
    "coastal": {"speed_mult": 1.0, "encounter_chance": 0.15},
    "urban": {"speed_mult": 1.0, "encounter_chance": 0.10},
    "underground": {"speed_mult": 0.5, "encounter_chance": 0.30},
    "underdark": {"speed_mult": 0.5, "encounter_chance": 0.35},
    "jungle": {"speed_mult": 0.25, "encounter_chance": 0.30},
    "ruins": {"speed_mult": 0.5, "encounter_chance": 0.25},
}


# ============================================================================
# MONSTER DATABASE
# ============================================================================

# Common monsters by CR for random encounter generation
MONSTERS_BY_CR = {
    0: [
        {"name": "Commoner", "hp": 4, "ac": 10, "type": "humanoid", "size": "medium"},
        {"name": "Rat", "hp": 1, "ac": 10, "type": "beast", "size": "tiny"},
        {"name": "Raven", "hp": 1, "ac": 12, "type": "beast", "size": "tiny"},
        {"name": "Frog", "hp": 1, "ac": 11, "type": "beast", "size": "tiny"},
    ],
    0.125: [
        {"name": "Bandit", "hp": 11, "ac": 12, "type": "humanoid", "size": "medium"},
        {"name": "Cultist", "hp": 9, "ac": 12, "type": "humanoid", "size": "medium"},
        {"name": "Giant Rat", "hp": 7, "ac": 12, "type": "beast", "size": "small"},
        {"name": "Kobold", "hp": 5, "ac": 12, "type": "humanoid", "size": "small"},
        {"name": "Stirge", "hp": 2, "ac": 14, "type": "beast", "size": "tiny"},
        {"name": "Tribal Warrior", "hp": 11, "ac": 12, "type": "humanoid", "size": "medium"},
    ],
    0.25: [
        {"name": "Acolyte", "hp": 9, "ac": 10, "type": "humanoid", "size": "medium"},
        {"name": "Goblin", "hp": 7, "ac": 15, "type": "humanoid", "size": "small"},
        {"name": "Skeleton", "hp": 13, "ac": 13, "type": "undead", "size": "medium"},
        {"name": "Wolf", "hp": 11, "ac": 13, "type": "beast", "size": "medium"},
        {"name": "Zombie", "hp": 22, "ac": 8, "type": "undead", "size": "medium"},
        {"name": "Giant Wolf Spider", "hp": 11, "ac": 13, "type": "beast", "size": "medium"},
    ],
    0.5: [
        {"name": "Orc", "hp": 15, "ac": 13, "type": "humanoid", "size": "medium"},
        {"name": "Hobgoblin", "hp": 11, "ac": 18, "type": "humanoid", "size": "medium"},
        {"name": "Scout", "hp": 16, "ac": 13, "type": "humanoid", "size": "medium"},
        {"name": "Shadow", "hp": 16, "ac": 12, "type": "undead", "size": "medium"},
        {"name": "Worg", "hp": 26, "ac": 13, "type": "monstrosity", "size": "large"},
        {"name": "Black Bear", "hp": 19, "ac": 11, "type": "beast", "size": "medium"},
    ],
    1: [
        {"name": "Bugbear", "hp": 27, "ac": 16, "type": "humanoid", "size": "medium"},
        {"name": "Dire Wolf", "hp": 37, "ac": 14, "type": "beast", "size": "large"},
        {"name": "Ghoul", "hp": 22, "ac": 12, "type": "undead", "size": "medium"},
        {"name": "Giant Spider", "hp": 26, "ac": 14, "type": "beast", "size": "large"},
        {"name": "Goblin Boss", "hp": 21, "ac": 17, "type": "humanoid", "size": "small"},
        {"name": "Specter", "hp": 22, "ac": 12, "type": "undead", "size": "medium"},
        {"name": "Spy", "hp": 27, "ac": 12, "type": "humanoid", "size": "medium"},
    ],
    2: [
        {"name": "Bandit Captain", "hp": 65, "ac": 15, "type": "humanoid", "size": "medium"},
        {"name": "Berserker", "hp": 67, "ac": 13, "type": "humanoid", "size": "medium"},
        {"name": "Ghast", "hp": 36, "ac": 13, "type": "undead", "size": "medium"},
        {"name": "Ogre", "hp": 59, "ac": 11, "type": "giant", "size": "large"},
        {"name": "Priest", "hp": 27, "ac": 13, "type": "humanoid", "size": "medium"},
        {"name": "Werewolf", "hp": 58, "ac": 11, "type": "humanoid", "size": "medium"},
    ],
    3: [
        {"name": "Knight", "hp": 52, "ac": 18, "type": "humanoid", "size": "medium"},
        {"name": "Manticore", "hp": 68, "ac": 14, "type": "monstrosity", "size": "large"},
        {"name": "Minotaur", "hp": 76, "ac": 14, "type": "monstrosity", "size": "large"},
        {"name": "Mummy", "hp": 58, "ac": 11, "type": "undead", "size": "medium"},
        {"name": "Owlbear", "hp": 59, "ac": 13, "type": "monstrosity", "size": "large"},
        {"name": "Veteran", "hp": 58, "ac": 17, "type": "humanoid", "size": "medium"},
    ],
    4: [
        {"name": "Banshee", "hp": 58, "ac": 12, "type": "undead", "size": "medium"},
        {"name": "Ettin", "hp": 85, "ac": 12, "type": "giant", "size": "large"},
        {"name": "Ghost", "hp": 45, "ac": 11, "type": "undead", "size": "medium"},
        {"name": "Wereboar", "hp": 78, "ac": 10, "type": "humanoid", "size": "medium"},
        {"name": "Flameskull", "hp": 40, "ac": 13, "type": "undead", "size": "tiny"},
    ],
    5: [
        {"name": "Bulette", "hp": 94, "ac": 17, "type": "monstrosity", "size": "large"},
        {"name": "Gladiator", "hp": 112, "ac": 16, "type": "humanoid", "size": "medium"},
        {"name": "Hill Giant", "hp": 105, "ac": 13, "type": "giant", "size": "huge"},
        {"name": "Troll", "hp": 84, "ac": 15, "type": "giant", "size": "large"},
        {"name": "Wraith", "hp": 67, "ac": 13, "type": "undead", "size": "medium"},
    ],
    6: [
        {"name": "Chimera", "hp": 114, "ac": 14, "type": "monstrosity", "size": "large"},
        {"name": "Cyclops", "hp": 138, "ac": 14, "type": "giant", "size": "huge"},
        {"name": "Wyvern", "hp": 110, "ac": 13, "type": "dragon", "size": "large"},
        {"name": "Young White Dragon", "hp": 133, "ac": 17, "type": "dragon", "size": "large"},
    ],
    7: [
        {"name": "Giant Ape", "hp": 157, "ac": 12, "type": "beast", "size": "huge"},
        {"name": "Oni", "hp": 110, "ac": 16, "type": "giant", "size": "large"},
        {"name": "Shield Guardian", "hp": 142, "ac": 17, "type": "construct", "size": "large"},
        {"name": "Young Black Dragon", "hp": 127, "ac": 18, "type": "dragon", "size": "large"},
    ],
    8: [
        {"name": "Assassin", "hp": 78, "ac": 15, "type": "humanoid", "size": "medium"},
        {"name": "Frost Giant", "hp": 138, "ac": 15, "type": "giant", "size": "huge"},
        {"name": "Hydra", "hp": 172, "ac": 15, "type": "monstrosity", "size": "huge"},
        {"name": "Young Green Dragon", "hp": 136, "ac": 18, "type": "dragon", "size": "large"},
    ],
    9: [
        {"name": "Bone Devil", "hp": 142, "ac": 19, "type": "fiend", "size": "large"},
        {"name": "Clay Golem", "hp": 133, "ac": 14, "type": "construct", "size": "large"},
        {"name": "Fire Giant", "hp": 162, "ac": 18, "type": "giant", "size": "huge"},
        {"name": "Young Blue Dragon", "hp": 152, "ac": 18, "type": "dragon", "size": "large"},
    ],
    10: [
        {"name": "Aboleth", "hp": 135, "ac": 17, "type": "aberration", "size": "large"},
        {"name": "Guardian Naga", "hp": 127, "ac": 18, "type": "monstrosity", "size": "large"},
        {"name": "Stone Golem", "hp": 178, "ac": 17, "type": "construct", "size": "large"},
        {"name": "Young Red Dragon", "hp": 178, "ac": 18, "type": "dragon", "size": "large"},
    ],
}

# Terrain-specific encounter tables
TERRAIN_ENCOUNTERS = {
    "road": {
        "combat": ["Bandits", "Wolves", "Goblins", "Hobgoblins", "Patrol"],
        "social": ["Merchant caravan", "Traveling priest", "Wandering bard", "Farmer with cart", "Pilgrim group"],
        "discovery": ["Abandoned wagon", "Milestone marker", "Roadside shrine", "Old campsite", "Wanted poster"],
    },
    "forest": {
        "combat": ["Wolves", "Giant Spiders", "Bandits", "Owlbear", "Goblins", "Ettercaps", "Trolls"],
        "social": ["Wood elf patrol", "Druid circle", "Hermit", "Logging camp", "Ranger"],
        "discovery": ["Ancient tree", "Hidden glade", "Abandoned cabin", "Fairy ring", "Bear cave"],
    },
    "plains": {
        "combat": ["Orcs", "Gnolls", "Lions", "Giant Eagles", "Centaurs"],
        "social": ["Nomad tribe", "Shepherd", "Traveling circus", "Military patrol"],
        "discovery": ["Standing stones", "Burial mound", "Abandoned farm", "Old battlefield"],
    },
    "mountains": {
        "combat": ["Giants", "Harpies", "Griffons", "Wyverns", "Stone Giants", "Trolls"],
        "social": ["Dwarf miners", "Mountain hermit", "Goliath tribe"],
        "discovery": ["Mine entrance", "Dragon lair entrance", "Mountain shrine", "Hidden cave"],
    },
    "hills": {
        "combat": ["Hobgoblins", "Ogres", "Hill Giants", "Worgs", "Gnolls"],
        "social": ["Halfling village", "Shepherd", "Prospectors"],
        "discovery": ["Burial cairn", "Hidden valley", "Old watchtower"],
    },
    "swamp": {
        "combat": ["Crocodiles", "Will-o'-Wisps", "Shambling Mound", "Lizardfolk", "Black Dragon"],
        "social": ["Lizardfolk tribe", "Hermit witch", "Escaped prisoners"],
        "discovery": ["Sunken ruins", "Witch's hut", "Giant frog", "Quicksand"],
    },
    "desert": {
        "combat": ["Giant Scorpions", "Mummies", "Gnolls", "Blue Dragon", "Sandworm"],
        "social": ["Desert nomads", "Merchant caravan", "Oasis settlement"],
        "discovery": ["Ancient ruins", "Hidden oasis", "Buried treasure", "Mirage"],
    },
    "arctic": {
        "combat": ["Winter Wolves", "Frost Giants", "White Dragon", "Yeti", "Ice Mephits"],
        "social": ["Goliath hunters", "Ice fishers", "Stranded travelers"],
        "discovery": ["Ice cave", "Frozen lake", "Ancient ice tomb", "Hot springs"],
    },
    "coastal": {
        "combat": ["Sahuagin", "Harpies", "Sea Hags", "Giant Crabs", "Merrow"],
        "social": ["Fishermen", "Shipwreck survivors", "Smugglers", "Sea elf scout"],
        "discovery": ["Shipwreck", "Hidden cove", "Sea cave", "Lighthouse"],
    },
    "urban": {
        "combat": ["Bandits", "Thugs", "Assassins", "Wererats", "Cultists"],
        "social": ["Street vendor", "City guard", "Noble", "Beggar", "Tavern keeper"],
        "discovery": ["Secret door", "Underground entrance", "Abandoned building", "Hidden cache"],
    },
    "underground": {
        "combat": ["Goblins", "Orcs", "Troglodytes", "Umber Hulks", "Drow", "Hook Horrors"],
        "social": ["Duergar traders", "Myconid colony", "Lost explorer"],
        "discovery": ["Underground lake", "Crystal cave", "Ancient ruins", "Collapsed tunnel"],
    },
    "underdark": {
        "combat": ["Drow patrol", "Mind Flayers", "Driders", "Purple Worms", "Beholders"],
        "social": ["Drow merchant", "Deep gnome refugees", "Escaped slave"],
        "discovery": ["Drow outpost", "Mind flayer colony", "Fungal forest", "Underground river"],
    },
    "jungle": {
        "combat": ["Giant Apes", "Dinosaurs", "Yuan-ti", "Assassin Vines", "Tribal Warriors"],
        "social": ["Native tribe", "Expedition camp", "Stranded explorer"],
        "discovery": ["Ancient temple", "Hidden waterfall", "Carnivorous plants", "Lost city entrance"],
    },
    "ruins": {
        "combat": ["Undead", "Constructs", "Cultists", "Golems", "Ghosts"],
        "social": ["Treasure hunters", "Archaeologists", "Cult leader"],
        "discovery": ["Hidden vault", "Ancient artifact", "Secret passage", "Trapped room"],
    },
}

# Non-combat event descriptions
RANDOM_EVENTS = {
    "weather": [
        {"name": "Sudden Storm", "description": "Dark clouds roll in quickly, bringing heavy rain and thunder.", "effect": "Travel slowed, possible shelter needed"},
        {"name": "Fog Bank", "description": "A thick fog rolls across the land, reducing visibility to 30 feet.", "effect": "Disadvantage on Perception, easy to get lost"},
        {"name": "Heat Wave", "description": "The sun beats down mercilessly, the air shimmering with heat.", "effect": "CON saves or exhaustion"},
        {"name": "Cold Snap", "description": "The temperature drops sharply, frost forming on surfaces.", "effect": "Need cold weather gear or CON saves"},
        {"name": "Beautiful Day", "description": "Perfect traveling weather - clear skies and a pleasant breeze.", "effect": "Advantage on Survival checks"},
    ],
    "discovery": [
        {"name": "Hidden Cache", "description": "Concealed behind rocks/foliage, you find supplies left by travelers.", "effect": "1d4 rations, possibly other items"},
        {"name": "Ancient Marker", "description": "A weathered stone marker with faded inscriptions.", "effect": "History check may reveal information"},
        {"name": "Scenic Vista", "description": "You reach a viewpoint with a stunning panoramic view.", "effect": "Short rest here is especially restful"},
        {"name": "Fresh Water Source", "description": "A natural spring with clear, cold water.", "effect": "Refill waterskins, safe to drink"},
        {"name": "Overgrown Path", "description": "An old trail, barely visible, leads off in another direction.", "effect": "May be a shortcut or lead somewhere interesting"},
    ],
    "rest_site": [
        {"name": "Abandoned Camp", "description": "An old campsite with a fire pit and some shelter.", "effect": "Safe place for short rest"},
        {"name": "Natural Shelter", "description": "A cave, hollow tree, or rocky overhang provides protection.", "effect": "Defensible rest location"},
        {"name": "Wayside Inn", "description": "A small inn or tavern appears along the road.", "effect": "Hot food, beds, information"},
        {"name": "Friendly Farm", "description": "A farmstead where travelers might find hospitality.", "effect": "Possible lodging for the night"},
    ],
    "social": [
        {"name": "Fellow Travelers", "description": "A group of travelers heading the same direction.", "effect": "May share news or rumors"},
        {"name": "Lost Child", "description": "A young person separated from their group.", "effect": "Opportunity to help, possible reward"},
        {"name": "Wounded Creature", "description": "An injured animal that could be helped.", "effect": "Animal Handling check to assist"},
        {"name": "Roadside Merchant", "description": "A peddler with a cart of various goods.", "effect": "Opportunity to buy/sell"},
    ],
}


# ============================================================================
# STORAGE
# ============================================================================

TRAVEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'state', 'travel')
os.makedirs(TRAVEL_DIR, exist_ok=True)
_travel_locks = {}


def _get_travel_path(channel_id: str) -> str:
    return os.path.join(TRAVEL_DIR, f'{channel_id}_travel.json')


def load_travel_state(channel_id: str) -> Optional[TravelState]:
    """Load travel state for a channel."""
    path = _get_travel_path(channel_id)
    if not os.path.exists(path):
        return None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return TravelState.from_dict(data)
    except Exception:
        return None


def save_travel_state(channel_id: str, state: TravelState):
    """Save travel state for a channel."""
    path = _get_travel_path(channel_id)
    lock = _travel_locks.setdefault(channel_id, Lock())
    
    with lock:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, indent=2)


def clear_travel_state(channel_id: str):
    """Clear travel state when arriving at destination."""
    path = _get_travel_path(channel_id)
    if os.path.exists(path):
        os.remove(path)


# ============================================================================
# DIFFICULTY CALCULATIONS
# ============================================================================

def get_party_xp_threshold(party_levels: List[int], difficulty: str) -> int:
    """Calculate party's XP threshold for a given difficulty."""
    total = 0
    for level in party_levels:
        level = max(1, min(20, level))  # Clamp to valid range
        total += XP_THRESHOLDS[level].get(difficulty, 0)
    return total


def get_encounter_multiplier(num_monsters: int, party_size: int) -> float:
    """Get encounter difficulty multiplier based on monster count and party size."""
    # Base multiplier from monster count
    if num_monsters == 1:
        mult = 1.0
    elif num_monsters == 2:
        mult = 1.5
    elif 3 <= num_monsters <= 6:
        mult = 2.0
    elif 7 <= num_monsters <= 10:
        mult = 2.5
    elif 11 <= num_monsters <= 14:
        mult = 3.0
    else:
        mult = 4.0
    
    # Adjust for party size
    if party_size < 3:
        mult *= 1.5  # Harder for small parties
    elif party_size >= 6:
        mult *= 0.5  # Easier for large parties
    
    return mult


def calculate_encounter_difficulty(
    monster_xp_total: int,
    num_monsters: int,
    party_levels: List[int]
) -> str:
    """Determine encounter difficulty rating."""
    party_size = len(party_levels)
    multiplier = get_encounter_multiplier(num_monsters, party_size)
    adjusted_xp = int(monster_xp_total * multiplier)
    
    # Get thresholds
    easy = get_party_xp_threshold(party_levels, "easy")
    medium = get_party_xp_threshold(party_levels, "medium")
    hard = get_party_xp_threshold(party_levels, "hard")
    deadly = get_party_xp_threshold(party_levels, "deadly")
    
    if adjusted_xp >= deadly:
        return "deadly"
    elif adjusted_xp >= hard:
        return "hard"
    elif adjusted_xp >= medium:
        return "medium"
    elif adjusted_xp >= easy:
        return "easy"
    else:
        return "trivial"


def get_appropriate_cr_range(party_levels: List[int], difficulty: str) -> Tuple[float, float]:
    """Get appropriate CR range for a given party and difficulty."""
    avg_level = sum(party_levels) / len(party_levels)
    party_size = len(party_levels)
    
    # Base CR ranges by difficulty
    if difficulty == "trivial":
        max_cr = max(0.125, avg_level * 0.25)
        min_cr = 0
    elif difficulty == "easy":
        max_cr = max(0.5, avg_level * 0.5)
        min_cr = 0
    elif difficulty == "medium":
        max_cr = avg_level
        min_cr = max(0.125, avg_level * 0.25)
    elif difficulty == "hard":
        max_cr = avg_level + 2
        min_cr = max(0.5, avg_level * 0.5)
    else:  # deadly
        max_cr = avg_level + 4
        min_cr = max(1, avg_level * 0.75)
    
    # Adjust for party size
    if party_size >= 5:
        max_cr += 1
    elif party_size <= 2:
        max_cr -= 1
        min_cr = max(0, min_cr - 0.5)
    
    return (min_cr, max_cr)


# ============================================================================
# ENCOUNTER GENERATION
# ============================================================================

def get_monsters_for_cr(cr: float) -> List[Dict]:
    """Get list of monsters at or near a given CR."""
    # Find exact match
    if cr in MONSTERS_BY_CR:
        return MONSTERS_BY_CR[cr]
    
    # Find nearest CR
    available_crs = sorted(MONSTERS_BY_CR.keys())
    for available_cr in available_crs:
        if available_cr >= cr:
            return MONSTERS_BY_CR.get(available_cr, [])
    
    # Return highest if nothing else
    return MONSTERS_BY_CR.get(max(available_crs), [])


def generate_combat_encounter(
    party_levels: List[int],
    terrain: str = "plains",
    difficulty: str = "medium"
) -> Encounter:
    """Generate a combat encounter appropriate for the party."""
    min_cr, max_cr = get_appropriate_cr_range(party_levels, difficulty)
    
    # Decide on encounter composition
    composition_roll = random.random()
    if composition_roll < 0.4:
        # Single strong monster
        num_monsters = 1
        target_cr = max_cr
    elif composition_roll < 0.7:
        # Small group (2-4)
        num_monsters = random.randint(2, 4)
        target_cr = (min_cr + max_cr) / 2
    else:
        # Larger group (4-8)
        num_monsters = random.randint(4, 8)
        target_cr = min_cr
    
    # Find appropriate monsters
    available_crs = [cr for cr in MONSTERS_BY_CR.keys() if min_cr <= cr <= target_cr + 1]
    if not available_crs:
        available_crs = [min(MONSTERS_BY_CR.keys())]
    
    selected_cr = random.choice(available_crs)
    monster_options = get_monsters_for_cr(selected_cr)
    
    if not monster_options:
        monster_options = [{"name": "Bandit", "hp": 11, "ac": 12, "type": "humanoid", "size": "medium"}]
    
    # Select monster type
    base_monster = random.choice(monster_options)
    
    # Generate the encounter
    monsters = []
    total_xp = 0
    for i in range(num_monsters):
        monster = base_monster.copy()
        monster["cr"] = selected_cr
        monster["xp"] = CR_TO_XP.get(selected_cr, 50)
        total_xp += monster["xp"]
        
        # Add variation for multiple monsters
        if num_monsters > 1:
            monster["name"] = f"{base_monster['name']} {i + 1}"
        
        monsters.append(monster)
    
    # Calculate actual difficulty
    actual_difficulty = calculate_encounter_difficulty(
        total_xp, num_monsters, party_levels
    )
    
    # Get terrain-specific description
    terrain_data = TERRAIN_ENCOUNTERS.get(terrain, TERRAIN_ENCOUNTERS["plains"])
    encounter_theme = random.choice(terrain_data.get("combat", ["Monsters"]))
    
    # Determine loot tier
    if actual_difficulty in ["deadly", "hard"]:
        loot_tier = "rare"
    elif actual_difficulty == "medium":
        loot_tier = "uncommon"
    else:
        loot_tier = "common"
    
    return Encounter(
        name=f"{encounter_theme} Encounter",
        event_type="combat",
        difficulty=actual_difficulty,
        monsters=monsters,
        description=f"A group of {base_monster['name']}s emerges from the {terrain}!",
        xp_reward=total_xp,
        loot_tier=loot_tier,
        terrain=terrain,
        special_conditions=[]
    )


def generate_social_encounter(terrain: str = "road") -> Encounter:
    """Generate a non-combat social encounter."""
    terrain_data = TERRAIN_ENCOUNTERS.get(terrain, TERRAIN_ENCOUNTERS["road"])
    social_options = terrain_data.get("social", ["Travelers"])
    
    encounter_name = random.choice(social_options)
    
    return Encounter(
        name=encounter_name,
        event_type="social",
        difficulty="none",
        monsters=[],
        description=f"You encounter {encounter_name.lower()} while traveling.",
        xp_reward=0,
        loot_tier="none",
        terrain=terrain,
        special_conditions=[]
    )


def generate_discovery_encounter(terrain: str = "road") -> Encounter:
    """Generate a discovery encounter."""
    terrain_data = TERRAIN_ENCOUNTERS.get(terrain, TERRAIN_ENCOUNTERS["road"])
    discovery_options = terrain_data.get("discovery", ["Old campsite"])
    
    discovery_name = random.choice(discovery_options)
    
    return Encounter(
        name=discovery_name,
        event_type="discovery",
        difficulty="none",
        monsters=[],
        description=f"While traveling, you discover {discovery_name.lower()}.",
        xp_reward=0,
        loot_tier="common",
        terrain=terrain,
        special_conditions=[]
    )


def generate_random_event(event_type: str = None) -> Dict[str, Any]:
    """Generate a random non-combat event."""
    if event_type is None:
        event_type = random.choice(list(RANDOM_EVENTS.keys()))
    
    events = RANDOM_EVENTS.get(event_type, RANDOM_EVENTS["discovery"])
    event = random.choice(events)
    
    return {
        "type": event_type,
        "name": event["name"],
        "description": event["description"],
        "effect": event["effect"]
    }


def roll_for_encounter(
    terrain: str,
    hours_since_last_check: float = 1,
    is_night: bool = False,
    party_is_stealthy: bool = False
) -> bool:
    """Roll to determine if a random encounter occurs."""
    base_chance = TERRAIN_MODIFIERS.get(terrain, TERRAIN_MODIFIERS["plains"])["encounter_chance"]
    
    # Modifiers
    if is_night:
        base_chance *= 1.5
    if party_is_stealthy:
        base_chance *= 0.5
    
    # Roll per hour of travel
    for _ in range(int(hours_since_last_check)):
        if random.random() < base_chance:
            return True
    
    return False


def determine_encounter_type() -> str:
    """Determine what type of encounter occurs."""
    roll = random.random()
    
    if roll < 0.50:
        return "combat"
    elif roll < 0.70:
        return "social"
    elif roll < 0.85:
        return "discovery"
    elif roll < 0.95:
        return "hazard"
    else:
        return "weather"


# ============================================================================
# TRAVEL SYSTEM
# ============================================================================

def start_travel(
    channel_id: str,
    origin: str,
    destination: str,
    distance_miles: float,
    terrain: str = "road",
    pace: str = "normal"
) -> TravelState:
    """Start traveling between two locations."""
    state = TravelState(
        origin=origin,
        destination=destination,
        terrain=terrain,
        total_distance_miles=distance_miles,
        traveled_miles=0,
        pace=pace,
        hours_traveled_today=0,
        days_traveled=0,
        encounters_today=0,
        last_encounter_check=datetime.now().isoformat(),
        is_resting=False
    )
    
    save_travel_state(channel_id, state)
    return state


def calculate_travel_time(
    distance_miles: float,
    terrain: str = "road",
    pace: str = "normal"
) -> Dict[str, Any]:
    """Calculate travel time for a journey."""
    pace_data = TRAVEL_SPEEDS.get(pace, TRAVEL_SPEEDS["normal"])
    terrain_mod = TERRAIN_MODIFIERS.get(terrain, TERRAIN_MODIFIERS["road"])
    
    effective_speed = pace_data["miles_per_day"] * terrain_mod["speed_mult"]
    days_required = distance_miles / effective_speed
    
    return {
        "distance_miles": distance_miles,
        "terrain": terrain,
        "pace": pace,
        "miles_per_day": effective_speed,
        "days_required": math.ceil(days_required),
        "hours_required": days_required * 8,  # 8 hours of travel per day
        "stealth_possible": pace_data["stealth_possible"],
        "perception_mod": pace_data["perception_mod"]
    }


def advance_travel(
    channel_id: str,
    hours: float = 1
) -> Dict[str, Any]:
    """Advance travel by a number of hours, checking for encounters."""
    state = load_travel_state(channel_id)
    if not state:
        return {"error": "No active travel"}
    
    pace_data = TRAVEL_SPEEDS.get(state.pace, TRAVEL_SPEEDS["normal"])
    terrain_mod = TERRAIN_MODIFIERS.get(state.terrain, TERRAIN_MODIFIERS["road"])
    
    # Calculate distance traveled
    miles_per_hour = pace_data["miles_per_hour"] * terrain_mod["speed_mult"]
    miles_traveled = hours * miles_per_hour
    
    state.traveled_miles += miles_traveled
    state.hours_traveled_today += hours
    
    # Check if we've arrived
    arrived = state.traveled_miles >= state.total_distance_miles
    if arrived:
        state.traveled_miles = state.total_distance_miles
    
    # Check for random encounter
    encounter = None
    is_stealthy = pace_data["stealth_possible"]
    is_night = state.hours_traveled_today > 12  # Simplified day/night
    
    if roll_for_encounter(state.terrain, hours, is_night, is_stealthy):
        state.encounters_today += 1
        encounter_type = determine_encounter_type()
        
        if encounter_type == "combat":
            # We'll need party levels passed in - for now use placeholder
            encounter = {"type": "combat", "needs_generation": True}
        elif encounter_type == "social":
            encounter = generate_social_encounter(state.terrain).to_dict()
        elif encounter_type == "discovery":
            encounter = generate_discovery_encounter(state.terrain).to_dict()
        else:
            encounter = generate_random_event(encounter_type)
    
    # End of day check
    if state.hours_traveled_today >= 8:
        state.days_traveled += 1
        state.hours_traveled_today = 0
        state.encounters_today = 0
    
    save_travel_state(channel_id, state)
    
    result = {
        "miles_traveled": miles_traveled,
        "total_traveled": state.traveled_miles,
        "remaining": state.total_distance_miles - state.traveled_miles,
        "progress_percent": (state.traveled_miles / state.total_distance_miles) * 100,
        "arrived": arrived,
        "encounter": encounter,
        "days_traveled": state.days_traveled,
        "hours_today": state.hours_traveled_today,
    }
    
    if arrived:
        clear_travel_state(channel_id)
        result["destination"] = state.destination
    
    return result


def get_travel_status(channel_id: str) -> Optional[Dict[str, Any]]:
    """Get current travel status."""
    state = load_travel_state(channel_id)
    if not state:
        return None
    
    return {
        "origin": state.origin,
        "destination": state.destination,
        "terrain": state.terrain,
        "pace": state.pace,
        "traveled_miles": state.traveled_miles,
        "total_miles": state.total_distance_miles,
        "remaining_miles": state.total_distance_miles - state.traveled_miles,
        "progress_percent": (state.traveled_miles / state.total_distance_miles) * 100,
        "days_traveled": state.days_traveled,
        "hours_today": state.hours_traveled_today,
        "encounters_today": state.encounters_today,
    }


# ============================================================================
# AI CONTEXT
# ============================================================================

def get_travel_context_for_ai(channel_id: str) -> str:
    """Build travel context for AI prompts."""
    state = load_travel_state(channel_id)
    if not state:
        return ""
    
    lines = [
        f"**Currently Traveling:** From {state.origin} to {state.destination}",
        f"**Terrain:** {state.terrain.title()}",
        f"**Pace:** {state.pace.title()}",
        f"**Progress:** {state.traveled_miles:.1f}/{state.total_distance_miles:.1f} miles ({(state.traveled_miles / state.total_distance_miles) * 100:.0f}%)",
        f"**Day {state.days_traveled + 1}**, {state.hours_traveled_today:.1f} hours traveled today",
    ]
    
    return "\n".join(lines)


# ============================================================================
# FORMATTING
# ============================================================================

def format_encounter_summary(encounter: Encounter) -> str:
    """Format encounter for display."""
    lines = [
        f"⚔️ **{encounter.name}**",
        f"*{encounter.description}*",
        f"Difficulty: {encounter.difficulty.title()}",
    ]
    
    if encounter.monsters:
        lines.append(f"Enemies: {len(encounter.monsters)}")
        monster_names = [m.get('name', 'Unknown') for m in encounter.monsters[:5]]
        lines.append(f"  • " + ", ".join(monster_names))
        if len(encounter.monsters) > 5:
            lines.append(f"  • ...and {len(encounter.monsters) - 5} more")
    
    if encounter.xp_reward:
        lines.append(f"XP Reward: {encounter.xp_reward}")
    
    return "\n".join(lines)


def format_travel_status(status: Dict[str, Any]) -> str:
    """Format travel status for display."""
    lines = [
        f"🗺️ **Travel Status**",
        f"From: {status['origin']}",
        f"To: {status['destination']}",
        f"",
        f"Terrain: {status['terrain'].title()}",
        f"Pace: {status['pace'].title()}",
        f"",
        f"Progress: {status['traveled_miles']:.1f} / {status['total_miles']:.1f} miles",
        f"Remaining: {status['remaining_miles']:.1f} miles",
        f"",
        f"Day {status['days_traveled'] + 1}",
        f"Hours traveled today: {status['hours_today']:.1f}/8",
    ]
    
    # Progress bar
    percent = status['progress_percent']
    filled = int(percent / 10)
    bar = "█" * filled + "░" * (10 - filled)
    lines.append(f"[{bar}] {percent:.0f}%")
    
    return "\n".join(lines)


def format_random_event(event: Dict[str, Any]) -> str:
    """Format a random event for display."""
    emoji_map = {
        "weather": "🌦️",
        "discovery": "🔍",
        "rest_site": "🏕️",
        "social": "👥",
        "hazard": "⚠️",
    }
    
    emoji = emoji_map.get(event.get("type", "discovery"), "❓")
    
    lines = [
        f"{emoji} **{event['name']}**",
        f"*{event['description']}*",
    ]
    
    if event.get("effect"):
        lines.append(f"Effect: {event['effect']}")
    
    return "\n".join(lines)
