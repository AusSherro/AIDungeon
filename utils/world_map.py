# ============================================================================
# WORLD MAP - Intelligent Travel & Location Tracking (Phase 14)
# ============================================================================
"""
This module provides:
1. Location graph with discovered/undiscovered tracking
2. Travel intent detection from player actions and AI narration
3. Automatic world map generation from exploration
4. Fast travel for known routes
5. Distance and terrain tracking between locations

Structured Tags:
- [TRAVEL: destination="Phandalin", distance=15, terrain=forest]
- [LOCATION_DISCOVERED: name="Ruined Tower", terrain=hills, poi=true]
- [ARRIVAL: "Phandalin"]
- [DISTANCE_REVEALED: from="Neverwinter" to="Phandalin" miles=100]
"""

import os
import json
import re
import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from datetime import datetime

# Try to import encounter_manager for travel system integration
try:
    from utils.encounter_manager import (
        start_travel, advance_travel, get_travel_status, clear_travel_state,
        TravelState, TERRAIN_MODIFIERS, TRAVEL_SPEEDS
    )
    HAS_ENCOUNTER_MANAGER = True
except ImportError:
    HAS_ENCOUNTER_MANAGER = False


# ============================================================================
# ENUMS
# ============================================================================

class LocationType(Enum):
    """Types of locations in the world."""
    CITY = "city"
    TOWN = "town"
    VILLAGE = "village"
    DUNGEON = "dungeon"
    CAVE = "cave"
    RUINS = "ruins"
    TOWER = "tower"
    CASTLE = "castle"
    FORTRESS = "fortress"
    TEMPLE = "temple"
    SHRINE = "shrine"
    CAMP = "camp"
    LANDMARK = "landmark"
    WILDERNESS = "wilderness"
    CROSSROADS = "crossroads"
    BRIDGE = "bridge"
    INN = "inn"
    MINE = "mine"
    FARM = "farm"
    PORT = "port"
    UNKNOWN = "unknown"


class DiscoveryStatus(Enum):
    """How much the party knows about a location."""
    UNKNOWN = "unknown"        # Just a name, no details
    HEARD_OF = "heard_of"      # Heard rumors about it
    KNOWN = "known"            # Know where it is, can travel there
    VISITED = "visited"        # Have been there
    EXPLORED = "explored"      # Fully explored


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Location:
    """A location in the world."""
    name: str
    terrain: str = "road"
    location_type: str = "unknown"
    description: str = ""
    status: str = "unknown"  # DiscoveryStatus value
    is_poi: bool = False  # Point of interest
    visited_count: int = 0
    first_visited: Optional[str] = None
    last_visited: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    connections: Dict[str, float] = field(default_factory=dict)  # {location_name: distance_miles}
    tags: List[str] = field(default_factory=list)  # "safe", "dangerous", "merchant", etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Location':
        return cls(**data)


@dataclass
class TravelIntent:
    """Detected travel intent from player action or AI narration."""
    destination: str
    distance: Optional[float] = None
    terrain: Optional[str] = None
    pace: str = "normal"
    source: str = "natural_language"  # "natural_language", "structured_tag", "command"
    confidence: float = 0.8


@dataclass
class LocationDiscovery:
    """A newly discovered location from AI narration."""
    name: str
    terrain: str = "wilderness"
    location_type: str = "unknown"
    description: str = ""
    is_poi: bool = False
    distance_from_current: Optional[float] = None


@dataclass
class WorldState:
    """The current state of the world map."""
    current_location: str = "Unknown"
    locations: Dict[str, Location] = field(default_factory=dict)
    travel_history: List[Dict[str, Any]] = field(default_factory=list)
    total_miles_traveled: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_location": self.current_location,
            "locations": {k: v.to_dict() for k, v in self.locations.items()},
            "travel_history": self.travel_history,
            "total_miles_traveled": self.total_miles_traveled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorldState':
        state = cls(
            current_location=data.get("current_location", "Unknown"),
            travel_history=data.get("travel_history", []),
            total_miles_traveled=data.get("total_miles_traveled", 0)
        )
        for name, loc_data in data.get("locations", {}).items():
            state.locations[name] = Location.from_dict(loc_data)
        return state


# ============================================================================
# DETECTION PATTERNS
# ============================================================================

