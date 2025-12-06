"""
Environment Manager - Traps, Hazards, Weather, Lighting, and Terrain Effects

Provides comprehensive environmental automation for D&D 5e:
- Trap placement, detection, triggering, and damage
- Weather conditions affecting combat and exploration
- Light levels and vision (darkvision, blindsight, etc.)
- Terrain effects (difficult terrain, cover, elevation)
- Hazard zones (lava, acid, magical effects)
"""

import os
import json
import re
import random
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from threading import Lock
from datetime import datetime

# ============================================================================
# ENUMS
# ============================================================================

class TrapTrigger(Enum):
    """How a trap is triggered."""
    PROXIMITY = "proximity"          # Entering a space
    PRESSURE_PLATE = "pressure_plate"  # Stepping on specific tile
    TRIPWIRE = "tripwire"            # Crossing a line
    INTERACTION = "interaction"       # Opening/touching something
    MAGICAL = "magical"              # Detecting magic or specific spell
    TIMED = "timed"                  # Goes off after X rounds


class TrapType(Enum):
    """Types of traps."""
    DART = "dart"
    PIT = "pit"
    SPIKE = "spike"
    POISON_GAS = "poison_gas"
    ROLLING_BOULDER = "rolling_boulder"
    FLAME = "flame"
    FROST = "frost"
    LIGHTNING = "lightning"
    ALARM = "alarm"
    NET = "net"
    MAGICAL = "magical"
    BLADE = "blade"
    COLLAPSING = "collapsing"


class WeatherType(Enum):
    """Weather conditions."""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    FOG = "fog"
    DENSE_FOG = "dense_fog"
    SNOW = "snow"
    BLIZZARD = "blizzard"
    HAIL = "hail"
    SANDSTORM = "sandstorm"
    EXTREME_HEAT = "extreme_heat"
    EXTREME_COLD = "extreme_cold"
    WIND = "wind"
    STRONG_WIND = "strong_wind"


class LightLevel(Enum):
    """Lighting conditions."""
    BRIGHT = "bright"              # Normal daylight
    DIM = "dim"                    # Twilight, torchlight at edge
    DARKNESS = "darkness"          # No light
    MAGICAL_DARKNESS = "magical_darkness"  # Darkness spell, blocks darkvision


class CoverType(Enum):
    """Cover levels."""
    NONE = "none"
    HALF = "half"                  # +2 AC, +2 Dex saves
    THREE_QUARTERS = "three_quarters"  # +5 AC, +5 Dex saves
    FULL = "full"                  # Can't be targeted directly


class TerrainType(Enum):
    """Terrain types with mechanical effects."""
    NORMAL = "normal"
    DIFFICULT = "difficult"        # Costs 2x movement
    WATER_SHALLOW = "water_shallow"  # Difficult terrain
    WATER_DEEP = "water_deep"      # Swimming required
    ICE = "ice"                    # Difficult + Dex save or fall
    LAVA = "lava"                  # Damage on entry
    ACID = "acid"                  # Damage on entry
    MAGICAL = "magical"            # Custom effect
    RUBBLE = "rubble"              # Difficult terrain
    MUD = "mud"                    # Difficult + may get stuck
    WEBS = "webs"                  # Difficult + may get restrained


class HazardType(Enum):
    """Environmental hazards."""
    FIRE = "fire"
    LAVA = "lava"
    ACID = "acid"
    POISON_CLOUD = "poison_cloud"
    MAGICAL_ZONE = "magical_zone"
    EXTREME_TEMPERATURE = "extreme_temperature"
    SUFFOCATION = "suffocation"
    FALLING = "falling"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Trap:
    """A trap in the environment."""
    name: str
    trap_type: str  # TrapType value
    trigger: str    # TrapTrigger value
    dc: int         # DC to detect and/or disarm
    save_type: str  # DEX, CON, WIS, etc.
    save_dc: int    # DC for saving throw when triggered
    damage_dice: str  # e.g., "2d10"
    damage_type: str  # piercing, fire, poison, etc.
    x: int = -1     # Position on map (-1 = anywhere/narrative)
    y: int = -1
    radius: int = 0  # Area of effect in squares (0 = single target)
    detected: bool = False
    triggered: bool = False
    disarmed: bool = False
    one_shot: bool = True  # Does it reset?
    description: str = ""
    effects: List[str] = field(default_factory=list)  # Additional effects: restrained, prone, etc.
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Trap':
        data = data.copy()
        if 'effects' not in data:
            data['effects'] = []
        return cls(**data)


@dataclass
class Hazard:
    """An environmental hazard zone."""
    name: str
    hazard_type: str  # HazardType value
    damage_dice: str
    damage_type: str
    save_type: str = "CON"
    save_dc: int = 15
    x: int = -1
    y: int = -1
    width: int = 1
    height: int = 1
    duration_rounds: int = -1  # -1 = permanent
    rounds_remaining: int = -1
    trigger_on_entry: bool = True
    trigger_on_start_turn: bool = True
    trigger_on_end_turn: bool = False
    description: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Hazard':
        return cls(**data)


@dataclass
class WeatherCondition:
    """Current weather conditions."""
    weather_type: str  # WeatherType value
    intensity: int = 1  # 1-3, affects severity
    duration_hours: int = -1  # -1 = indefinite
    effects: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WeatherCondition':
        data = data.copy()
        if 'effects' not in data:
            data['effects'] = {}
        return cls(**data)


@dataclass
class LightingCondition:
    """Current lighting in an area."""
    light_level: str  # LightLevel value
    source: str = ""  # What's providing light
    radius: int = 0   # Radius in feet (0 = entire area)
    x: int = -1       # Light source position
    y: int = -1
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LightingCondition':
        return cls(**data)


