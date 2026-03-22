"""
World Generator Module for Dynamic Environment Generation.

This module handles:
1. Detection and parsing of environment tags from AI narration
2. Location-based environment presets
3. Time-of-day tracking with automatic lighting
4. Location memory (remembering environment per location)
5. Integration with environment_manager.py for applying changes
"""

import re
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from utils.tag_parser import parse_all_tags, ParsedTags


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TimeState:
    """Tracks in-game time."""
    hour: int = 8  # 0-23, starts at 8am
    day: int = 1
    month: int = 1
    year: int = 1490  # Forgotten Realms default
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimeState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_time_of_day(self) -> str:
        """Get time period based on hour."""
        if 5 <= self.hour < 7:
            return "dawn"
        elif 7 <= self.hour < 12:
            return "morning"
        elif 12 <= self.hour < 14:
            return "midday"
        elif 14 <= self.hour < 17:
            return "afternoon"
        elif 17 <= self.hour < 20:
            return "evening"
        elif 20 <= self.hour < 22:
            return "dusk"
        else:
            return "night"
    
    def get_lighting_for_outdoor(self) -> str:
        """Get appropriate lighting level for outdoor areas."""
        if 7 <= self.hour < 19:
            return "bright"
        elif 5 <= self.hour < 7 or 19 <= self.hour < 21:
            return "dim"
        else:
            return "darkness"
    
    def advance(self, hours: int = 1):
        """Advance time by hours."""
        self.hour += hours
        while self.hour >= 24:
            self.hour -= 24
            self.day += 1
        while self.day > 30:  # Simple 30-day months
            self.day -= 30
            self.month += 1
        while self.month > 12:
            self.month -= 12
            self.year += 1
    
    def format_time(self) -> str:
        """Format time for display."""
        period = "AM" if self.hour < 12 else "PM"
        display_hour = self.hour if self.hour <= 12 else self.hour - 12
        if display_hour == 0:
            display_hour = 12
        return f"{display_hour}:00 {period}, Day {self.day}, Month {self.month}, Year {self.year}"


@dataclass
class LocationMemory:
    """Stores environment state for a specific location."""
    location_name: str
    weather_type: Optional[str] = None
    weather_intensity: int = 1
    lighting_level: str = "bright"
    lighting_source: str = ""
    is_outdoor: bool = True
    terrain_zones: List[Dict[str, Any]] = field(default_factory=list)
    known_traps: List[str] = field(default_factory=list)  # Trap names
    hazards: List[str] = field(default_factory=list)  # Hazard descriptions
    last_visited: Optional[str] = None  # ISO timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocationMemory":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class EnvironmentChange:
    """Represents a detected environment change from AI narration."""
    change_type: str  # "weather", "lighting", "trap", "hazard", "time", "location"
    value: str  # The detected value
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# LOCATION PRESETS - Environment defaults for common locations
# ============================================================================