# Structured tags from AI narration
TRAVEL_TAG_PATTERN = re.compile(
    r'\[TRAVEL:\s*destination\s*=\s*"([^"]+)"(?:\s*,\s*distance\s*=\s*(\d+(?:\.\d+)?))?' +
    r'(?:\s*,\s*terrain\s*=\s*(\w+))?\]',
    re.IGNORECASE
)

LOCATION_DISCOVERED_TAG_PATTERN = re.compile(
    r'\[LOCATION_DISCOVERED:\s*name\s*=\s*"([^"]+)"' +
    r'(?:\s*,\s*terrain\s*=\s*(\w+))?' +
    r'(?:\s*,\s*type\s*=\s*(\w+))?' +
    r'(?:\s*,\s*poi\s*=\s*(true|false))?\]',
    re.IGNORECASE
)

ARRIVAL_TAG_PATTERN = re.compile(
    r'\[ARRIVAL:\s*"([^"]+)"\]',
    re.IGNORECASE
)

DISTANCE_REVEALED_TAG_PATTERN = re.compile(
    r'\[DISTANCE_REVEALED:\s*from\s*=\s*"([^"]+)"\s*to\s*=\s*"([^"]+)"\s*miles\s*=\s*(\d+(?:\.\d+)?)\]',
    re.IGNORECASE
)

# Natural language travel patterns
TRAVEL_INTENT_PATTERNS = [
    # "We travel to Phandalin" / "Let's head to the forest"
    re.compile(
        r'\b(?:we|i|let\'?s?|party|group)\s+(?:travel|head|go|journey|walk|march|ride|trek|venture|make\s+(?:our|my)\s+way)\s+' +
        r'(?:to(?:ward)?|towards?|for|into|through)\s+(?:the\s+)?([A-Z][a-zA-Z\s\']+?)(?:\s*[,.]|$|\s+(?:to|and|in\s+search))',
        re.IGNORECASE
    ),
    # "Set out for Neverwinter" / "Head towards the mountains"
    re.compile(
        r'\b(?:set\s+out|depart|leave)\s+(?:for|to(?:ward)?|towards?)\s+(?:the\s+)?([A-Z][a-zA-Z\s\']+?)(?:\s*[,.]|$)',
        re.IGNORECASE
    ),
    # "Continue to Phandalin" / "Continue our journey to..."
    re.compile(
        r'\b(?:continue|resume|press\s+on)\s+(?:to(?:ward)?|towards?|our\s+journey\s+to)\s+(?:the\s+)?([A-Z][a-zA-Z\s\']+?)(?:\s*[,.]|$)',
        re.IGNORECASE
    ),
]

# AI narration patterns indicating travel/movement
AI_TRAVEL_NARRATION_PATTERNS = [
    # "The party travels for X hours/days"
    re.compile(
        r'(?:the\s+)?(?:party|group|you|adventurers?)\s+(?:travel|journey|trek|walk|march|ride)s?\s+' +
        r'(?:for\s+)?(\d+)\s+(hours?|days?)',
        re.IGNORECASE
    ),
    # "After X hours of travel, you reach..."
    re.compile(
        r'after\s+(\d+)\s+(hours?|days?)\s+(?:of\s+)?(?:travel|journey|walking|riding)',
        re.IGNORECASE
    ),
    # "You arrive at..."
    re.compile(
        r'\b(?:you|the\s+party|everyone)\s+(?:arrive|reach|come\s+to|enter)\s+(?:at\s+)?(?:the\s+)?([A-Z][a-zA-Z\s\']+)',
        re.IGNORECASE
    ),
]

# Location type detection from name/description
LOCATION_TYPE_KEYWORDS = {
    LocationType.CITY: ["city", "metropolis", "capital"],
    LocationType.TOWN: ["town", "township"],
    LocationType.VILLAGE: ["village", "hamlet", "settlement"],
    LocationType.DUNGEON: ["dungeon", "prison", "jail", "cells"],
    LocationType.CAVE: ["cave", "cavern", "grotto", "underground"],
    LocationType.RUINS: ["ruins", "ruined", "abandoned", "decrepit"],
    LocationType.TOWER: ["tower", "spire", "obelisk"],
    LocationType.CASTLE: ["castle", "palace", "keep", "stronghold"],
    LocationType.FORTRESS: ["fortress", "fort", "citadel", "bastion"],
    LocationType.TEMPLE: ["temple", "cathedral", "church", "monastery"],
    LocationType.SHRINE: ["shrine", "altar", "sanctuary"],
    LocationType.CAMP: ["camp", "campsite", "encampment"],
    LocationType.LANDMARK: ["landmark", "monument", "statue"],
    LocationType.CROSSROADS: ["crossroads", "intersection", "junction"],
    LocationType.BRIDGE: ["bridge", "crossing"],
    LocationType.INN: ["inn", "tavern", "pub", "waystation"],
    LocationType.MINE: ["mine", "quarry", "dig site"],
    LocationType.FARM: ["farm", "ranch", "homestead"],
    LocationType.PORT: ["port", "harbor", "dock", "pier"],
}

