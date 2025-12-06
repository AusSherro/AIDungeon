"""
Resource Manager for AI Dungeon Master
Handles automatic detection and consumption of character resources:
- Spell slots when spells are cast
- Class resources (Ki, Rage, Bardic Inspiration, etc.)
- Ammunition for ranged weapons
- Consumable items (potions, scrolls)
"""

import re
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass, field

# Import D&D 5e data for spell/ability detection
try:
    from .dnd5e_data import SPELLS, get_spell, CLASSES, get_class_data
    DND_DATA_AVAILABLE = True
except ImportError:
    SPELLS = {}
    DND_DATA_AVAILABLE = False

try:
    from .character_manager import (
        load_character, save_character, use_spell_slot,
        get_ability_modifier, remove_from_inventory
    )
except ImportError:
    pass


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ResourceConsumption:
    """Represents a detected resource consumption from narrative."""
    resource_type: str  # 'spell_slot', 'ki', 'rage', 'bardic_inspiration', etc.
    resource_name: str  # Name of specific resource (spell name, ability name)
    amount: int = 1     # Amount consumed
    level: Optional[int] = None  # For spell slots, the level used
    success: bool = False  # Whether consumption succeeded
    message: str = ""   # User-facing message about the consumption
    
    
@dataclass
class DetectedSpell:
    """Represents a spell detected in narrative text."""
    name: str
    level: int
    is_cantrip: bool
    match_text: str  # The text that triggered the detection
    confidence: float = 1.0  # How confident we are this is a spell cast


@dataclass
class DetectedAbility:
    """Represents a class ability detected in narrative text."""
    name: str
    class_name: str
    resource_type: str  # 'ki', 'rage', 'bardic_inspiration', etc.
    cost: int = 1
    match_text: str = ""


@dataclass
class DetectedConsumable:
    """Represents a consumable item usage detected in narrative."""
    item_name: str
    item_type: str  # 'potion', 'scroll', 'ammunition', 'other'
    quantity: int = 1
    match_text: str = ""


# =============================================================================
# SPELL DETECTION PATTERNS
# =============================================================================

# Patterns that indicate spell casting
SPELL_CAST_PATTERNS = [
    r"(?:I |i )?cast(?:s|ing)?\s+(?:the\s+)?(?:spell\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
    r"(?:I |i )?use(?:s|ing)?\s+(?:my\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:spell|cantrip)",
    r"(?:I |i )?invoke(?:s|ing)?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
    r"(?:I |i )?chant(?:s|ing)?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
    r"(?:with |using )?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+spell",
    r"(?:I |i )?unleash(?:es|ing)?\s+(?:a\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
]

# Spell name variations/aliases
SPELL_ALIASES = {
    "fireball": "Fireball",
    "fire ball": "Fireball",
    "magic missile": "Magic Missile",
    "magic missiles": "Magic Missile",
    "cure wounds": "Cure Wounds",
    "healing word": "Healing Word",
    "eldritch blast": "Eldritch Blast",
    "sacred flame": "Sacred Flame",
    "guiding bolt": "Guiding Bolt",
    "thunderwave": "Thunderwave",
    "thunder wave": "Thunderwave",
    "shield": "Shield",
    "misty step": "Misty Step",
    "counterspell": "Counterspell",
    "counter spell": "Counterspell",
    "dispel magic": "Dispel Magic",
    "hold person": "Hold Person",
    "hold monster": "Hold Monster",
    "lightning bolt": "Lightning Bolt",
    "chromatic orb": "Chromatic Orb",
    "mage armor": "Mage Armor",
    "detect magic": "Detect Magic",
    "identify": "Identify",
    "sleep": "Sleep",
    "charm person": "Charm Person",
    "invisibility": "Invisibility",
    "fly": "Fly",
    "haste": "Haste",
    "bless": "Bless",
    "bane": "Bane",
    "hex": "Hex",
    "hunter's mark": "Hunter's Mark",
    "hunters mark": "Hunter's Mark",
    "smite": "Divine Smite",  # Special handling
    "divine smite": "Divine Smite",
    "lay on hands": "Lay on Hands",
    "wild shape": "Wild Shape",
}


# =============================================================================
# CLASS ABILITY PATTERNS
# =============================================================================

