import os
import json
from threading import Lock

CHAR_DIR = os.path.join(os.path.dirname(__file__), '..', 'characters')
os.makedirs(CHAR_DIR, exist_ok=True)
_char_locks = {}

# D&D 5e skill list with associated ability
SKILLS = {
    'acrobatics': 'DEX',
    'animal_handling': 'WIS',
    'arcana': 'INT',
    'athletics': 'STR',
    'deception': 'CHA',
    'history': 'INT',
    'insight': 'WIS',
    'intimidation': 'CHA',
    'investigation': 'INT',
    'medicine': 'WIS',
    'nature': 'INT',
    'perception': 'WIS',
    'performance': 'CHA',
    'persuasion': 'CHA',
    'religion': 'INT',
    'sleight_of_hand': 'DEX',
    'stealth': 'DEX',
    'survival': 'WIS'
}

DEFAULT_STATS = {
    'STR': 10,
    'DEX': 10,
    'CON': 10,
    'INT': 10,
    'WIS': 10,
    'CHA': 10,
    'proficiency': 2,
    'skills': {},  # skill_name: True/False for proficiency
    'expertise': [],  # skills with expertise (double proficiency)
    'hp': 10,
    'max_hp': 10,
    'temp_hp': 0,
    'hit_dice': '1d8',
    'hit_dice_used': 0,
    'class': '',
    'race': '',
    'background': '',
    'alignment': '',
    'speed': 30,
    'ac': 10,
    'initiative_bonus': 0,
    'spell_slots': {
        '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0, '7': 0, '8': 0, '9': 0
    },
    'spell_slots_used': {
        '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0, '7': 0, '8': 0, '9': 0
    },
    'spells_known': [],
    'xp': 0,
    'level': 1,
    'inventory': [],
    'equipment': {
        'armor': None,
        'weapon': None,
        'shield': None
    },
    'conditions': [],  # poisoned, stunned, etc.
    'death_saves': {'successes': 0, 'failures': 0},
    'inspiration': False,
    'features': []  # class/race features
}

def _get_char_path(user_id):
    return os.path.join(CHAR_DIR, f'{user_id}.json')

def get_proficiency_bonus(level):
    """Calculate proficiency bonus based on level"""
    if level < 5:
        return 2
    elif level < 9:
        return 3
    elif level < 13:
        return 4
    elif level < 17:
        return 5
    else:
        return 6

def get_ability_modifier(score):
    """Calculate ability modifier from ability score"""
    return (score - 10) // 2

def calculate_skill_bonus(char_data, skill):
    """Calculate total skill bonus including proficiency"""
    skill = skill.lower()
    if skill not in SKILLS:
        return 0
    
    ability = SKILLS[skill]
    base_mod = get_ability_modifier(char_data.get(ability, 10))
    
    if char_data.get('skills', {}).get(skill, False):
        # Proficient
        prof_bonus = char_data.get('proficiency', 2)
        if skill in char_data.get('expertise', []):
            # Expertise doubles proficiency bonus
            prof_bonus *= 2
        return base_mod + prof_bonus
    else:
        return base_mod

def load_character(user_id):
    path = _get_char_path(user_id)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # Ensure all default fields exist
        for key, value in DEFAULT_STATS.items():
            if key not in data:
                data[key] = value
        return data

def save_character(user_id, data):
    path = _get_char_path(user_id)
    lock = _char_locks.setdefault(user_id, Lock())
    with lock:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def register_character(user_id, name, class_name='Fighter', race='Human'):
    data = dict(DEFAULT_STATS)
    data['name'] = name
    data['class'] = class_name
    data['race'] = race
    
    # Set initial HP based on class
    if class_name.lower() in ['barbarian']:
        data['hit_dice'] = '1d12'
        data['hp'] = data['max_hp'] = 12 + get_ability_modifier(data['CON'])
    elif class_name.lower() in ['fighter', 'paladin', 'ranger']:
        data['hit_dice'] = '1d10'
        data['hp'] = data['max_hp'] = 10 + get_ability_modifier(data['CON'])
    elif class_name.lower() in ['wizard', 'sorcerer']:
        data['hit_dice'] = '1d6'
        data['hp'] = data['max_hp'] = 6 + get_ability_modifier(data['CON'])
    else:  # Default d8 classes
        data['hit_dice'] = '1d8'
        data['hp'] = data['max_hp'] = 8 + get_ability_modifier(data['CON'])
    
    save_character(user_id, data)
    return data