# Terrain detection from description
TERRAIN_KEYWORDS = {
    "forest": ["forest", "woods", "woodland", "grove", "trees"],
    "mountains": ["mountain", "peak", "cliff", "highland"],
    "hills": ["hill", "rolling", "foothills"],
    "plains": ["plain", "grassland", "meadow", "field", "prairie"],
    "swamp": ["swamp", "marsh", "bog", "wetland", "mire"],
    "desert": ["desert", "sand", "dunes", "arid", "wasteland"],
    "arctic": ["arctic", "tundra", "frozen", "ice", "snow"],
    "coastal": ["coast", "beach", "shore", "seaside"],
    "jungle": ["jungle", "rainforest", "tropical"],
    "underground": ["underground", "subterranean", "underdark", "cave"],
    "urban": ["city", "town", "village", "streets", "buildings"],
    "road": ["road", "path", "trail", "highway", "route"],
    "ruins": ["ruins", "ruined", "crumbling"],
}


# ============================================================================
# FILE OPERATIONS
# ============================================================================

def get_world_path(channel_id: str) -> str:
    """Get path to world map file for a channel."""
    os.makedirs("state", exist_ok=True)
    return os.path.join("state", f"world_{channel_id}.json")


def load_world_state(channel_id: str) -> WorldState:
    """Load world state from file."""
    path = get_world_path(channel_id)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return WorldState.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading world state: {e}")
    return WorldState()


def save_world_state(channel_id: str, state: WorldState):
    """Save world state to file."""
    path = get_world_path(channel_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state.to_dict(), f, indent=2)


# ============================================================================
# LOCATION MANAGEMENT
# ============================================================================

def add_location(
    channel_id: str,
    name: str,
    terrain: str = "wilderness",
    location_type: str = "unknown",
    description: str = "",
    is_poi: bool = False,
    status: str = "known",
    tags: Optional[List[str]] = None
) -> Location:
    """Add a new location to the world map."""
    state = load_world_state(channel_id)
    
    # Check if location already exists
    name_lower = name.lower()
    for existing_name in state.locations:
        if existing_name.lower() == name_lower:
            # Update existing location if we have new info
            existing = state.locations[existing_name]
            if description and not existing.description:
                existing.description = description
            if terrain != "wilderness" and existing.terrain == "wilderness":
                existing.terrain = terrain
            if location_type != "unknown" and existing.location_type == "unknown":
                existing.location_type = location_type
            if is_poi:
                existing.is_poi = True
            if status in ["known", "visited", "explored"]:
                # Only upgrade status, never downgrade
                status_order = ["unknown", "heard_of", "known", "visited", "explored"]
                if status_order.index(status) > status_order.index(existing.status):
                    existing.status = status
            save_world_state(channel_id, state)
            return existing
    
    # Create new location
    location = Location(
        name=name,
        terrain=terrain,
        location_type=location_type,
        description=description,
        status=status,
        is_poi=is_poi,
        tags=tags or []
    )
    
    state.locations[name] = location
    save_world_state(channel_id, state)
    return location


def get_location(channel_id: str, name: str) -> Optional[Location]:
    """Get a location by name (case-insensitive)."""
    state = load_world_state(channel_id)
    name_lower = name.lower()
    for loc_name, location in state.locations.items():
        if loc_name.lower() == name_lower:
            return location
    return None


def get_current_location(channel_id: str) -> str:
    """Get the party's current location."""
    state = load_world_state(channel_id)
    return state.current_location