# Class-specific ability detection patterns
CLASS_ABILITY_PATTERNS = {
    "barbarian": {
        "rage": {
            "patterns": [
                r"(?:I |i )?(?:enter|go into|activate|start)\s+(?:a\s+)?rage",
                r"(?:I |i )?rage\b",
                r"(?:I |i )?(?:become|am|go)\s+(?:enraged|berserk)",
                r"raging",
            ],
            "resource": "rages_used",
            "max_resource": "rages_per_day",
        },
        "reckless_attack": {
            "patterns": [
                r"(?:I |i )?(?:attack|strike)\s+recklessly",
                r"reckless attack",
            ],
            "resource": None,  # No resource cost, just tracking
        },
    },
    "bard": {
        "bardic_inspiration": {
            "patterns": [
                r"(?:I |i )?(?:give|grant|use|spend)\s+(?:my\s+)?bardic inspiration",
                r"(?:I |i )?inspire\s+(?:\w+)\s+(?:with|using)\s+(?:my\s+)?(?:music|song|words)",
                r"bardic inspiration die",
            ],
            "resource": "bardic_inspiration_used",
            "max_resource": "cha_mod",  # CHA modifier times per long rest
        },
    },
    "cleric": {
        "channel_divinity": {
            "patterns": [
                r"(?:I |i )?(?:use|invoke|channel)\s+(?:my\s+)?channel divinity",
                r"(?:I |i )?(?:turn|destroy)\s+undead",
            ],
            "resource": "channel_divinity_used",
            "max_resource": 1,  # 1 at level 1-5, 2 at 6+, 3 at 18+
        },
    },
    "druid": {
        "wild_shape": {
            "patterns": [
                r"(?:I |i )?(?:use|activate)\s+wild shape",
                r"(?:I |i )?(?:transform|change|shift)\s+into\s+(?:a\s+)?(\w+)",
                r"(?:I |i )?wild shape\s+into",
            ],
            "resource": "wild_shape_uses",
            "max_resource": 2,
        },
    },
    "fighter": {
        "action_surge": {
            "patterns": [
                r"(?:I |i )?(?:use|activate)\s+action surge",
                r"action surge",
            ],
            "resource": "action_surge_used",
            "max_resource": 1,  # 2 at level 17+
        },
        "second_wind": {
            "patterns": [
                r"(?:I |i )?(?:use|activate)\s+second wind",
                r"second wind",
            ],
            "resource": "second_wind_used",
            "max_resource": 1,
        },
    },
    "monk": {
        "ki": {
            "patterns": [
                r"(?:I |i )?(?:spend|use)\s+(?:\d+\s+)?ki\s+(?:point|points)?",
                r"flurry of blows",
                r"patient defense",
                r"step of the wind",
                r"stunning strike",
            ],
            "resource": "ki_used",
            "max_resource": "level",
            "costs": {
                "flurry of blows": 1,
                "patient defense": 1,
                "step of the wind": 1,
                "stunning strike": 1,
            },
        },
    },
    "paladin": {
        "divine_smite": {
            "patterns": [
                r"(?:I |i )?(?:use|invoke|channel)\s+(?:divine\s+)?smite",
                r"divine smite",
                r"smite(?:s)?\s+(?:the|with)",
            ],
            "resource": "spell_slot",  # Uses spell slots
            "default_level": 1,
        },
        "lay_on_hands": {
            "patterns": [
                r"(?:I |i )?(?:use|invoke)\s+lay on hands",
                r"lay(?:s)?\s+(?:my\s+)?hands\s+on",
            ],
            "resource": "lay_on_hands_pool",
            "max_resource": "level * 5",
        },
        "channel_divinity": {
            "patterns": [
                r"(?:I |i )?(?:use|invoke|channel)\s+(?:my\s+)?channel divinity",
            ],
            "resource": "channel_divinity_used",
            "max_resource": 1,
        },
    },
    "sorcerer": {
        "sorcery_points": {
            "patterns": [
                r"(?:I |i )?(?:spend|use)\s+(?:\d+\s+)?sorcery\s+points?",
                r"metamagic",
                r"quickened spell",
                r"twinned spell",
                r"empowered spell",
                r"subtle spell",
            ],
            "resource": "sorcery_points_used",
            "max_resource": "level",
        },
    },
    "warlock": {
        # Warlocks use pact magic (short rest slots)
        "pact_magic": {
            "patterns": [],  # Detected through spell casting
            "resource": "pact_slots_used",
        },
    },
}


