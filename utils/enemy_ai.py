"""
Enemy AI System for D&D 5e Combat
Provides intelligent decision-making for enemy turns in combat.
"""

import random
from typing import Optional, Dict, List, Any, Tuple
from utils.dice_roller import roll_dice

# =============================================================================
# ENEMY BEHAVIOR PROFILES
# =============================================================================

ENEMY_PROFILES = {
    "mindless": {
        "target_priority": ["nearest"],
        "flee_threshold": None,  # Never flees
        "tactics": "aggressive",
        "description": "Mindless creatures attack the nearest target relentlessly"
    },
    "beast": {
        "target_priority": ["wounded", "isolated", "nearest"],
        "flee_threshold": 0.25,  # Flees at 25% HP
        "tactics": "pack",
        "description": "Pack hunters target the weak and isolated"
    },
    "humanoid_soldier": {
        "target_priority": ["caster", "healer", "lowest_ac"],
        "flee_threshold": 0.5,  # Flees when hurt and outnumbered
        "tactics": "tactical",
        "description": "Trained fighters focus on eliminating threats"
    },
    "humanoid_brute": {
        "target_priority": ["nearest", "wounded"],
        "flee_threshold": 0.3,
        "tactics": "aggressive",
        "description": "Brutes charge in and attack aggressively"
    },
    "spellcaster": {
        "target_priority": ["threat", "grouped", "caster"],
        "flee_threshold": 0.3,
        "tactics": "ranged",
        "description": "Casters stay at range and target groups"
    },
    "boss": {
        "target_priority": ["threat", "spread_damage"],
        "flee_threshold": None,  # Bosses don't flee
        "tactics": "legendary",
        "uses_lair_actions": True,
        "description": "Bosses use legendary abilities and spread damage"
    },
    "support": {
        "target_priority": ["ally_low_hp", "nearest_enemy"],
        "flee_threshold": 0.4,
        "tactics": "support",
        "description": "Support enemies heal allies and debuff players"
    },
}

# Map monster types to behavior profiles
MONSTER_PROFILE_MAP = {
    # Mindless
    "zombie": "mindless",
    "skeleton": "mindless",
    "animated armor": "mindless",
    "flesh golem": "mindless",
    
    # Beasts
    "wolf": "beast",
    "dire wolf": "beast",
    "giant spider": "beast",
    "giant rat": "beast",
    "giant wolf spider": "beast",
    "panther": "beast",
    "lion": "beast",
    "bear": "beast",
    
    # Humanoid Soldiers
    "hobgoblin": "humanoid_soldier",
    "knight": "humanoid_soldier",
    "veteran": "humanoid_soldier",
    "guard": "humanoid_soldier",
    "bandit captain": "humanoid_soldier",
    
    # Humanoid Brutes
    "orc": "humanoid_brute",
    "bugbear": "humanoid_brute",
    "ogre": "humanoid_brute",
    "troll": "humanoid_brute",
    "minotaur": "humanoid_brute",
    
    # Spellcasters
    "goblin shaman": "spellcaster",
    "mage": "spellcaster",
    "cult fanatic": "spellcaster",
    "lich": "spellcaster",
    
    # Bosses (have legendary actions)
    "dragon": "boss",
    "young green dragon": "boss",
    "adult red dragon": "boss",
    "ancient black dragon": "boss",
    "beholder": "boss",
    "mind flayer": "boss",
    
    # Default for humanoid-type enemies
    "goblin": "humanoid_soldier",
    "kobold": "humanoid_soldier",
    "bandit": "humanoid_soldier",
    "cultist": "humanoid_soldier",
    "thug": "humanoid_brute",
}


def get_enemy_profile(enemy: Dict) -> Dict:
    """Get the behavior profile for an enemy based on its type."""
    monster_type = enemy.get('monster_type', enemy.get('name', '')).lower()
    
    # Check if enemy has legendary actions (automatic boss profile)
    if enemy.get('legendary_actions'):
        return ENEMY_PROFILES["boss"]
    
    # Look up in profile map
    for key, profile_name in MONSTER_PROFILE_MAP.items():
        if key in monster_type:
            return ENEMY_PROFILES[profile_name]
    
    # Default to humanoid_brute for unknown enemies
    return ENEMY_PROFILES["humanoid_brute"]


# =============================================================================
# TARGET SELECTION
# =============================================================================