def set_current_location(channel_id: str, location_name: str):
    """Set the party's current location."""
    state = load_world_state(channel_id)
    state.current_location = location_name
    
    # Mark as visited
    if location_name in state.locations:
        loc = state.locations[location_name]
        loc.visited_count += 1
        loc.last_visited = datetime.now().isoformat()
        if not loc.first_visited:
            loc.first_visited = datetime.now().isoformat()
        if loc.status in ["unknown", "heard_of", "known"]:
            loc.status = "visited"
    else:
        # Add new location as visited
        add_location(channel_id, location_name, status="visited")
    
    save_world_state(channel_id, state)


def connect_locations(
    channel_id: str,
    location1: str,
    location2: str,
    distance_miles: float,
    bidirectional: bool = True
):
    """Connect two locations with a known distance."""
    state = load_world_state(channel_id)
    
    # Ensure both locations exist
    if location1 not in state.locations:
        add_location(channel_id, location1)
        state = load_world_state(channel_id)
    if location2 not in state.locations:
        add_location(channel_id, location2)
        state = load_world_state(channel_id)
    
    state.locations[location1].connections[location2] = distance_miles
    if bidirectional:
        state.locations[location2].connections[location1] = distance_miles
    
    save_world_state(channel_id, state)


def get_distance(channel_id: str, from_loc: str, to_loc: str) -> Optional[float]:
    """Get known distance between two locations."""
    state = load_world_state(channel_id)
    
    if from_loc in state.locations:
        return state.locations[from_loc].connections.get(to_loc)
    return None


def get_all_locations(channel_id: str) -> Dict[str, Location]:
    """Get all known locations."""
    state = load_world_state(channel_id)
    return state.locations


def get_visited_locations(channel_id: str) -> List[Location]:
    """Get all visited locations."""
    state = load_world_state(channel_id)
    return [loc for loc in state.locations.values() if loc.status == "visited" or loc.status == "explored"]


def get_known_locations(channel_id: str) -> List[Location]:
    """Get all locations the party knows about (can travel to)."""
    state = load_world_state(channel_id)
    return [loc for loc in state.locations.values() if loc.status in ["known", "visited", "explored"]]


# ============================================================================
# TRAVEL INTENT DETECTION
# ============================================================================

def detect_structured_travel_tag(text: str) -> Optional[TravelIntent]:
    """Detect [TRAVEL: destination="...", distance=X, terrain=...] tag."""
    match = TRAVEL_TAG_PATTERN.search(text)
    if match:
        destination = match.group(1)
        distance = float(match.group(2)) if match.group(2) else None
        terrain = match.group(3) if match.group(3) else None
        
        return TravelIntent(
            destination=destination,
            distance=distance,
            terrain=terrain,
            source="structured_tag",
            confidence=1.0
        )
    return None


def detect_natural_language_travel(text: str) -> Optional[TravelIntent]:
    """Detect travel intent from natural language like 'we head to Phandalin'."""
    for pattern in TRAVEL_INTENT_PATTERNS:
        match = pattern.search(text)
        if match:
            destination = match.group(1).strip()
            # Clean up destination name
            destination = destination.rstrip('.,!?')
            
            # Skip if destination is too short or generic
            if len(destination) < 3:
                continue
            if destination.lower() in ["the", "a", "an", "it", "there"]:
                continue
            
            return TravelIntent(
                destination=destination,
                source="natural_language",
                confidence=0.7
            )
    return None


def detect_arrival_tag(text: str) -> Optional[str]:
    """Detect [ARRIVAL: "Location"] tag indicating party has arrived."""
    match = ARRIVAL_TAG_PATTERN.search(text)
    if match:
        return match.group(1)
    return None


def detect_location_discovered_tag(text: str) -> Optional[LocationDiscovery]:
    """Detect [LOCATION_DISCOVERED: name="...", terrain=..., type=..., poi=...] tag."""
    match = LOCATION_DISCOVERED_TAG_PATTERN.search(text)
    if match:
        name = match.group(1)
        terrain = match.group(2) or "wilderness"
        loc_type = match.group(3) or "unknown"
        is_poi = match.group(4) and match.group(4).lower() == "true"
        
        return LocationDiscovery(
            name=name,
            terrain=terrain,
            location_type=loc_type,
            is_poi=is_poi
        )
    return None


