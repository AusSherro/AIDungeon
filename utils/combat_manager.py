import os
import json
import random
from threading import Lock
from utils.character_manager import load_character
from utils.dice_roller import roll_dice

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
    return [
        {
            'type': 'enemy',
            'id': None,
            'name': f"{name} {i+1}" if count > 1 else name,
            'hp': enemy['hp'],
            'max_hp': enemy['hp'],
            'ac': enemy['ac'],
            'init_bonus': enemy.get('init_bonus', 0),
            'status': [],
            'initiative': 0,
        }
        for i in range(count)
    ]

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