# =============================================================================
# CONSUMABLE DETECTION PATTERNS
# =============================================================================

CONSUMABLE_PATTERNS = {
    "potion": {
        "patterns": [
            r"(?:I |i )?(?:drink|quaff|consume|use)\s+(?:a\s+|my\s+)?(?:potion\s+of\s+)?(\w+(?:\s+\w+)*)\s+potion",
            r"(?:I |i )?(?:drink|quaff|consume|use)\s+(?:a\s+|my\s+)?potion\s+of\s+(\w+(?:\s+\w+)*)",
            r"(?:I |i )?(?:drink|quaff|consume|use)\s+(?:the\s+)?(\w+\s+)?potion",
        ],
        "common_items": {
            "healing": "Potion of Healing",
            "greater healing": "Potion of Greater Healing",
            "superior healing": "Potion of Superior Healing",
            "supreme healing": "Potion of Supreme Healing",
            "invisibility": "Potion of Invisibility",
            "speed": "Potion of Speed",
            "flying": "Potion of Flying",
            "fire resistance": "Potion of Fire Resistance",
        },
    },
    "scroll": {
        "patterns": [
            r"(?:I |i )?(?:read|use|cast from)\s+(?:a\s+|my\s+)?scroll\s+of\s+(\w+(?:\s+\w+)*)",
            r"(?:I |i )?(?:read|use)\s+(?:the\s+)?(\w+)\s+scroll",
        ],
    },
    "ammunition": {
        "patterns": [
            r"(?:I |i )?(?:fire|shoot|loose)\s+(?:an?\s+)?arrow",
            r"(?:I |i )?(?:fire|shoot)\s+(?:a\s+)?(?:crossbow\s+)?bolt",
            r"(?:I |i )?(?:throw|hurl)\s+(?:a\s+)?dart",
            r"(?:I |i )?(?:sling|throw)\s+(?:a\s+)?(?:sling\s+)?bullet",
        ],
        "ammo_types": {
            "arrow": "Arrows (20)",
            "bolt": "Crossbow Bolts (20)", 
            "dart": "Dart",
            "bullet": "Sling Bullets (20)",
        },
    },
}


# =============================================================================
# DETECTION FUNCTIONS
# =============================================================================

def detect_spell_cast(text: str, character_data: dict = None) -> List[DetectedSpell]:
    """
    Detect spell casting from narrative text.
    
    Args:
        text: The narrative text to analyze
        character_data: Optional character data for validation
        
    Returns:
        List of DetectedSpell objects
    """
    detected = []
    text_lower = text.lower()
    
    # First, check for direct spell name mentions (case-insensitive)
    for spell_name, spell_data in SPELLS.items():
        spell_lower = spell_name.lower()
        
        # Check if spell name appears in casting context
        for pattern in SPELL_CAST_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                potential_spell = match.group(1).strip()
                potential_spell_lower = potential_spell.lower()
                
                # Check against known spells
                if potential_spell_lower == spell_lower or potential_spell == spell_name:
                    detected.append(DetectedSpell(
                        name=spell_name,
                        level=spell_data.get('level', 0),
                        is_cantrip=spell_data.get('level', 0) == 0,
                        match_text=match.group(0),
                        confidence=1.0
                    ))
                    break
    
    # Check for spell aliases
    for alias, canonical_name in SPELL_ALIASES.items():
        if alias in text_lower:
            # Verify it's in a casting context
            casting_indicators = ['cast', 'use', 'invoke', 'chant', 'unleash', 'with']
            if any(ind in text_lower for ind in casting_indicators):
                spell_data = SPELLS.get(canonical_name, {})
                
                # Avoid duplicates
                if not any(d.name == canonical_name for d in detected):
                    detected.append(DetectedSpell(
                        name=canonical_name,
                        level=spell_data.get('level', 1) if spell_data else 1,
                        is_cantrip=spell_data.get('level', 1) == 0 if spell_data else False,
                        match_text=alias,
                        confidence=0.9
                    ))
    
    # If character data provided, validate against known/prepared spells
    if character_data and detected:
        known_spells = set(character_data.get('spells_known', []))
        prepared_spells = set(character_data.get('prepared_spells', []))
        cantrips = set(character_data.get('cantrips_known', []))
        
        # Boost confidence for known spells
        for spell in detected:
            if spell.name in known_spells or spell.name in prepared_spells or spell.name in cantrips:
                spell.confidence = 1.0
    
    return detected