def detect_distance_revealed_tag(text: str) -> Optional[Tuple[str, str, float]]:
    """Detect [DISTANCE_REVEALED: from="A" to="B" miles=X] tag."""
    match = DISTANCE_REVEALED_TAG_PATTERN.search(text)
    if match:
        from_loc = match.group(1)
        to_loc = match.group(2)
        miles = float(match.group(3))
        return (from_loc, to_loc, miles)
    return None


def detect_ai_travel_narration(text: str) -> Optional[Dict[str, Any]]:
    """Detect travel progress or arrival from AI narration."""
    for pattern in AI_TRAVEL_NARRATION_PATTERNS:
        match = pattern.search(text)
        if match:
            groups = match.groups()
            
            # Check if this is an arrival pattern (has location name)
            if len(groups) >= 1 and not groups[0].isdigit():
                return {
                    "type": "arrival",
                    "location": groups[0].strip().rstrip('.,!?')
                }
            
            # Otherwise it's a travel duration
            if len(groups) >= 2:
                amount = int(groups[0])
                unit = groups[1].lower()
                hours = amount if "hour" in unit else amount * 8
                return {
                    "type": "travel_progress",
                    "hours": hours
                }
    return None


def detect_travel_intent(
    player_action: str,
    ai_narration: Optional[str] = None,
    channel_id: Optional[str] = None
) -> Optional[TravelIntent]:
    """
    Detect travel intent from player action or AI narration.
    
    Returns TravelIntent if travel should be initiated.
    """
    # First check for structured tag in player action
    intent = detect_structured_travel_tag(player_action)
    if intent:
        return intent
    
    # Check for structured tag in AI narration
    if ai_narration:
        intent = detect_structured_travel_tag(ai_narration)
        if intent:
            return intent
    
    # Check for natural language in player action
    intent = detect_natural_language_travel(player_action)
    if intent:
        # Try to get distance from world map if available
        if channel_id:
            current = get_current_location(channel_id)
            distance = get_distance(channel_id, current, intent.destination)
            if distance:
                intent.distance = distance
            
            # Try to get terrain from destination
            dest_loc = get_location(channel_id, intent.destination)
            if dest_loc:
                intent.terrain = dest_loc.terrain
        
        return intent
    
    return None


# ============================================================================
# TYPE DETECTION
# ============================================================================

def detect_location_type(name: str, description: str = "") -> str:
    """Detect location type from name and description."""
    combined = f"{name} {description}".lower()
    
    for loc_type, keywords in LOCATION_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in combined:
                return loc_type.value
    
    return "unknown"


def detect_terrain(name: str, description: str = "") -> str:
    """Detect terrain from name and description."""
    combined = f"{name} {description}".lower()
    
    for terrain, keywords in TERRAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword in combined:
                return terrain
    
    return "wilderness"


# ============================================================================
# TRAVEL PROCESSING
# ============================================================================

def process_narration_for_travel(
    channel_id: str,
    player_action: str,
    ai_narration: str
) -> Dict[str, Any]:
    """
    Process AI narration for travel-related events.
    
    Returns dict with:
    - travel_started: TravelIntent if travel was initiated
    - arrival: str location name if party arrived somewhere
    - locations_discovered: List[LocationDiscovery] of new locations
    - distances_revealed: List[Tuple[str, str, float]] of new distance info
    - travel_progress: Dict if travel time passed
    """
    result = {
        "travel_started": None,
        "arrival": None,
        "locations_discovered": [],
        "distances_revealed": [],
        "travel_progress": None
    }
    
    # Check for travel intent
    travel_intent = detect_travel_intent(player_action, ai_narration, channel_id)
    if travel_intent:
        result["travel_started"] = travel_intent
    
    # Check for arrival tag
    arrival = detect_arrival_tag(ai_narration)
    if arrival:
        result["arrival"] = arrival
        # Update current location
        set_current_location(channel_id, arrival)
        # Add to world map if not exists
        add_location(channel_id, arrival, status="visited")
    
    # Check for discovered locations
    # Look for multiple discoveries
    for match in LOCATION_DISCOVERED_TAG_PATTERN.finditer(ai_narration):
        discovery = detect_location_discovered_tag(match.group(0))
        if discovery:
            result["locations_discovered"].append(discovery)
            # Add to world map
            add_location(
                channel_id,
                discovery.name,
                terrain=discovery.terrain,
                location_type=discovery.location_type,
                is_poi=discovery.is_poi,
                status="heard_of"
            )
    
    # Check for distance revelations
    for match in DISTANCE_REVEALED_TAG_PATTERN.finditer(ai_narration):
        distance_info = detect_distance_revealed_tag(match.group(0))
        if distance_info:
            result["distances_revealed"].append(distance_info)
            # Update world map
            connect_locations(channel_id, distance_info[0], distance_info[1], distance_info[2])
    
    # Check for AI travel narration (time passing)
    travel_narration = detect_ai_travel_narration(ai_narration)
    if travel_narration:
        if travel_narration["type"] == "travel_progress":
            result["travel_progress"] = travel_narration
        elif travel_narration["type"] == "arrival" and not result["arrival"]:
            result["arrival"] = travel_narration["location"]
            set_current_location(channel_id, travel_narration["location"])
    
    return result


