"""
Inventory & Equipment Context Manager
Handles attunement, magic item identification, loot distribution, and encumbrance.
"""

import json
import os
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# =============================================================================
# CONSTANTS
# =============================================================================

# Items that require attunement (partial list - add more as needed)
ATTUNEMENT_ITEMS = {
    # Uncommon
    "Bag of Holding": False,  # No attunement
    "Boots of Elvenkind": False,
    "Cloak of Elvenkind": False,
    "Gauntlets of Ogre Power": True,
    "Goggles of Night": False,
    "Ring of Protection": True,
    "Wand of Magic Missiles": False,
    "+1 Weapon": False,
    "+1 Shield": False,
    
    # Rare
    "+2 Weapon": False,
    "+2 Shield": False,
    "Amulet of Health": True,
    "Belt of Hill Giant Strength": True,
    "Cloak of Displacement": True,
    "Flame Tongue": True,
    "Ring of Spell Storing": True,
    "Staff of the Python": True,
    "Wand of Fireballs": True,
    "Wings of Flying": True,
    
    # Very Rare
    "+3 Weapon": False,
    "+3 Shield": False,
    "Belt of Fire Giant Strength": True,
    "Cloak of Invisibility": True,
    "Dancing Sword": True,
    "Ring of Regeneration": True,
    "Ring of Telekinesis": True,
    "Rod of Alertness": True,
    "Staff of Fire": True,
    "Staff of Power": True,
    
    # Legendary
    "Holy Avenger": True,
    "Luck Blade": True,
    "Ring of Three Wishes": False,
    "Rod of Lordly Might": True,
    "Robe of the Archmagi": True,
    "Staff of the Magi": True,
    "Vorpal Sword": True,
    "Belt of Storm Giant Strength": True,
}

# Standard item weights in pounds
ITEM_WEIGHTS = {
    # Weapons
    "Dagger": 1,
    "Shortsword": 2,
    "Longsword": 3,
    "Greatsword": 6,
    "Handaxe": 2,
    "Battleaxe": 4,
    "Greataxe": 7,
    "Spear": 3,
    "Quarterstaff": 4,
    "Longbow": 2,
    "Shortbow": 2,
    "Light Crossbow": 5,
    "Heavy Crossbow": 18,
    
    # Armor
    "Leather Armor": 10,
    "Studded Leather": 13,
    "Chain Shirt": 20,
    "Chain Mail": 55,
    "Scale Mail": 45,
    "Plate Armor": 65,
    "Shield": 6,
    
    # Adventuring Gear
    "Backpack": 5,
    "Bedroll": 7,
    "Rope (50 ft)": 10,
    "Torch": 1,
    "Rations (1 day)": 2,
    "Waterskin": 5,
    "Potion of Healing": 0.5,
    "Potion of Greater Healing": 0.5,
    
    # Treasure
    "Coins (50)": 1,  # 50 coins = 1 lb
}

# Max attunement slots
MAX_ATTUNEMENT_SLOTS = 3

# Encumbrance thresholds (multiplied by STR score)
ENCUMBRANCE_NORMAL = 5  # Up to STR × 5 lbs = no penalty
ENCUMBRANCE_HEAVY = 10  # Up to STR × 10 lbs = -10 speed
ENCUMBRANCE_MAX = 15    # Up to STR × 15 lbs = max carry capacity


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MagicItem:
    """Represents a magic item with identification status."""
    name: str
    identified: bool = False
    identified_name: str = ""  # What the item is called before identification
    requires_attunement: bool = False
    attuned: bool = False
    rarity: str = "common"
    effect: str = ""
    
    def display_name(self) -> str:
        """Get the name to display based on identification status."""
        if self.identified:
            return self.name
        return self.identified_name or f"Unidentified {self.rarity.title()} Item"


@dataclass
class LootClaim:
    """Tracks a pending loot distribution."""
    loot_id: str
    items: List[str]
    currency: Dict[str, int]
    claims: Dict[str, List[str]] = field(default_factory=dict)  # user_id -> items claimed
    timestamp: float = 0