LOCATION_PRESETS = {
    # Indoor locations
    "cave": {
        "is_outdoor": False,
        "lighting": "darkness",
        "lighting_source": "natural cave",
        "terrain": ["difficult"],
    },
    "cavern": {
        "is_outdoor": False,
        "lighting": "darkness",
        "lighting_source": "natural cavern",
        "terrain": ["difficult"],
    },
    "dungeon": {
        "is_outdoor": False,
        "lighting": "darkness",
        "lighting_source": "dungeon",
        "terrain": [],
    },
    "crypt": {
        "is_outdoor": False,
        "lighting": "darkness",
        "lighting_source": "tomb",
        "terrain": [],
    },
    "tomb": {
        "is_outdoor": False,
        "lighting": "darkness",
        "lighting_source": "tomb",
        "terrain": [],
    },
    "mine": {
        "is_outdoor": False,
        "lighting": "darkness",
        "lighting_source": "abandoned mine",
        "terrain": ["difficult"],
    },
    "sewer": {
        "is_outdoor": False,
        "lighting": "darkness",
        "lighting_source": "sewer tunnels",
        "terrain": ["shallow_water"],
    },
    "cellar": {
        "is_outdoor": False,
        "lighting": "dim",
        "lighting_source": "cellar",
        "terrain": [],
    },
    "basement": {
        "is_outdoor": False,
        "lighting": "dim",
        "lighting_source": "basement",
        "terrain": [],
    },
    "tavern": {
        "is_outdoor": False,
        "lighting": "bright",
        "lighting_source": "hearth fire and candles",
        "terrain": [],
    },
    "inn": {
        "is_outdoor": False,
        "lighting": "bright",
        "lighting_source": "hearth fire and candles",
        "terrain": [],
    },
    "temple": {
        "is_outdoor": False,
        "lighting": "bright",
        "lighting_source": "sacred flames",
        "terrain": [],
    },
    "castle": {
        "is_outdoor": False,
        "lighting": "bright",
        "lighting_source": "torches and candles",
        "terrain": [],
    },
    "tower": {
        "is_outdoor": False,
        "lighting": "dim",
        "lighting_source": "sparse torches",
        "terrain": [],
    },
    "ruins": {
        "is_outdoor": True,
        "lighting": "time_based",  # Will use time-of-day
        "terrain": ["difficult", "rubble"],
    },
    "abandoned": {
        "is_outdoor": False,
        "lighting": "dim",
        "lighting_source": "cracks in walls",
        "terrain": ["difficult"],
    },
    
    # Outdoor locations
    "forest": {
        "is_outdoor": True,
        "lighting": "dim",  # Canopy cover
        "lighting_source": "filtered sunlight",
        "terrain": ["difficult"],
    },
    "woods": {
        "is_outdoor": True,
        "lighting": "dim",
        "lighting_source": "filtered sunlight",
        "terrain": ["difficult"],
    },
    "jungle": {
        "is_outdoor": True,
        "lighting": "dim",
        "lighting_source": "dense canopy",
        "terrain": ["difficult"],
    },
    "swamp": {
        "is_outdoor": True,
        "lighting": "dim",
        "lighting_source": "murky atmosphere",
        "terrain": ["difficult", "shallow_water", "mud"],
    },
    "marsh": {
        "is_outdoor": True,
        "lighting": "dim",
        "terrain": ["difficult", "shallow_water"],
    },
    "mountain": {
        "is_outdoor": True,
        "lighting": "time_based",
        "terrain": ["difficult"],
    },
    "desert": {
        "is_outdoor": True,
        "lighting": "time_based",
        "weather": "extreme_heat",
        "terrain": [],
    },
    "arctic": {
        "is_outdoor": True,
        "lighting": "time_based",
        "weather": "extreme_cold",
        "terrain": ["ice", "snow"],
    },
    "tundra": {
        "is_outdoor": True,
        "lighting": "time_based",
        "weather": "extreme_cold",
        "terrain": ["ice"],
    },
    "plains": {
        "is_outdoor": True,
        "lighting": "time_based",
        "terrain": [],
    },
    "grassland": {
        "is_outdoor": True,
        "lighting": "time_based",
        "terrain": [],
    },
    "road": {
        "is_outdoor": True,
        "lighting": "time_based",
        "terrain": [],
    },
    "village": {
        "is_outdoor": True,
        "lighting": "time_based",
        "terrain": [],
    },
    "town": {
        "is_outdoor": True,
        "lighting": "time_based",
        "terrain": [],
    },
    "city": {
        "is_outdoor": True,
        "lighting": "time_based",
        "terrain": [],
    },
    "coast": {
        "is_outdoor": True,
        "lighting": "time_based",
        "terrain": [],
    },
    "beach": {
        "is_outdoor": True,
        "lighting": "time_based",
        "terrain": [],
    },
    "underwater": {
        "is_outdoor": False,
        "lighting": "dim",
        "lighting_source": "filtered light from above",
        "terrain": ["deep_water"],
    },
}


# ============================================================================
# DETECTION PATTERNS
# ============================================================================

# Structured tag patterns
ENVIRONMENT_TAG_PATTERN = re.compile(
    r"\[ENVIRONMENT:\s*([^\]]+)\]",
    re.IGNORECASE
)

WEATHER_TAG_PATTERN = re.compile(
    r"\[WEATHER:\s*([^\]]+)\]",
    re.IGNORECASE
)

LIGHTING_TAG_PATTERN = re.compile(
    r"\[LIGHTING:\s*([^\]]+)\]",
    re.IGNORECASE
)

TRAP_TAG_PATTERN = re.compile(
    r"\[TRAP:\s*([^\]]+)\]",
    re.IGNORECASE
)

HAZARD_TAG_PATTERN = re.compile(
    r"\[HAZARD:\s*([^\]]+)\]",
    re.IGNORECASE
)

TIME_TAG_PATTERN = re.compile(
    r"\[TIME:\s*([^\]]+)\]",
    re.IGNORECASE
)

LOCATION_TAG_PATTERN = re.compile(
    r"\[LOCATION:\s*([^\]]+)\]",
    re.IGNORECASE
)

# Natural language weather detection
WEATHER_KEYWORDS = {
    "clear": ["clear sky", "sunny", "clear weather", "bright sun", "cloudless"],
    "cloudy": ["cloudy", "overcast", "clouds gather", "gray sky"],
    "rain": ["rain begins", "it starts raining", "raindrops", "light rain", "drizzle"],
    "heavy_rain": ["heavy rain", "downpour", "torrential", "pouring rain"],
    "thunderstorm": ["thunder", "lightning", "storm", "thunderstorm"],
    "fog": ["fog rolls in", "mist", "foggy", "misty"],
    "dense_fog": ["thick fog", "dense fog", "can barely see"],
    "snow": ["snow begins", "snowfall", "flurries", "snowing"],
    "blizzard": ["blizzard", "snowstorm", "whiteout"],
    "sandstorm": ["sandstorm", "sand whips"],
    "wind": ["wind picks up", "windy", "gusts"],
    "strong_wind": ["strong wind", "gale", "powerful wind"],
}