def detect_class_ability(text: str, character_data: dict) -> List[DetectedAbility]:
    """
    Detect class ability usage from narrative text.
    
    Args:
        text: The narrative text to analyze
        character_data: Character data to determine class
        
    Returns:
        List of DetectedAbility objects
    """
    detected = []
    
    if not character_data:
        return detected
    
    char_class = character_data.get('class', '').lower()
    
    # Get ability patterns for this class
    class_abilities = CLASS_ABILITY_PATTERNS.get(char_class, {})
    
    for ability_name, ability_data in class_abilities.items():
        patterns = ability_data.get('patterns', [])
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Determine cost
                cost = 1
                costs = ability_data.get('costs', {})
                for cost_trigger, cost_value in costs.items():
                    if cost_trigger in text.lower():
                        cost = cost_value
                        break
                
                detected.append(DetectedAbility(
                    name=ability_name,
                    class_name=char_class,
                    resource_type=ability_data.get('resource', ability_name),
                    cost=cost,
                    match_text=match.group(0)
                ))
                break  # Only detect once per ability
    
    return detected


def detect_consumable_use(text: str, character_data: dict = None) -> List[DetectedConsumable]:
    """
    Detect consumable item usage from narrative text.
    
    Args:
        text: The narrative text to analyze
        character_data: Optional character data for inventory validation
        
    Returns:
        List of DetectedConsumable objects
    """
    detected = []
    text_lower = text.lower()
    
    # Check potion usage
    for pattern in CONSUMABLE_PATTERNS['potion']['patterns']:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            potion_type = match.group(1).lower().strip() if match.lastindex else "healing"
            common_items = CONSUMABLE_PATTERNS['potion']['common_items']
            
            # Try to match to a known potion
            item_name = common_items.get(potion_type, f"Potion of {potion_type.title()}")
            
            detected.append(DetectedConsumable(
                item_name=item_name,
                item_type="potion",
                quantity=1,
                match_text=match.group(0)
            ))
            break
    
    # Check scroll usage
    for pattern in CONSUMABLE_PATTERNS['scroll']['patterns']:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            spell_name = match.group(1).title() if match.lastindex else "Unknown"
            
            detected.append(DetectedConsumable(
                item_name=f"Scroll of {spell_name}",
                item_type="scroll",
                quantity=1,
                match_text=match.group(0)
            ))
            break
    
    # Check ammunition usage
    for pattern in CONSUMABLE_PATTERNS['ammunition']['patterns']:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            match_text = match.group(0).lower()
            ammo_types = CONSUMABLE_PATTERNS['ammunition']['ammo_types']
            
            for ammo_key, ammo_name in ammo_types.items():
                if ammo_key in match_text:
                    detected.append(DetectedConsumable(
                        item_name=ammo_name,
                        item_type="ammunition",
                        quantity=1,
                        match_text=match.group(0)
                    ))
                    break
    
    # Validate against inventory if character data provided
    if character_data and detected:
        inventory = character_data.get('inventory', [])
        # Filter to items in inventory (or keep all if no validation needed)
        # This is informational - consumption still attempts
    
    return detected


# =============================================================================
# RESOURCE CONSUMPTION FUNCTIONS
# =============================================================================

