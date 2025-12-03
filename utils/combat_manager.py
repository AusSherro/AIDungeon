import os
import json
import random
from threading import Lock
from utils.character_manager import load_character
from utils.dice_roller import roll_dice

# Try to import monster data
try:
    from utils.dnd5e_data import get_monster, MONSTERS
    MONSTER_DATA_AVAILABLE = True
except ImportError:
    MONSTER_DATA_AVAILABLE = False


# Allow duplicate enemy names like "Goblin*2" to create Goblin 1, Goblin 2
def _expand_enemy(enemy):
    name = enemy['name']
    count = 1
    if '*' in name:
        base, qty = name.split('*', 1)
        try:
            count = int(qty)
            name = base.strip()
        except ValueError:
            pass
    
    # Check if this is a known monster
    monster_data = None
    if MONSTER_DATA_AVAILABLE:
        monster_data = get_monster(name)
    
    enemies = []
    for i in range(count):
        display_name = f"{name} {i+1}" if count > 1 else name
        
        if monster_data:
            # Use monster statblock
            dex_mod = (monster_data['stats']['DEX'] - 10) // 2
            enemy_data = {
                'type': 'enemy',
                'id': None,
                'name': display_name,
                'monster_type': name,
                'hp': monster_data['hp'],
                'max_hp': monster_data['hp'],
                'ac': monster_data['ac'],
                'init_bonus': dex_mod,
                'status': [],
                'initiative': 0,
                'stats': monster_data['stats'],
                'actions': monster_data.get('actions', []),
                'traits': monster_data.get('traits', []),
                'cr': monster_data.get('cr', '0'),
                'xp': monster_data.get('xp', 0),
            }
            
            # Add legendary actions if present
            if monster_data.get('legendary_actions'):
                enemy_data['legendary_actions'] = monster_data['legendary_actions']
                enemy_data['legendary_actions_remaining'] = len(monster_data['legendary_actions'])
            
            # Add legendary resistance if present
            if monster_data.get('legendary_resistances'):
                enemy_data['legendary_resistances'] = monster_data['legendary_resistances']
                enemy_data['legendary_resistances_remaining'] = monster_data['legendary_resistances']
            
            # Add reactions if present
            if monster_data.get('reactions'):
                enemy_data['monster_reactions'] = monster_data['reactions']
        else:
            # Use provided stats
            enemy_data = {
                'type': 'enemy',
                'id': None,
                'name': display_name,
                'hp': enemy['hp'],
                'max_hp': enemy['hp'],
                'ac': enemy['ac'],
                'init_bonus': enemy.get('init_bonus', 0),
                'status': [],
                'initiative': 0,
            }
        
        enemies.append(enemy_data)
    
    return enemies

COMBAT_DIR = os.path.join(os.path.dirname(__file__), '..', 'combat')
os.makedirs(COMBAT_DIR, exist_ok=True)
_combat_locks = {}

def _get_combat_path(channel_id):
    return os.path.join(COMBAT_DIR, f'{channel_id}.json')

def load_combat(channel_id):
    path = _get_combat_path(channel_id)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_combat(channel_id, data):
    path = _get_combat_path(channel_id)
    lock = _combat_locks.setdefault(channel_id, Lock())
    with lock:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def start_combat(channel_id, players, enemies):
    """
    Start a combat encounter.
    players: list of (user_id, display_name)
    enemies: list of dicts {name, hp, ac}
    """
    combatants = []
    for user_id, name in players:
        char = load_character(user_id)
        if char:
            hp = char.get('hp', 10)
            max_hp = char.get('max_hp', 10)
            ac = char.get('ac', 10)
            dex_mod = (char.get('DEX', 10) - 10) // 2
            init_bonus = char.get('initiative_bonus', 0) + dex_mod
        else:
            hp = max_hp = 10
            ac = 10
            init_bonus = 0
        combatants.append({
            'type': 'player', 
            'id': user_id, 
            'name': name, 
            'hp': hp,
            'max_hp': max_hp,
            'ac': ac, 
            'init_bonus': init_bonus,
            'status': [], 
            'initiative': 0
        })
    for enemy in enemies:
        combatants.extend(_expand_enemy(enemy))
    state = {
        'combatants': combatants,
        'turn_order': [],
        'active': False,
        'current_turn': 0,
        'round': 1
    }
    save_combat(channel_id, state)
    return state

