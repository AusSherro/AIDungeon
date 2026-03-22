"""
Combat Trigger Detection System for AI DM Bot

Automatically detects when combat should start from:
1. AI narration (enemies attack, combat begins, etc.)
2. Player actions (I attack, I cast fireball at, etc.)
3. Structured AI combat tags [COMBAT: ...]

Handles:
- Combat intent detection from narration and player actions
- Enemy parsing and stat lookup
- Surprise round mechanics
- Post-combat loot generation
"""

import re
import random
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from utils.tag_parser import parse_all_tags, ParsedTags


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class CombatInitiator(Enum):
    """Who initiated combat."""
    AI_NARRATION = "ai_narration"      # AI described enemies attacking
    PLAYER_ATTACK = "player_attack"     # Player declared an attack
    STRUCTURED_TAG = "structured_tag"   # AI used [COMBAT: ...] format
    AMBUSH_PARTY = "ambush_party"       # Party surprised enemies
    AMBUSH_ENEMY = "ambush_enemy"       # Enemies surprised party


@dataclass
class CombatTriggerResult:
    """Result of combat trigger detection."""
    triggered: bool = False
    initiator: Optional[CombatInitiator] = None
    enemies: List[Dict[str, Any]] = field(default_factory=list)
    surprise_round: Optional[str] = None  # 'party', 'enemies', or None
    context: str = ""
    error: Optional[str] = None


@dataclass
class EnemySpec:
    """Specification for an enemy to add to combat."""
    name: str
    count: int = 1
    hp: Optional[int] = None
    ac: Optional[int] = None
    from_database: bool = False


# =============================================================================
# COMBAT DETECTION PATTERNS
# =============================================================================

# Structured AI combat tag pattern: [COMBAT: 3 goblins, 1 hobgoblin captain]
STRUCTURED_COMBAT_PATTERN = re.compile(
    r'\[COMBAT:\s*([^\]]+)\]',
    re.IGNORECASE
)

# AI narration combat triggers - when AI describes combat starting
AI_COMBAT_TRIGGERS = re.compile(
    r'(?:'
    r'roll\s+(?:for\s+)?initiative|'
    r'combat\s+begins|'
    r'the\s+battle\s+(?:begins|starts|is\s+joined)|'
    r'(?:they|he|she|it|the\s+\w+)\s+(?:attacks?|lunges?|charges?|swings?|strikes?)\s+(?:at\s+)?(?:you|the\s+party)|'
    r'(?:draw|draws|drawn)\s+(?:their|his|her|its)\s+(?:weapons?|swords?|blades?|axes?)|'
    r'ambush!?|'
    r'(?:enemies|creatures?|monsters?)\s+(?:attack|approach\s+aggressively|ready\s+(?:for|to)\s+(?:combat|attack|fight))|'
    r'hostilities?\s+(?:begins?|breaks?\s+out|commences?)|'
    r'prepare\s+(?:for|to)\s+(?:fight|battle|defend)|'
    r'initiative\s+order'
    r')',
    re.IGNORECASE
)

# Player action combat triggers - when player declares attack intent
PLAYER_ATTACK_PATTERNS = [
    # Direct attacks
    re.compile(r'i\s+(?:attack|strike|hit|slash|stab|punch|kick)\s+(?:the\s+)?(.+)', re.I),
    re.compile(r'i\s+(?:swing|thrust|jab|smash)\s+(?:my\s+\w+\s+)?(?:at\s+)?(?:the\s+)?(.+)', re.I),
    
    # Ranged attacks
    re.compile(r'i\s+(?:shoot|fire|loose)\s+(?:an?\s+)?(?:arrow|bolt|bullet)?\s*(?:at\s+)?(?:the\s+)?(.+)', re.I),
    re.compile(r'i\s+(?:throw|hurl)\s+(?:my\s+)?(?:\w+\s+)?(?:at\s+)?(?:the\s+)?(.+)', re.I),
    
    # Spell attacks
    re.compile(r'i\s+cast\s+(?:a\s+)?(\w+(?:\s+\w+)?)\s+(?:at|on|against)\s+(?:the\s+)?(.+)', re.I),
    re.compile(r'i\s+(?:use|unleash|channel)\s+(.+?)\s+(?:at|on|against)\s+(?:the\s+)?(.+)', re.I),
    
    # Aggressive actions
    re.compile(r'i\s+(?:charge|rush|leap)\s+(?:at\s+)?(?:the\s+)?(.+)', re.I),
    re.compile(r'i\s+(?:draw|unsheathe)\s+(?:my\s+)?(?:\w+)\s+and\s+attack\s+(?:the\s+)?(.+)', re.I),
]