# =============================================================================
# ATTUNEMENT MANAGEMENT
# =============================================================================

def get_attunement_slots(user_id: str) -> Dict:
    """Get attunement status for a character."""
    from utils.character_manager import load_character
    
    char = load_character(user_id)
    if not char:
        return {"slots_used": 0, "slots_max": MAX_ATTUNEMENT_SLOTS, "items": []}
    
    attuned = char.get("attuned_items", [])
    return {
        "slots_used": len(attuned),
        "slots_max": MAX_ATTUNEMENT_SLOTS,
        "items": attuned
    }


def attune_item(user_id: str, item_name: str) -> Tuple[bool, str]:
    """Attune to a magic item (requires short rest)."""
    from utils.character_manager import load_character, save_character
    
    char = load_character(user_id)
    if not char:
        return False, "Character not found"
    
    # Check if item is in inventory
    inventory = char.get("inventory", [])
    if item_name not in inventory:
        return False, f"You don't have {item_name} in your inventory"
    
    # Check if item requires attunement
    requires = requires_attunement(item_name)
    if not requires:
        return False, f"{item_name} doesn't require attunement"
    
    # Check attunement slots
    attuned = char.get("attuned_items", [])
    if len(attuned) >= MAX_ATTUNEMENT_SLOTS:
        return False, f"All {MAX_ATTUNEMENT_SLOTS} attunement slots are in use. Unattune an item first."
    
    # Check if already attuned
    if item_name in attuned:
        return False, f"You're already attuned to {item_name}"
    
    # Attune
    attuned.append(item_name)
    char["attuned_items"] = attuned
    save_character(user_id, char)
    
    slots_remaining = MAX_ATTUNEMENT_SLOTS - len(attuned)
    return True, f"✨ Attuned to **{item_name}**! ({slots_remaining} attunement slot{'s' if slots_remaining != 1 else ''} remaining)"


def unattune_item(user_id: str, item_name: str) -> Tuple[bool, str]:
    """End attunement to a magic item."""
    from utils.character_manager import load_character, save_character
    
    char = load_character(user_id)
    if not char:
        return False, "Character not found"
    
    attuned = char.get("attuned_items", [])
    if item_name not in attuned:
        return False, f"You're not attuned to {item_name}"
    
    attuned.remove(item_name)
    char["attuned_items"] = attuned
    save_character(user_id, char)
    
    slots_remaining = MAX_ATTUNEMENT_SLOTS - len(attuned)
    return True, f"Ended attunement to **{item_name}**. ({slots_remaining} attunement slot{'s' if slots_remaining != 1 else ''} available)"


def requires_attunement(item_name: str) -> bool:
    """Check if an item requires attunement."""
    # Check known items
    if item_name in ATTUNEMENT_ITEMS:
        return ATTUNEMENT_ITEMS[item_name]
    
    # Check for generic magic items
    if item_name.startswith("+") and ("Weapon" in item_name or "Shield" in item_name):
        return False
    
    # Check for keywords that often indicate attunement
    attunement_keywords = ["Ring of", "Amulet of", "Belt of", "Cloak of", "Staff of", "Rod of", "Robe of"]
    for keyword in attunement_keywords:
        if keyword in item_name:
            return True
    
    return False


# =============================================================================
# MAGIC ITEM IDENTIFICATION
# =============================================================================