def get_threat_score(target: Dict, enemy: Dict) -> int:
    """
    Calculate a threat score for a target.
    Higher score = more threatening to the enemy.
    """
    score = 0
    
    # Spellcasters are high priority (check for spell slots)
    if target.get('spell_slots'):
        score += 30
    
    # Characters with concentration spells are threats
    if target.get('concentration'):
        score += 25
    
    # Healers (clerics, druids, paladins, bards) are priority
    char_class = target.get('class', '').lower()
    if char_class in ['cleric', 'druid', 'paladin', 'bard']:
        score += 20
    
    # Low HP targets are easier kills
    hp_ratio = target.get('hp', 1) / max(target.get('max_hp', 1), 1)
    if hp_ratio < 0.25:
        score += 15  # Critical HP
    elif hp_ratio < 0.5:
        score += 10  # Wounded
    
    # Low AC = easier to hit
    ac = target.get('ac', 10)
    if ac < 14:
        score += 10
    elif ac > 18:
        score -= 10
    
    return score


def get_distance(pos1: Tuple[int, int], pos2: Tuple[int, int], scale: int = 5) -> int:
    """Calculate distance in feet between two positions (using 5ft grid)."""
    dx = abs(pos1[0] - pos2[0])
    dy = abs(pos1[1] - pos2[1])
    # Use D&D diagonal movement (5ft per square)
    return max(dx, dy) * scale


def attack_target_selection(
    combatants: List[Dict],
    enemy: Dict,
    profile: Optional[Dict] = None
) -> Optional[Dict]:
    """
    Select the best target for an enemy to attack.
    
    Args:
        combatants: List of all combatants in combat
        enemy: The enemy making the attack
        profile: Optional behavior profile override
    
    Returns:
        The selected target, or None if no valid targets
    """
    if profile is None:
        profile = get_enemy_profile(enemy)
    
    # Get valid targets (players who are alive)
    targets = [
        c for c in combatants 
        if c.get('type') == 'player' 
        and c.get('hp', 0) > 0 
        and 'unconscious' not in c.get('status', [])
        and 'dead' not in c.get('status', [])
    ]
    
    if not targets:
        return None
    
    priority = profile.get('target_priority', ['nearest'])
    
    # Score each target based on priority
    target_scores = []
    for target in targets:
        score = 0
        
        for i, criterion in enumerate(priority):
            weight = len(priority) - i  # Earlier criteria are more important
            
            if criterion == 'nearest':
                # Lower distance = higher score
                # Without map positions, estimate based on initiative order
                score += weight * 10
                
            elif criterion == 'wounded':
                hp_ratio = target.get('hp', 1) / max(target.get('max_hp', 1), 1)
                if hp_ratio < 0.5:
                    score += weight * (1 - hp_ratio) * 20
                    
            elif criterion == 'caster':
                if target.get('spell_slots') or target.get('class', '').lower() in ['wizard', 'sorcerer', 'warlock', 'bard', 'cleric', 'druid']:
                    score += weight * 15
                    
            elif criterion == 'healer':
                if target.get('class', '').lower() in ['cleric', 'druid', 'paladin', 'bard']:
                    score += weight * 15
                    
            elif criterion == 'lowest_ac':
                ac = target.get('ac', 10)
                score += weight * (20 - ac)  # Lower AC = higher score
                
            elif criterion == 'threat':
                score += weight * get_threat_score(target, enemy) / 10
                
            elif criterion == 'isolated':
                # Check if target is alone (no allies nearby)
                # Simplified: just adds some random factor
                score += weight * random.randint(0, 5)
                
            elif criterion == 'spread_damage':
                # Bosses prefer targets that haven't been hit recently
                if not target.get('damaged_this_round'):
                    score += weight * 10
        
        target_scores.append((target, score))
    
    # Sort by score (highest first) and return best target
    target_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Add some randomness for tied or close scores
    top_targets = [t for t, s in target_scores if s >= target_scores[0][1] - 5]
    
    return random.choice(top_targets)


def get_nearest_target(combatants: List[Dict], enemy: Dict, target_type: str = 'player') -> Optional[Dict]:
    """Get the nearest valid target of the specified type."""
    targets = [
        c for c in combatants 
        if c.get('type') == target_type 
        and c.get('hp', 0) > 0 
        and 'unconscious' not in c.get('status', [])
    ]
    
    if not targets:
        return None
    
    # Without map positions, just pick randomly (could be enhanced with map integration)
    return random.choice(targets)