def consume_spell_slot(user_id: str, spell: DetectedSpell, preferred_level: int = None) -> ResourceConsumption:
    """
    Consume a spell slot for casting a spell.
    
    Args:
        user_id: The player's user ID
        spell: The detected spell being cast
        preferred_level: Preferred slot level (for upcasting)
        
    Returns:
        ResourceConsumption result
    """
    # Cantrips don't consume slots
    if spell.is_cantrip:
        return ResourceConsumption(
            resource_type="cantrip",
            resource_name=spell.name,
            amount=0,
            success=True,
            message=f"Cast cantrip: {spell.name}"
        )
    
    char_data = load_character(user_id)
    if not char_data:
        return ResourceConsumption(
            resource_type="spell_slot",
            resource_name=spell.name,
            success=False,
            message="Character not found"
        )
    
    # Determine slot level to use
    slot_level = preferred_level if preferred_level else spell.level
    
    if slot_level < spell.level:
        return ResourceConsumption(
            resource_type="spell_slot",
            resource_name=spell.name,
            level=slot_level,
            success=False,
            message=f"{spell.name} requires at least a level {spell.level} slot"
        )
    
    # Check for available slot
    slot_key = str(slot_level)
    available = char_data.get('spell_slots', {}).get(slot_key, 0)
    used = char_data.get('spell_slots_used', {}).get(slot_key, 0)
    
    if used >= available:
        # Try to find a higher level slot
        for try_level in range(slot_level + 1, 10):
            try_key = str(try_level)
            avail = char_data.get('spell_slots', {}).get(try_key, 0)
            u = char_data.get('spell_slots_used', {}).get(try_key, 0)
            if u < avail:
                slot_level = try_level
                slot_key = try_key
                break
        else:
            return ResourceConsumption(
                resource_type="spell_slot",
                resource_name=spell.name,
                level=spell.level,
                success=False,
                message=f"No spell slots of level {spell.level}+ remaining"
            )
    
    # Consume the slot
    success = use_spell_slot(user_id, slot_level)
    
    if success:
        upcast_msg = f" (upcast at level {slot_level})" if slot_level > spell.level else ""
        remaining = available - used - 1
        return ResourceConsumption(
            resource_type="spell_slot",
            resource_name=spell.name,
            amount=1,
            level=slot_level,
            success=True,
            message=f"🔮 Cast {spell.name}{upcast_msg} - Level {slot_level} slots: {remaining}/{available}"
        )
    else:
        return ResourceConsumption(
            resource_type="spell_slot",
            resource_name=spell.name,
            level=slot_level,
            success=False,
            message=f"Failed to consume spell slot"
        )


def consume_class_resource(user_id: str, ability: DetectedAbility) -> ResourceConsumption:
    """
    Consume a class resource for using an ability.
    
    Args:
        user_id: The player's user ID
        ability: The detected ability being used
        
    Returns:
        ResourceConsumption result
    """
    char_data = load_character(user_id)
    if not char_data:
        return ResourceConsumption(
            resource_type=ability.resource_type,
            resource_name=ability.name,
            success=False,
            message="Character not found"
        )
    
    resource_key = ability.resource_type
    
    # Handle special resources
    if resource_key == "spell_slot":
        # Divine Smite uses spell slots
        default_level = CLASS_ABILITY_PATTERNS.get(ability.class_name, {}).get(ability.name, {}).get('default_level', 1)
        from .dnd5e_data import get_spell
        fake_spell = DetectedSpell(
            name=ability.name,
            level=default_level,
            is_cantrip=False,
            match_text=ability.match_text
        )
        return consume_spell_slot(user_id, fake_spell)
    
    if resource_key is None:
        # No resource cost, just tracking
        return ResourceConsumption(
            resource_type="tracking_only",
            resource_name=ability.name,
            success=True,
            message=f"Used {ability.name.replace('_', ' ').title()}"
        )
    
    # Get current usage and max
    current_used = char_data.get(resource_key, 0)
    
    # Calculate max resource
    ability_config = CLASS_ABILITY_PATTERNS.get(ability.class_name, {}).get(ability.name, {})
    max_resource = ability_config.get('max_resource', 1)
    
    if max_resource == "level":
        max_resource = char_data.get('level', 1)
    elif max_resource == "cha_mod":
        from .character_manager import get_ability_modifier
        max_resource = max(1, get_ability_modifier(char_data.get('CHA', 10)))
    elif max_resource == "level * 5":
        max_resource = char_data.get('level', 1) * 5
    elif isinstance(max_resource, str):
        max_resource = 1
    
    # Check if resource available
    if current_used >= max_resource:
        return ResourceConsumption(
            resource_type=resource_key,
            resource_name=ability.name,
            success=False,
            message=f"No {ability.name.replace('_', ' ').title()} uses remaining"
        )
    
    # Consume the resource
    char_data[resource_key] = current_used + ability.cost
    save_character(user_id, char_data)
    
    remaining = max_resource - current_used - ability.cost
    ability_display = ability.name.replace('_', ' ').title()
    
    return ResourceConsumption(
        resource_type=resource_key,
        resource_name=ability.name,
        amount=ability.cost,
        success=True,
        message=f"⚡ Used {ability_display} - {remaining}/{max_resource} uses remaining"
    )