def generate_unidentified_name(item_name: str, rarity: str) -> str:
    """Generate a mysterious name for an unidentified item."""
    prefixes = {
        "weapon": ["Glowing", "Rune-etched", "Ancient", "Gleaming", "Strange"],
        "armor": ["Ornate", "Unusual", "Masterwork", "Enchanted-looking", "Peculiar"],
        "ring": ["Mysterious", "Ornate", "Glimmering", "Ancient", "Unusual"],
        "wondrous": ["Magical", "Strange", "Curious", "Mystical", "Enchanted"],
        "potion": ["Bubbling", "Glowing", "Strange", "Colorful", "Swirling"],
        "wand": ["Carved", "Crystal-tipped", "Ancient", "Rune-covered", "Ornate"],
        "staff": ["Gnarled", "Crystal-topped", "Ancient", "Rune-carved", "Mystical"],
        "rod": ["Metal", "Ornate", "Strange", "Enchanted", "Unusual"],
    }
    
    # Determine item type
    item_lower = item_name.lower()
    if "sword" in item_lower or "axe" in item_lower or "weapon" in item_lower or "dagger" in item_lower:
        item_type = "weapon"
        base = "Weapon"
    elif "armor" in item_lower or "shield" in item_lower or "mail" in item_lower:
        item_type = "armor"
        base = "Armor"
    elif "ring" in item_lower:
        item_type = "ring"
        base = "Ring"
    elif "potion" in item_lower:
        item_type = "potion"
        base = "Potion"
    elif "wand" in item_lower:
        item_type = "wand"
        base = "Wand"
    elif "staff" in item_lower:
        item_type = "staff"
        base = "Staff"
    elif "rod" in item_lower:
        item_type = "rod"
        base = "Rod"
    else:
        item_type = "wondrous"
        base = "Item"
    
    prefix = random.choice(prefixes.get(item_type, prefixes["wondrous"]))
    return f"{prefix} {base}"


def identify_item(user_id: str, item_name: str, method: str = "arcana") -> Tuple[bool, str, Optional[Dict]]:
    """
    Attempt to identify a magic item.
    
    Args:
        user_id: The character identifying
        item_name: The unidentified item name or description
        method: "arcana" (DC 15 Arcana check), "identify" (spell), or "short_rest" (handle during rest)
    
    Returns:
        (success, message, item_data if identified)
    """
    from utils.character_manager import load_character, save_character
    
    char = load_character(user_id)
    if not char:
        return False, "Character not found", None
    
    # Find the unidentified item in inventory
    unidentified_items = char.get("unidentified_items", {})
    
    if item_name not in char.get("inventory", []) and item_name not in unidentified_items:
        return False, f"You don't have '{item_name}' in your inventory", None
    
    # Check if already identified
    if item_name not in unidentified_items:
        return False, f"'{item_name}' is already identified (or isn't magical)", None
    
    item_data = unidentified_items[item_name]
    real_name = item_data.get("real_name", item_name)
    
    # Identification methods
    if method == "identify":
        # Identify spell - automatic success
        success = True
    elif method == "short_rest":
        # Short rest with item - automatic success
        success = True
    else:
        # Arcana check - need to roll
        return False, f"Roll an Arcana check (DC 15) to identify this item. Use `/roll arcana` and report the result.", None
    
    if success:
        # Move from unidentified to regular inventory with real name
        if item_name in char.get("inventory", []):
            char["inventory"].remove(item_name)
        char["inventory"].append(real_name)
        del unidentified_items[item_name]
        char["unidentified_items"] = unidentified_items
        save_character(user_id, char)
        
        effect = item_data.get("effect", "Unknown effect")
        rarity = item_data.get("rarity", "unknown")
        attune = "Requires attunement" if item_data.get("requires_attunement") else "No attunement required"
        
        return True, f"✨ **Identified: {real_name}**\n*Rarity: {rarity.title()}*\n*{attune}*\n{effect}", item_data
    
    return False, "Failed to identify the item.", None