# Enemy name extraction pattern - find enemies in text
ENEMY_EXTRACT_PATTERN = re.compile(
    r'(\d+)?\s*'  # Optional count
    r'(goblins?|orcs?|bandits?|skeletons?|zombies?|wolves?|spiders?|'
    r'kobolds?|cultists?|thugs?|guards?|soldiers?|knights?|trolls?|ogres?|'
    r'gnolls?|bugbears?|hobgoblins?|ghouls?|ghasts?|wights?|wraiths?|'
    r'dire\s+wolves?|giant\s+spiders?|owlbears?|dragons?|drakes?|'
    r'elementals?|demons?|devils?|imps?|mephits?|'
    r'rats?|giant\s+rats?|bats?|giant\s+bats?|'
    r'minotaurs?|medusas?|harpies?|griffons?|manticores?|'
    r'vampires?|liches?|mummies?|spectres?|shadows?|'
    r'giants?|hill\s+giants?|frost\s+giants?|fire\s+giants?|'
    r'assassins?|archers?|mages?|priests?|warlocks?|necromancers?|'
    r'berserkers?|gladiators?|veterans?|champions?)',
    re.IGNORECASE
)

# Structured enemy spec pattern: "3 goblins, 1 hobgoblin captain"
STRUCTURED_ENEMY_PATTERN = re.compile(
    r'(\d+)\s+([a-zA-Z][a-zA-Z\s]+?)(?:,|$|\sand\s)',
    re.IGNORECASE
)


# =============================================================================
# MONSTER DATABASE INTEGRATION
# =============================================================================

def get_monster_stats(monster_name: str) -> Optional[Dict[str, Any]]:
    """
    Look up monster stats from dnd5e_data.py.
    
    Returns dict with hp, ac, stats, etc. or None if not found.
    """
    try:
        from utils.dnd5e_data import MONSTERS, get_monster
        
        # First try exact match
        if monster_name in MONSTERS:
            return MONSTERS[monster_name]
        
        # Try title case
        title_name = monster_name.title()
        if title_name in MONSTERS:
            return MONSTERS[title_name]
        
        # Try using get_monster which handles variations
        result = get_monster(monster_name)
        if result:
            return result
        
        return None
    except ImportError:
        return None


def normalize_monster_name(name: str) -> str:
    """Normalize monster name for database lookup."""
    # Remove trailing numbers/suffixes like "goblin1" -> "goblin"
    name = re.sub(r'\d+$', '', name.strip())
    
    # Convert to singular if plural
    singular_map = {
        'goblins': 'goblin',
        'orcs': 'orc',
        'bandits': 'bandit',
        'skeletons': 'skeleton',
        'zombies': 'zombie',
        'wolves': 'wolf',
        'dire wolves': 'dire wolf',
        'spiders': 'spider',
        'giant spiders': 'giant spider',
        'kobolds': 'kobold',
        'cultists': 'cultist',
        'thugs': 'thug',
        'guards': 'guard',
        'soldiers': 'soldier',
        'knights': 'knight',
        'trolls': 'troll',
        'ogres': 'ogre',
        'gnolls': 'gnoll',
        'bugbears': 'bugbear',
        'hobgoblins': 'hobgoblin',
        'ghouls': 'ghoul',
        'ghasts': 'ghast',
        'wights': 'wight',
        'wraiths': 'wraith',
        'rats': 'rat',
        'giant rats': 'giant rat',
        'bats': 'bat',
        'giant bats': 'giant bat',
    }
    
    lower_name = name.lower().strip()
    if lower_name in singular_map:
        return singular_map[lower_name].title()
    
    # Default: title case the name
    return name.strip().title()


