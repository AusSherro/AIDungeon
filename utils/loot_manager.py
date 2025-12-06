"""
Loot Tables & Treasure Generation
Random loot drops, treasure hoards, and magic item generation for D&D 5e.
"""

import random
from typing import Dict, List, Optional, Tuple
from enum import Enum

# =============================================================================
# LOOT RARITY
# =============================================================================

class Rarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    VERY_RARE = "very_rare"
    LEGENDARY = "legendary"

RARITY_COLORS = {
    Rarity.COMMON: "⚪",
    Rarity.UNCOMMON: "🟢",
    Rarity.RARE: "🔵",
    Rarity.VERY_RARE: "🟣",
    Rarity.LEGENDARY: "🟠",
}

# =============================================================================
# CURRENCY
# =============================================================================

def roll_currency(cr: int) -> Dict[str, int]:
    """
    Roll random currency based on Challenge Rating.
    
    Args:
        cr: Challenge Rating of the encounter
        
    Returns:
        Dict with cp, sp, ep, gp, pp amounts
    """
    currency = {'cp': 0, 'sp': 0, 'ep': 0, 'gp': 0, 'pp': 0}
    
    if cr < 1:
        # Very low CR - copper and silver
        currency['cp'] = random.randint(1, 6) * 10
        currency['sp'] = random.randint(0, 3) * 5
    elif cr <= 4:
        # Low CR - silver and gold
        currency['sp'] = random.randint(2, 12) * 10
        currency['gp'] = random.randint(1, 6) * 5
    elif cr <= 10:
        # Medium CR - gold focus
        currency['gp'] = random.randint(4, 24) * 10
        if random.random() < 0.3:
            currency['pp'] = random.randint(1, 6)
    elif cr <= 16:
        # High CR - gold and platinum
        currency['gp'] = random.randint(6, 36) * 50
        currency['pp'] = random.randint(2, 12) * 5
    else:
        # Very high CR - massive wealth
        currency['gp'] = random.randint(10, 60) * 100
        currency['pp'] = random.randint(5, 30) * 10
    
    return currency


def format_currency(currency: Dict[str, int]) -> str:
    """Format currency dict as a readable string."""
    parts = []
    if currency.get('pp', 0) > 0:
        parts.append(f"{currency['pp']} pp")
    if currency.get('gp', 0) > 0:
        parts.append(f"{currency['gp']} gp")
    if currency.get('ep', 0) > 0:
        parts.append(f"{currency['ep']} ep")
    if currency.get('sp', 0) > 0:
        parts.append(f"{currency['sp']} sp")
    if currency.get('cp', 0) > 0:
        parts.append(f"{currency['cp']} cp")
    
    return ", ".join(parts) if parts else "nothing"


def currency_to_gp(currency: Dict[str, int]) -> float:
    """Convert all currency to gold piece equivalent."""
    return (
        currency.get('cp', 0) / 100 +
        currency.get('sp', 0) / 10 +
        currency.get('ep', 0) / 2 +
        currency.get('gp', 0) +
        currency.get('pp', 0) * 10
    )


# =============================================================================
# MUNDANE LOOT TABLES
# =============================================================================

MUNDANE_LOOT = {
    'weapons': [
        "Rusty Dagger", "Chipped Shortsword", "Worn Handaxe", "Bent Spear",
        "Crude Club", "Battered Shield", "Old Crossbow", "Quiver (12 arrows)",
        "Light Hammer", "Sling with stones",
    ],
    'armor': [
        "Torn Leather Armor", "Dented Chain Shirt", "Padded Vest",
        "Wooden Shield", "Battered Helm", "Old Boots",
    ],
    'adventuring_gear': [
        "Rope (50 ft)", "Torch (3)", "Rations (3 days)", "Waterskin",
        "Backpack", "Bedroll", "Tinderbox", "Crowbar", "Grappling Hook",
        "Lantern", "Oil Flask (3)", "Pitons (10)", "Hempen Rope",
        "Caltrops", "Ball Bearings", "Chalk (5 pieces)", "Mirror",
    ],
    'valuables': [
        "Silver Ring", "Copper Bracelet", "Glass Beads", "Silk Scarf",
        "Pewter Goblet", "Ivory Dice", "Carved Bone Figurine",
        "Embroidered Handkerchief", "Polished Stone", "Feathered Hat",
    ],
    'trinkets': [
        "Lucky Rabbit's Foot", "Strange Coin", "Love Letter",
        "Wanted Poster", "Treasure Map (probably fake)", "Key (unknown lock)",
        "Playing Cards", "Loaded Dice", "Empty Vial", "Mysterious Note",
        "Old Journal", "Pressed Flower", "Lock of Hair", "Small Bell",
    ],
}