# Natural language lighting detection
LIGHTING_KEYWORDS = {
    "bright": ["brightly lit", "well-lit", "bright light", "sunlight streams"],
    "dim": ["dimly lit", "flickering", "sparse light", "shadows", "twilight"],
    "darkness": ["pitch black", "total darkness", "no light", "can't see", "blind darkness"],
    "magical_darkness": ["magical darkness", "supernatural darkness", "unnatural dark"],
}

# Natural language location detection - REQUIRES movement verbs to trigger
# These patterns require the party to actually be MOVING to the location
LOCATION_ENTRY_PATTERNS = {
    "cave": [
        r"(?:enter|step into|arrive at|reach|go into|walk into|head into|move into)\s+(?:the\s+)?(?:dark\s+)?cave",
        r"(?:enter|step into|arrive at|reach)\s+(?:the\s+)?cavern",
        r"inside\s+the\s+cave",
        r"cave\s+entrance",
    ],
    "dungeon": [
        r"(?:enter|step into|descend into|arrive at|reach)\s+(?:the\s+)?(?:ancient\s+)?dungeon",
        r"(?:enter|step into)\s+(?:the\s+)?underground\s+complex",
    ],
    "forest": [
        r"(?:enter|step into|walk into|arrive at|reach|travel into|head into)\s+(?:the\s+)?(?:\w+\s+)?(?:forest|woods|woodland)",
        r"trees\s+surround\s+(?:you|the\s+party)",
    ],
    "swamp": [
        r"(?:enter|step into|wade into|arrive at|reach)\s+(?:the\s+)?(?:\w+\s+)?(?:swamp|marsh|bog)",
        r"murky\s+waters\s+surround",
    ],
    "tavern": [
        r"(?:enter|step into|walk into|arrive at|push\s+(?:open|through))\s+(?:the\s+)?(?:\w+\s+)?(?:tavern|inn)",
        r"(?:enter|step into)\s+(?:the\s+)?(?:common\s+room|bar)",
    ],
    "temple": [
        r"(?:enter|step into|arrive at|reach)\s+(?:the\s+)?(?:\w+\s+)?(?:temple|shrine|sacred\s+place|holy\s+site)",
    ],
    "castle": [
        r"(?:enter|approach|arrive at|reach)\s+(?:the\s+)?(?:\w+\s+)?(?:castle|fortress|keep|stronghold)",
    ],
    "ruins": [
        r"(?:enter|explore|arrive at|reach|approach)\s+(?:the\s+)?(?:\w+\s+)?ruins",
        r"(?:enter|step into)\s+(?:the\s+)?(?:crumbling|ancient)\s+(?:structure|building|ruins)",
    ],
    "crypt": [
        r"(?:enter|descend into|step into|arrive at)\s+(?:the\s+)?(?:\w+\s+)?(?:crypt|tomb|burial\s+chamber|mausoleum)",
    ],
    "city": [
        r"(?:enter|arrive at|reach|approach)\s+(?:the\s+)?(?:\w+\s+)?(?:city|town|village)",
        r"(?:walk|step)\s+into\s+(?:the\s+)?(?:streets|marketplace)",
    ],
    "road": [
        r"(?:set\s+out\s+on|travel\s+along|walk\s+(?:down|along)|follow)\s+(?:the\s+)?(?:\w+\s+)?(?:road|path|trail|highway)",
    ],
    "mountain": [
        r"(?:climb|ascend|reach|arrive at)\s+(?:the\s+)?(?:\w+\s+)?(?:mountain|peak|mountainside)",
        r"(?:scale|climb)\s+(?:the\s+)?cliff",
    ],
    "desert": [
        r"(?:enter|step into|arrive at|reach|travel into)\s+(?:the\s+)?(?:\w+\s+)?(?:desert|wasteland)",
        r"(?:enter|step into)\s+(?:the\s+)?sand\s+dunes",
    ],
    "arctic": [
        r"(?:enter|step into|arrive at|reach|travel into)\s+(?:the\s+)?(?:\w+\s+)?(?:arctic|frozen\s+(?:waste|land)|tundra)",
        r"(?:step\s+onto|arrive\s+at)\s+(?:the\s+)?glacier",
    ],
    "underwater": [
        r"(?:descend|dive|swim)\s+(?:beneath\s+the\s+waves|underwater)",
        r"(?:reach|arrive\s+at)\s+(?:the\s+)?ocean\s+floor",
    ],
}