def set_stat(user_id, stat, value):
    data = load_character(user_id)
    if not data:
        return None
    
    stat_upper = stat.upper()
    if stat_upper in ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']:
        old_value = data.get(stat_upper, 10)
        data[stat_upper] = value
        
        # Update HP if CON changed
        if stat_upper == 'CON':
            con_diff = get_ability_modifier(value) - get_ability_modifier(old_value)
            data['max_hp'] += con_diff * data.get('level', 1)
            data['hp'] = min(data['hp'], data['max_hp'])
        
        # Update AC if DEX changed and not wearing heavy armor
        if stat_upper == 'DEX':
            # Simple AC recalculation (can be expanded based on armor type)
            data['ac'] = 10 + get_ability_modifier(value)
        
        save_character(user_id, data)
        return data
    return None

def add_inventory(user_id, item):
    data = load_character(user_id)
    if not data:
        return None
    data.setdefault('inventory', []).append(item)
    save_character(user_id, data)
    return data

def remove_inventory(user_id, item):
    data = load_character(user_id)
    if not data:
        return None
    if item in data.get('inventory', []):
        data['inventory'].remove(item)
        save_character(user_id, data)
        return data
    return None

def set_skill(user_id, skill, proficient=True):
    data = load_character(user_id)
    if not data:
        return None
    skill = skill.lower()
    if skill not in SKILLS:
        return None
    data.setdefault('skills', {})[skill] = proficient
    save_character(user_id, data)
    return data

def add_expertise(user_id, skill):
    data = load_character(user_id)
    if not data:
        return None
    skill = skill.lower()
    if skill not in SKILLS:
        return None
    if skill not in data.get('expertise', []):
        data.setdefault('expertise', []).append(skill)
        save_character(user_id, data)
    return data

def damage_character(user_id, damage):
    data = load_character(user_id)
    if not data:
        return None
    
    # Apply damage to temp HP first
    if data.get('temp_hp', 0) > 0:
        if damage <= data['temp_hp']:
            data['temp_hp'] -= damage
            save_character(user_id, data)
            return data
        else:
            damage -= data['temp_hp']
            data['temp_hp'] = 0
    
    data['hp'] = max(0, data['hp'] - damage)
    save_character(user_id, data)
    return data

def heal_character(user_id, healing):
    data = load_character(user_id)
    if not data:
        return None
    data['hp'] = min(data['max_hp'], data['hp'] + healing)
    save_character(user_id, data)
    return data

def set_hp(user_id, hp):
    data = load_character(user_id)
    if not data:
        return None
    data['hp'] = max(0, min(hp, data['max_hp']))
    save_character(user_id, data)
    return data

def set_temp_hp(user_id, temp_hp):
    data = load_character(user_id)
    if not data:
        return None
    # Temp HP doesn't stack, take the higher value
    data['temp_hp'] = max(data.get('temp_hp', 0), temp_hp)
    save_character(user_id, data)
    return data

def set_max_hp(user_id, max_hp):
    data = load_character(user_id)
    if not data:
        return None
    data['max_hp'] = max_hp
    data['hp'] = min(data['hp'], max_hp)
    save_character(user_id, data)
    return data

def set_class(user_id, class_name):
    data = load_character(user_id)
    if not data:
        return None
    data['class'] = class_name
    save_character(user_id, data)
    return data

def set_race(user_id, race):
    data = load_character(user_id)
    if not data:
        return None
    data['race'] = race
    save_character(user_id, data)
    return data

def use_spell_slot(user_id, level):
    data = load_character(user_id)
    if not data:
        return None
    level_str = str(level)
    if data['spell_slots_used'].get(level_str, 0) < data['spell_slots'].get(level_str, 0):
        data['spell_slots_used'][level_str] += 1
        save_character(user_id, data)
        return True
    return False

def reset_spell_slots(user_id):
    data = load_character(user_id)
    if not data:
        return None
    for level in data['spell_slots_used']:
        data['spell_slots_used'][level] = 0
    save_character(user_id, data)
    return data