def roll_initiative(channel_id):
    """Roll initiative for all combatants and sort turn order."""
    state = load_combat(channel_id)
    if not state:
        return None
    for c in state['combatants']:
        roll = roll_dice('1d20')[0]
        bonus = c.get('init_bonus', 0)
        c['initiative'] = roll + bonus
        c['init_roll'] = roll  # Store the raw roll for display
    state['turn_order'] = sorted(state['combatants'], key=lambda x: x['initiative'], reverse=True)
    state['active'] = True
    state['current_turn'] = 0
    save_combat(channel_id, state)
    return state

def next_turn(channel_id):
    state = load_combat(channel_id)
    if not state or not state['active']:
        return None
    n = len(state['turn_order'])
    for _ in range(n):
        state['current_turn'] = (state['current_turn'] + 1) % n
        active = state['turn_order'][state['current_turn']]
        if active.get('hp', 1) > 0 and 'unconscious' not in active.get('status', []) and 'dead' not in active.get('status', []):
            break
    save_combat(channel_id, state)
    return state

def attack(channel_id, attacker_id, target_name, attack_bonus, damage_dice):
    """Resolve an attack roll and apply damage."""
    state = load_combat(channel_id)
    if not state or not state.get('active'):
        return None
    attacker = next((c for c in state['combatants'] if str(c.get('id')) == str(attacker_id)), None)
    target = next((c for c in state['combatants'] if c['name'].lower() == target_name.lower()), None)
    if not attacker or not target:
        return None
    
    # Roll attack
    attack_roll = roll_dice('1d20')[0]
    is_crit = attack_roll == 20
    is_fumble = attack_roll == 1
    total_attack = attack_roll + attack_bonus
    hit = (total_attack >= target.get('ac', 10) or is_crit) and not is_fumble
    
    damage = 0
    if hit:
        damage_result = roll_dice(damage_dice)[0]
        if is_crit:
            # Critical hit - double the dice (simplified: double damage)
            damage = damage_result * 2
        else:
            damage = damage_result
        target['hp'] = max(0, target.get('hp', 0) - damage)
        if target['hp'] == 0:
            if 'unconscious' not in target.get('status', []):
                target.setdefault('status', []).append('unconscious')
    
    save_combat(channel_id, state)
    return {
        'roll': attack_roll,
        'total': total_attack,
        'hit': hit,
        'crit': is_crit,
        'fumble': is_fumble,
        'damage': damage,
        'target': target['name'],
        'target_hp': target['hp'],
        'target_max_hp': target.get('max_hp', target['hp'])
    }


def get_combat_status(channel_id):
    """Get formatted combat status for display."""
    state = load_combat(channel_id)
    if not state or not state.get('active'):
        return None
    
    current = state['turn_order'][state['current_turn']]
    
    return {
        'round': state.get('round', 1),
        'current_combatant': current,
        'turn_order': state['turn_order'],
        'current_index': state['current_turn']
    }

def add_reaction(channel_id, user_id, reaction):
    state = load_combat(channel_id)
    if not state:
        return None
    for c in state['combatants']:
        if c.get('id') == user_id:
            c.setdefault('reactions', []).append(reaction)
    save_combat(channel_id, state)
    return state

def get_active_combatant(channel_id):
    state = load_combat(channel_id)
    if not state or not state['active']:
        return None
    return state['turn_order'][state['current_turn']]


def apply_aoe_damage(channel_id, targets, damage):
    """Placeholder for area-of-effect damage."""
    state = load_combat(channel_id)
    if not state or not state.get('active'):
        return None
    for name in targets:
        target = next((c for c in state['combatants'] if c['name'].lower() == name.lower()), None)
        if target:
            target['hp'] = max(0, target.get('hp', 0) - damage)
            if target['hp'] == 0:
                target.setdefault('status', []).append('unconscious')
    save_combat(channel_id, state)
    return state


def apply_status(channel_id, target_name, status):
    """Placeholder for applying a status condition to a target."""
    state = load_combat(channel_id)
    if not state or not state.get('active'):
        return None
    target = next((c for c in state['combatants'] if c['name'].lower() == target_name.lower()), None)
    if not target:
        return None
    target.setdefault('status', []).append(status)
    save_combat(channel_id, state)
    return state

def end_combat(channel_id):
    path = _get_combat_path(channel_id)
    if os.path.exists(path):
        os.remove(path)


# =============================================================================
# LEGENDARY ACTIONS & RESISTANCES
# =============================================================================

