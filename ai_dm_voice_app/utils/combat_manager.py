import os
import json
import random
from threading import Lock
from utils.character_manager import load_character
from utils.dice_roller import roll_dice

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
    # players: list of (user_id, display_name)
    # enemies: list of dicts {name, hp, ac}
    combatants = []
    for user_id, name in players:
        char = load_character(user_id)
        hp = char.get('CON', 10) if char else 10
        ac = char.get('DEX', 10) if char else 10
        combatants.append({'type': 'player', 'id': user_id, 'name': name, 'hp': hp, 'ac': ac, 'status': [], 'initiative': 0})
    for enemy in enemies:
        combatants.append({'type': 'enemy', 'id': None, 'name': enemy['name'], 'hp': enemy['hp'], 'ac': enemy['ac'], 'status': [], 'initiative': 0})
    state = {
        'combatants': combatants,
        'turn_order': [],
        'active': False,
        'current_turn': 0
    }
    save_combat(channel_id, state)
    return state

def roll_initiative(channel_id):
    state = load_combat(channel_id)
    if not state:
        return None
    for c in state['combatants']:
        c['initiative'] = roll_dice('1d20')[0] + (c['ac'] // 2 - 5 if c['type'] == 'player' else 0)
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
    roll = roll_dice('1d20')[0] + attack_bonus
    hit = roll >= target.get('ac', 10)
    damage = 0
    if hit:
        damage = roll_dice(damage_dice)[0]
        target['hp'] = max(0, target.get('hp', 0) - damage)
        if target['hp'] == 0:
            target.setdefault('status', []).append('unconscious')
    save_combat(channel_id, state)
    return {'roll': roll, 'hit': hit, 'damage': damage, 'target': target['name'], 'target_hp': target['hp']}

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

def end_combat(channel_id):
    path = _get_combat_path(channel_id)
    if os.path.exists(path):
        os.remove(path)