# =============================================================================
# ACTION SELECTION
# =============================================================================

def select_action(enemy: Dict, targets: List[Dict], combat_state: Dict) -> Dict:
    """
    Select the best action for an enemy to take.
    
    Returns a dict with:
        - action_type: 'attack', 'multiattack', 'spell', 'ability', 'flee', 'disengage'
        - action: The specific action/attack to use
        - target: The target of the action (if applicable)
    """
    profile = get_enemy_profile(enemy)
    actions = enemy.get('actions', [])
    
    # Check for flee condition first
    if should_flee(enemy, profile, combat_state):
        return {
            'action_type': 'flee',
            'action': 'Dash away',
            'target': None,
            'description': f"{enemy['name']} flees from combat!"
        }
    
    # Select target
    target = attack_target_selection(combat_state.get('combatants', []), enemy, profile)
    
    if not target:
        # No valid targets, take defensive action
        return {
            'action_type': 'dodge',
            'action': 'Dodge',
            'target': None,
            'description': f"{enemy['name']} takes the Dodge action."
        }
    
    # Check for multiattack first (most efficient use of action)
    multiattack = next((a for a in actions if 'multiattack' in a.get('name', '').lower()), None)
    
    if multiattack:
        return {
            'action_type': 'multiattack',
            'action': multiattack,
            'target': target,
            'description': multiattack.get('description', f"{enemy['name']} makes multiple attacks.")
        }
    
    # Check for special abilities (recharge abilities, breath weapons, etc.)
    special = select_special_ability(enemy, target, combat_state)
    if special:
        return special
    
    # Default to best single attack
    attack = select_best_attack(enemy, target)
    
    if attack:
        return {
            'action_type': 'attack',
            'action': attack,
            'target': target,
            'description': f"{enemy['name']} attacks {target['name']}."
        }
    
    # Fallback: basic attack with default stats
    return {
        'action_type': 'attack',
        'action': {
            'name': 'Attack',
            'attack_bonus': (enemy.get('stats', {}).get('STR', 10) - 10) // 2 + 2,
            'damage': '1d6',
            'damage_type': 'bludgeoning'
        },
        'target': target,
        'description': f"{enemy['name']} attacks {target['name']}."
    }


def select_best_attack(enemy: Dict, target: Dict) -> Optional[Dict]:
    """Select the most effective attack against a target."""
    actions = enemy.get('actions', [])
    attacks = [a for a in actions if 'attack' in a.get('name', '').lower() or a.get('attack_bonus')]
    
    if not attacks:
        return None
    
    # Score each attack
    attack_scores = []
    for attack in attacks:
        score = 0
        
        # Higher attack bonus = more likely to hit
        attack_bonus = attack.get('attack_bonus', 0)
        target_ac = target.get('ac', 10)
        hit_chance = min(0.95, max(0.05, (21 + attack_bonus - target_ac) / 20))
        
        # Estimate average damage
        damage_dice = attack.get('damage', '1d6')
        avg_damage = estimate_average_damage(damage_dice)
        
        # Expected damage = hit chance * damage
        score = hit_chance * avg_damage
        
        # Check for damage type vulnerabilities/resistances
        damage_type = attack.get('damage_type', 'bludgeoning')
        if damage_type in target.get('vulnerabilities', []):
            score *= 2
        elif damage_type in target.get('resistances', []):
            score *= 0.5
        elif damage_type in target.get('immunities', []):
            score *= 0
        
        attack_scores.append((attack, score))
    
    # Return highest scoring attack
    if attack_scores:
        attack_scores.sort(key=lambda x: x[1], reverse=True)
        return attack_scores[0][0]
    
    return attacks[0] if attacks else None