GEMS = {
    10: ["Azurite", "Banded Agate", "Blue Quartz", "Eye Agate", "Hematite", 
         "Lapis Lazuli", "Malachite", "Moss Agate", "Obsidian", "Rhodochrosite",
         "Tiger Eye", "Turquoise"],
    50: ["Bloodstone", "Carnelian", "Chalcedony", "Chrysoprase", "Citrine",
         "Jasper", "Moonstone", "Onyx", "Quartz", "Sardonyx", "Star Rose Quartz",
         "Zircon"],
    100: ["Amber", "Amethyst", "Chrysoberyl", "Coral", "Garnet", "Jade", "Jet",
          "Pearl", "Spinel", "Tourmaline"],
    500: ["Alexandrite", "Aquamarine", "Black Pearl", "Blue Spinel", 
          "Peridot", "Topaz"],
    1000: ["Black Opal", "Blue Sapphire", "Emerald", "Fire Opal", "Opal",
           "Star Ruby", "Star Sapphire", "Yellow Sapphire"],
    5000: ["Black Sapphire", "Diamond", "Jacinth", "Ruby"],
}

ART_OBJECTS = {
    25: ["Silver ewer", "Carved bone statuette", "Small gold bracelet",
         "Cloth-of-gold vestments", "Black velvet mask", "Copper chalice"],
    250: ["Gold ring set with bloodstones", "Carved ivory statuette",
          "Gold bracelet", "Silver necklace with gemstone pendant",
          "Bronze crown", "Silk robe with gold embroidery"],
    750: ["Silver chalice with moonstones", "Silver-plated steel longsword",
          "Carved harp of exotic wood", "Small gold idol", "Gold dragon comb",
          "Obsidian statuette with gold fittings"],
    2500: ["Fine gold chain set with fire opal", "Old masterpiece painting",
           "Embroidered silk mantle with gems", "Platinum bracelet",
           "Gold crown with sapphires", "Ivory drinking horn with gold filigree"],
    7500: ["Jeweled gold crown", "Jeweled platinum ring", "Small gold statuette",
           "Gold dragon figurine with gems", "Masterwork jeweled dagger"],
}

# =============================================================================
# MAGIC ITEMS
# =============================================================================