def add_unidentified_item(user_id: str, real_name: str, effect: str, rarity: str = "uncommon") -> Tuple[bool, str]:
    """Add an unidentified magic item to a character's inventory."""
    from utils.character_manager import load_character, save_character
    
    char = load_character(user_id)
    if not char:
        return False, "Character not found"
    
    # Generate mysterious name
    mysterious_name = generate_unidentified_name(real_name, rarity)
    
    # Store mapping
    unidentified = char.get("unidentified_items", {})
    unidentified[mysterious_name] = {
        "real_name": real_name,
        "effect": effect,
        "rarity": rarity,
        "requires_attunement": requires_attunement(real_name)
    }
    char["unidentified_items"] = unidentified
    
    # Add mysterious name to inventory
    char.setdefault("inventory", []).append(mysterious_name)
    save_character(user_id, char)
    
    return True, f"Added **{mysterious_name}** to inventory (unidentified)"


# =============================================================================
# ENCUMBRANCE SYSTEM
# =============================================================================

def get_item_weight(item_name: str) -> float:
    """Get the weight of an item in pounds."""
    # Check exact match
    if item_name in ITEM_WEIGHTS:
        return ITEM_WEIGHTS[item_name]
    
    # Check partial matches
    item_lower = item_name.lower()
    
    # Potions are light
    if "potion" in item_lower:
        return 0.5
    
    # Weapons by type
    if "dagger" in item_lower:
        return 1
    if "sword" in item_lower:
        if "short" in item_lower:
            return 2
        if "great" in item_lower:
            return 6
        return 3
    if "axe" in item_lower:
        if "hand" in item_lower:
            return 2
        if "great" in item_lower:
            return 7
        return 4
    if "bow" in item_lower:
        return 2
    if "crossbow" in item_lower:
        return 6 if "heavy" in item_lower else 5
    
    # Armor
    if "plate" in item_lower:
        return 65
    if "chain" in item_lower:
        return 40
    if "leather" in item_lower:
        return 10
    if "shield" in item_lower:
        return 6
    
    # Default weight for unknown items
    return 1


def calculate_encumbrance(user_id: str) -> Dict:
    """Calculate encumbrance for a character."""
    from utils.character_manager import load_character
    
    char = load_character(user_id)
    if not char:
        return {"error": "Character not found"}
    
    strength = char.get("STR", 10)
    
    # Calculate total weight
    total_weight = 0.0
    
    # Inventory items
    for item in char.get("inventory", []):
        total_weight += get_item_weight(item)
    
    # Equipped items
    equipment = char.get("equipment", {})
    if equipment.get("armor"):
        total_weight += get_item_weight(equipment["armor"])
    if equipment.get("weapon"):
        total_weight += get_item_weight(equipment["weapon"])
    if equipment.get("shield"):
        total_weight += get_item_weight(equipment["shield"])
    
    # Add gold weight (50 coins = 1 lb)
    gold = char.get("gold", 0)
    total_weight += gold / 50
    
    # Calculate thresholds
    normal_limit = strength * ENCUMBRANCE_NORMAL
    heavy_limit = strength * ENCUMBRANCE_HEAVY
    max_limit = strength * ENCUMBRANCE_MAX
    
    # Determine status
    if total_weight > max_limit:
        status = "over_encumbered"
        speed_penalty = "Cannot move"
        warning = "⚠️ **OVER ENCUMBERED!** You cannot move. Drop items immediately!"
    elif total_weight > heavy_limit:
        status = "heavily_encumbered"
        speed_penalty = "-20 ft speed, disadvantage on checks"
        warning = "⚠️ **Heavily Encumbered!** Speed reduced by 20 ft, disadvantage on ability checks, attack rolls, and STR/DEX saves."
    elif total_weight > normal_limit:
        status = "encumbered"
        speed_penalty = "-10 ft speed"
        warning = "⚠️ **Encumbered!** Speed reduced by 10 ft."
    else:
        status = "normal"
        speed_penalty = "None"
        warning = None
    
    return {
        "total_weight": round(total_weight, 1),
        "normal_limit": normal_limit,
        "heavy_limit": heavy_limit,
        "max_limit": max_limit,
        "status": status,
        "speed_penalty": speed_penalty,
        "warning": warning,
        "strength": strength
    }