def select_special_ability(enemy: Dict, target: Dict, combat_state: Dict) -> Optional[Dict]:
    """Check for and select special abilities like breath weapons."""
    actions = enemy.get('actions', [])
    
    # Check for recharge abilities
    for action in actions:
        if 'recharge' in action.get('name', '').lower():
            # Roll to see if it recharges (typically 5-6 on d6)
            recharge_roll = random.randint(1, 6)
            if recharge_roll >= 5:
                return {
                    'action_type': 'ability',
                    'action': action,
                    'target': target,
                    'description': action.get('description', f"{enemy['name']} uses {action['name']}!"),
                    'is_recharged': True
                }
    
    # Check for breath weapons or AoE that aren't on cooldown
    for action in actions:
        name_lower = action.get('name', '').lower()
        if 'breath' in name_lower or 'cone' in name_lower or 'aoe' in action.get('type', '').lower():
            # Use if multiple targets could be hit (simplified logic)
            players_in_combat = len([c for c in combat_state.get('combatants', []) 
                                     if c.get('type') == 'player' and c.get('hp', 0) > 0])
            if players_in_combat >= 2:
                return {
                    'action_type': 'ability',
                    'action': action,
                    'target': None,  # AoE
                    'description': action.get('description', f"{enemy['name']} uses {action['name']}!")
                }
    
    return None


def estimate_average_damage(damage_dice: str) -> float:
    """Estimate average damage from a damage expression like '2d6+3'."""
    import re
    
    # Parse dice notation
    match = re.match(r'(\d+)?d(\d+)(?:\s*\+\s*(\d+))?', damage_dice)
    if not match:
        return 5.0  # Default estimate
    
    num_dice = int(match.group(1)) if match.group(1) else 1
    die_size = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0
    
    avg_die = (1 + die_size) / 2
    return num_dice * avg_die + modifier


# =============================================================================
# FLEE/MORALE CHECK
# =============================================================================

def should_flee(enemy: Dict, profile: Dict, combat_state: Dict) -> bool:
    """
    Determine if an enemy should flee based on morale.
    """
    flee_threshold = profile.get('flee_threshold')
    
    if flee_threshold is None:
        return False  # This enemy never flees
    
    hp = enemy.get('hp', 0)
    max_hp = enemy.get('max_hp', 1)
    hp_ratio = hp / max_hp
    
    # Check HP threshold
    if hp_ratio > flee_threshold:
        return False
    
    # Additional check: Are allies losing?
    allies = [c for c in combat_state.get('combatants', []) 
              if c.get('type') == 'enemy' and c.get('hp', 0) > 0]
    enemies = [c for c in combat_state.get('combatants', []) 
               if c.get('type') == 'player' and c.get('hp', 0) > 0]
    
    # More likely to flee if outnumbered
    if len(allies) < len(enemies):
        return random.random() < 0.7  # 70% chance to flee when outnumbered and hurt
    
    # Base flee chance when low HP
    return random.random() < 0.3


# =============================================================================
# MOVEMENT AI
# =============================================================================

def calculate_movement(enemy: Dict, target: Optional[Dict], combat_state: Dict, 
                       map_data: Optional[Dict] = None) -> Dict:
    """
    Calculate optimal movement for an enemy.
    
    Returns:
        Dict with 'movement_type', 'distance', 'direction', 'description'
    """
    profile = get_enemy_profile(enemy)
    tactics = profile.get('tactics', 'aggressive')
    
    # Get enemy's speed (default 30ft)
    speed = enemy.get('speed', 30)
    
    if target is None:
        return {
            'movement_type': 'none',
            'distance': 0,
            'description': f"{enemy['name']} holds position."
        }
    
    # Without map data, use simplified movement logic
    if tactics in ['aggressive', 'pack']:
        # Move to engage in melee
        return {
            'movement_type': 'approach',
            'distance': speed,
            'description': f"{enemy['name']} moves toward {target['name']}.",
            'target': target['name']
        }
    
    elif tactics == 'ranged':
        # Try to maintain distance
        return {
            'movement_type': 'maintain_range',
            'distance': speed // 2,
            'description': f"{enemy['name']} repositions for a better shot.",
            'preferred_range': 30
        }
    
    elif tactics == 'tactical':
        # Try flanking or cover
        return {
            'movement_type': 'tactical',
            'distance': speed,
            'description': f"{enemy['name']} maneuvers tactically.",
            'seek_advantage': True
        }
    
    elif tactics == 'support':
        # Stay near allies
        return {
            'movement_type': 'support',
            'distance': speed // 2,
            'description': f"{enemy['name']} stays close to allies."
        }
    
    return {
        'movement_type': 'approach',
        'distance': speed,
        'description': f"{enemy['name']} advances."
    }


# =============================================================================
# LEGENDARY ACTIONS
# =============================================================================