MAGIC_ITEMS = {
    Rarity.COMMON: [
        {"name": "Potion of Healing", "type": "potion", "effect": "Heals 2d4+2 HP"},
        {"name": "Cloak of Billowing", "type": "wondrous", "effect": "Billows dramatically on command"},
        {"name": "Dread Helm", "type": "armor", "effect": "Eyes glow red while worn"},
        {"name": "Hat of Wizardry", "type": "wondrous", "effect": "+1 to spell attack rolls"},
        {"name": "Candle of the Deep", "type": "wondrous", "effect": "Cannot be extinguished by water"},
        {"name": "Veteran's Cane", "type": "weapon", "effect": "Transforms into a longsword"},
        {"name": "Tankard of Sobriety", "type": "wondrous", "effect": "Never get drunk"},
        {"name": "Ear Horn of Hearing", "type": "wondrous", "effect": "Advantage on Perception (hearing)"},
    ],
    Rarity.UNCOMMON: [
        {"name": "Bag of Holding", "type": "wondrous", "effect": "Holds 500 lbs in extradimensional space"},
        {"name": "+1 Weapon", "type": "weapon", "effect": "+1 to attack and damage rolls"},
        {"name": "+1 Shield", "type": "armor", "effect": "+1 bonus to AC (on top of shield bonus)"},
        {"name": "Boots of Elvenkind", "type": "wondrous", "effect": "Advantage on Stealth checks"},
        {"name": "Cloak of Elvenkind", "type": "wondrous", "effect": "Advantage on Stealth, disadvantage to spot you"},
        {"name": "Gauntlets of Ogre Power", "type": "wondrous", "effect": "STR becomes 19"},
        {"name": "Goggles of Night", "type": "wondrous", "effect": "Darkvision 60 ft"},
        {"name": "Immovable Rod", "type": "wondrous", "effect": "Stays fixed in place when activated"},
        {"name": "Potion of Greater Healing", "type": "potion", "effect": "Heals 4d4+4 HP"},
        {"name": "Ring of Protection", "type": "ring", "effect": "+1 to AC and saving throws"},
        {"name": "Rope of Climbing", "type": "wondrous", "effect": "Moves and knots on command"},
        {"name": "Wand of Magic Missiles", "type": "wand", "effect": "Casts Magic Missile (7 charges)"},
    ],
    Rarity.RARE: [
        {"name": "+2 Weapon", "type": "weapon", "effect": "+2 to attack and damage rolls"},
        {"name": "+2 Shield", "type": "armor", "effect": "+2 bonus to AC"},
        {"name": "Amulet of Health", "type": "wondrous", "effect": "CON becomes 19"},
        {"name": "Belt of Hill Giant Strength", "type": "wondrous", "effect": "STR becomes 21"},
        {"name": "Cloak of Displacement", "type": "wondrous", "effect": "Disadvantage on attacks against you"},
        {"name": "Flame Tongue", "type": "weapon", "effect": "+2d6 fire damage, sheds light"},
        {"name": "Ring of Spell Storing", "type": "ring", "effect": "Stores up to 5 spell levels"},
        {"name": "Staff of the Python", "type": "staff", "effect": "Becomes a giant constrictor snake"},
        {"name": "Wand of Fireballs", "type": "wand", "effect": "Casts Fireball (7 charges)"},
        {"name": "Wings of Flying", "type": "wondrous", "effect": "Fly speed 60 ft for 1 hour"},
        {"name": "Potion of Superior Healing", "type": "potion", "effect": "Heals 8d4+8 HP"},
    ],
    Rarity.VERY_RARE: [
        {"name": "+3 Weapon", "type": "weapon", "effect": "+3 to attack and damage rolls"},
        {"name": "+3 Shield", "type": "armor", "effect": "+3 bonus to AC"},
        {"name": "Belt of Fire Giant Strength", "type": "wondrous", "effect": "STR becomes 25"},
        {"name": "Cloak of Invisibility", "type": "wondrous", "effect": "Invisible for 2 hours"},
        {"name": "Dancing Sword", "type": "weapon", "effect": "Fights on its own"},
        {"name": "Ring of Regeneration", "type": "ring", "effect": "Regain 1d6 HP every 10 minutes"},
        {"name": "Ring of Telekinesis", "type": "ring", "effect": "Cast Telekinesis at will"},
        {"name": "Rod of Alertness", "type": "rod", "effect": "+1 initiative, can't be surprised"},
        {"name": "Staff of Fire", "type": "staff", "effect": "Cast fire spells (10 charges)"},
        {"name": "Staff of Power", "type": "staff", "effect": "+2 AC, saves, spell attacks, 20 charges"},
    ],
    Rarity.LEGENDARY: [
        {"name": "Holy Avenger", "type": "weapon", "effect": "+3, extra radiant vs fiends/undead, aura"},
        {"name": "Luck Blade", "type": "weapon", "effect": "+1 saves, reroll 1/day, wish (1d4-1)"},
        {"name": "Ring of Three Wishes", "type": "ring", "effect": "Cast Wish 3 times"},
        {"name": "Rod of Lordly Might", "type": "rod", "effect": "Multiple weapon forms, special powers"},
        {"name": "Robe of the Archmagi", "type": "wondrous", "effect": "+2 AC, saves, spell DC, resistance"},
        {"name": "Staff of the Magi", "type": "staff", "effect": "Absorb spells, 50 charges, many spells"},
        {"name": "Vorpal Sword", "type": "weapon", "effect": "+3, decapitates on natural 20"},
        {"name": "Belt of Storm Giant Strength", "type": "wondrous", "effect": "STR becomes 29"},
        {"name": "Cloak of Invisibility", "type": "wondrous", "effect": "Permanent invisibility"},
    ],
}