def start_travel_from_intent(
    channel_id: str,
    intent: TravelIntent
) -> Dict[str, Any]:
    """
    Start travel based on detected intent.
    
    Uses encounter_manager.start_travel() if available.
    """
    state = load_world_state(channel_id)
    current = state.current_location
    
    # Get or estimate distance
    distance = intent.distance
    if not distance:
        # Check world map for known distance
        distance = get_distance(channel_id, current, intent.destination)
    if not distance:
        # Estimate based on how well we know the destination
        dest_loc = get_location(channel_id, intent.destination)
        if dest_loc and dest_loc.status in ["visited", "explored"]:
            distance = 10.0  # Short distance for known places
        else:
            distance = 30.0  # Default unknown distance
    
    # Get or detect terrain
    terrain = intent.terrain
    if not terrain:
        dest_loc = get_location(channel_id, intent.destination)
        if dest_loc:
            terrain = dest_loc.terrain
        else:
            terrain = "road"
    
    # Record in travel history
    state.travel_history.append({
        "from": current,
        "to": intent.destination,
        "distance": distance,
        "terrain": terrain,
        "started": datetime.now().isoformat(),
        "source": intent.source
    })
    save_world_state(channel_id, state)
    
    # Start travel using encounter_manager if available
    if HAS_ENCOUNTER_MANAGER:
        travel_state = start_travel(
            channel_id=channel_id,
            origin=current,
            destination=intent.destination,
            distance_miles=distance,
            terrain=terrain,
            pace=intent.pace
        )
        return {
            "started": True,
            "origin": current,
            "destination": intent.destination,
            "distance": distance,
            "terrain": terrain,
            "pace": intent.pace,
            "travel_state": travel_state
        }
    else:
        return {
            "started": True,
            "origin": current,
            "destination": intent.destination,
            "distance": distance,
            "terrain": terrain,
            "pace": intent.pace,
            "travel_state": None
        }


def complete_travel(channel_id: str, destination: str) -> Dict[str, Any]:
    """Complete travel and update world state."""
    state = load_world_state(channel_id)
    previous_location = state.current_location
    
    # Update current location
    set_current_location(channel_id, destination)
    
    # Update travel history
    if state.travel_history:
        last_travel = state.travel_history[-1]
        if last_travel.get("to") == destination and not last_travel.get("completed"):
            last_travel["completed"] = datetime.now().isoformat()
            if last_travel.get("distance"):
                state.total_miles_traveled += last_travel["distance"]
    
    # Ensure locations are connected if we learned the distance
    if HAS_ENCOUNTER_MANAGER:
        travel_status = get_travel_status(channel_id)
        if travel_status:
            distance = travel_status.get("total_miles", travel_status.get("traveled_miles"))
            if distance:
                connect_locations(channel_id, previous_location, destination, distance)
            clear_travel_state(channel_id)
    
    save_world_state(channel_id, state)
    
    return {
        "completed": True,
        "previous_location": previous_location,
        "new_location": destination
    }


# ============================================================================
# FAST TRAVEL
# ============================================================================

def can_fast_travel(channel_id: str, destination: str) -> bool:
    """Check if party can fast travel to a destination."""
    loc = get_location(channel_id, destination)
    if not loc:
        return False
    
    # Can fast travel to visited or explored locations
    return loc.status in ["visited", "explored"]