def select_legendary_action(enemy: Dict, combat_state: Dict, 
                            trigger_context: Optional[str] = None) -> Optional[Dict]:
    """
    Select a legendary action to use between player turns.
    
    Args:
        enemy: The legendary creature
        combat_state: Current combat state
        trigger_context: What triggered the check (e.g., "player_attacked", "spell_cast")
    
    Returns:
        Dict with selected legendary action, or None if shouldn't act
    """
    legendary_actions = enemy.get('legendary_actions', [])
    remaining = enemy.get('legendary_actions_remaining', 0)
    
    if not legendary_actions or remaining <= 0:
        return None
    
    hp_ratio = enemy.get('hp', 1) / max(enemy.get('max_hp', 1), 1)
    
    # Strategic selection based on situation
    available_actions = []
    
    for action in legendary_actions:
        cost = action.get('cost', 1)
        if cost <= remaining:
            available_actions.append(action)
    
    if not available_actions:
        return None
    
    # Prioritize based on situation
    if hp_ratio < 0.3:
        # Low HP: Prefer defensive/movement actions
        defensive = [a for a in available_actions if 
                     'move' in a.get('name', '').lower() or 
                     'teleport' in a.get('name', '').lower()]
        if defensive:
            return random.choice(defensive)
    
    if trigger_context == 'player_grouped':
        # Players grouped: Use AoE if available
        aoe = [a for a in available_actions if 
               'wing' in a.get('name', '').lower() or
               'tail' in a.get('name', '').lower()]
        if aoe:
            return random.choice(aoe)
    
    # Default: Random selection from available actions
    # Weight toward cheaper actions to spread them out
    weighted = []
    for action in available_actions:
        cost = action.get('cost', 1)
        weight = 4 - cost  # Cost 1 = weight 3, Cost 3 = weight 1
        weighted.extend([action] * weight)
    
    return random.choice(weighted) if weighted else random.choice(available_actions)


def should_use_legendary_action(enemy: Dict, combat_state: Dict) -> bool:
    """
    Determine if the enemy should use a legendary action now.
    
    This is called after each player turn to decide if the legendary
    creature should react.
    """
    remaining = enemy.get('legendary_actions_remaining', 0)
    if remaining <= 0:
        return False
    
    # Calculate how many player turns remain this round
    turn_order = combat_state.get('turn_order', [])
    current_turn = combat_state.get('current_turn', 0)
    
    players_remaining = sum(1 for i, c in enumerate(turn_order) 
                           if i > current_turn and c.get('type') == 'player')
    
    # Use legendary actions strategically
    # If many actions remaining and few player turns left, use more
    if remaining > players_remaining:
        return True
    
    # Random chance based on remaining actions
    return random.random() < (0.3 * remaining)


# =============================================================================
# SPELL SELECTION (for spellcasting enemies)
# =============================================================================

def select_spell(enemy: Dict, targets: List[Dict], combat_state: Dict) -> Optional[Dict]:
    """
    Select a spell for a spellcasting enemy to cast.
    
    Returns dict with spell info or None if should use regular action.
    """
    spells = enemy.get('spells', [])
    spell_slots = enemy.get('spell_slots', {})
    
    if not spells:
        return None
    
    # Analyze tactical situation
    players = [c for c in combat_state.get('combatants', []) 
               if c.get('type') == 'player' and c.get('hp', 0) > 0]
    allies = [c for c in combat_state.get('combatants', []) 
              if c.get('type') == 'enemy' and c.get('hp', 0) > 0]
    
    hp_ratio = enemy.get('hp', 1) / max(enemy.get('max_hp', 1), 1)
    
    # Priority: AoE if players grouped, single target otherwise
    if len(players) >= 3:
        # Look for AoE spells
        aoe_spells = [s for s in spells if s.get('aoe') or 
                      s.get('name', '').lower() in ['fireball', 'lightning bolt', 'cone of cold', 'ice storm']]
        if aoe_spells:
            spell = random.choice(aoe_spells)
            return {
                'spell': spell,
                'targets': players,
                'description': f"{enemy['name']} casts {spell['name']}!"
            }
    
    # If low HP, try to escape or buff
    if hp_ratio < 0.3:
        escape_spells = [s for s in spells if 
                         s.get('name', '').lower() in ['misty step', 'dimension door', 'teleport', 'invisibility', 'mirror image', 'shield']]
        if escape_spells:
            spell = random.choice(escape_spells)
            return {
                'spell': spell,
                'targets': [enemy],
                'description': f"{enemy['name']} casts {spell['name']} on itself!"
            }
    
    # Default: Damage spell on priority target
    target = attack_target_selection(combat_state.get('combatants', []), enemy)
    if target:
        damage_spells = [s for s in spells if s.get('damage')]
        if damage_spells:
            spell = random.choice(damage_spells)
            return {
                'spell': spell,
                'targets': [target],
                'description': f"{enemy['name']} casts {spell['name']} at {target['name']}!"
            }
    
    return None