def use_legendary_action(channel_id, enemy_name, action_index=0):
    """Use a legendary action for an enemy.
    
    Args:
        channel_id: The channel ID
        enemy_name: Name of the enemy using the action
        action_index: Index of the legendary action to use
    
    Returns:
        dict with action details or None if failed
    """
    state = load_combat(channel_id)
    if not state or not state.get('active'):
        return None
    
    enemy = next((c for c in state['combatants'] if c['name'].lower() == enemy_name.lower()), None)
    if not enemy:
        return None
    
    # Check if enemy has legendary actions
    remaining = enemy.get('legendary_actions_remaining', 0)
    actions = enemy.get('legendary_actions', [])
    
    if remaining <= 0:
        return {'error': f"{enemy_name} has no legendary actions remaining"}
    
    if not actions or action_index >= len(actions):
        return {'error': f"{enemy_name} has no legendary action at index {action_index}"}
    
    action = actions[action_index]
    cost = action.get('cost', 1)
    
    if remaining < cost:
        return {'error': f"Legendary action costs {cost} but only {remaining} remaining"}
    
    # Use the action
    enemy['legendary_actions_remaining'] = remaining - cost
    save_combat(channel_id, state)
    
    return {
        'enemy': enemy_name,
        'action': action,
        'remaining': enemy['legendary_actions_remaining'],
    }


def use_legendary_resistance(channel_id, enemy_name):
    """Use a legendary resistance to auto-succeed a saving throw.
    
    Returns:
        dict with result or None if failed
    """
    state = load_combat(channel_id)
    if not state or not state.get('active'):
        return None
    
    enemy = next((c for c in state['combatants'] if c['name'].lower() == enemy_name.lower()), None)
    if not enemy:
        return None
    
    remaining = enemy.get('legendary_resistances_remaining', 0)
    
    if remaining <= 0:
        return {'error': f"{enemy_name} has no legendary resistances remaining"}
    
    enemy['legendary_resistances_remaining'] = remaining - 1
    save_combat(channel_id, state)
    
    return {
        'enemy': enemy_name,
        'success': True,
        'remaining': enemy['legendary_resistances_remaining'],
    }


def reset_legendary_actions(channel_id, enemy_name):
    """Reset legendary actions at the start of the enemy's turn."""
    state = load_combat(channel_id)
    if not state or not state.get('active'):
        return None
    
    enemy = next((c for c in state['combatants'] if c['name'].lower() == enemy_name.lower()), None)
    if not enemy:
        return None
    
    if 'legendary_actions' in enemy:
        enemy['legendary_actions_remaining'] = len(enemy['legendary_actions'])
        save_combat(channel_id, state)
    
    return enemy


# =============================================================================
# LAIR ACTIONS
# =============================================================================

def set_lair_actions(channel_id, lair_actions):
    """Set lair actions for the current combat.
    
    Args:
        channel_id: The channel ID
        lair_actions: List of lair action descriptions
    """
    state = load_combat(channel_id)
    if not state:
        return None
    
    state['lair_actions'] = lair_actions
    state['lair_action_used_this_round'] = False
    save_combat(channel_id, state)
    return state


def use_lair_action(channel_id, action_index=0):
    """Use a lair action (typically at initiative count 20).
    
    Returns:
        dict with action details or None if failed
    """
    state = load_combat(channel_id)
    if not state or not state.get('active'):
        return None
    
    if state.get('lair_action_used_this_round'):
        return {'error': "Lair action already used this round"}
    
    actions = state.get('lair_actions', [])
    if not actions or action_index >= len(actions):
        return {'error': f"No lair action at index {action_index}"}
    
    action = actions[action_index]
    state['lair_action_used_this_round'] = True
    save_combat(channel_id, state)
    
    return {
        'action': action,
        'round': state.get('round', 1),
    }


def get_lair_actions(channel_id):
    """Get available lair actions for the combat."""
    state = load_combat(channel_id)
    if not state:
        return None
    
    return {
        'actions': state.get('lair_actions', []),
        'used_this_round': state.get('lair_action_used_this_round', False),
    }


# =============================================================================
# ENHANCED INITIATIVE TRACKING
# =============================================================================