def build_enemy_list(enemy_specs: List[EnemySpec]) -> List[Dict[str, Any]]:
    """
    Convert enemy specifications to full enemy data for combat.
    
    Uses dnd5e_data.py for known monsters, provides defaults for unknown.
    """
    enemies = []
    
    for spec in enemy_specs:
        base_name = normalize_monster_name(spec.name)
        monster_data = get_monster_stats(base_name)
        
        for i in range(spec.count):
            if spec.count > 1:
                display_name = f"{base_name} {i + 1}"
            else:
                display_name = base_name
            
            if monster_data:
                # Use database stats
                enemy = {
                    'name': display_name,
                    'hp': spec.hp or monster_data.get('hp', 10),
                    'ac': spec.ac or monster_data.get('ac', 12),
                    'monster_type': base_name,
                    'cr': monster_data.get('cr', '0'),
                    'xp': monster_data.get('xp', 0),
                    'from_database': True
                }
            else:
                # Use provided stats or defaults
                enemy = {
                    'name': display_name,
                    'hp': spec.hp or 10,
                    'ac': spec.ac or 12,
                    'monster_type': base_name,
                    'cr': '0',
                    'xp': 25,
                    'from_database': False
                }
            
            enemies.append(enemy)
    
    return enemies


# =============================================================================
# COMBAT TRIGGER DETECTION
# =============================================================================

def detect_structured_combat(text: str, parsed: Optional[ParsedTags] = None) -> Optional[CombatTriggerResult]:
    """
    Detect structured combat tag in AI response.
    
    Format: [COMBAT: 3 goblins, 1 hobgoblin captain]
    """
    if parsed is None:
        parsed = parse_all_tags(text)

    if not parsed.combat:
        return None

    enemies_text = parsed.combat[0]["enemies"]
    enemy_specs = parse_enemy_list(enemies_text)
    
    if not enemy_specs:
        return None
    
    enemies = build_enemy_list(enemy_specs)

    surprise = None
    if parsed.surprise:
        surprise = parsed.surprise[0]
    
    return CombatTriggerResult(
        triggered=True,
        initiator=CombatInitiator.STRUCTURED_TAG,
        enemies=enemies,
        surprise_round=surprise,
        context=text
    )


def detect_ai_combat_narration(text: str) -> Optional[CombatTriggerResult]:
    """
    Detect when AI narration indicates combat starting.
    """
    if not AI_COMBAT_TRIGGERS.search(text):
        return None
    
    # Extract enemies from the text
    enemy_specs = extract_enemies_from_text(text)
    
    if not enemy_specs:
        # Combat triggered but no specific enemies identified
        return CombatTriggerResult(
            triggered=True,
            initiator=CombatInitiator.AI_NARRATION,
            enemies=[],
            context=text,
            error="Combat detected but no enemies identified"
        )
    
    enemies = build_enemy_list(enemy_specs)
    
    # Check for ambush keywords
    surprise = None
    if re.search(r'ambush|surprise|caught\s+off\s+guard|didn\'t\s+see', text, re.I):
        # Enemies are ambushing the party
        surprise = 'enemies'
    
    return CombatTriggerResult(
        triggered=True,
        initiator=CombatInitiator.AI_NARRATION,
        enemies=enemies,
        surprise_round=surprise,
        context=text
    )