def get_fast_travel_options(channel_id: str) -> List[Dict[str, Any]]:
    """Get list of locations available for fast travel."""
    state = load_world_state(channel_id)
    current = state.current_location
    
    options = []
    for name, loc in state.locations.items():
        if name == current:
            continue
        if loc.status in ["visited", "explored"]:
            distance = loc.connections.get(current)
            options.append({
                "name": name,
                "terrain": loc.terrain,
                "type": loc.location_type,
                "distance": distance,
                "visited_count": loc.visited_count
            })
    
    return sorted(options, key=lambda x: x.get("distance") or 999)


def fast_travel(channel_id: str, destination: str) -> Dict[str, Any]:
    """
    Execute fast travel to a known destination.
    
    Returns result with travel time but minimal encounter chance.
    """
    if not can_fast_travel(channel_id, destination):
        return {"error": f"Cannot fast travel to {destination}. Location must be visited first."}
    
    state = load_world_state(channel_id)
    current = state.current_location
    
    # Get distance
    dest_loc = state.locations.get(destination)
    distance = dest_loc.connections.get(current) if dest_loc else None
    
    if not distance:
        distance = 15.0  # Default for known but unmeasured routes
    
    terrain = dest_loc.terrain if dest_loc else "road"
    
    # Calculate travel time
    speed_mult = TERRAIN_MODIFIERS.get(terrain, {}).get("speed_mult", 1.0) if HAS_ENCOUNTER_MANAGER else 1.0
    hours = distance / (3 * speed_mult)  # Normal pace
    days = math.ceil(hours / 8)
    
    # Update state
    set_current_location(channel_id, destination)
    state = load_world_state(channel_id)
    state.total_miles_traveled += distance
    state.travel_history.append({
        "from": current,
        "to": destination,
        "distance": distance,
        "terrain": terrain,
        "started": datetime.now().isoformat(),
        "completed": datetime.now().isoformat(),
        "fast_travel": True
    })
    save_world_state(channel_id, state)
    
    return {
        "success": True,
        "previous_location": current,
        "new_location": destination,
        "distance": distance,
        "travel_time_hours": hours,
        "travel_time_days": days,
        "fast_travel": True
    }


# ============================================================================
# AI CONTEXT
# ============================================================================

def get_world_context_for_ai(channel_id: str) -> str:
    """Build world context for AI prompts."""
    state = load_world_state(channel_id)
    
    lines = [
        "## WORLD MAP CONTEXT",
        f"**Current Location:** {state.current_location}",
    ]
    
    # Add current location details
    current_loc = state.locations.get(state.current_location)
    if current_loc:
        if current_loc.description:
            lines.append(f"*{current_loc.description}*")
        lines.append(f"Terrain: {current_loc.terrain.title()}")
    
    # Add nearby/connected locations
    if current_loc and current_loc.connections:
        lines.append("")
        lines.append("**Known Nearby Locations:**")
        for dest, distance in sorted(current_loc.connections.items(), key=lambda x: x[1]):
            dest_loc = state.locations.get(dest)
            terrain_info = f" ({dest_loc.terrain})" if dest_loc else ""
            lines.append(f"  • {dest}: {distance:.1f} miles{terrain_info}")
    
    # Add other known locations
    other_known = [
        loc for name, loc in state.locations.items()
        if name != state.current_location
        and name not in (current_loc.connections if current_loc else {})
        and loc.status in ["known", "heard_of"]
    ]
    if other_known:
        lines.append("")
        lines.append("**Other Known Locations:**")
        for loc in other_known[:5]:
            status = "(rumors only)" if loc.status == "heard_of" else ""
            lines.append(f"  • {loc.name} {status}")
    
    lines.append("")
    lines.append(f"**Total Miles Traveled:** {state.total_miles_traveled:.0f}")
    
    return "\n".join(lines)


def get_travel_instructions_for_ai() -> str:
    """Get AI instructions for travel tags."""
    return """
## TRAVEL & LOCATION TAGS

When the party travels or discovers new locations, use these tags:

**Starting Travel:**
When the party begins traveling to a destination:
`[TRAVEL: destination="Location Name", distance=15, terrain=forest]`

**Discovering Locations:**
When NPCs mention or party discovers a new location:
`[LOCATION_DISCOVERED: name="Ruined Tower", terrain=hills, type=ruins, poi=true]`

**Arriving at Destination:**
When the party arrives at their destination:
`[ARRIVAL: "Location Name"]`

**Distance Information:**
When distance between locations is revealed:
`[DISTANCE_REVEALED: from="Neverwinter" to="Phandalin" miles=100]`

**Example Narration:**
"The innkeeper tells you about a ruined tower in the hills, about a day's journey east.
[LOCATION_DISCOVERED: name="Shadowspire Tower", terrain=hills, type=ruins, poi=true]
[DISTANCE_REVEALED: from="Phandalin" to="Shadowspire Tower" miles=25]"

"After traveling through the forest, you finally see the walls of Phandalin.
[ARRIVAL: "Phandalin"]"
"""