# Simple keywords for reference (used in parsing, NOT for detection)
LOCATION_KEYWORDS = {
    "cave": ["cave", "cavern"],
    "dungeon": ["dungeon", "underground complex"],
    "forest": ["forest", "woods", "woodland"],
    "swamp": ["swamp", "marsh", "bog"],
    "tavern": ["tavern", "inn", "bar", "common room"],
    "temple": ["temple", "shrine", "sacred place", "holy site"],
    "castle": ["castle", "fortress", "keep", "stronghold"],
    "ruins": ["ruins", "ancient ruins"],
    "crypt": ["crypt", "tomb", "burial chamber", "mausoleum"],
    "city": ["city", "town", "village", "streets", "marketplace"],
    "road": ["road", "path", "trail", "highway"],
    "mountain": ["mountain", "peak", "cliff", "mountainside"],
    "desert": ["desert", "sand dunes", "wasteland"],
    "arctic": ["arctic", "frozen", "tundra", "glacier"],
    "underwater": ["underwater", "ocean floor"],
}

# Time keywords
TIME_KEYWORDS = {
    "dawn": ["dawn", "sunrise", "first light", "day breaks"],
    "morning": ["morning", "early day"],
    "midday": ["midday", "noon", "high sun"],
    "afternoon": ["afternoon", "late day"],
    "evening": ["evening", "sunset", "dusk approaches"],
    "dusk": ["dusk", "twilight", "sun sets"],
    "night": ["night", "nightfall", "darkness falls", "midnight", "after dark"],
}

# Time advancement keywords
TIME_ADVANCE_PATTERNS = [
    (re.compile(r"(\d+)\s*hours?\s+pass", re.IGNORECASE), "hours"),
    (re.compile(r"rest\s+for\s+(\d+)\s*hours?", re.IGNORECASE), "hours"),
    (re.compile(r"long\s+rest", re.IGNORECASE), "long_rest"),  # 8 hours
    (re.compile(r"short\s+rest", re.IGNORECASE), "short_rest"),  # 1 hour
    (re.compile(r"night\s+passes", re.IGNORECASE), "night"),  # Advance to dawn
    (re.compile(r"dawn\s+breaks", re.IGNORECASE), "dawn"),  # Set to dawn
]


# ============================================================================
# STORAGE FUNCTIONS
# ============================================================================

def get_world_state_path(channel_id: str) -> Path:
    """Get the path to the world state file."""
    return Path("state") / f"{channel_id}_world.json"


def load_world_state(channel_id: str) -> Dict[str, Any]:
    """Load world state for a channel."""
    path = get_world_state_path(channel_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "time": TimeState().to_dict(),
        "current_location": "",
        "location_memory": {},
    }