def detect_player_attack_intent(action: str, context: str = "") -> Optional[CombatTriggerResult]:
    """
    Detect when a player action indicates they want to start combat.
    
    Args:
        action: The player's /do action text
        context: Additional context (e.g., current location, nearby NPCs)
    
    Returns:
        CombatTriggerResult if attack intent detected, None otherwise
    """
    for pattern in PLAYER_ATTACK_PATTERNS:
        match = pattern.search(action)
        if match:
            # Try to identify the target
            target = match.group(1) if match.lastindex >= 1 else ""
            target = target.strip().rstrip('.!?')
            
            # Try to extract enemies from the target
            enemy_specs = extract_enemies_from_text(target)
            
            if not enemy_specs and target:
                # Player is attacking something we don't recognize
                # Create a placeholder - AI will provide stats
                enemy_specs = [EnemySpec(name=target.title(), count=1)]
            
            enemies = build_enemy_list(enemy_specs) if enemy_specs else []
            
            # Check if player is trying to sneak attack (surprise)
            surprise = None
            if re.search(r'sneak|stealth|surprise|from\s+behind|ambush', action, re.I):
                surprise = 'party'
            
            return CombatTriggerResult(
                triggered=True,
                initiator=CombatInitiator.PLAYER_ATTACK,
                enemies=enemies,
                surprise_round=surprise,
                context=action
            )
    
    return None


def parse_enemy_list(enemies_text: str) -> List[EnemySpec]:
    """
    Parse an enemy list string into EnemySpec objects.
    
    Examples:
        "3 goblins, 1 hobgoblin captain" -> [EnemySpec("goblin", 3), EnemySpec("hobgoblin captain", 1)]
        "goblin, orc, orc" -> [EnemySpec("goblin", 1), EnemySpec("orc", 2)]
    """
    specs = []
    
    # First try structured pattern: "3 goblins, 1 hobgoblin"
    for match in STRUCTURED_ENEMY_PATTERN.finditer(enemies_text):
        count = int(match.group(1))
        name = match.group(2).strip()
        specs.append(EnemySpec(name=name, count=count))
    
    if specs:
        return specs
    
    # Fallback: parse comma-separated names
    parts = [p.strip() for p in enemies_text.split(',')]
    name_counts = {}
    
    for part in parts:
        if not part:
            continue
        
        # Check for "X name" format
        count_match = re.match(r'^(\d+)\s+(.+)$', part)
        if count_match:
            count = int(count_match.group(1))
            name = count_match.group(2).strip()
        else:
            count = 1
            name = part
        
        # Normalize name
        name = normalize_monster_name(name)
        
        if name in name_counts:
            name_counts[name] += count
        else:
            name_counts[name] = count
    
    return [EnemySpec(name=name, count=count) for name, count in name_counts.items()]


def extract_enemies_from_text(text: str) -> List[EnemySpec]:
    """
    Extract enemy specifications from freeform text.
    """
    specs = []
    seen = set()
    
    for match in ENEMY_EXTRACT_PATTERN.finditer(text):
        count = int(match.group(1)) if match.group(1) else 1
        name = normalize_monster_name(match.group(2))
        
        if name.lower() not in seen:
            seen.add(name.lower())
            specs.append(EnemySpec(name=name, count=count))
    
    return specs


# =============================================================================
# SURPRISE MECHANICS
# =============================================================================

def calculate_surprise(
    party_stealth_rolls: List[int],
    enemy_passive_perception: int,
    party_passive_perception: Optional[List[int]] = None,
    enemy_stealth_roll: Optional[int] = None
) -> Tuple[bool, bool]:
    """
    Calculate surprise for combat.
    
    Args:
        party_stealth_rolls: List of party stealth rolls (if sneaking)
        enemy_passive_perception: Enemies' passive perception
        party_passive_perception: List of party passive perception scores
        enemy_stealth_roll: Enemy stealth roll (if ambushing)
    
    Returns:
        (party_surprised, enemies_surprised) tuple
    """
    party_surprised = False
    enemies_surprised = False
    
    # Check if party surprises enemies
    if party_stealth_rolls:
        # All party members must beat enemy perception
        lowest_stealth = min(party_stealth_rolls)
        if lowest_stealth >= enemy_passive_perception:
            enemies_surprised = True
    
    # Check if enemies surprise party
    if enemy_stealth_roll and party_passive_perception:
        # Enemies must beat all party passive perceptions
        highest_passive = max(party_passive_perception)
        if enemy_stealth_roll >= highest_passive:
            party_surprised = True
    
    return (party_surprised, enemies_surprised)