# ============================================================================
# FORMATTING
# ============================================================================

def format_location(loc: Location) -> str:
    """Format a single location for display."""
    status_emoji = {
        "unknown": "❓",
        "heard_of": "👂",
        "known": "📍",
        "visited": "✅",
        "explored": "🗺️"
    }
    
    emoji = status_emoji.get(loc.status, "❓")
    poi = "⭐ " if loc.is_poi else ""
    
    lines = [
        f"{emoji} **{poi}{loc.name}**",
        f"Type: {loc.location_type.title()} | Terrain: {loc.terrain.title()}"
    ]
    
    if loc.description:
        lines.append(f"*{loc.description}*")
    
    if loc.visited_count > 0:
        lines.append(f"Visited: {loc.visited_count} time(s)")
    
    if loc.connections:
        lines.append("Connections:")
        for dest, dist in sorted(loc.connections.items(), key=lambda x: x[1]):
            lines.append(f"  → {dest}: {dist:.1f} miles")
    
    if loc.tags:
        lines.append(f"Tags: {', '.join(loc.tags)}")
    
    return "\n".join(lines)


def format_world_map(channel_id: str) -> str:
    """Format the full world map for display."""
    state = load_world_state(channel_id)
    
    lines = [
        "🗺️ **WORLD MAP**",
        f"Current Location: **{state.current_location}**",
        f"Total Miles Traveled: {state.total_miles_traveled:.0f}",
        ""
    ]
    
    if not state.locations:
        lines.append("*No locations discovered yet.*")
        return "\n".join(lines)
    
    # Group by status
    explored = [loc for loc in state.locations.values() if loc.status == "explored"]
    visited = [loc for loc in state.locations.values() if loc.status == "visited"]
    known = [loc for loc in state.locations.values() if loc.status == "known"]
    heard_of = [loc for loc in state.locations.values() if loc.status == "heard_of"]
    
    if explored:
        lines.append("**🗺️ Fully Explored:**")
        for loc in explored:
            poi = "⭐ " if loc.is_poi else ""
            lines.append(f"  {poi}{loc.name} ({loc.terrain})")
    
    if visited:
        lines.append("")
        lines.append("**✅ Visited:**")
        for loc in visited:
            poi = "⭐ " if loc.is_poi else ""
            lines.append(f"  {poi}{loc.name} ({loc.terrain})")
    
    if known:
        lines.append("")
        lines.append("**📍 Known Locations:**")
        for loc in known:
            poi = "⭐ " if loc.is_poi else ""
            lines.append(f"  {poi}{loc.name} ({loc.terrain})")
    
    if heard_of:
        lines.append("")
        lines.append("**👂 Heard Of:**")
        for loc in heard_of:
            lines.append(f"  {loc.name}")
    
    return "\n".join(lines)


def format_travel_result(result: Dict[str, Any]) -> str:
    """Format travel result for display."""
    if "error" in result:
        return f"❌ {result['error']}"
    
    if result.get("fast_travel"):
        lines = [
            f"⚡ **Fast Travel Complete**",
            f"From: {result['previous_location']}",
            f"To: {result['new_location']}",
            f"Distance: {result['distance']:.1f} miles",
            f"Travel Time: {result['travel_time_days']} day(s)",
        ]
    elif result.get("started"):
        lines = [
            f"🚶 **Journey Begun**",
            f"From: {result['origin']}",
            f"To: {result['destination']}",
            f"Distance: {result['distance']:.1f} miles",
            f"Terrain: {result['terrain'].title()}",
            f"Pace: {result['pace'].title()}",
        ]
    elif result.get("completed"):
        lines = [
            f"🏁 **Arrived at {result['new_location']}**",
            f"Previous Location: {result['previous_location']}",
        ]
    else:
        return str(result)
    
    return "\n".join(lines)