# =============================================================================
# MAIN EXECUTION FUNCTIONS
# =============================================================================

def execute_enemy_turn(channel_id: str, enemy: Dict, combat_state: Dict) -> Dict:
    """
    Execute a complete enemy turn.
    
    This is the main entry point for enemy AI.
    
    Returns:
        Dict with:
            - actions: List of actions taken
            - movement: Movement taken
            - narration_context: Information for AI narration
            - damage_dealt: Total damage dealt
            - targets_hit: Targets that were hit
    """
    from utils.combat_manager import attack as resolve_attack, damage_combatant
    
    result = {
        'enemy_name': enemy['name'],
        'actions': [],
        'movement': None,
        'damage_dealt': 0,
        'targets_hit': [],
        'conditions_applied': [],
        'narration_context': {}
    }
    
    # Get targets
    targets = [c for c in combat_state.get('combatants', []) 
               if c.get('type') == 'player' and c.get('hp', 0) > 0]
    
    if not targets:
        result['actions'].append({
            'type': 'none',
            'description': f"{enemy['name']} has no targets and waits."
        })
        return result
    
    # Calculate movement
    target = attack_target_selection(combat_state.get('combatants', []), enemy)
    movement = calculate_movement(enemy, target, combat_state)
    result['movement'] = movement
    
    # Select and execute action
    action_choice = select_action(enemy, targets, combat_state)
    
    if action_choice['action_type'] == 'flee':
        result['actions'].append({
            'type': 'flee',
            'description': action_choice['description']
        })
        return result
    
    if action_choice['action_type'] == 'dodge':
        result['actions'].append({
            'type': 'dodge', 
            'description': action_choice['description']
        })
        return result
    
    # Execute attack(s)
    if action_choice['action_type'] == 'multiattack':
        # Parse multiattack description for number of attacks
        multiattack = action_choice['action']
        num_attacks = parse_multiattack_count(multiattack)
        
        for i in range(num_attacks):
            # Select target for each attack (could vary for spread_damage)
            attack_target = action_choice['target']
            if get_enemy_profile(enemy).get('target_priority', [])[0:1] == ['spread_damage']:
                # Boss behavior: spread attacks
                attack_target = random.choice(targets) if targets else action_choice['target']
            
            if attack_target:
                attack_result = execute_single_attack(
                    channel_id, enemy, attack_target, 
                    select_best_attack(enemy, attack_target)
                )
                result['actions'].append(attack_result)
                if attack_result.get('hit'):
                    result['damage_dealt'] += attack_result.get('damage', 0)
                    if attack_target['name'] not in result['targets_hit']:
                        result['targets_hit'].append(attack_target['name'])
    
    elif action_choice['action_type'] == 'attack':
        attack_result = execute_single_attack(
            channel_id, enemy, action_choice['target'], 
            action_choice['action']
        )
        result['actions'].append(attack_result)
        if attack_result.get('hit'):
            result['damage_dealt'] += attack_result.get('damage', 0)
            result['targets_hit'].append(action_choice['target']['name'])
    
    elif action_choice['action_type'] == 'ability':
        result['actions'].append({
            'type': 'ability',
            'ability': action_choice['action'],
            'description': action_choice['description'],
            'target': action_choice.get('target', {}).get('name') if action_choice.get('target') else 'multiple targets'
        })
    
    # Build narration context
    result['narration_context'] = {
        'enemy_name': enemy['name'],
        'enemy_type': enemy.get('monster_type', enemy['name']),
        'hp_status': 'healthy' if enemy.get('hp', 1) / max(enemy.get('max_hp', 1), 1) > 0.5 else 'wounded',
        'num_attacks': len([a for a in result['actions'] if a.get('type') in ['attack', 'multiattack']]),
        'total_damage': result['damage_dealt'],
        'targets': result['targets_hit'],
        'did_crit': any(a.get('crit') for a in result['actions']),
        'did_miss_all': all(not a.get('hit', True) for a in result['actions'] if a.get('type') == 'attack')
    }
    
    return result