def add_combatant_mid_combat(channel_id, combatant_data, initiative_roll=None):
    """Add a new combatant to ongoing combat.
    
    Args:
        channel_id: The channel ID
        combatant_data: Dict with name, hp, ac, etc.
        initiative_roll: Optional pre-rolled initiative (otherwise rolls automatically)
    """
    state = load_combat(channel_id)
    if not state:
        return None
    
    # Set up the combatant
    init_bonus = combatant_data.get('init_bonus', 0)
    if initiative_roll is None:
        initiative_roll = roll_dice('1d20')[0] + init_bonus
    
    new_combatant = {
        'type': combatant_data.get('type', 'enemy'),
        'id': combatant_data.get('id'),
        'name': combatant_data['name'],
        'hp': combatant_data['hp'],
        'max_hp': combatant_data.get('max_hp', combatant_data['hp']),
        'ac': combatant_data['ac'],
        'init_bonus': init_bonus,
        'status': [],
        'initiative': initiative_roll,
        'init_roll': initiative_roll - init_bonus,
    }
    
    state['combatants'].append(new_combatant)
    
    # Re-sort turn order
    state['turn_order'] = sorted(
        [c for c in state['combatants'] if c.get('hp', 1) > 0],
        key=lambda x: x['initiative'],
        reverse=True
    )
    
    save_combat(channel_id, state)
    return state


def remove_combatant(channel_id, combatant_name):
    """Remove a combatant from combat entirely."""
    state = load_combat(channel_id)
    if not state:
        return None
    
    # Find and remove
    state['combatants'] = [c for c in state['combatants'] if c['name'].lower() != combatant_name.lower()]
    state['turn_order'] = [c for c in state['turn_order'] if c['name'].lower() != combatant_name.lower()]
    
    # Adjust current turn if needed
    if state['current_turn'] >= len(state['turn_order']):
        state['current_turn'] = 0
    
    save_combat(channel_id, state)
    return state


def delay_turn(channel_id, combatant_name, new_initiative):
    """Delay a combatant's turn to a new initiative count."""
    state = load_combat(channel_id)
    if not state or not state.get('active'):
        return None
    
    combatant = next((c for c in state['combatants'] if c['name'].lower() == combatant_name.lower()), None)
    if not combatant:
        return None
    
    combatant['initiative'] = new_initiative
    combatant['delayed'] = True
    
    # Re-sort turn order
    state['turn_order'] = sorted(
        [c for c in state['combatants'] if c.get('hp', 1) > 0 and 'dead' not in c.get('status', [])],
        key=lambda x: x['initiative'],
        reverse=True
    )
    
    save_combat(channel_id, state)
    return state


def ready_action(channel_id, combatant_name, trigger, action):
    """Set a readied action with a trigger condition."""
    state = load_combat(channel_id)
    if not state or not state.get('active'):
        return None
    
    combatant = next((c for c in state['combatants'] if c['name'].lower() == combatant_name.lower()), None)
    if not combatant:
        return None
    
    combatant['readied_action'] = {
        'trigger': trigger,
        'action': action,
    }
    
    save_combat(channel_id, state)
    return state


def trigger_readied_action(channel_id, combatant_name):
    """Trigger a combatant's readied action."""
    state = load_combat(channel_id)
    if not state or not state.get('active'):
        return None
    
    combatant = next((c for c in state['combatants'] if c['name'].lower() == combatant_name.lower()), None)
    if not combatant or 'readied_action' not in combatant:
        return None
    
    readied = combatant.pop('readied_action')
    save_combat(channel_id, state)
    
    return {
        'combatant': combatant_name,
        'trigger': readied['trigger'],
        'action': readied['action'],
    }


# =============================================================================
# ROUND TRACKING ENHANCEMENTS
# =============================================================================

def advance_round(channel_id):
    """Advance to the next round, resetting round-based effects."""
    state = load_combat(channel_id)
    if not state or not state.get('active'):
        return None
    
    state['round'] = state.get('round', 1) + 1
    state['current_turn'] = 0
    
    # Reset lair action
    state['lair_action_used_this_round'] = False
    
    # Process start-of-round effects
    effects_triggered = []
    
    for combatant in state['combatants']:
        # Regeneration (like Trolls)
        if combatant.get('regeneration') and combatant.get('hp', 0) > 0:
            if not combatant.get('regeneration_blocked'):
                regen = combatant['regeneration']
                old_hp = combatant['hp']
                combatant['hp'] = min(combatant['max_hp'], combatant['hp'] + regen)
                if combatant['hp'] > old_hp:
                    effects_triggered.append(f"{combatant['name']} regenerates {combatant['hp'] - old_hp} HP")
            combatant['regeneration_blocked'] = False  # Reset for next round
        
        # Duration-based status effects
        if combatant.get('status_durations'):
            expired = []
            for status, duration in list(combatant['status_durations'].items()):
                if duration <= 1:
                    expired.append(status)
                else:
                    combatant['status_durations'][status] -= 1
            
            for status in expired:
                if status in combatant.get('status', []):
                    combatant['status'].remove(status)
                del combatant['status_durations'][status]
                effects_triggered.append(f"{combatant['name']}: {status} expired")
    
    save_combat(channel_id, state)
    
    return {
        'round': state['round'],
        'effects': effects_triggered,
    }