def save_world_state(channel_id: str, state: Dict[str, Any]):
    """Save world state for a channel."""
    path = get_world_state_path(channel_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def get_time_state(channel_id: str) -> TimeState:
    """Get the current time state for a channel."""
    world = load_world_state(channel_id)
    return TimeState.from_dict(world.get("time", {}))


def set_time_state(channel_id: str, time_state: TimeState):
    """Set the time state for a channel."""
    world = load_world_state(channel_id)
    world["time"] = time_state.to_dict()
    save_world_state(channel_id, world)


def get_location_memory(channel_id: str, location: str) -> Optional[LocationMemory]:
    """Get remembered environment for a location."""
    world = load_world_state(channel_id)
    memories = world.get("location_memory", {})
    if location.lower() in memories:
        return LocationMemory.from_dict(memories[location.lower()])
    return None


def set_location_memory(channel_id: str, memory: LocationMemory):
    """Save environment memory for a location."""
    world = load_world_state(channel_id)
    if "location_memory" not in world:
        world["location_memory"] = {}
    memory.last_visited = datetime.now().isoformat()
    world["location_memory"][memory.location_name.lower()] = memory.to_dict()
    save_world_state(channel_id, world)


def get_current_location(channel_id: str) -> str:
    """Get the current tracked location."""
    world = load_world_state(channel_id)
    return world.get("current_location", "")


def set_current_location(channel_id: str, location: str):
    """Set the current tracked location."""
    world = load_world_state(channel_id)
    world["current_location"] = location
    save_world_state(channel_id, world)


# ============================================================================
# DETECTION FUNCTIONS
# ============================================================================

def detect_structured_tags(text: str, parsed: Optional[ParsedTags] = None) -> List[EnvironmentChange]:
    """Detect structured environment tags in AI narration."""
    if parsed is None:
        parsed = parse_all_tags(text)

    changes = []
    
    # [WEATHER: rain] or [WEATHER: heavy rain, intensity 2]
    for weather_str in parsed.weather:
        intensity = 1
        intensity_match = re.search(r"intensity\s*(\d+)", weather_str, re.IGNORECASE)
        if intensity_match:
            intensity = int(intensity_match.group(1))
            weather_str = re.sub(r",?\s*intensity\s*\d+", "", weather_str).strip()
        weather_type = weather_str.lower().replace(" ", "_")
        changes.append(EnvironmentChange(
            change_type="weather",
            value=weather_type,
            details={"intensity": intensity}
        ))
    
    # [LIGHTING: dim] or [LIGHTING: darkness, source: no windows]
    for lighting_str in parsed.lighting:
        source = ""
        source_match = re.search(r"source[:\s]+([^,\]]+)", lighting_str, re.IGNORECASE)
        if source_match:
            source = source_match.group(1).strip()
            lighting_str = re.sub(r",?\s*source[:\s]+[^,\]]+", "", lighting_str).strip()
        light_level = lighting_str.lower().replace(" ", "_")
        changes.append(EnvironmentChange(
            change_type="lighting",
            value=light_level,
            details={"source": source}
        ))
    
    # [TRAP: pit trap at entrance]
    for trap_str in parsed.traps:
        trap_info = parse_trap_string(trap_str)
        changes.append(EnvironmentChange(
            change_type="trap",
            value=trap_info.get("template", trap_str),
            details=trap_info
        ))
    
    # [HAZARD: lava pool, 2d6 fire]
    for hazard_str in parsed.hazards:
        hazard_info = parse_hazard_string(hazard_str)
        changes.append(EnvironmentChange(
            change_type="hazard",
            value=hazard_info.get("type", hazard_str),
            details=hazard_info
        ))
    
    # [TIME: 3 hours pass] or [TIME: night]
    for time_str in parsed.time_changes:
        time_info = parse_time_string(time_str.lower())
        changes.append(EnvironmentChange(
            change_type="time",
            value=time_info.get("action", time_str),
            details=time_info
        ))
    
    # [LOCATION: Dark Cave]
    for location_str in parsed.locations:
        changes.append(EnvironmentChange(
            change_type="location",
            value=location_str,
            details={"raw": location_str}
        ))
    
    # [ENVIRONMENT: dark cave, cold, dripping water]
    for env_str in parsed.environment:
        env_info = parse_environment_string(env_str)
        for key, value in env_info.items():
            if key == "location":
                changes.append(EnvironmentChange(change_type="location", value=value, details={}))
            elif key == "lighting":
                changes.append(EnvironmentChange(change_type="lighting", value=value, details={}))
            elif key == "weather":
                changes.append(EnvironmentChange(change_type="weather", value=value, details={}))
    
    return changes


def detect_natural_language(text: str) -> List[EnvironmentChange]:
    """Detect environment changes from natural language narration.
    
    Location detection is strict - requires movement verbs to avoid false positives
    when NPCs merely mention locations in dialogue.
    """
    changes = []
    text_lower = text.lower()
    
    # Skip detection if text appears to be inside NPC dialogue
    # (contains quoted speech that mentions locations)
    # We'll still detect if it's the narration mentioning location changes
    
    # Detect weather changes (still use keyword matching)
    for weather_type, keywords in WEATHER_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                changes.append(EnvironmentChange(
                    change_type="weather",
                    value=weather_type,
                    details={"detected_from": keyword}
                ))
                break
    
    # Detect lighting changes (still use keyword matching)
    for light_level, keywords in LIGHTING_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                changes.append(EnvironmentChange(
                    change_type="lighting",
                    value=light_level,
                    details={"detected_from": keyword}
                ))
                break
    
    # Detect location changes - use REGEX patterns that require movement verbs
    # This prevents false positives when NPCs just talk about places
    for location_type, patterns in LOCATION_ENTRY_PATTERNS.items():
        matched = False
        for pattern in patterns:
            if re.search(pattern, text_lower):
                changes.append(EnvironmentChange(
                    change_type="location",
                    value=location_type,
                    details={"detected_from": pattern}
                ))
                matched = True
                break
        if matched:
            break  # Only detect one location change per narration
    
    # Detect time changes/advances
    for time_period, keywords in TIME_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                changes.append(EnvironmentChange(
                    change_type="time",
                    value=time_period,
                    details={"action": "set_period"}
                ))
                break
    
    # Detect time advancement
    for pattern, advance_type in TIME_ADVANCE_PATTERNS:
        match = pattern.search(text)
        if match:
            if advance_type == "hours":
                hours = int(match.group(1))
                changes.append(EnvironmentChange(
                    change_type="time",
                    value="advance",
                    details={"hours": hours}
                ))
            elif advance_type == "long_rest":
                changes.append(EnvironmentChange(
                    change_type="time",
                    value="advance",
                    details={"hours": 8}
                ))
            elif advance_type == "short_rest":
                changes.append(EnvironmentChange(
                    change_type="time",
                    value="advance",
                    details={"hours": 1}
                ))
            elif advance_type == "night":
                changes.append(EnvironmentChange(
                    change_type="time",
                    value="advance_to",
                    details={"target": "dawn"}
                ))
            elif advance_type == "dawn":
                changes.append(EnvironmentChange(
                    change_type="time",
                    value="set",
                    details={"hour": 6}
                ))
            break
    
    return changes


def detect_environment_changes(text: str) -> List[EnvironmentChange]:
    """
    Main entry point: detect all environment changes from AI narration.
    Prefers structured tags over natural language detection.
    """
    # First try structured tags
    structured = detect_structured_tags(text)
    if structured:
        return structured
    
    # Fall back to natural language detection
    return detect_natural_language(text)


# ============================================================================
# PARSING HELPERS
# ============================================================================

def parse_trap_string(trap_str: str) -> Dict[str, Any]:
    """Parse trap specification string."""
    trap_str_lower = trap_str.lower()
    result = {"raw": trap_str}
    
    # Check for known templates
    trap_templates = [
        "pit_trap", "pit trap", "poison_dart", "poison dart", "flame_jet",
        "flame jet", "spike_trap", "spike trap", "poison_gas", "poison gas",
        "net_trap", "net trap", "blade_trap", "blade trap", "swinging blade",
        "lightning_rune", "lightning rune", "alarm", "collapsing_ceiling",
        "collapsing ceiling"
    ]
    
    for template in trap_templates:
        if template.replace("_", " ") in trap_str_lower or template in trap_str_lower:
            result["template"] = template.replace(" ", "_")
            break
    
    # Check for DC
    dc_match = re.search(r"dc\s*(\d+)", trap_str_lower)
    if dc_match:
        result["dc"] = int(dc_match.group(1))
    
    # Check for trigger type
    triggers = ["pressure_plate", "tripwire", "proximity", "interaction", "magical"]
    for trigger in triggers:
        if trigger.replace("_", " ") in trap_str_lower or trigger in trap_str_lower:
            result["trigger"] = trigger
            break
    
    # Check for position/location description
    position_match = re.search(r"at\s+(?:the\s+)?([^,]+)", trap_str, re.IGNORECASE)
    if position_match:
        result["position_desc"] = position_match.group(1).strip()
    
    return result


def parse_hazard_string(hazard_str: str) -> Dict[str, Any]:
    """Parse hazard specification string."""
    hazard_str_lower = hazard_str.lower()
    result = {"raw": hazard_str}
    
    # Check for hazard types
    hazard_types = {
        "lava": "lava",
        "fire": "fire",
        "acid": "acid",
        "cold": "cold",
        "lightning": "lightning",
        "poison": "poison",
        "necrotic": "necrotic",
        "radiant": "radiant",
    }
    
    for keyword, hazard_type in hazard_types.items():
        if keyword in hazard_str_lower:
            result["type"] = hazard_type
            break
    
    # Check for damage
    damage_match = re.search(r"(\d+d\d+)\s*(\w+)?", hazard_str)
    if damage_match:
        result["damage"] = damage_match.group(1)
        if damage_match.group(2):
            result["damage_type"] = damage_match.group(2)
    
    return result


def parse_time_string(time_str: str) -> Dict[str, Any]:
    """Parse time specification string."""
    result = {"raw": time_str}
    time_lower = time_str.lower()
    
    # Check for rest first (before hour matching)
    if "long rest" in time_lower:
        result["action"] = "advance"
        result["hours"] = 8
        return result
    if "short rest" in time_lower:
        result["action"] = "advance"
        result["hours"] = 1
        return result
    
    # Range: "4 to 5 hours" → take average
    range_match = re.search(r"(\d+)\s*(?:to|-)\s*(\d+)\s*hours?", time_lower)
    if range_match:
        result["action"] = "advance"
        result["hours"] = (int(range_match.group(1)) + int(range_match.group(2))) // 2
        return result
    
    # Direct number: "3 hours", "about 3 hours"
    hours_match = re.search(r"(\d+)\s*hours?", time_lower)
    if hours_match:
        result["action"] = "advance"
        result["hours"] = int(hours_match.group(1))
        return result
    
    # Vague durations
    if "few" in time_lower and "hour" in time_lower:
        result["action"] = "advance"
        result["hours"] = 3
        return result
    if "several" in time_lower and "hour" in time_lower:
        result["action"] = "advance"
        result["hours"] = 5
        return result
    if "couple" in time_lower and "hour" in time_lower:
        result["action"] = "advance"
        result["hours"] = 2
        return result
    
    # Minutes: "30 minutes" = at least 1 hour
    min_match = re.search(r"(\d+)\s*minutes?", time_lower)
    if min_match:
        result["action"] = "advance"
        result["hours"] = max(1, int(min_match.group(1)) // 60)
        return result
    
    # Check for specific time periods
    time_periods = ["dawn", "morning", "midday", "afternoon", "evening", "dusk", "night"]
    for period in time_periods:
        if period in time_lower:
            result["action"] = "set_period"
            result["period"] = period
            return result
    
    result["action"] = "unknown"
    return result


def parse_environment_string(env_str: str) -> Dict[str, Any]:
    """Parse compound environment description."""
    result = {}
    env_lower = env_str.lower()
    
    # Check for location
    for loc_type, keywords in LOCATION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in env_lower:
                result["location"] = loc_type
                break
        if "location" in result:
            break
    
    # Check for lighting
    for light_level, keywords in LIGHTING_KEYWORDS.items():
        for keyword in keywords:
            if keyword in env_lower:
                result["lighting"] = light_level
                break
        if "lighting" in result:
            break
    
    # Check lighting descriptors
    if "dark" in env_lower and "lighting" not in result:
        result["lighting"] = "darkness"
    elif "dim" in env_lower and "lighting" not in result:
        result["lighting"] = "dim"
    elif "bright" in env_lower and "lighting" not in result:
        result["lighting"] = "bright"
    
    # Check for weather
    for weather_type, keywords in WEATHER_KEYWORDS.items():
        for keyword in keywords:
            if keyword in env_lower:
                result["weather"] = weather_type
                break
        if "weather" in result:
            break
    
    return result


# ============================================================================
# ENVIRONMENT APPLICATION
# ============================================================================

def apply_environment_changes(
    channel_id: str,
    changes: List[EnvironmentChange],
    current_location: str = ""
) -> List[str]:
    """
    Apply detected environment changes using environment_manager functions.
    Returns list of change descriptions for feedback.
    """
    from utils.environment_manager import (
        set_weather, set_lighting, create_trap_from_template,
        create_trap, create_hazard
    )
    
    results = []
    
    for change in changes:
        try:
            if change.change_type == "weather":
                weather_type = change.value
                intensity = change.details.get("intensity", 1)
                weather = set_weather(channel_id, weather_type, intensity)
                if weather:
                    results.append(f"🌤️ Weather changed to: {weather_type} (intensity {intensity})")
            
            elif change.change_type == "lighting":
                light_level = change.value
                source = change.details.get("source", "")
                set_lighting(channel_id, light_level, source)
                results.append(f"💡 Lighting changed to: {light_level}")
            
            elif change.change_type == "trap":
                template = change.details.get("template")
                if template:
                    trap = create_trap_from_template(
                        channel_id, template,
                        name=change.details.get("name"),
                        x=change.details.get("x", -1),
                        y=change.details.get("y", -1)
                    )
                    if trap:
                        results.append(f"⚠️ Trap placed: {trap.name}")
                else:
                    # Custom trap - use minimal creation
                    results.append(f"⚠️ Trap detected in narration (use /trap to define)")
            
            elif change.change_type == "hazard":
                hazard_type = change.value
                damage = change.details.get("damage", "1d6")
                hazard = create_hazard(
                    channel_id,
                    name=f"{hazard_type.title()} Hazard",
                    hazard_type=hazard_type,
                    damage=damage,
                    damage_type=change.details.get("damage_type", hazard_type)
                )
                if hazard:
                    results.append(f"☣️ Hazard created: {hazard.name}")
            
            elif change.change_type == "time":
                time_state = get_time_state(channel_id)
                action = change.details.get("action", change.value)
                
                if action == "advance":
                    hours = change.details.get("hours", 1)
                    time_state.advance(hours)
                    set_time_state(channel_id, time_state)
                    results.append(f"⏰ Time advanced by {hours} hour(s): {time_state.format_time()}")
                    
                    # Update lighting for outdoor locations if applicable
                    update_lighting_for_time(channel_id, time_state)
                
                elif action == "set_period":
                    period = change.details.get("period", change.value)
                    hour = period_to_hour(period)
                    time_state.hour = hour
                    set_time_state(channel_id, time_state)
                    results.append(f"⏰ Time set to {period}: {time_state.format_time()}")
                    
                    update_lighting_for_time(channel_id, time_state)
                
                elif action == "advance_to":
                    target = change.details.get("target", "dawn")
                    target_hour = period_to_hour(target)
                    if time_state.hour >= target_hour:
                        time_state.day += 1
                    time_state.hour = target_hour
                    set_time_state(channel_id, time_state)
                    results.append(f"⏰ Time advanced to {target}: {time_state.format_time()}")
                    
                    update_lighting_for_time(channel_id, time_state)
            
            elif change.change_type == "location":
                location = change.value
                set_current_location(channel_id, location)
                
                # Apply location preset if available
                preset_results = apply_location_preset(channel_id, location)
                if preset_results:
                    results.extend(preset_results)
                else:
                    results.append(f"📍 Location: {location}")
        
        except Exception as e:
            results.append(f"⚠️ Error applying {change.change_type}: {str(e)}")
    
    return results


def apply_location_preset(channel_id: str, location: str, override: bool = True) -> List[str]:
    """Apply environment preset for a location type.
    
    Args:
        channel_id: Discord channel ID
        location: Location name to apply preset for
        override: If False, skip preset if custom lighting has been manually set
    """
    from utils.environment_manager import set_weather, set_lighting, get_lighting
    
    if not override:
        current = get_lighting(channel_id)
        if current and current.source and current.source not in ("", "natural", "time_based"):
            return [f"📍 At: {location} (custom lighting preserved)"]
    
    results = []
    
    # Normalize location name and find matching preset
    location_lower = location.lower()
    preset = None
    preset_name = None
    
    for name, data in LOCATION_PRESETS.items():
        if name in location_lower:
            preset = data
            preset_name = name
            break
    
    if not preset:
        # Check for partial matches
        for name, data in LOCATION_PRESETS.items():
            if location_lower in name or name in location_lower:
                preset = data
                preset_name = name
                break
    
    if not preset:
        return [f"📍 Entered: {location}"]
    
    results.append(f"📍 Entered: {location} ({preset_name})")
    
    # Check for saved memory first
    memory = get_location_memory(channel_id, location)
    if memory:
        # Restore from memory
        if memory.weather_type:
            set_weather(channel_id, memory.weather_type, memory.weather_intensity)
            results.append(f"🌤️ Restored weather: {memory.weather_type}")
        
        set_lighting(channel_id, memory.lighting_level, memory.lighting_source)
        results.append(f"💡 Restored lighting: {memory.lighting_level}")
        
        return results
    
    # Apply preset
    is_outdoor = preset.get("is_outdoor", True)
    
    # Lighting
    lighting = preset.get("lighting", "bright")
    if lighting == "time_based":
        time_state = get_time_state(channel_id)
        lighting = time_state.get_lighting_for_outdoor()
    
    source = preset.get("lighting_source", "")
    set_lighting(channel_id, lighting, source)
    results.append(f"💡 Lighting: {lighting}")
    
    # Weather (only for outdoor or if specified)
    if is_outdoor or "weather" in preset:
        weather = preset.get("weather")
        if weather:
            set_weather(channel_id, weather, 1)
            results.append(f"🌤️ Weather: {weather}")
    
    # Save to memory
    new_memory = LocationMemory(
        location_name=location,
        weather_type=preset.get("weather"),
        lighting_level=lighting,
        lighting_source=source,
        is_outdoor=is_outdoor,
        terrain_zones=preset.get("terrain", []),
    )
    set_location_memory(channel_id, new_memory)
    
    return results


def period_to_hour(period: str) -> int:
    """Convert time period name to hour."""
    periods = {
        "dawn": 6,
        "morning": 8,
        "midday": 12,
        "noon": 12,
        "afternoon": 14,
        "evening": 18,
        "dusk": 20,
        "night": 22,
        "midnight": 0,
    }
    return periods.get(period.lower(), 8)


def update_lighting_for_time(channel_id: str, time_state: TimeState):
    """Update lighting based on time for outdoor locations."""
    from utils.environment_manager import set_lighting, get_lighting
    
    # Determine if current location is outdoor using preset/memory, not light source
    current_loc = get_current_location(channel_id)
    if current_loc:
        memory = get_location_memory(channel_id, current_loc)
        if memory and not memory.is_outdoor:
            return  # Don't change lighting in indoor locations
        # Check preset if no memory
        if not memory:
            loc_lower = current_loc.lower()
            for name, preset in LOCATION_PRESETS.items():
                if name in loc_lower or loc_lower in name:
                    if not preset.get("is_outdoor", True):
                        return  # Indoor preset — don't change lighting
                    break
    
    current = get_lighting(channel_id)
    new_level = time_state.get_lighting_for_outdoor()
    if current.light_level != new_level:
        set_lighting(channel_id, new_level, "natural")


# ============================================================================
# CONTEXT FOR AI
# ============================================================================

def get_world_context_for_ai(channel_id: str) -> str:
    """Get world state context for AI prompt."""
    time_state = get_time_state(channel_id)
    current_loc = get_current_location(channel_id)
    
    lines = []
    lines.append(f"**Time:** {time_state.get_time_of_day().title()}, {time_state.format_time()}")
    
    if current_loc:
        lines.append(f"**Current Location:** {current_loc}")
        memory = get_location_memory(channel_id, current_loc)
        if memory:
            if memory.is_outdoor:
                lines.append("(Outdoor area)")
            else:
                lines.append("(Indoor area)")
    
    return "\n".join(lines)


# ============================================================================
# MAIN PROCESSING FUNCTION
# ============================================================================

def process_narration_for_environment(
    channel_id: str,
    narration: str,
    current_location: str = ""
) -> Tuple[List[EnvironmentChange], List[str]]:
    """
    Main entry point: process AI narration for environment changes.
    
    Returns:
        Tuple of (detected changes, applied results)
    """
    # Detect changes
    changes = detect_environment_changes(narration)
    
    if not changes:
        return [], []
    
    # Apply changes
    results = apply_environment_changes(channel_id, changes, current_location)
    
    return changes, results