def format_encumbrance_status(user_id: str) -> str:
    """Get formatted encumbrance status."""
    enc = calculate_encumbrance(user_id)
    if "error" in enc:
        return enc["error"]
    
    bar_length = 20
    fill_ratio = min(1.0, enc["total_weight"] / enc["max_limit"])
    filled = int(bar_length * fill_ratio)
    
    if enc["status"] == "over_encumbered":
        bar_char = "🟥"
    elif enc["status"] == "heavily_encumbered":
        bar_char = "🟧"
    elif enc["status"] == "encumbered":
        bar_char = "🟨"
    else:
        bar_char = "🟩"
    
    bar = bar_char * filled + "⬜" * (bar_length - filled)
    
    lines = [
        f"⚖️ **Encumbrance:** {enc['total_weight']} / {enc['max_limit']} lbs",
        f"{bar}",
        f"Normal: {enc['normal_limit']} lbs | Heavy: {enc['heavy_limit']} lbs | Max: {enc['max_limit']} lbs"
    ]
    
    if enc["warning"]:
        lines.append(enc["warning"])
    
    return "\n".join(lines)


# =============================================================================
# LOOT DISTRIBUTION
# =============================================================================

# Store pending loot for distribution
_pending_loot: Dict[str, LootClaim] = {}


def create_loot_distribution(channel_id: str, items: List[str], currency: Dict[str, int]) -> str:
    """Create a pending loot distribution for players to claim."""
    import time
    import uuid
    
    loot_id = str(uuid.uuid4())[:8]
    
    _pending_loot[channel_id] = LootClaim(
        loot_id=loot_id,
        items=items.copy(),
        currency=currency.copy(),
        claims={},
        timestamp=time.time()
    )
    
    return loot_id


def claim_loot_item(channel_id: str, user_id: str, item_name: str) -> Tuple[bool, str]:
    """Claim an item from pending loot."""
    from utils.character_manager import load_character, add_inventory
    
    if channel_id not in _pending_loot:
        return False, "No pending loot to claim"
    
    loot = _pending_loot[channel_id]
    
    # Check if item is available
    if item_name not in loot.items:
        return False, f"'{item_name}' is not in the loot pile"
    
    # Check if character exists
    char = load_character(user_id)
    if not char:
        return False, "You don't have a character registered"
    
    # Claim the item
    loot.items.remove(item_name)
    loot.claims.setdefault(user_id, []).append(item_name)
    
    # Add to inventory
    add_inventory(user_id, item_name)
    
    char_name = char.get("name", "Unknown")
    return True, f"**{char_name}** claimed **{item_name}**!"


def claim_loot_gold(channel_id: str, user_id: str, amount: int = None) -> Tuple[bool, str]:
    """Claim gold from pending loot (or split evenly if no amount specified)."""
    from utils.character_manager import load_character, save_character
    
    if channel_id not in _pending_loot:
        return False, "No pending loot to claim"
    
    loot = _pending_loot[channel_id]
    available_gp = loot.currency.get("gp", 0)
    
    if available_gp <= 0:
        return False, "No gold remaining in the loot"
    
    char = load_character(user_id)
    if not char:
        return False, "You don't have a character registered"
    
    if amount is None:
        amount = available_gp  # Take all
    
    amount = min(amount, available_gp)
    
    # Update loot
    loot.currency["gp"] = available_gp - amount
    
    # Add to character
    char["gold"] = char.get("gold", 0) + amount
    save_character(user_id, char)
    
    char_name = char.get("name", "Unknown")
    return True, f"**{char_name}** claimed **{amount} gp**!"


def get_pending_loot(channel_id: str) -> Optional[LootClaim]:
    """Get pending loot for a channel."""
    return _pending_loot.get(channel_id)