def get_combat_summary(channel_id):
    """Get a detailed combat summary for display."""
    state = load_combat(channel_id)
    if not state:
        return None
    
    summary = {
        'round': state.get('round', 1),
        'active': state.get('active', False),
        'current_turn': state.get('current_turn', 0),
        'players': [],
        'enemies': [],
        'dead': [],
        'lair_actions': state.get('lair_actions'),
    }
    
    if state.get('turn_order'):
        current = state['turn_order'][state['current_turn']]
        summary['current_combatant'] = current['name']
    
    for combatant in state.get('combatants', []):
        entry = {
            'name': combatant['name'],
            'hp': combatant.get('hp', 0),
            'max_hp': combatant.get('max_hp', combatant.get('hp', 0)),
            'ac': combatant.get('ac', 10),
            'initiative': combatant.get('initiative', 0),
            'status': combatant.get('status', []),
        }
        
        # Add legendary info for enemies
        if combatant.get('legendary_actions_remaining') is not None:
            entry['legendary_actions'] = combatant['legendary_actions_remaining']
        if combatant.get('legendary_resistances_remaining') is not None:
            entry['legendary_resistances'] = combatant['legendary_resistances_remaining']
        
        if combatant.get('hp', 0) <= 0 or 'dead' in combatant.get('status', []):
            summary['dead'].append(entry)
        elif combatant.get('type') == 'player':
            summary['players'].append(entry)
        else:
            summary['enemies'].append(entry)
    
    # Calculate XP total from enemies
    total_xp = sum(e.get('xp', 0) for c in state.get('combatants', []) 
                   if c.get('type') == 'enemy' for e in [c])
    summary['total_xp'] = total_xp
    
    return summary


def heal_combatant(channel_id, target_name, amount):
    """Heal a combatant by a specified amount."""
    state = load_combat(channel_id)
    if not state:
        return None
    
    target = next((c for c in state['combatants'] if c['name'].lower() == target_name.lower()), None)
    if not target:
        return None
    
    old_hp = target.get('hp', 0)
    max_hp = target.get('max_hp', old_hp)
    target['hp'] = min(max_hp, old_hp + amount)
    
    # Remove unconscious if healed from 0
    if old_hp <= 0 and target['hp'] > 0:
        if 'unconscious' in target.get('status', []):
            target['status'].remove('unconscious')
    
    save_combat(channel_id, state)
    
    return {
        'target': target_name,
        'old_hp': old_hp,
        'new_hp': target['hp'],
        'max_hp': max_hp,
        'healed': target['hp'] - old_hp,
    }


def damage_combatant(channel_id, target_name, amount, damage_type=None):
    """Apply damage to a combatant with optional damage type tracking."""
    state = load_combat(channel_id)
    if not state:
        return None
    
    target = next((c for c in state['combatants'] if c['name'].lower() == target_name.lower()), None)
    if not target:
        return None
    
    # Check for resistances/immunities/vulnerabilities
    actual_damage = amount
    modifier = None
    
    if damage_type:
        immunities = target.get('immunities', [])
        resistances = target.get('resistances', [])
        vulnerabilities = target.get('vulnerabilities', [])
        
        if damage_type.lower() in [i.lower() for i in immunities]:
            actual_damage = 0
            modifier = 'immune'
        elif damage_type.lower() in [v.lower() for v in vulnerabilities]:
            actual_damage = amount * 2
            modifier = 'vulnerable'
        elif damage_type.lower() in [r.lower() for r in resistances]:
            actual_damage = amount // 2
            modifier = 'resistant'
    
    old_hp = target.get('hp', 0)
    target['hp'] = max(0, old_hp - actual_damage)
    
    # Track if regeneration should be blocked (acid/fire for trolls)
    if damage_type and damage_type.lower() in ['acid', 'fire']:
        target['regeneration_blocked'] = True
    
    # Apply unconscious if at 0 HP
    if target['hp'] <= 0 and 'unconscious' not in target.get('status', []):
        target['status'].append('unconscious')
    
    save_combat(channel_id, state)
    
    return {
        'target': target_name,
        'damage_dealt': actual_damage,
        'damage_type': damage_type,
        'modifier': modifier,
        'old_hp': old_hp,
        'new_hp': target['hp'],
    }