def execute_single_attack(channel_id: str, attacker: Dict, target: Dict, 
                          attack: Dict) -> Dict:
    """Execute a single attack and return the result."""
    from utils.combat_manager import attack as resolve_attack
    
    attack_bonus = attack.get('attack_bonus', 0)
    
    # If no attack bonus specified, calculate from STR
    if attack_bonus == 0 and attacker.get('stats'):
        str_mod = (attacker['stats'].get('STR', 10) - 10) // 2
        attack_bonus = str_mod + 2  # Assume +2 proficiency
    
    damage_dice = attack.get('damage', '1d6')
    
    # Roll attack
    attack_roll = random.randint(1, 20)
    is_crit = attack_roll == 20
    is_fumble = attack_roll == 1
    total_attack = attack_roll + attack_bonus
    
    target_ac = target.get('ac', 10)
    hit = (total_attack >= target_ac or is_crit) and not is_fumble
    
    damage = 0
    if hit:
        # Roll damage
        damage = roll_dice(damage_dice)[0]
        if is_crit:
            # Double damage on crit
            damage = damage * 2
    
    result = {
        'type': 'attack',
        'attack_name': attack.get('name', 'Attack'),
        'attacker': attacker['name'],
        'target': target['name'],
        'attack_roll': attack_roll,
        'attack_total': total_attack,
        'target_ac': target_ac,
        'hit': hit,
        'crit': is_crit,
        'fumble': is_fumble,
        'damage': damage,
        'damage_type': attack.get('damage_type', 'bludgeoning'),
        'description': ''
    }
    
    # Build description
    if is_fumble:
        result['description'] = f"{attacker['name']}'s {attack.get('name', 'attack')} misses wildly!"
    elif is_crit:
        result['description'] = f"{attacker['name']} scores a CRITICAL HIT on {target['name']} for {damage} damage!"
    elif hit:
        result['description'] = f"{attacker['name']} hits {target['name']} with {attack.get('name', 'an attack')} for {damage} damage."
    else:
        result['description'] = f"{attacker['name']}'s {attack.get('name', 'attack')} misses {target['name']}."
    
    return result


def parse_multiattack_count(multiattack: Dict) -> int:
    """Parse a multiattack action to determine how many attacks it includes."""
    description = multiattack.get('description', '').lower()
    
    # Look for patterns like "makes two attacks" or "makes 2 attacks"
    import re
    
    number_words = {'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6}
    
    # Check for word numbers
    for word, num in number_words.items():
        if word in description:
            return num
    
    # Check for digit numbers
    match = re.search(r'(\d+)\s*(?:melee|ranged)?\s*attacks?', description)
    if match:
        return int(match.group(1))
    
    # Default to 2 attacks for multiattack
    return 2


# =============================================================================
# LAIR ACTIONS
# =============================================================================

def select_lair_action(lair_actions: List[str], combat_state: Dict, 
                       last_lair_action: Optional[int] = None) -> Optional[Dict]:
    """
    Select a lair action to use at initiative count 20.
    
    Args:
        lair_actions: List of available lair action descriptions
        combat_state: Current combat state
        last_lair_action: Index of the lair action used last round (to avoid repeats)
    
    Returns:
        Dict with selected lair action, or None
    """
    if not lair_actions:
        return None
    
    # Filter out the last used action if possible
    available_indices = list(range(len(lair_actions)))
    if last_lair_action is not None and len(lair_actions) > 1:
        available_indices = [i for i in available_indices if i != last_lair_action]
    
    selected_index = random.choice(available_indices)
    
    return {
        'index': selected_index,
        'description': lair_actions[selected_index],
        'round': combat_state.get('round', 1)
    }


def process_lair_actions(channel_id: str, combat_state: Dict) -> Optional[Dict]:
    """
    Process lair actions at initiative count 20.
    
    Returns:
        Dict with lair action result, or None if no lair actions
    """
    lair_actions = combat_state.get('lair_actions', [])
    
    if not lair_actions:
        return None
    
    if combat_state.get('lair_action_used_this_round'):
        return None
    
    last_used = combat_state.get('last_lair_action_index')
    selected = select_lair_action(lair_actions, combat_state, last_used)
    
    if selected:
        return {
            'type': 'lair_action',
            'description': selected['description'],
            'round': selected['round']
        }
    
    return None