def roll_surprise_stealth(dex_modifier: int = 0, proficiency: int = 0, has_proficiency: bool = False) -> int:
    """Roll stealth for surprise calculation."""
    roll = random.randint(1, 20)
    bonus = dex_modifier + (proficiency if has_proficiency else 0)
    return roll + bonus


# =============================================================================
# POST-COMBAT LOOT GENERATION
# =============================================================================

# CR to gold and loot rarity mapping
CR_LOOT_TABLE = {
    '0': {'gold_min': 1, 'gold_max': 6, 'magic_chance': 0.01},
    '1/8': {'gold_min': 2, 'gold_max': 8, 'magic_chance': 0.02},
    '1/4': {'gold_min': 3, 'gold_max': 12, 'magic_chance': 0.03},
    '1/2': {'gold_min': 5, 'gold_max': 20, 'magic_chance': 0.05},
    '1': {'gold_min': 10, 'gold_max': 30, 'magic_chance': 0.08},
    '2': {'gold_min': 15, 'gold_max': 50, 'magic_chance': 0.10},
    '3': {'gold_min': 25, 'gold_max': 75, 'magic_chance': 0.12},
    '4': {'gold_min': 40, 'gold_max': 100, 'magic_chance': 0.15},
    '5': {'gold_min': 60, 'gold_max': 150, 'magic_chance': 0.18},
    '6': {'gold_min': 80, 'gold_max': 200, 'magic_chance': 0.20},
    '7': {'gold_min': 100, 'gold_max': 300, 'magic_chance': 0.22},
    '8': {'gold_min': 150, 'gold_max': 400, 'magic_chance': 0.25},
    '9': {'gold_min': 200, 'gold_max': 500, 'magic_chance': 0.28},
    '10': {'gold_min': 300, 'gold_max': 700, 'magic_chance': 0.30},
}

# Common mundane loot by enemy type
MUNDANE_LOOT = {
    'humanoid': [
        'Pouch with coins', 'Dagger', 'Leather pouch', 'Rations (1 day)',
        'Waterskin', 'Tinderbox', 'Torch', 'Rope (50 feet)', 'Bedroll',
        'Simple weapon', 'Light armor scraps', 'Worn boots'
    ],
    'undead': [
        'Tattered clothes', 'Old coins', 'Rusty weapon', 'Bone fragment',
        'Ancient jewelry', 'Decayed scroll', 'Burial shroud'
    ],
    'beast': [
        'Pelt', 'Fangs', 'Claws', 'Hide', 'Meat', 'Bones',
        'Feathers', 'Scales'
    ],
    'monstrosity': [
        'Monster hide', 'Sharp claws', 'Venom sac', 'Strange organ',
        'Tough scales', 'Horn', 'Eye'
    ],
    'default': [
        'Coins', 'Trinket', 'Small gem', 'Curiosity'
    ]
}