def format_pending_loot(channel_id: str) -> str:
    """Format pending loot for display."""
    loot = _pending_loot.get(channel_id)
    if not loot:
        return "No pending loot."
    
    lines = ["💰 **Unclaimed Loot:**"]
    
    # Currency
    if any(v > 0 for v in loot.currency.values()):
        currency_parts = []
        for coin, amount in [("pp", loot.currency.get("pp", 0)), 
                            ("gp", loot.currency.get("gp", 0)),
                            ("sp", loot.currency.get("sp", 0)),
                            ("cp", loot.currency.get("cp", 0))]:
            if amount > 0:
                currency_parts.append(f"{amount} {coin}")
        if currency_parts:
            lines.append(f"  🪙 {', '.join(currency_parts)}")
    
    # Items
    if loot.items:
        for item in loot.items:
            lines.append(f"  📦 {item}")
    else:
        lines.append("  *All items claimed*")
    
    # Claims made
    if loot.claims:
        lines.append("\n**Claimed:**")
        for user_id, items in loot.claims.items():
            from utils.character_manager import load_character
            char = load_character(user_id)
            name = char.get("name", "Unknown") if char else "Unknown"
            lines.append(f"  {name}: {', '.join(items)}")
    
    return "\n".join(lines)


def clear_pending_loot(channel_id: str):
    """Clear pending loot after distribution."""
    if channel_id in _pending_loot:
        del _pending_loot[channel_id]


# =============================================================================
# INVENTORY CONTEXT FOR AI
# =============================================================================

def get_inventory_context_for_ai(user_id: str) -> str:
    """Generate inventory context for the AI prompt."""
    from utils.character_manager import load_character
    
    char = load_character(user_id)
    if not char:
        return ""
    
    lines = []
    
    # Equipped items
    equipment = char.get("equipment", {})
    equipped_items = []
    if equipment.get("weapon"):
        equipped_items.append(f"Weapon: {equipment['weapon']}")
    if equipment.get("armor"):
        equipped_items.append(f"Armor: {equipment['armor']}")
    if equipment.get("shield"):
        equipped_items.append(f"Shield")
    
    if equipped_items:
        lines.append(f"Equipped: {', '.join(equipped_items)}")
    
    # Attuned items
    attuned = char.get("attuned_items", [])
    if attuned:
        lines.append(f"Attuned: {', '.join(attuned)}")
    
    # Notable inventory items (potions, magic items, tools)
    inventory = char.get("inventory", [])
    notable_items = []
    for item in inventory:
        item_lower = item.lower()
        if any(keyword in item_lower for keyword in ["potion", "scroll", "wand", "ring", "amulet", "cloak", "+1", "+2", "+3", "rope", "torch", "lantern"]):
            notable_items.append(item)
    
    if notable_items:
        # Count duplicates
        item_counts = {}
        for item in notable_items:
            item_counts[item] = item_counts.get(item, 0) + 1
        
        notable_str = []
        for item, count in item_counts.items():
            if count > 1:
                notable_str.append(f"{item} (×{count})")
            else:
                notable_str.append(item)
        
        lines.append(f"Notable items: {', '.join(notable_str[:10])}")  # Limit to 10
    
    # Gold
    gold = char.get("gold", 0)
    if gold > 0:
        lines.append(f"Gold: {gold} gp")
    
    # Encumbrance warning
    enc = calculate_encumbrance(user_id)
    if enc.get("status") in ["encumbered", "heavily_encumbered", "over_encumbered"]:
        lines.append(f"⚠️ {enc['status'].replace('_', ' ').title()}")
    
    if lines:
        return "**Equipment:** " + " | ".join(lines)
    return ""


def get_party_inventory_context(player_ids: List[str]) -> str:
    """Get inventory context for the whole party."""
    contexts = []
    for pid in player_ids:
        from utils.character_manager import load_character
        char = load_character(pid)
        if char:
            name = char.get("name", "Unknown")
            ctx = get_inventory_context_for_ai(pid)
            if ctx:
                contexts.append(f"{name}: {ctx}")
    
    if contexts:
        return "\n**Party Equipment:**\n" + "\n".join(contexts)
    return ""