def consume_item(user_id: str, consumable: DetectedConsumable) -> ResourceConsumption:
    """
    Consume an item from inventory.
    
    Args:
        user_id: The player's user ID
        consumable: The detected consumable being used
        
    Returns:
        ResourceConsumption result
    """
    char_data = load_character(user_id)
    if not char_data:
        return ResourceConsumption(
            resource_type=consumable.item_type,
            resource_name=consumable.item_name,
            success=False,
            message="Character not found"
        )
    
    inventory = char_data.get('inventory', [])
    
    # Check if item exists in inventory
    item_found = False
    for item in inventory:
        if consumable.item_name.lower() in item.lower() or item.lower() in consumable.item_name.lower():
            item_found = True
            consumable.item_name = item  # Use exact inventory name
            break
    
    if not item_found:
        # For ammunition, check for bundles
        if consumable.item_type == "ammunition":
            for item in inventory:
                ammo_keywords = {
                    "arrow": ["arrow", "arrows"],
                    "bolt": ["bolt", "bolts", "crossbow bolt"],
                    "dart": ["dart", "darts"],
                    "bullet": ["bullet", "bullets", "sling bullet"],
                }
                for ammo_type, keywords in ammo_keywords.items():
                    if any(kw in consumable.item_name.lower() for kw in keywords):
                        if any(kw in item.lower() for kw in keywords):
                            item_found = True
                            consumable.item_name = item
                            break
                if item_found:
                    break
    
    if not item_found:
        return ResourceConsumption(
            resource_type=consumable.item_type,
            resource_name=consumable.item_name,
            success=False,
            message=f"You don't have {consumable.item_name} in your inventory"
        )
    
    # Remove item from inventory
    result, msg = remove_from_inventory(user_id, consumable.item_name, consumable.quantity)
    
    if result:
        emoji = "🧪" if consumable.item_type == "potion" else "📜" if consumable.item_type == "scroll" else "🏹"
        return ResourceConsumption(
            resource_type=consumable.item_type,
            resource_name=consumable.item_name,
            amount=consumable.quantity,
            success=True,
            message=f"{emoji} Used {consumable.item_name}"
        )
    else:
        return ResourceConsumption(
            resource_type=consumable.item_type,
            resource_name=consumable.item_name,
            success=False,
            message=msg
        )


# =============================================================================
# MAIN PROCESSING FUNCTION
# =============================================================================

def process_narrative_for_resources(
    user_id: str, 
    narrative: str, 
    auto_consume: bool = True
) -> Dict[str, Any]:
    """
    Process narrative text to detect and optionally consume resources.
    
    This is the main entry point for resource detection. It analyzes
    the player's narrative text for spell casting, ability usage, and
    consumable usage, then optionally consumes those resources.
    
    Args:
        user_id: The player's user ID
        narrative: The narrative text to analyze
        auto_consume: If True, automatically consume detected resources
        
    Returns:
        Dict containing:
            - detected_spells: List of DetectedSpell
            - detected_abilities: List of DetectedAbility
            - detected_consumables: List of DetectedConsumable
            - consumptions: List of ResourceConsumption (if auto_consume)
            - summary: User-friendly summary string
    """
    char_data = load_character(user_id)
    
    result = {
        'detected_spells': [],
        'detected_abilities': [],
        'detected_consumables': [],
        'consumptions': [],
        'summary': "",
    }
    
    # Detect all resource usage
    result['detected_spells'] = detect_spell_cast(narrative, char_data)
    result['detected_abilities'] = detect_class_ability(narrative, char_data)
    result['detected_consumables'] = detect_consumable_use(narrative, char_data)
    
    if not auto_consume:
        return result
    
    # Process spell consumptions
    for spell in result['detected_spells']:
        consumption = consume_spell_slot(user_id, spell)
        result['consumptions'].append(consumption)
    
    # Process ability consumptions
    for ability in result['detected_abilities']:
        consumption = consume_class_resource(user_id, ability)
        result['consumptions'].append(consumption)
    
    # Process consumable usage
    for consumable in result['detected_consumables']:
        consumption = consume_item(user_id, consumable)
        result['consumptions'].append(consumption)
    
    # Build summary
    successful = [c for c in result['consumptions'] if c.success]
    failed = [c for c in result['consumptions'] if not c.success]
    
    summary_parts = []
    for c in successful:
        summary_parts.append(c.message)
    
    for c in failed:
        summary_parts.append(f"❌ {c.message}")
    
    result['summary'] = "\n".join(summary_parts)
    
    return result