# Magic items by rarity for random loot
MAGIC_ITEMS_BY_RARITY = {
    'common': [
        'Potion of Healing', 'Potion of Climbing', 'Candle of the Deep',
        'Cloak of Billowing', 'Dread Helm', 'Ear Horn of Hearing',
        'Mystery Key', 'Perfume of Bewitching', 'Rope of Mending'
    ],
    'uncommon': [
        'Potion of Greater Healing', 'Bag of Holding', 'Boots of Elvenkind',
        'Cloak of Elvenkind', 'Goggles of Night', 'Hat of Disguise',
        'Immovable Rod', 'Ring of Jumping', 'Wand of Magic Missiles'
    ],
    'rare': [
        'Potion of Superior Healing', 'Ring of Protection', 'Cloak of Displacement',
        'Belt of Dwarvenkind', 'Flame Tongue', 'Ring of Spell Storing'
    ]
}


def get_loot_rarity_for_cr(cr: str) -> str:
    """Determine magic item rarity based on CR."""
    try:
        cr_num = float(cr.replace('/', '.').replace('1.8', '0.125').replace('1.4', '0.25').replace('1.2', '0.5'))
    except:
        cr_num = 0
    
    if cr_num <= 2:
        return 'common'
    elif cr_num <= 6:
        return 'uncommon'
    else:
        return 'rare'


def generate_loot_for_enemies(
    defeated_enemies: List[Dict[str, Any]],
    party_size: int = 4
) -> Dict[str, Any]:
    """
    Generate loot based on defeated enemies.
    
    Args:
        defeated_enemies: List of enemy dicts with name, cr, xp, etc.
        party_size: Number of players for scaling
    
    Returns:
        Dict with 'gold', 'items', 'magic_items' lists
    """
    total_gold = 0
    items = []
    magic_items = []
    
    for enemy in defeated_enemies:
        cr = enemy.get('cr', '0')
        enemy_type = enemy.get('type', 'humanoid')
        
        # Get loot table for this CR
        loot_table = CR_LOOT_TABLE.get(cr, CR_LOOT_TABLE['0'])
        
        # Roll gold
        gold = random.randint(loot_table['gold_min'], loot_table['gold_max'])
        total_gold += gold
        
        # Roll for mundane loot (50% chance per enemy)
        if random.random() < 0.5:
            loot_pool = MUNDANE_LOOT.get(enemy_type, MUNDANE_LOOT['default'])
            item = random.choice(loot_pool)
            if item not in items:
                items.append(item)
        
        # Roll for magic item
        if random.random() < loot_table['magic_chance']:
            rarity = get_loot_rarity_for_cr(cr)
            magic_pool = MAGIC_ITEMS_BY_RARITY.get(rarity, MAGIC_ITEMS_BY_RARITY['common'])
            magic_item = random.choice(magic_pool)
            magic_items.append({
                'name': magic_item,
                'rarity': rarity,
                'identified': False  # Requires identification
            })
    
    return {
        'gold': total_gold,
        'items': items,
        'magic_items': magic_items,
        'total_enemies': len(defeated_enemies)
    }


def calculate_xp_from_combat(defeated_enemies: List[Dict[str, Any]], party_size: int = 4) -> int:
    """Calculate total XP from defeated enemies, divided by party size."""
    total_xp = sum(enemy.get('xp', 0) for enemy in defeated_enemies)
    return total_xp // party_size if party_size > 0 else total_xp


def generate_and_register_loot(channel_id: str, defeated_enemies: List[Dict[str, Any]], party_size: int = 4) -> Dict[str, Any]:
    """Generate loot from defeated enemies and register it as a claimable loot pile.
    
    This is the single entry point for the loot pipeline:
    combat_trigger generates → inventory_manager stores → claim commands distribute.
    
    Returns:
        The generated loot dict (gold, items, magic_items).
    """
    from utils.inventory_manager import create_loot_distribution
    
    loot = generate_loot_for_enemies(defeated_enemies, party_size)
    
    # Build combined item list
    all_items = list(loot.get('items', []))
    for magic_item in loot.get('magic_items', []):
        if magic_item.get('identified', True):
            all_items.append(magic_item['name'])
        else:
            all_items.append(f"Unidentified {magic_item.get('rarity', 'magic')} item")
    
    gold = loot.get('gold', 0)
    
    if all_items or gold > 0:
        create_loot_distribution(
            channel_id,
            items=all_items,
            currency={"gp": gold},
            source=f"Defeated {len(defeated_enemies)} enemies"
        )
    
    return loot