@dataclass
class EnvironmentState:
    """Complete environmental state for a channel."""
    traps: List[Trap] = field(default_factory=list)
    hazards: List[Hazard] = field(default_factory=list)
    weather: Optional[WeatherCondition] = None
    lighting: LightingCondition = field(default_factory=lambda: LightingCondition(light_level="bright"))
    terrain_zones: List[Dict] = field(default_factory=list)  # Custom terrain zones
    
    def to_dict(self) -> dict:
        return {
            "traps": [t.to_dict() for t in self.traps],
            "hazards": [h.to_dict() for h in self.hazards],
            "weather": self.weather.to_dict() if self.weather else None,
            "lighting": self.lighting.to_dict(),
            "terrain_zones": self.terrain_zones,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EnvironmentState':
        traps = [Trap.from_dict(t) for t in data.get("traps", [])]
        hazards = [Hazard.from_dict(h) for h in data.get("hazards", [])]
        weather = WeatherCondition.from_dict(data["weather"]) if data.get("weather") else None
        lighting = LightingCondition.from_dict(data.get("lighting", {"light_level": "bright"}))
        terrain_zones = data.get("terrain_zones", [])
        return cls(traps=traps, hazards=hazards, weather=weather, lighting=lighting, terrain_zones=terrain_zones)


# ============================================================================
# TRAP TEMPLATES
# ============================================================================

TRAP_TEMPLATES = {
    "pit_trap": {
        "name": "Pit Trap",
        "trap_type": "pit",
        "trigger": "pressure_plate",
        "dc": 15,
        "save_type": "DEX",
        "save_dc": 12,
        "damage_dice": "2d6",
        "damage_type": "bludgeoning",
        "description": "A concealed pit opens beneath your feet!",
        "effects": ["prone"],
    },
    "poison_dart": {
        "name": "Poison Dart Trap",
        "trap_type": "dart",
        "trigger": "tripwire",
        "dc": 13,
        "save_type": "CON",
        "save_dc": 13,
        "damage_dice": "1d4",
        "damage_type": "piercing",
        "description": "Darts shoot from hidden holes in the walls!",
        "effects": ["poisoned"],  # On failed save
    },
    "flame_jet": {
        "name": "Flame Jet",
        "trap_type": "flame",
        "trigger": "proximity",
        "dc": 14,
        "save_type": "DEX",
        "save_dc": 14,
        "damage_dice": "4d6",
        "damage_type": "fire",
        "radius": 2,
        "description": "Jets of flame erupt from the floor!",
    },
    "spike_trap": {
        "name": "Spiked Pit",
        "trap_type": "spike",
        "trigger": "pressure_plate",
        "dc": 15,
        "save_type": "DEX",
        "save_dc": 13,
        "damage_dice": "3d6",
        "damage_type": "piercing",
        "description": "The floor gives way to a pit filled with sharpened spikes!",
        "effects": ["prone"],
    },
    "poison_gas": {
        "name": "Poison Gas Trap",
        "trap_type": "poison_gas",
        "trigger": "interaction",
        "dc": 16,
        "save_type": "CON",
        "save_dc": 15,
        "damage_dice": "3d6",
        "damage_type": "poison",
        "radius": 3,
        "description": "A cloud of noxious green gas fills the area!",
        "effects": ["poisoned"],
    },
    "net_trap": {
        "name": "Net Trap",
        "trap_type": "net",
        "trigger": "tripwire",
        "dc": 12,
        "save_type": "DEX",
        "save_dc": 12,
        "damage_dice": "0",
        "damage_type": "none",
        "description": "A heavy net falls from above!",
        "effects": ["restrained"],
    },
    "blade_trap": {
        "name": "Swinging Blade",
        "trap_type": "blade",
        "trigger": "proximity",
        "dc": 14,
        "save_type": "DEX",
        "save_dc": 14,
        "damage_dice": "3d8",
        "damage_type": "slashing",
        "description": "A massive blade swings down from the ceiling!",
        "one_shot": False,  # Resets
    },
    "lightning_rune": {
        "name": "Lightning Rune",
        "trap_type": "magical",
        "trigger": "magical",
        "dc": 18,
        "save_type": "DEX",
        "save_dc": 16,
        "damage_dice": "5d8",
        "damage_type": "lightning",
        "radius": 2,
        "description": "A magical rune crackles with lightning!",
    },
    "alarm": {
        "name": "Alarm Trap",
        "trap_type": "alarm",
        "trigger": "proximity",
        "dc": 12,
        "save_type": "DEX",
        "save_dc": 0,
        "damage_dice": "0",
        "damage_type": "none",
        "description": "A magical alarm sounds throughout the area!",
        "effects": ["alerted_enemies"],
    },
    "collapsing_ceiling": {
        "name": "Collapsing Ceiling",
        "trap_type": "collapsing",
        "trigger": "interaction",
        "dc": 17,
        "save_type": "DEX",
        "save_dc": 15,
        "damage_dice": "4d10",
        "damage_type": "bludgeoning",
        "radius": 3,
        "description": "The ceiling begins to collapse!",
        "effects": ["prone", "difficult_terrain"],
    },
}


# ============================================================================
# WEATHER EFFECTS
# ============================================================================

WEATHER_EFFECTS = {
    "clear": {
        "name": "Clear",
        "description": "Clear skies with good visibility.",
        "perception_mod": 0,
        "ranged_mod": 0,
        "movement_mod": 1.0,
    },
    "cloudy": {
        "name": "Cloudy",
        "description": "Overcast skies.",
        "perception_mod": 0,
        "ranged_mod": 0,
        "movement_mod": 1.0,
    },
    "rain": {
        "name": "Rain",
        "description": "Steady rain falls, reducing visibility and making surfaces slick.",
        "perception_mod": -2,
        "ranged_mod": 0,
        "movement_mod": 1.0,
        "extinguishes_flames": True,
        "disadvantage": ["perception_hearing"],
    },
    "heavy_rain": {
        "name": "Heavy Rain",
        "description": "Torrential downpour severely limits visibility.",
        "perception_mod": -5,
        "ranged_mod": -2,
        "movement_mod": 0.75,
        "extinguishes_flames": True,
        "lightly_obscured": True,
        "disadvantage": ["perception", "ranged_beyond_normal"],
    },
    "thunderstorm": {
        "name": "Thunderstorm",
        "description": "Thunder, lightning, and heavy rain create chaos.",
        "perception_mod": -5,
        "ranged_mod": -2,
        "movement_mod": 0.75,
        "extinguishes_flames": True,
        "heavily_obscured_far": True,
        "disadvantage": ["perception", "concentration"],
        "lightning_risk": True,
    },
    "fog": {
        "name": "Fog",
        "description": "Mist reduces visibility.",
        "perception_mod": -3,
        "ranged_mod": -2,
        "lightly_obscured": True,
        "vision_range_feet": 60,
    },
    "dense_fog": {
        "name": "Dense Fog",
        "description": "Thick fog severely limits sight.",
        "perception_mod": -5,
        "ranged_mod": -5,
        "heavily_obscured": True,
        "vision_range_feet": 30,
        "disadvantage": ["ranged_attacks"],
    },
    "snow": {
        "name": "Snow",
        "description": "Snowfall creates difficult terrain and reduces visibility.",
        "perception_mod": -2,
        "ranged_mod": 0,
        "movement_mod": 0.75,
        "difficult_terrain": True,
    },
    "blizzard": {
        "name": "Blizzard",
        "description": "Blinding snow and freezing wind.",
        "perception_mod": -5,
        "ranged_mod": -5,
        "movement_mod": 0.5,
        "heavily_obscured": True,
        "difficult_terrain": True,
        "cold_damage_per_hour": "1d4",
        "disadvantage": ["perception", "ranged_attacks"],
    },
    "sandstorm": {
        "name": "Sandstorm",
        "description": "Whipping sand stings exposed skin and blinds travelers.",
        "perception_mod": -5,
        "ranged_mod": -5,
        "movement_mod": 0.5,
        "heavily_obscured": True,
        "damage_per_round": "1d4",
        "damage_type": "slashing",
        "disadvantage": ["perception", "ranged_attacks"],
    },
    "extreme_heat": {
        "name": "Extreme Heat",
        "description": "Oppressive heat saps strength.",
        "con_save_dc": 10,
        "con_save_interval": "hour",
        "exhaustion_on_fail": True,
        "water_required": True,
    },
    "extreme_cold": {
        "name": "Extreme Cold",
        "description": "Bitter cold threatens frostbite.",
        "con_save_dc": 10,
        "con_save_interval": "hour",
        "cold_damage_on_fail": "1d4",
        "cold_resistance_immunity": True,
    },
    "wind": {
        "name": "Wind",
        "description": "Strong wind affects ranged attacks.",
        "ranged_mod": -2,
        "disadvantage": ["ranged_attacks_long"],
    },
    "strong_wind": {
        "name": "Strong Wind",
        "description": "Gale-force winds threaten to knock creatures down.",
        "ranged_mod": -5,
        "movement_mod": 0.75,
        "disadvantage": ["ranged_attacks", "flying"],
        "strength_save_dc": 10,
        "prone_on_fail": True,
    },
}


# ============================================================================
# LIGHTING EFFECTS
# ============================================================================

LIGHT_EFFECTS = {
    "bright": {
        "name": "Bright Light",
        "description": "Normal visibility.",
        "perception_mod": 0,
        "stealth_mod": 0,
    },
    "dim": {
        "name": "Dim Light",
        "description": "Lightly obscured. Disadvantage on Perception checks relying on sight.",
        "lightly_obscured": True,
        "perception_mod": -5,
        "stealth_mod": 2,
        "disadvantage": ["perception_sight"],
    },
    "darkness": {
        "name": "Darkness",
        "description": "Heavily obscured. Effectively blind without darkvision.",
        "heavily_obscured": True,
        "blinded_without_darkvision": True,
        "auto_fail_sight_checks": True,
        "stealth_mod": 5,
        "advantage": ["stealth"],
        "disadvantage": ["attack_rolls_without_darkvision"],
    },
    "magical_darkness": {
        "name": "Magical Darkness",
        "description": "Even darkvision cannot pierce this darkness.",
        "heavily_obscured": True,
        "blinded": True,
        "blocks_darkvision": True,
        "auto_fail_sight_checks": True,
    },
}


# ============================================================================
# TERRAIN EFFECTS
# ============================================================================

TERRAIN_EFFECTS = {
    "normal": {
        "name": "Normal Terrain",
        "movement_cost": 1,
    },
    "difficult": {
        "name": "Difficult Terrain",
        "movement_cost": 2,
    },
    "water_shallow": {
        "name": "Shallow Water",
        "movement_cost": 2,
        "extinguishes_fire": True,
    },
    "water_deep": {
        "name": "Deep Water",
        "movement_cost": 2,
        "requires_swimming": True,
        "disadvantage": ["melee_attacks"],
    },
    "ice": {
        "name": "Ice",
        "movement_cost": 2,
        "dex_save_dc": 10,
        "prone_on_fail": True,
    },
    "lava": {
        "name": "Lava",
        "movement_cost": 2,
        "damage_on_entry": "10d10",
        "damage_on_start_turn": "10d10",
        "damage_type": "fire",
    },
    "acid": {
        "name": "Acid Pool",
        "movement_cost": 2,
        "damage_on_entry": "4d6",
        "damage_on_start_turn": "4d6",
        "damage_type": "acid",
    },
    "rubble": {
        "name": "Rubble",
        "movement_cost": 2,
        "cover": "half",
    },
    "mud": {
        "name": "Mud",
        "movement_cost": 2,
        "strength_save_dc": 12,
        "restrained_on_fail": True,
    },
    "webs": {
        "name": "Webs",
        "movement_cost": 4,
        "dex_save_dc": 12,
        "restrained_on_fail": True,
        "flammable": True,
    },
}


# ============================================================================
# COVER BONUSES
# ============================================================================

COVER_BONUSES = {
    "none": {"ac": 0, "dex_save": 0},
    "half": {"ac": 2, "dex_save": 2},
    "three_quarters": {"ac": 5, "dex_save": 5},
    "full": {"ac": None, "dex_save": None, "cannot_target": True},
}


# ============================================================================
# STORAGE
# ============================================================================

ENVIRONMENT_DIR = os.path.join(os.path.dirname(__file__), '..', 'state', 'environment')
os.makedirs(ENVIRONMENT_DIR, exist_ok=True)
_env_locks = {}


def _get_env_path(channel_id: str) -> str:
    return os.path.join(ENVIRONMENT_DIR, f'{channel_id}_env.json')


def load_environment(channel_id: str) -> EnvironmentState:
    """Load environment state for a channel."""
    path = _get_env_path(channel_id)
    if not os.path.exists(path):
        return EnvironmentState()
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return EnvironmentState.from_dict(data)
    except Exception:
        return EnvironmentState()


def save_environment(channel_id: str, env: EnvironmentState):
    """Save environment state for a channel."""
    path = _get_env_path(channel_id)
    lock = _env_locks.setdefault(channel_id, Lock())
    
    with lock:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(env.to_dict(), f, indent=2)


# ============================================================================
# TRAP MANAGEMENT
# ============================================================================

def create_trap(
    channel_id: str,
    name: str,
    trap_type: str = "pit",
    trigger: str = "pressure_plate",
    dc: int = 15,
    save_type: str = "DEX",
    save_dc: int = 13,
    damage_dice: str = "2d6",
    damage_type: str = "bludgeoning",
    x: int = -1,
    y: int = -1,
    radius: int = 0,
    description: str = "",
    effects: List[str] = None,
    one_shot: bool = True,
) -> Trap:
    """Create and add a trap to the environment."""
    env = load_environment(channel_id)
    
    trap = Trap(
        name=name,
        trap_type=trap_type,
        trigger=trigger,
        dc=dc,
        save_type=save_type,
        save_dc=save_dc,
        damage_dice=damage_dice,
        damage_type=damage_type,
        x=x,
        y=y,
        radius=radius,
        description=description,
        effects=effects or [],
        one_shot=one_shot,
    )
    
    env.traps.append(trap)
    save_environment(channel_id, env)
    return trap


def create_trap_from_template(
    channel_id: str,
    template: str,
    x: int = -1,
    y: int = -1,
    **overrides
) -> Optional[Trap]:
    """Create a trap from a template."""
    if template not in TRAP_TEMPLATES:
        return None
    
    template_data = TRAP_TEMPLATES[template].copy()
    template_data.update(overrides)
    template_data['x'] = x
    template_data['y'] = y
    
    return create_trap(channel_id, **template_data)


def get_trap(channel_id: str, trap_name: str) -> Optional[Trap]:
    """Get a trap by name."""
    env = load_environment(channel_id)
    for trap in env.traps:
        if trap.name.lower() == trap_name.lower():
            return trap
    return None


def get_traps_at_position(channel_id: str, x: int, y: int) -> List[Trap]:
    """Get all traps at a specific position."""
    env = load_environment(channel_id)
    return [t for t in env.traps if t.x == x and t.y == y and not t.triggered and not t.disarmed]


def detect_trap(channel_id: str, trap_name: str, perception_roll: int) -> Dict[str, Any]:
    """Attempt to detect a trap with a Perception check."""
    env = load_environment(channel_id)
    
    for trap in env.traps:
        if trap.name.lower() == trap_name.lower():
            if trap.detected:
                return {"success": True, "already_detected": True, "trap": trap}
            
            if perception_roll >= trap.dc:
                trap.detected = True
                save_environment(channel_id, env)
                return {"success": True, "trap": trap}
            else:
                return {"success": False, "dc": trap.dc, "roll": perception_roll}
    
    return {"error": f"Trap '{trap_name}' not found"}


def disarm_trap(channel_id: str, trap_name: str, check_roll: int) -> Dict[str, Any]:
    """Attempt to disarm a trap with a Thieves' Tools or DEX check."""
    env = load_environment(channel_id)
    
    for trap in env.traps:
        if trap.name.lower() == trap_name.lower():
            if trap.disarmed:
                return {"success": True, "already_disarmed": True}
            if trap.triggered:
                return {"error": "Trap has already been triggered"}
            
            # Disarm DC is usually same as detect DC or slightly higher
            disarm_dc = trap.dc + 2
            
            if check_roll >= disarm_dc:
                trap.disarmed = True
                save_environment(channel_id, env)
                return {"success": True, "trap": trap}
            elif check_roll < disarm_dc - 5:
                # Critical failure - trigger the trap
                return {"success": False, "triggered": True, "trap": trap}
            else:
                return {"success": False, "dc": disarm_dc, "roll": check_roll}
    
    return {"error": f"Trap '{trap_name}' not found"}


def trigger_trap(channel_id: str, trap_name: str, targets: List[str]) -> Dict[str, Any]:
    """Trigger a trap and calculate damage for targets."""
    env = load_environment(channel_id)
    
    for trap in env.traps:
        if trap.name.lower() == trap_name.lower():
            if trap.triggered and trap.one_shot:
                return {"error": "Trap has already been triggered and doesn't reset"}
            if trap.disarmed:
                return {"error": "Trap has been disarmed"}
            
            trap.triggered = True
            save_environment(channel_id, env)
            
            return {
                "trap": trap,
                "targets": targets,
                "save_type": trap.save_type,
                "save_dc": trap.save_dc,
                "damage_dice": trap.damage_dice,
                "damage_type": trap.damage_type,
                "effects": trap.effects,
                "description": trap.description,
                "radius": trap.radius,
            }
    
    return {"error": f"Trap '{trap_name}' not found"}


def check_trap_triggers(channel_id: str, x: int, y: int, trigger_type: str = "proximity") -> List[Trap]:
    """Check if any traps are triggered at a position."""
    env = load_environment(channel_id)
    triggered = []
    
    for trap in env.traps:
        if trap.disarmed or (trap.triggered and trap.one_shot):
            continue
        
        # Check trigger type match
        if trap.trigger != trigger_type and trigger_type != "any":
            continue
        
        # Check position
        if trap.x != -1 and trap.y != -1:
            # Trap has specific position
            if trap.x == x and trap.y == y:
                triggered.append(trap)
            elif trap.radius > 0:
                # Check if in radius
                distance = max(abs(trap.x - x), abs(trap.y - y))
                if distance <= trap.radius:
                    triggered.append(trap)
    
    return triggered


def remove_trap(channel_id: str, trap_name: str) -> bool:
    """Remove a trap from the environment."""
    env = load_environment(channel_id)
    original_count = len(env.traps)
    env.traps = [t for t in env.traps if t.name.lower() != trap_name.lower()]
    
    if len(env.traps) < original_count:
        save_environment(channel_id, env)
        return True
    return False


def list_traps(channel_id: str, include_triggered: bool = False) -> List[Trap]:
    """List all traps in the environment."""
    env = load_environment(channel_id)
    if include_triggered:
        return env.traps
    return [t for t in env.traps if not t.triggered or not t.one_shot]


# ============================================================================
# HAZARD MANAGEMENT
# ============================================================================

def create_hazard(
    channel_id: str,
    name: str,
    hazard_type: str = "fire",
    damage_dice: str = "2d6",
    damage_type: str = "fire",
    save_type: str = "DEX",
    save_dc: int = 15,
    x: int = -1,
    y: int = -1,
    width: int = 1,
    height: int = 1,
    duration_rounds: int = -1,
    trigger_on_entry: bool = True,
    trigger_on_start_turn: bool = True,
    trigger_on_end_turn: bool = False,
    description: str = "",
) -> Hazard:
    """Create and add a hazard zone."""
    env = load_environment(channel_id)
    
    hazard = Hazard(
        name=name,
        hazard_type=hazard_type,
        damage_dice=damage_dice,
        damage_type=damage_type,
        save_type=save_type,
        save_dc=save_dc,
        x=x,
        y=y,
        width=width,
        height=height,
        duration_rounds=duration_rounds,
        rounds_remaining=duration_rounds,
        trigger_on_entry=trigger_on_entry,
        trigger_on_start_turn=trigger_on_start_turn,
        trigger_on_end_turn=trigger_on_end_turn,
        description=description,
    )
    
    env.hazards.append(hazard)
    save_environment(channel_id, env)
    return hazard


def get_hazards_at_position(channel_id: str, x: int, y: int) -> List[Hazard]:
    """Get all hazards covering a position."""
    env = load_environment(channel_id)
    hazards = []
    
    for h in env.hazards:
        if h.x == -1 and h.y == -1:
            # Narrative hazard, affects whole area
            hazards.append(h)
        elif h.x <= x < h.x + h.width and h.y <= y < h.y + h.height:
            hazards.append(h)
    
    return hazards


def process_hazard_damage(
    channel_id: str,
    target_name: str,
    x: int,
    y: int,
    trigger_type: str = "entry"  # entry, start_turn, end_turn
) -> List[Dict[str, Any]]:
    """Process hazard damage for a target at a position."""
    hazards = get_hazards_at_position(channel_id, x, y)
    damage_results = []
    
    for hazard in hazards:
        should_trigger = False
        if trigger_type == "entry" and hazard.trigger_on_entry:
            should_trigger = True
        elif trigger_type == "start_turn" and hazard.trigger_on_start_turn:
            should_trigger = True
        elif trigger_type == "end_turn" and hazard.trigger_on_end_turn:
            should_trigger = True
        
        if should_trigger:
            damage_results.append({
                "hazard": hazard.name,
                "target": target_name,
                "damage_dice": hazard.damage_dice,
                "damage_type": hazard.damage_type,
                "save_type": hazard.save_type,
                "save_dc": hazard.save_dc,
                "description": hazard.description,
            })
    
    return damage_results


def tick_hazard_durations(channel_id: str) -> List[str]:
    """Tick down hazard durations, return names of expired hazards."""
    env = load_environment(channel_id)
    expired = []
    
    for hazard in env.hazards:
        if hazard.duration_rounds > 0:
            hazard.rounds_remaining -= 1
            if hazard.rounds_remaining <= 0:
                expired.append(hazard.name)
    
    # Remove expired hazards
    env.hazards = [h for h in env.hazards if h.name not in expired]
    save_environment(channel_id, env)
    
    return expired


def remove_hazard(channel_id: str, hazard_name: str) -> bool:
    """Remove a hazard from the environment."""
    env = load_environment(channel_id)
    original_count = len(env.hazards)
    env.hazards = [h for h in env.hazards if h.name.lower() != hazard_name.lower()]
    
    if len(env.hazards) < original_count:
        save_environment(channel_id, env)
        return True
    return False


def list_hazards(channel_id: str) -> List[Hazard]:
    """List all hazards in the environment."""
    env = load_environment(channel_id)
    return env.hazards


# ============================================================================
# WEATHER MANAGEMENT
# ============================================================================

def set_weather(channel_id: str, weather_type: str, intensity: int = 1, duration_hours: int = -1) -> Optional[WeatherCondition]:
    """Set the current weather condition."""
    if weather_type not in WEATHER_EFFECTS:
        return None
    
    env = load_environment(channel_id)
    effects = WEATHER_EFFECTS[weather_type].copy()
    
    weather = WeatherCondition(
        weather_type=weather_type,
        intensity=max(1, min(3, intensity)),
        duration_hours=duration_hours,
        effects=effects,
    )
    
    env.weather = weather
    save_environment(channel_id, env)
    return weather


def get_weather(channel_id: str) -> Optional[WeatherCondition]:
    """Get current weather conditions."""
    env = load_environment(channel_id)
    return env.weather


def clear_weather(channel_id: str):
    """Clear weather back to default."""
    env = load_environment(channel_id)
    env.weather = None
    save_environment(channel_id, env)


def get_weather_effects(channel_id: str) -> Dict[str, Any]:
    """Get mechanical effects of current weather."""
    env = load_environment(channel_id)
    if not env.weather:
        return WEATHER_EFFECTS["clear"]
    
    effects = env.weather.effects.copy()
    
    # Intensity modifiers
    intensity = env.weather.intensity
    if intensity >= 2:
        effects["perception_mod"] = effects.get("perception_mod", 0) - 2
        effects["ranged_mod"] = effects.get("ranged_mod", 0) - 1
    if intensity >= 3:
        effects["perception_mod"] = effects.get("perception_mod", 0) - 2
        effects["ranged_mod"] = effects.get("ranged_mod", 0) - 2
        effects["movement_mod"] = effects.get("movement_mod", 1.0) * 0.75
    
    return effects


# ============================================================================
# LIGHTING MANAGEMENT
# ============================================================================

def set_lighting(channel_id: str, light_level: str, source: str = "", radius: int = 0, x: int = -1, y: int = -1) -> LightingCondition:
    """Set the current lighting condition."""
    env = load_environment(channel_id)
    
    lighting = LightingCondition(
        light_level=light_level,
        source=source,
        radius=radius,
        x=x,
        y=y,
    )
    
    env.lighting = lighting
    save_environment(channel_id, env)
    return lighting


def get_lighting(channel_id: str) -> LightingCondition:
    """Get current lighting conditions."""
    env = load_environment(channel_id)
    return env.lighting


def get_lighting_effects(channel_id: str) -> Dict[str, Any]:
    """Get mechanical effects of current lighting."""
    env = load_environment(channel_id)
    light_level = env.lighting.light_level
    
    if light_level in LIGHT_EFFECTS:
        return LIGHT_EFFECTS[light_level]
    return LIGHT_EFFECTS["bright"]


def check_vision(
    channel_id: str,
    creature_vision: List[str],  # ["normal", "darkvision_60", "blindsight_30", etc.]
    target_x: int = -1,
    target_y: int = -1,
) -> Dict[str, Any]:
    """Check if a creature can see in current conditions."""
    env = load_environment(channel_id)
    lighting = env.lighting
    
    result = {
        "can_see": True,
        "lightly_obscured": False,
        "heavily_obscured": False,
        "disadvantage_perception": False,
        "advantage_stealth_against": False,
    }
    
    # Check lighting level
    if lighting.light_level == "darkness":
        # Check for darkvision
        has_darkvision = any("darkvision" in v for v in creature_vision)
        has_blindsight = any("blindsight" in v for v in creature_vision)
        has_truesight = any("truesight" in v for v in creature_vision)
        
        if has_truesight or has_blindsight:
            result["can_see"] = True
        elif has_darkvision:
            # Darkvision treats darkness as dim light
            result["lightly_obscured"] = True
            result["disadvantage_perception"] = True
        else:
            result["can_see"] = False
            result["heavily_obscured"] = True
    
    elif lighting.light_level == "magical_darkness":
        # Only truesight can see through magical darkness
        has_truesight = any("truesight" in v for v in creature_vision)
        has_blindsight = any("blindsight" in v for v in creature_vision)
        
        if has_truesight:
            result["can_see"] = True
        elif has_blindsight:
            result["can_see"] = True  # Blindsight works
        else:
            result["can_see"] = False
            result["heavily_obscured"] = True
    
    elif lighting.light_level == "dim":
        result["lightly_obscured"] = True
        result["disadvantage_perception"] = True
        result["advantage_stealth_against"] = True
    
    # Apply weather effects
    if env.weather:
        weather_effects = env.weather.effects
        if weather_effects.get("heavily_obscured"):
            result["heavily_obscured"] = True
            result["can_see"] = False
        elif weather_effects.get("lightly_obscured"):
            result["lightly_obscured"] = True
            result["disadvantage_perception"] = True
    
    return result


# ============================================================================
# TERRAIN MANAGEMENT
# ============================================================================

def add_terrain_zone(
    channel_id: str,
    name: str,
    terrain_type: str,
    x: int,
    y: int,
    width: int = 1,
    height: int = 1,
) -> Dict[str, Any]:
    """Add a terrain zone to the environment."""
    if terrain_type not in TERRAIN_EFFECTS:
        return {"error": f"Unknown terrain type: {terrain_type}"}
    
    env = load_environment(channel_id)
    
    zone = {
        "name": name,
        "terrain_type": terrain_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "effects": TERRAIN_EFFECTS[terrain_type],
    }
    
    env.terrain_zones.append(zone)
    save_environment(channel_id, env)
    return zone


def get_terrain_at_position(channel_id: str, x: int, y: int) -> Dict[str, Any]:
    """Get terrain effects at a specific position."""
    env = load_environment(channel_id)
    
    # Check custom terrain zones
    for zone in env.terrain_zones:
        if zone["x"] <= x < zone["x"] + zone["width"] and zone["y"] <= y < zone["y"] + zone["height"]:
            return zone["effects"]
    
    return TERRAIN_EFFECTS["normal"]


def get_movement_cost(channel_id: str, x: int, y: int) -> int:
    """Get movement cost for a position (1 = normal, 2 = difficult)."""
    terrain = get_terrain_at_position(channel_id, x, y)
    return terrain.get("movement_cost", 1)


def check_terrain_effects(channel_id: str, target_name: str, x: int, y: int) -> List[Dict[str, Any]]:
    """Check for terrain effects when entering a position."""
    terrain = get_terrain_at_position(channel_id, x, y)
    effects = []
    
    if terrain.get("damage_on_entry"):
        effects.append({
            "type": "damage",
            "target": target_name,
            "damage_dice": terrain["damage_on_entry"],
            "damage_type": terrain.get("damage_type", "fire"),
            "terrain": terrain.get("name", "hazardous terrain"),
        })
    
    if terrain.get("dex_save_dc"):
        effects.append({
            "type": "save",
            "target": target_name,
            "save_type": "DEX",
            "dc": terrain["dex_save_dc"],
            "effect_on_fail": "prone" if terrain.get("prone_on_fail") else "restrained",
            "terrain": terrain.get("name", "difficult terrain"),
        })
    
    if terrain.get("strength_save_dc"):
        effects.append({
            "type": "save",
            "target": target_name,
            "save_type": "STR",
            "dc": terrain["strength_save_dc"],
            "effect_on_fail": "restrained" if terrain.get("restrained_on_fail") else "prone",
            "terrain": terrain.get("name", "difficult terrain"),
        })
    
    return effects


def remove_terrain_zone(channel_id: str, zone_name: str) -> bool:
    """Remove a terrain zone."""
    env = load_environment(channel_id)
    original_count = len(env.terrain_zones)
    env.terrain_zones = [z for z in env.terrain_zones if z.get("name", "").lower() != zone_name.lower()]
    
    if len(env.terrain_zones) < original_count:
        save_environment(channel_id, env)
        return True
    return False


def list_terrain_zones(channel_id: str) -> List[Dict]:
    """List all custom terrain zones."""
    env = load_environment(channel_id)
    return env.terrain_zones


# ============================================================================
# COVER CALCULATIONS
# ============================================================================

def get_cover_bonus(cover_type: str) -> Dict[str, Any]:
    """Get AC and Dex save bonuses for cover type."""
    return COVER_BONUSES.get(cover_type, COVER_BONUSES["none"])


def calculate_cover(
    attacker_x: int,
    attacker_y: int,
    target_x: int,
    target_y: int,
    obstacles: List[Dict],  # List of {x, y, cover_type}
) -> str:
    """Calculate cover between attacker and target based on obstacles."""
    # Simple line-of-sight check
    dx = target_x - attacker_x
    dy = target_y - attacker_y
    steps = max(abs(dx), abs(dy))
    
    if steps == 0:
        return "none"
    
    best_cover = "none"
    cover_order = ["none", "half", "three_quarters", "full"]
    
    for i in range(1, steps):
        check_x = attacker_x + (dx * i // steps)
        check_y = attacker_y + (dy * i // steps)
        
        for obstacle in obstacles:
            if obstacle["x"] == check_x and obstacle["y"] == check_y:
                obstacle_cover = obstacle.get("cover_type", "half")
                if cover_order.index(obstacle_cover) > cover_order.index(best_cover):
                    best_cover = obstacle_cover
    
    return best_cover


# ============================================================================
# ENVIRONMENT CONTEXT FOR AI
# ============================================================================

def get_environment_context_for_ai(channel_id: str) -> str:
    """Build environment context for AI prompts."""
    env = load_environment(channel_id)
    lines = []
    
    # Lighting
    lighting = env.lighting
    if lighting.light_level != "bright":
        light_effects = LIGHT_EFFECTS.get(lighting.light_level, {})
        lines.append(f"**Lighting:** {light_effects.get('name', lighting.light_level)} - {light_effects.get('description', '')}")
    
    # Weather
    if env.weather:
        weather_effects = env.weather.effects
        lines.append(f"**Weather:** {weather_effects.get('name', env.weather.weather_type)} (intensity {env.weather.intensity}) - {weather_effects.get('description', '')}")
    
    # Active hazards
    if env.hazards:
        lines.append("**Hazards:**")
        for h in env.hazards:
            duration = f" ({h.rounds_remaining} rounds)" if h.duration_rounds > 0 else ""
            lines.append(f"- {h.name}: {h.damage_dice} {h.damage_type} damage{duration}")
    
    # Known traps (detected ones)
    detected_traps = [t for t in env.traps if t.detected and not t.triggered and not t.disarmed]
    if detected_traps:
        lines.append("**Detected Traps:**")
        for t in detected_traps:
            lines.append(f"- {t.name} ({t.trap_type})")
    
    # Terrain zones
    if env.terrain_zones:
        lines.append("**Terrain:**")
        for zone in env.terrain_zones:
            effects = zone.get("effects", {})
            lines.append(f"- {zone['name']}: {effects.get('name', zone['terrain_type'])}")
    
    return "\n".join(lines) if lines else ""


# ============================================================================
# FORMATTING
# ============================================================================

def format_trap_info(trap: Trap) -> str:
    """Format trap information for display."""
    status = "⚠️ Active"
    if trap.disarmed:
        status = "✅ Disarmed"
    elif trap.triggered:
        status = "💥 Triggered"
    elif trap.detected:
        status = "👁️ Detected"
    else:
        status = "❓ Hidden"
    
    lines = [
        f"**{trap.name}** ({trap.trap_type}) - {status}",
        f"Trigger: {trap.trigger} | Detection DC: {trap.dc}",
        f"Save: {trap.save_type} DC {trap.save_dc}",
        f"Damage: {trap.damage_dice} {trap.damage_type}",
    ]
    
    if trap.effects:
        lines.append(f"Effects: {', '.join(trap.effects)}")
    
    if trap.description:
        lines.append(f"*{trap.description}*")
    
    if trap.x >= 0 and trap.y >= 0:
        lines.append(f"Position: ({trap.x}, {trap.y})")
    
    return "\n".join(lines)


def format_hazard_info(hazard: Hazard) -> str:
    """Format hazard information for display."""
    lines = [
        f"**{hazard.name}** ({hazard.hazard_type})",
        f"Damage: {hazard.damage_dice} {hazard.damage_type}",
        f"Save: {hazard.save_type} DC {hazard.save_dc}",
    ]
    
    triggers = []
    if hazard.trigger_on_entry:
        triggers.append("on entry")
    if hazard.trigger_on_start_turn:
        triggers.append("start of turn")
    if hazard.trigger_on_end_turn:
        triggers.append("end of turn")
    lines.append(f"Triggers: {', '.join(triggers)}")
    
    if hazard.duration_rounds > 0:
        lines.append(f"Duration: {hazard.rounds_remaining} rounds remaining")
    
    if hazard.x >= 0 and hazard.y >= 0:
        lines.append(f"Area: ({hazard.x}, {hazard.y}) to ({hazard.x + hazard.width - 1}, {hazard.y + hazard.height - 1})")
    
    if hazard.description:
        lines.append(f"*{hazard.description}*")
    
    return "\n".join(lines)


def format_weather_info(weather: WeatherCondition) -> str:
    """Format weather information for display."""
    effects = weather.effects
    lines = [
        f"**{effects.get('name', weather.weather_type)}** (Intensity {weather.intensity}/3)",
        f"*{effects.get('description', '')}*",
    ]
    
    if effects.get("perception_mod"):
        lines.append(f"Perception: {effects['perception_mod']:+d}")
    if effects.get("ranged_mod"):
        lines.append(f"Ranged attacks: {effects['ranged_mod']:+d}")
    if effects.get("movement_mod") and effects["movement_mod"] != 1.0:
        lines.append(f"Movement: {int(effects['movement_mod'] * 100)}%")
    if effects.get("difficult_terrain"):
        lines.append("Creates difficult terrain")
    if effects.get("disadvantage"):
        lines.append(f"Disadvantage on: {', '.join(effects['disadvantage'])}")
    
    return "\n".join(lines)


def format_lighting_info(lighting: LightingCondition) -> str:
    """Format lighting information for display."""
    effects = LIGHT_EFFECTS.get(lighting.light_level, {})
    lines = [
        f"**{effects.get('name', lighting.light_level)}**",
        f"*{effects.get('description', '')}*",
    ]
    
    if lighting.source:
        lines.append(f"Source: {lighting.source}")
    if lighting.radius > 0:
        lines.append(f"Radius: {lighting.radius} feet")
    
    return "\n".join(lines)


def format_environment_summary(channel_id: str) -> str:
    """Format complete environment summary for display."""
    env = load_environment(channel_id)
    sections = []
    
    # Lighting
    lighting_info = format_lighting_info(env.lighting)
    sections.append(f"🔦 **LIGHTING**\n{lighting_info}")
    
    # Weather
    if env.weather:
        weather_info = format_weather_info(env.weather)
        sections.append(f"🌦️ **WEATHER**\n{weather_info}")
    
    # Traps
    if env.traps:
        trap_lines = []
        for trap in env.traps:
            status = "❓" if not trap.detected else ("✅" if trap.disarmed else ("💥" if trap.triggered else "⚠️"))
            trap_lines.append(f"{status} {trap.name} ({trap.trap_type})")
        sections.append(f"⚙️ **TRAPS**\n" + "\n".join(trap_lines))
    
    # Hazards
    if env.hazards:
        hazard_lines = []
        for hazard in env.hazards:
            duration = f" [{hazard.rounds_remaining}r]" if hazard.duration_rounds > 0 else ""
            hazard_lines.append(f"☠️ {hazard.name}: {hazard.damage_dice} {hazard.damage_type}{duration}")
        sections.append(f"💀 **HAZARDS**\n" + "\n".join(hazard_lines))
    
    # Terrain
    if env.terrain_zones:
        terrain_lines = []
        for zone in env.terrain_zones:
            terrain_lines.append(f"🗺️ {zone['name']} ({zone['terrain_type']})")
        sections.append(f"🏔️ **TERRAIN**\n" + "\n".join(terrain_lines))
    
    return "\n\n".join(sections) if sections else "No environmental effects active."