def long_rest(user_id):
    data = load_character(user_id)
    if not data:
        return None
    # Restore HP to max
    data['hp'] = data['max_hp']
    # Reset spell slots
    for level in data['spell_slots_used']:
        data['spell_slots_used'][level] = 0
    # Reset hit dice used (regain half total)
    data['hit_dice_used'] = max(0, data['hit_dice_used'] - (data['level'] // 2))
    # Clear death saves
    data['death_saves'] = {'successes': 0, 'failures': 0}
    save_character(user_id, data)
    return data

def short_rest(user_id, hit_dice_to_use=0):
    data = load_character(user_id)
    if not data:
        return None
    
    # Use hit dice to heal
    available_dice = data['level'] - data.get('hit_dice_used', 0)
    dice_used = min(hit_dice_to_use, available_dice)
    
    if dice_used > 0:
        # Simplified healing calculation
        import random
        dice_type = int(data.get('hit_dice', '1d8').split('d')[1])
        healing = sum(random.randint(1, dice_type) + get_ability_modifier(data['CON']) 
                     for _ in range(dice_used))
        data['hp'] = min(data['max_hp'], data['hp'] + healing)
        data['hit_dice_used'] = data.get('hit_dice_used', 0) + dice_used
    
    save_character(user_id, data)
    return data

def add_condition(user_id, condition):
    data = load_character(user_id)
    if not data:
        return None
    if condition not in data.get('conditions', []):
        data.setdefault('conditions', []).append(condition)
        save_character(user_id, data)
    return data

def remove_condition(user_id, condition):
    data = load_character(user_id)
    if not data:
        return None
    if condition in data.get('conditions', []):
        data['conditions'].remove(condition)
        save_character(user_id, data)
    return data

def death_save(user_id, success):
    data = load_character(user_id)
    if not data or data['hp'] > 0:
        return None
    
    if success:
        data['death_saves']['successes'] += 1
        if data['death_saves']['successes'] >= 3:
            # Stabilized
            data['hp'] = 1
            data['death_saves'] = {'successes': 0, 'failures': 0}
    else:
        data['death_saves']['failures'] += 1
        if data['death_saves']['failures'] >= 3:
            # Character dies
            add_condition(user_id, 'dead')
    
    save_character(user_id, data)
    return data

def level_up(user_id):
    data = load_character(user_id)
    if not data:
        return None
    
    data['level'] += 1
    data['proficiency'] = get_proficiency_bonus(data['level'])
    
    # Increase max HP (roll hit die + CON modifier)
    import random
    dice_type = int(data.get('hit_dice', '1d8').split('d')[1])
    hp_increase = random.randint(1, dice_type) + get_ability_modifier(data['CON'])
    data['max_hp'] += hp_increase
    data['hp'] += hp_increase
    
    save_character(user_id, data)
    return data

def set_spell_slots(user_id, slots):
    data = load_character(user_id)
    if not data:
        return None
    data['spell_slots'] = slots
    save_character(user_id, data)
    return data

def set_xp(user_id, xp):
    data = load_character(user_id)
    if not data:
        return None
    data['xp'] = xp
    
    # Check for level up based on XP thresholds
    xp_thresholds = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000,
                     85000, 100000, 120000, 140000, 165000, 195000, 225000, 265000, 305000, 355000]
    
    for level, threshold in enumerate(xp_thresholds):
        if xp >= threshold:
            data['level'] = level + 1
            data['proficiency'] = get_proficiency_bonus(level + 1)
    
    save_character(user_id, data)
    return data

def set_level(user_id, level):
    data = load_character(user_id)
    if not data:
        return None
    data['level'] = level
    data['proficiency'] = get_proficiency_bonus(level)
    save_character(user_id, data)
    return data

def get_character_summary(user_id):
    """Get a formatted summary of character stats for display"""
    data = load_character(user_id)
    if not data:
        return None
    
    summary = f"**{data.get('name', 'Unknown')}** - Level {data['level']} {data.get('race', '')} {data.get('class', '')}\n"
    summary += f"HP: {data['hp']}/{data['max_hp']}"
    if data.get('temp_hp', 0) > 0:
        summary += f" (Temp: {data['temp_hp']})"
    summary += f" | AC: {data.get('ac', 10)}\n"
    
    # Ability scores with modifiers
    summary += "**Abilities:** "
    for stat in ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']:
        mod = get_ability_modifier(data.get(stat, 10))
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        summary += f"{stat}: {data.get(stat, 10)} ({mod_str}) "
    
    # Conditions
    if data.get('conditions'):
        summary += f"\n**Conditions:** {', '.join(data['conditions'])}"
    
    return summary