def get_resource_status(user_id: str) -> Dict[str, Any]:
    """
    Get the current status of all character resources.
    
    Args:
        user_id: The player's user ID
        
    Returns:
        Dict containing current resource status
    """
    char_data = load_character(user_id)
    if not char_data:
        return {}
    
    status = {
        'spell_slots': {},
        'class_resources': {},
        'consumables_count': {},
    }
    
    # Spell slots
    for level in range(1, 10):
        level_str = str(level)
        total = char_data.get('spell_slots', {}).get(level_str, 0)
        used = char_data.get('spell_slots_used', {}).get(level_str, 0)
        if total > 0:
            status['spell_slots'][level] = {
                'total': total,
                'used': used,
                'remaining': total - used
            }
    
    # Class resources
    char_class = char_data.get('class', '').lower()
    class_abilities = CLASS_ABILITY_PATTERNS.get(char_class, {})
    
    for ability_name, ability_data in class_abilities.items():
        resource_key = ability_data.get('resource')
        if resource_key and resource_key != "spell_slot":
            max_resource = ability_data.get('max_resource', 1)
            
            if max_resource == "level":
                max_resource = char_data.get('level', 1)
            elif max_resource == "cha_mod":
                max_resource = max(1, get_ability_modifier(char_data.get('CHA', 10)))
            elif max_resource == "level * 5":
                max_resource = char_data.get('level', 1) * 5
            elif isinstance(max_resource, str):
                max_resource = 1
            
            used = char_data.get(resource_key, 0)
            
            status['class_resources'][ability_name] = {
                'total': max_resource,
                'used': used,
                'remaining': max_resource - used
            }
    
    # Count consumables in inventory
    inventory = char_data.get('inventory', [])
    for item in inventory:
        item_lower = item.lower()
        if 'potion' in item_lower:
            status['consumables_count']['potions'] = status['consumables_count'].get('potions', 0) + 1
        elif 'scroll' in item_lower:
            status['consumables_count']['scrolls'] = status['consumables_count'].get('scrolls', 0) + 1
        elif any(ammo in item_lower for ammo in ['arrow', 'bolt', 'dart', 'bullet']):
            status['consumables_count']['ammunition'] = status['consumables_count'].get('ammunition', 0) + 1
    
    return status


def format_resource_status(user_id: str) -> str:
    """
    Format resource status as a user-friendly string.
    
    Args:
        user_id: The player's user ID
        
    Returns:
        Formatted string showing resource status
    """
    status = get_resource_status(user_id)
    if not status:
        return "No character found"
    
    lines = ["**📊 Resource Status**"]
    
    # Spell slots
    if status.get('spell_slots'):
        slot_parts = []
        for level, data in sorted(status['spell_slots'].items()):
            slot_parts.append(f"L{level}: {data['remaining']}/{data['total']}")
        lines.append(f"🔮 **Spell Slots:** {' | '.join(slot_parts)}")
    
    # Class resources
    for ability, data in status.get('class_resources', {}).items():
        ability_name = ability.replace('_', ' ').title()
        lines.append(f"⚡ **{ability_name}:** {data['remaining']}/{data['total']}")
    
    # Consumables
    consumables = status.get('consumables_count', {})
    if consumables:
        cons_parts = []
        if 'potions' in consumables:
            cons_parts.append(f"🧪 Potions: {consumables['potions']}")
        if 'scrolls' in consumables:
            cons_parts.append(f"📜 Scrolls: {consumables['scrolls']}")
        if 'ammunition' in consumables:
            cons_parts.append(f"🏹 Ammo: {consumables['ammunition']}")
        if cons_parts:
            lines.append(" | ".join(cons_parts))
    
    return "\n".join(lines)