# =============================================================================
# LOOT GENERATION FUNCTIONS
# =============================================================================

def roll_mundane_loot(count: int = 1, category: str = None) -> List[str]:
    """
    Roll random mundane loot items.
    
    Args:
        count: Number of items to generate
        category: Specific category or None for random
        
    Returns:
        List of item names
    """
    items = []
    categories = list(MUNDANE_LOOT.keys())
    
    for _ in range(count):
        cat = category if category and category in MUNDANE_LOOT else random.choice(categories)
        item = random.choice(MUNDANE_LOOT[cat])
        items.append(item)
    
    return items


def roll_gems(cr: int, count: int = None) -> List[Tuple[str, int]]:
    """
    Roll random gems based on CR.
    
    Args:
        cr: Challenge Rating
        count: Number of gems (default based on CR)
        
    Returns:
        List of (gem_name, value_gp) tuples
    """
    # Determine gem tier based on CR
    if cr <= 4:
        values = [10, 50]
    elif cr <= 10:
        values = [50, 100]
    elif cr <= 16:
        values = [100, 500]
    else:
        values = [500, 1000, 5000]
    
    if count is None:
        count = random.randint(1, max(1, cr // 2))
    
    gems = []
    for _ in range(count):
        value = random.choice(values)
        gem_name = random.choice(GEMS[value])
        gems.append((gem_name, value))
    
    return gems


def roll_art_objects(cr: int, count: int = None) -> List[Tuple[str, int]]:
    """
    Roll random art objects based on CR.
    
    Args:
        cr: Challenge Rating
        count: Number of items (default based on CR)
        
    Returns:
        List of (object_name, value_gp) tuples
    """
    # Determine value tier based on CR
    if cr <= 4:
        values = [25]
    elif cr <= 10:
        values = [25, 250]
    elif cr <= 16:
        values = [250, 750]
    else:
        values = [750, 2500, 7500]
    
    if count is None:
        count = random.randint(1, max(1, cr // 3))
    
    objects = []
    for _ in range(count):
        value = random.choice(values)
        obj_name = random.choice(ART_OBJECTS[value])
        objects.append((obj_name, value))
    
    return objects


def roll_magic_item(max_rarity: Rarity = Rarity.RARE) -> Optional[Dict]:
    """
    Roll a random magic item up to a maximum rarity.
    
    Args:
        max_rarity: Maximum rarity to roll
        
    Returns:
        Magic item dict or None
    """
    # Rarity weights (more common items more likely)
    rarity_weights = {
        Rarity.COMMON: 50,
        Rarity.UNCOMMON: 30,
        Rarity.RARE: 15,
        Rarity.VERY_RARE: 4,
        Rarity.LEGENDARY: 1,
    }
    
    # Filter to max rarity
    rarity_order = [Rarity.COMMON, Rarity.UNCOMMON, Rarity.RARE, Rarity.VERY_RARE, Rarity.LEGENDARY]
    max_index = rarity_order.index(max_rarity)
    available = rarity_order[:max_index + 1]
    
    # Weighted random selection
    total_weight = sum(rarity_weights[r] for r in available)
    roll = random.randint(1, total_weight)
    
    cumulative = 0
    selected_rarity = available[0]
    for rarity in available:
        cumulative += rarity_weights[rarity]
        if roll <= cumulative:
            selected_rarity = rarity
            break
    
    items = MAGIC_ITEMS.get(selected_rarity, [])
    if not items:
        return None
    
    item = random.choice(items).copy()
    item['rarity'] = selected_rarity.value
    item['rarity_icon'] = RARITY_COLORS[selected_rarity]
    return item


def generate_treasure_hoard(cr: int, include_magic: bool = True) -> Dict:
    """
    Generate a complete treasure hoard based on CR.
    
    Args:
        cr: Challenge Rating of the encounter
        include_magic: Whether to include magic items
        
    Returns:
        Dict with all treasure components
    """
    hoard = {
        'currency': roll_currency(cr),
        'gems': [],
        'art_objects': [],
        'magic_items': [],
        'mundane': [],
    }
    
    # Add gems (chance based on CR)
    if random.random() < min(0.8, 0.3 + cr * 0.05):
        hoard['gems'] = roll_gems(cr)
    
    # Add art objects (chance based on CR)
    if random.random() < min(0.6, 0.2 + cr * 0.04):
        hoard['art_objects'] = roll_art_objects(cr)
    
    # Add magic items (chance based on CR)
    if include_magic and random.random() < min(0.5, 0.1 + cr * 0.03):
        # Determine max rarity based on CR
        if cr <= 4:
            max_rarity = Rarity.UNCOMMON
        elif cr <= 10:
            max_rarity = Rarity.RARE
        elif cr <= 16:
            max_rarity = Rarity.VERY_RARE
        else:
            max_rarity = Rarity.LEGENDARY
        
        num_items = 1 if cr < 10 else random.randint(1, 2)
        for _ in range(num_items):
            item = roll_magic_item(max_rarity)
            if item:
                hoard['magic_items'].append(item)
    
    # Add mundane loot
    hoard['mundane'] = roll_mundane_loot(random.randint(1, 3))
    
    return hoard


def generate_enemy_loot(enemy_name: str, cr: int = 1) -> Dict:
    """
    Generate loot dropped by a defeated enemy.
    
    Args:
        enemy_name: Name of the defeated enemy
        cr: Challenge Rating of the enemy
        
    Returns:
        Dict with loot items
    """
    loot = {
        'enemy': enemy_name,
        'currency': {},
        'items': [],
    }
    
    # Currency (most enemies have some coins)
    if random.random() < 0.7:
        loot['currency'] = roll_currency(max(0, cr - 1))
    
    # Mundane loot
    if random.random() < 0.5:
        loot['items'].extend(roll_mundane_loot(1))
    
    # Small chance of something valuable
    if random.random() < 0.1 + cr * 0.02:
        if random.random() < 0.5:
            gems = roll_gems(cr, 1)
            for gem, value in gems:
                loot['items'].append(f"{gem} ({value} gp)")
        else:
            item = roll_magic_item(Rarity.UNCOMMON if cr < 5 else Rarity.RARE)
            if item:
                loot['items'].append(f"{item['rarity_icon']} {item['name']}")
    
    return loot


def format_loot_display(loot: Dict) -> str:
    """Format loot dict for Discord display."""
    lines = ["💰 **Loot Found:**"]
    
    if loot.get('currency'):
        currency_str = format_currency(loot['currency'])
        if currency_str != "nothing":
            lines.append(f"  🪙 {currency_str}")
    
    if loot.get('gems'):
        for gem, value in loot['gems']:
            lines.append(f"  💎 {gem} ({value} gp)")
    
    if loot.get('art_objects'):
        for obj, value in loot['art_objects']:
            lines.append(f"  🖼️ {obj} ({value} gp)")
    
    if loot.get('magic_items'):
        for item in loot['magic_items']:
            lines.append(f"  {item['rarity_icon']} **{item['name']}** - {item['effect']}")
    
    if loot.get('mundane'):
        for item in loot['mundane']:
            lines.append(f"  📦 {item}")
    
    if loot.get('items'):
        for item in loot['items']:
            lines.append(f"  📦 {item}")
    
    return "\n".join(lines) if len(lines) > 1 else "No loot found."


def calculate_total_value(loot: Dict) -> int:
    """Calculate total gold value of loot."""
    total = 0
    
    if loot.get('currency'):
        total += int(currency_to_gp(loot['currency']))
    
    if loot.get('gems'):
        total += sum(value for _, value in loot['gems'])
    
    if loot.get('art_objects'):
        total += sum(value for _, value in loot['art_objects'])
    
    return total