# =============================================================================
# MAIN DETECTION FUNCTION
# =============================================================================

def detect_combat_trigger(
    text: str,
    player_action: Optional[str] = None,
    is_ai_response: bool = True,
    parsed: Optional[ParsedTags] = None
) -> Optional[CombatTriggerResult]:
    """
    Main function to detect if combat should start.
    
    Checks in order:
    1. Structured combat tag [COMBAT: ...]
    2. AI narration combat triggers
    3. Player attack intent (if player_action provided)
    
    Args:
        text: The text to analyze (AI response or narration)
        player_action: Optional player action to check for attack intent
        is_ai_response: Whether text is from AI (affects detection priority)
        parsed: Optional pre-parsed tags (avoids re-parsing)
    
    Returns:
        CombatTriggerResult if combat should start, None otherwise
    """
    if parsed is None:
        parsed = parse_all_tags(text)

    # First, check for structured tag (highest priority)
    result = detect_structured_combat(text, parsed=parsed)
    if result:
        return result
    
    # Then check AI narration
    if is_ai_response:
        result = detect_ai_combat_narration(text)
        if result:
            return result
    
    # Finally check player attack intent
    if player_action:
        result = detect_player_attack_intent(player_action)
        if result:
            return result
    
    return None


def format_combat_start_message(
    result: CombatTriggerResult,
    initiative_order: List[Dict[str, Any]] = None
) -> str:
    """Format a message announcing combat start."""
    lines = ["⚔️ **COMBAT INITIATED!**\n"]
    
    # Show initiator
    if result.initiator == CombatInitiator.PLAYER_ATTACK:
        lines.append("*You strike first!*\n")
    elif result.initiator == CombatInitiator.AMBUSH_PARTY:
        lines.append("🎯 *You have surprise! Enemies are caught off-guard.*\n")
    elif result.initiator == CombatInitiator.AMBUSH_ENEMY:
        lines.append("💀 *Ambush! The enemies have surprise!*\n")
    
    # List enemies
    if result.enemies:
        enemy_list = ", ".join(e['name'] for e in result.enemies)
        lines.append(f"**Enemies:** {enemy_list}\n")
    
    # Initiative order if provided
    if initiative_order:
        lines.append("\n**Initiative Order:**")
        for i, c in enumerate(initiative_order):
            marker = "➤ " if i == 0 else "  "
            hp_str = f"{c.get('hp', '?')}/{c.get('max_hp', c.get('hp', '?'))}"
            lines.append(f"{marker}**{c['initiative']}** - {c['name']} (HP: {hp_str}, AC: {c.get('ac', '?')})")
    
    # Add hint
    lines.append("\n*Use `/attack <target>` to attack, `/nextturn` when done.*")
    
    return "\n".join(lines)


def format_post_combat_loot(loot: Dict[str, Any]) -> str:
    """Format post-combat loot for display."""
    lines = ["💰 **LOOT FOUND!**\n"]
    
    if loot['gold'] > 0:
        lines.append(f"**Gold:** {loot['gold']} gp")
    
    if loot['items']:
        lines.append(f"**Items:** {', '.join(loot['items'])}")
    
    if loot['magic_items']:
        magic_list = []
        for item in loot['magic_items']:
            if item['identified']:
                magic_list.append(f"✨ {item['name']} ({item['rarity']})")
            else:
                magic_list.append(f"❓ *Unidentified magical item*")
        lines.append(f"**Magic Items:** {', '.join(magic_list)}")
    
    lines.append("\n*Use `/claimloot <item>` to claim, `/splitgold` to divide gold.*")
    lines.append("*Use `/identify <item>` to identify magic items.*")
    
    return "\n".join(lines)
