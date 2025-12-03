import os
import json
from threading import Lock

# Import D&D 5e data
try:
    from .dnd5e_data import (
        CLASSES, SPELLS, RACES, 
        get_class_data, get_spell_slots, get_features_at_level, get_all_features_up_to_level,
        get_spells_for_class, get_spell, get_cantrips_for_class,
        get_race_data, get_level_for_xp, get_proficiency_bonus as dnd_proficiency,
        XP_THRESHOLDS
    )
    DND_DATA_AVAILABLE = True
except ImportError:
    DND_DATA_AVAILABLE = False

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
    'features': [],  # class/race features
    'cantrips_known': [],  # known cantrips
    'prepared_spells': [],  # currently prepared spells
    'subrace': '',  # e.g., "Hill Dwarf"
    'subclass': '',  # e.g., "Champion" Fighter
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

def register_character(user_id, name, class_name='Fighter', race='Human', subrace=None):
    data = dict(DEFAULT_STATS)
    data['name'] = name
    data['class'] = class_name
    data['race'] = race
    if subrace:
        data['subrace'] = subrace
    
    # Use D&D 5e data if available
    if DND_DATA_AVAILABLE:
        class_data = get_class_data(class_name)
        race_data = get_race_data(race, subrace)
        
        if class_data:
            # Set hit dice and initial HP
            hit_die = class_data.get('hit_die', 8)
            data['hit_dice'] = f"1d{hit_die}"
            data['hp'] = data['max_hp'] = hit_die + get_ability_modifier(data['CON'])
            
            # Set initial spell slots if spellcaster
            if class_data.get('spellcasting'):
                slots = get_spell_slots(class_name, 1)
                for level, num in slots.items():
                    data['spell_slots'][str(level)] = num
            
            # Set initial features
            data['features'] = get_features_at_level(class_name, 1)
        
        if race_data:
            # Apply racial speed
            data['speed'] = race_data.get('speed', 30)
            
            # Add racial traits to features
            data['features'].extend(race_data.get('traits', []))
            
            # Note: Ability score bonuses should be applied during character creation
            # via a separate function to allow for point-buy or rolled stats
    else:
        # Fallback: Set initial HP based on class
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
    """Complete a long rest, restoring HP, spell slots, and other resources.
    
    Returns:
        dict with 'data' (updated character) and 'summary' (what was restored)
    """
    data = load_character(user_id)
    if not data:
        return None
    
    summary = []
    
    # Restore HP to max
    old_hp = data['hp']
    data['hp'] = data['max_hp']
    if old_hp < data['max_hp']:
        summary.append(f"HP restored: {old_hp} → {data['max_hp']}")
    
    # Reset all spell slots
    slots_restored = False
    for level in data['spell_slots_used']:
        if data['spell_slots_used'][level] > 0:
            slots_restored = True
        data['spell_slots_used'][level] = 0
    
    # Reset Warlock pact slots if applicable
    if data.get('pact_slots_used', 0) > 0:
        data['pact_slots_used'] = 0
        summary.append("Pact magic slots restored")
    elif slots_restored:
        summary.append("Spell slots restored")
    
    # Reset hit dice used (regain half total, minimum 1)
    old_hit_dice_used = data.get('hit_dice_used', 0)
    dice_to_regain = max(1, data['level'] // 2)
    data['hit_dice_used'] = max(0, old_hit_dice_used - dice_to_regain)
    if old_hit_dice_used > 0:
        summary.append(f"Hit dice regained: {dice_to_regain}")
    
    # Clear death saves
    data['death_saves'] = {'successes': 0, 'failures': 0}
    
    # Reduce exhaustion by 1 (if any and if well-fed)
    if data.get('exhaustion_level', 0) > 0:
        data['exhaustion_level'] -= 1
        summary.append(f"Exhaustion reduced to level {data['exhaustion_level']}")
        if data['exhaustion_level'] == 0:
            if 'Exhaustion' in data.get('conditions', []):
                data['conditions'].remove('Exhaustion')
    
    # Reset class-specific resources
    class_name = data.get('class', '').lower()
    
    # Barbarian - restore rages
    if class_name == 'barbarian':
        data['rages_used'] = 0
        summary.append("Rages restored")
    
    # Monk - restore ki points
    if class_name == 'monk':
        data['ki_used'] = 0
        summary.append("Ki points restored")
    
    # Sorcerer - sorcery points (note: they DON'T auto-restore on long rest in base rules)
    # But Font of Magic allows conversion, so we track it
    
    # Fighter - restore Second Wind and Action Surge
    if class_name == 'fighter':
        data['second_wind_used'] = False
        data['action_surge_used'] = 0
        summary.append("Second Wind and Action Surge restored")
    
    # Paladin - Lay on Hands pool restores
    if class_name == 'paladin':
        data['lay_on_hands_pool'] = data['level'] * 5
        summary.append(f"Lay on Hands pool restored ({data['level'] * 5} HP)")
    
    # Cleric/Paladin - Channel Divinity
    if class_name in ['cleric', 'paladin']:
        data['channel_divinity_used'] = 0
        summary.append("Channel Divinity restored")
    
    # Druid - Wild Shape uses
    if class_name == 'druid':
        data['wild_shape_uses'] = 2
        summary.append("Wild Shape uses restored")
    
    # Bard - Bardic Inspiration
    if class_name == 'bard':
        data['bardic_inspiration_used'] = 0
        summary.append("Bardic Inspiration restored")
    
    save_character(user_id, data)
    
    if not summary:
        summary.append("Fully rested")
    
    return {
        'data': data,
        'summary': summary
    }


def short_rest(user_id, hit_dice_to_use=0):
    """Complete a short rest, spending hit dice to heal and recovering some resources.
    
    Args:
        user_id: The user's ID
        hit_dice_to_use: Number of hit dice to spend for healing
    
    Returns:
        dict with 'data' (updated character), 'healing' (amount healed), and 'summary'
    """
    data = load_character(user_id)
    if not data:
        return None
    
    summary = []
    total_healing = 0
    
    # Use hit dice to heal
    available_dice = data['level'] - data.get('hit_dice_used', 0)
    dice_used = min(hit_dice_to_use, available_dice)
    
    if dice_used > 0:
        import random
        dice_type = int(data.get('hit_dice', '1d8').split('d')[1])
        con_mod = get_ability_modifier(data['CON'])
        
        healing_rolls = []
        for _ in range(dice_used):
            roll = random.randint(1, dice_type)
            heal = max(0, roll + con_mod)  # Minimum 0 per die
            healing_rolls.append(f"{roll}+{con_mod}={heal}")
            total_healing += heal
        
        old_hp = data['hp']
        data['hp'] = min(data['max_hp'], data['hp'] + total_healing)
        actual_healing = data['hp'] - old_hp
        data['hit_dice_used'] = data.get('hit_dice_used', 0) + dice_used
        
        summary.append(f"Spent {dice_used} hit dice, healed {actual_healing} HP")
    
    # Class-specific short rest recovery
    class_name = data.get('class', '').lower()
    
    # Warlock - Pact Magic slots recover on short rest!
    if class_name == 'warlock':
        if data.get('pact_slots_used', 0) > 0:
            data['pact_slots_used'] = 0
            summary.append("Pact magic slots restored!")
    
    # Fighter - Second Wind recovers (but they might have used it before the rest)
    if class_name == 'fighter':
        if data.get('second_wind_used', False):
            data['second_wind_used'] = False
            summary.append("Second Wind restored")
    
    # Monk - Ki points fully restore on short rest
    if class_name == 'monk':
        if data.get('ki_used', 0) > 0:
            data['ki_used'] = 0
            summary.append("Ki points restored")
    
    # Druid (Circle of the Land) - Recover spell slots? (Subclass feature)
    # Wizard - Arcane Recovery (once per day, on short rest) - handled separately
    
    # Bard - Song of Rest adds healing (handled in healing calculation above)
    
    # Cleric/Paladin - Channel Divinity restores
    if class_name in ['cleric', 'paladin']:
        if data.get('channel_divinity_used', 0) > 0:
            data['channel_divinity_used'] = 0
            summary.append("Channel Divinity restored")
    
    save_character(user_id, data)
    
    if not summary:
        summary.append("Rested but nothing to recover")
    
    return {
        'data': data,
        'healing': total_healing,
        'summary': summary
    }

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

def level_up(user_id, roll_hp=True):
    """Level up a character, gaining HP and new features.
    
    Args:
        user_id: The user's ID
        roll_hp: If True, roll for HP. If False, take average.
    
    Returns:
        dict with 'data' (updated character), 'hp_gained', and 'new_features'
    """
    data = load_character(user_id)
    if not data:
        return None
    
    old_level = data['level']
    new_level = old_level + 1
    data['level'] = new_level
    data['proficiency'] = get_proficiency_bonus(new_level)
    
    # Calculate HP increase
    import random
    dice_type = int(data.get('hit_dice', '1d8').split('d')[1])
    
    if roll_hp:
        hp_increase = random.randint(1, dice_type) + get_ability_modifier(data['CON'])
    else:
        # Take average (rounded up)
        hp_increase = (dice_type // 2) + 1 + get_ability_modifier(data['CON'])
    
    hp_increase = max(1, hp_increase)  # Minimum 1 HP per level
    data['max_hp'] += hp_increase
    data['hp'] += hp_increase
    
    # Update hit dice count
    data['hit_dice'] = f"{new_level}d{dice_type}"
    
    new_features = []
    
    # Get new class features from D&D 5e data
    if DND_DATA_AVAILABLE:
        class_name = data.get('class', 'Fighter')
        class_data = get_class_data(class_name)
        
        if class_data:
            # Add new features for this level
            new_features = get_features_at_level(class_name, new_level)
            for feature in new_features:
                if feature not in data.get('features', []):
                    data.setdefault('features', []).append(feature)
            
            # Update spell slots if spellcaster
            if class_data.get('spellcasting'):
                slots = get_spell_slots(class_name, new_level)
                for level, num in slots.items():
                    data['spell_slots'][str(level)] = num
                
                # Check for new cantrips
                casting = class_data['spellcasting']
                cantrips = casting.get('cantrips', {})
                for lvl in sorted(cantrips.keys()):
                    if lvl == new_level:
                        # Character gains additional cantrip slots at this level
                        pass  # They choose which cantrips to learn
    
    save_character(user_id, data)
    return {
        'data': data,
        'hp_gained': hp_increase,
        'new_features': new_features
    }

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


# =============================================================================
# SPELL MANAGEMENT FUNCTIONS
# =============================================================================

def learn_spell(user_id, spell_name):
    """Add a spell to the character's known spells."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    if DND_DATA_AVAILABLE:
        spell = get_spell(spell_name)
        if not spell:
            return None, f"Spell '{spell_name}' not found"
        
        # Check if class can learn this spell
        char_class = data.get('class', '')
        if char_class not in spell.get('classes', []):
            return None, f"{char_class}s cannot learn {spell_name}"
    
    if spell_name not in data.get('spells_known', []):
        data.setdefault('spells_known', []).append(spell_name)
        save_character(user_id, data)
        return data, f"Learned {spell_name}!"
    
    return data, f"Already knows {spell_name}"


def forget_spell(user_id, spell_name):
    """Remove a spell from the character's known spells."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    if spell_name in data.get('spells_known', []):
        data['spells_known'].remove(spell_name)
        # Also remove from prepared if it was prepared
        if spell_name in data.get('prepared_spells', []):
            data['prepared_spells'].remove(spell_name)
        save_character(user_id, data)
        return data, f"Forgot {spell_name}"
    
    return None, f"Doesn't know {spell_name}"


def learn_cantrip(user_id, cantrip_name):
    """Add a cantrip to the character's known cantrips."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    if DND_DATA_AVAILABLE:
        spell = get_spell(cantrip_name)
        if not spell:
            return None, f"Cantrip '{cantrip_name}' not found"
        if spell.get('level', 1) != 0:
            return None, f"'{cantrip_name}' is not a cantrip"
        
        char_class = data.get('class', '')
        if char_class not in spell.get('classes', []):
            return None, f"{char_class}s cannot learn {cantrip_name}"
    
    if cantrip_name not in data.get('cantrips_known', []):
        data.setdefault('cantrips_known', []).append(cantrip_name)
        save_character(user_id, data)
        return data, f"Learned cantrip: {cantrip_name}!"
    
    return data, f"Already knows {cantrip_name}"


def prepare_spell(user_id, spell_name):
    """Prepare a known spell for casting."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    # Check if spell is known (for known casters) or available (for prepared casters)
    if DND_DATA_AVAILABLE:
        class_data = get_class_data(data.get('class', 'Fighter'))
        if class_data and class_data.get('spellcasting'):
            casting_type = class_data['spellcasting'].get('type', 'known')
            
            if casting_type == 'known':
                # Must know the spell first
                if spell_name not in data.get('spells_known', []):
                    return None, f"Must learn {spell_name} before preparing it"
            # For prepared casters (Cleric, Druid, Wizard, Paladin), 
            # they can prepare from their full class list
    
    if spell_name in data.get('prepared_spells', []):
        return data, f"{spell_name} is already prepared"
    
    data.setdefault('prepared_spells', []).append(spell_name)
    save_character(user_id, data)
    return data, f"Prepared {spell_name}"


def unprepare_spell(user_id, spell_name):
    """Remove a spell from prepared spells."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    if spell_name in data.get('prepared_spells', []):
        data['prepared_spells'].remove(spell_name)
        save_character(user_id, data)
        return data, f"Unprepared {spell_name}"
    
    return None, f"{spell_name} was not prepared"


def cast_spell(user_id, spell_name, slot_level=None):
    """Cast a spell, consuming a spell slot.
    
    Args:
        user_id: The user's ID
        spell_name: Name of the spell to cast
        slot_level: Level of spell slot to use (None = auto-select minimum)
    
    Returns:
        tuple of (success: bool, message: str, spell_data: dict or None)
    """
    data = load_character(user_id)
    if not data:
        return False, "Character not found", None
    
    spell = None
    spell_level = 0
    
    if DND_DATA_AVAILABLE:
        spell = get_spell(spell_name)
        if not spell:
            return False, f"Spell '{spell_name}' not found", None
        spell_level = spell.get('level', 0)
    else:
        # Without data, assume level 1 spell
        spell_level = 1
    
    # Cantrips don't use spell slots
    if spell_level == 0:
        if spell_name not in data.get('cantrips_known', []):
            return False, f"You don't know the cantrip {spell_name}", None
        return True, f"Cast {spell_name}!", spell
    
    # Check if spell is prepared (or known for known casters)
    is_prepared = spell_name in data.get('prepared_spells', [])
    is_known = spell_name in data.get('spells_known', [])
    
    if not is_prepared and not is_known:
        return False, f"You haven't prepared {spell_name}", None
    
    # Determine slot level to use
    if slot_level is None:
        slot_level = spell_level
    
    if slot_level < spell_level:
        return False, f"{spell_name} requires at least a level {spell_level} slot", None
    
    # Check for available spell slot
    slot_key = str(slot_level)
    available = data['spell_slots'].get(slot_key, 0) - data['spell_slots_used'].get(slot_key, 0)
    
    if available <= 0:
        return False, f"No level {slot_level} spell slots remaining", None
    
    # Use the slot
    data['spell_slots_used'][slot_key] = data['spell_slots_used'].get(slot_key, 0) + 1
    save_character(user_id, data)
    
    upcast_msg = f" at level {slot_level}" if slot_level > spell_level else ""
    return True, f"Cast {spell_name}{upcast_msg}!", spell


def get_available_spells(user_id):
    """Get all spells available to a character (known + class list for prepared casters)."""
    data = load_character(user_id)
    if not data:
        return None
    
    result = {
        'cantrips': data.get('cantrips_known', []),
        'known': data.get('spells_known', []),
        'prepared': data.get('prepared_spells', []),
        'spell_slots': data.get('spell_slots', {}),
        'spell_slots_used': data.get('spell_slots_used', {}),
    }
    
    # For prepared casters, show full class spell list
    if DND_DATA_AVAILABLE:
        class_name = data.get('class', '')
        class_data = get_class_data(class_name)
        
        if class_data and class_data.get('spellcasting'):
            casting_type = class_data['spellcasting'].get('type', 'known')
            
            if casting_type == 'prepared':
                # Get max spell level they can cast
                max_spell_level = 0
                for slot_lvl, count in result['spell_slots'].items():
                    if count > 0:
                        max_spell_level = max(max_spell_level, int(slot_lvl))
                
                # Get all class spells up to that level
                result['class_spell_list'] = get_spells_for_class(class_name, max_spell_level)
    
    return result


def get_spell_slots_remaining(user_id):
    """Get remaining spell slots for a character."""
    data = load_character(user_id)
    if not data:
        return None
    
    remaining = {}
    for level in range(1, 10):
        level_str = str(level)
        total = data['spell_slots'].get(level_str, 0)
        used = data['spell_slots_used'].get(level_str, 0)
        if total > 0:
            remaining[level_str] = {'total': total, 'used': used, 'remaining': total - used}
    
    return remaining


def apply_racial_bonuses(user_id, race_name, subrace=None):
    """Apply racial ability score bonuses to a character."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    if not DND_DATA_AVAILABLE:
        return None, "D&D 5e data not available"
    
    race_data = get_race_data(race_name, subrace)
    if not race_data:
        return None, f"Race '{race_name}' not found"
    
    # Apply ability bonuses
    for stat, bonus in race_data.get('ability_bonuses', {}).items():
        data[stat] = data.get(stat, 10) + bonus
    
    # Update race/subrace
    data['race'] = race_name
    if subrace:
        data['subrace'] = subrace
    
    # Apply speed
    data['speed'] = race_data.get('speed', 30)
    
    # Add racial traits as features
    for trait in race_data.get('traits', []):
        if trait not in data.get('features', []):
            data.setdefault('features', []).append(trait)
    
    # Recalculate HP with new CON
    dice_type = int(data.get('hit_dice', '1d8').split('d')[1])
    data['max_hp'] = dice_type + get_ability_modifier(data['CON'])
    data['hp'] = data['max_hp']
    
    save_character(user_id, data)
    return data, f"Applied {race_name}" + (f" ({subrace})" if subrace else "") + " bonuses"


def get_class_features(class_name, level):
    """Get all features a class has at a given level."""
    if not DND_DATA_AVAILABLE:
        return []
    return get_all_features_up_to_level(class_name, level)


def get_available_classes():
    """Get list of available classes."""
    if DND_DATA_AVAILABLE:
        return list(CLASSES.keys())
    return ['Fighter', 'Wizard', 'Rogue', 'Cleric', 'Ranger', 'Barbarian', 
            'Bard', 'Druid', 'Monk', 'Paladin', 'Sorcerer', 'Warlock']


def get_available_races():
    """Get list of available races."""
    if DND_DATA_AVAILABLE:
        return list(RACES.keys())
    return ['Human', 'Elf', 'Dwarf', 'Halfling', 'Half-Elf', 'Half-Orc', 
            'Gnome', 'Dragonborn', 'Tiefling']


# =============================================================================
# EQUIPMENT MANAGEMENT FUNCTIONS
# =============================================================================

# Import equipment data
try:
    from .dnd5e_data import (
        WEAPONS, ARMOR, AMMUNITION, ADVENTURING_GEAR, CONDITIONS,
        get_weapon, get_armor, calculate_ac as dnd_calculate_ac,
        get_condition, get_condition_effects, apply_exhaustion_effects,
        check_attack_modifiers, check_attacks_against_modifiers
    )
    EQUIPMENT_DATA_AVAILABLE = True
except ImportError:
    EQUIPMENT_DATA_AVAILABLE = False


def equip_weapon(user_id, weapon_name):
    """Equip a weapon from inventory."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    # Check if weapon is in inventory
    if weapon_name not in data.get('inventory', []):
        return None, f"You don't have {weapon_name} in your inventory"
    
    # Check if it's a valid weapon
    if EQUIPMENT_DATA_AVAILABLE:
        weapon = get_weapon(weapon_name)
        if not weapon:
            # Could be a custom/magic weapon - allow it
            pass
    
    # Unequip current weapon (put back in inventory if exists)
    old_weapon = data.get('equipment', {}).get('weapon')
    if old_weapon and old_weapon not in data.get('inventory', []):
        data.setdefault('inventory', []).append(old_weapon)
    
    # Equip new weapon
    data.setdefault('equipment', {})['weapon'] = weapon_name
    
    # Remove from general inventory (it's now equipped)
    if weapon_name in data['inventory']:
        data['inventory'].remove(weapon_name)
    
    save_character(user_id, data)
    return data, f"Equipped {weapon_name}"


def unequip_weapon(user_id):
    """Unequip current weapon and put back in inventory."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    weapon = data.get('equipment', {}).get('weapon')
    if not weapon:
        return data, "No weapon equipped"
    
    data['equipment']['weapon'] = None
    data.setdefault('inventory', []).append(weapon)
    
    save_character(user_id, data)
    return data, f"Unequipped {weapon}"


def equip_armor(user_id, armor_name):
    """Equip armor from inventory and recalculate AC."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    # Check if armor is in inventory
    if armor_name not in data.get('inventory', []):
        return None, f"You don't have {armor_name} in your inventory"
    
    # Check if it's valid armor and check strength requirement
    if EQUIPMENT_DATA_AVAILABLE:
        armor = get_armor(armor_name)
        if armor:
            str_req = armor.get('strength_req')
            if str_req and data.get('STR', 10) < str_req:
                return None, f"{armor_name} requires {str_req} Strength (you have {data.get('STR', 10)})"
    
    # Unequip current armor
    old_armor = data.get('equipment', {}).get('armor')
    if old_armor and old_armor not in data.get('inventory', []):
        data.setdefault('inventory', []).append(old_armor)
    
    # Equip new armor
    data.setdefault('equipment', {})['armor'] = armor_name
    
    # Remove from general inventory
    if armor_name in data['inventory']:
        data['inventory'].remove(armor_name)
    
    # Recalculate AC
    _recalculate_ac(data)
    
    save_character(user_id, data)
    return data, f"Equipped {armor_name} (AC: {data['ac']})"


def unequip_armor(user_id):
    """Unequip armor and recalculate AC."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    armor = data.get('equipment', {}).get('armor')
    if not armor:
        return data, "No armor equipped"
    
    data['equipment']['armor'] = None
    data.setdefault('inventory', []).append(armor)
    
    # Recalculate AC
    _recalculate_ac(data)
    
    save_character(user_id, data)
    return data, f"Unequipped {armor} (AC: {data['ac']})"


def equip_shield(user_id, shield_name="Shield"):
    """Equip a shield and recalculate AC."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    # Check if shield is in inventory
    if shield_name not in data.get('inventory', []):
        return None, f"You don't have a {shield_name} in your inventory"
    
    # Unequip current shield
    old_shield = data.get('equipment', {}).get('shield')
    if old_shield and old_shield not in data.get('inventory', []):
        data.setdefault('inventory', []).append(old_shield)
    
    # Equip shield
    data.setdefault('equipment', {})['shield'] = shield_name
    
    # Remove from inventory
    if shield_name in data['inventory']:
        data['inventory'].remove(shield_name)
    
    # Recalculate AC
    _recalculate_ac(data)
    
    save_character(user_id, data)
    return data, f"Equipped {shield_name} (AC: {data['ac']})"


def unequip_shield(user_id):
    """Unequip shield and recalculate AC."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    shield = data.get('equipment', {}).get('shield')
    if not shield:
        return data, "No shield equipped"
    
    data['equipment']['shield'] = None
    data.setdefault('inventory', []).append(shield)
    
    # Recalculate AC
    _recalculate_ac(data)
    
    save_character(user_id, data)
    return data, f"Unequipped shield (AC: {data['ac']})"


def _recalculate_ac(data):
    """Internal function to recalculate AC based on equipped armor."""
    dex_mod = get_ability_modifier(data.get('DEX', 10))
    armor_name = data.get('equipment', {}).get('armor')
    has_shield = data.get('equipment', {}).get('shield') is not None
    
    if EQUIPMENT_DATA_AVAILABLE:
        data['ac'] = dnd_calculate_ac(armor_name, dex_mod, has_shield)
    else:
        # Fallback calculation
        base_ac = 10 + dex_mod
        if has_shield:
            base_ac += 2
        data['ac'] = base_ac


def get_weapon_damage(user_id):
    """Get the damage dice and type for currently equipped weapon."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    weapon_name = data.get('equipment', {}).get('weapon')
    if not weapon_name:
        # Unarmed strike
        return "1", "bludgeoning", "Unarmed Strike"
    
    if EQUIPMENT_DATA_AVAILABLE:
        weapon = get_weapon(weapon_name)
        if weapon:
            return weapon['damage'], weapon['damage_type'], weapon_name
    
    # Default fallback
    return "1d6", "slashing", weapon_name


def get_equipment_summary(user_id):
    """Get a summary of equipped items."""
    data = load_character(user_id)
    if not data:
        return None
    
    equipment = data.get('equipment', {})
    
    summary = []
    
    weapon = equipment.get('weapon')
    if weapon:
        if EQUIPMENT_DATA_AVAILABLE:
            weapon_data = get_weapon(weapon)
            if weapon_data:
                props = ", ".join(weapon_data.get('properties', [])) or "none"
                summary.append(f"⚔️ **Weapon:** {weapon} ({weapon_data['damage']} {weapon_data['damage_type']}) - {props}")
            else:
                summary.append(f"⚔️ **Weapon:** {weapon}")
        else:
            summary.append(f"⚔️ **Weapon:** {weapon}")
    else:
        summary.append("⚔️ **Weapon:** None (Unarmed)")
    
    armor = equipment.get('armor')
    if armor:
        if EQUIPMENT_DATA_AVAILABLE:
            armor_data = get_armor(armor)
            if armor_data:
                stealth = " (Stealth Disadvantage)" if armor_data.get('stealth_disadvantage') else ""
                summary.append(f"🛡️ **Armor:** {armor} (Base AC {armor_data['ac']}){stealth}")
            else:
                summary.append(f"🛡️ **Armor:** {armor}")
        else:
            summary.append(f"🛡️ **Armor:** {armor}")
    else:
        summary.append("🛡️ **Armor:** None (Unarmored)")
    
    shield = equipment.get('shield')
    if shield:
        summary.append(f"🛡️ **Shield:** {shield} (+2 AC)")
    
    summary.append(f"🔰 **Total AC:** {data.get('ac', 10)}")
    
    return "\n".join(summary)


def add_to_inventory(user_id, item_name, quantity=1):
    """Add items to inventory with quantity support."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    for _ in range(quantity):
        data.setdefault('inventory', []).append(item_name)
    
    save_character(user_id, data)
    
    if quantity > 1:
        return data, f"Added {quantity}x {item_name} to inventory"
    return data, f"Added {item_name} to inventory"


def remove_from_inventory(user_id, item_name, quantity=1):
    """Remove items from inventory."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    removed = 0
    for _ in range(quantity):
        if item_name in data.get('inventory', []):
            data['inventory'].remove(item_name)
            removed += 1
    
    if removed == 0:
        return None, f"You don't have {item_name} in your inventory"
    
    save_character(user_id, data)
    
    if quantity > 1:
        return data, f"Removed {removed}x {item_name} from inventory"
    return data, f"Removed {item_name} from inventory"


def get_inventory_summary(user_id):
    """Get a formatted inventory summary with item counts."""
    data = load_character(user_id)
    if not data:
        return None
    
    inventory = data.get('inventory', [])
    if not inventory:
        return "📦 **Inventory:** Empty"
    
    # Count items
    item_counts = {}
    for item in inventory:
        item_counts[item] = item_counts.get(item, 0) + 1
    
    # Format
    lines = ["📦 **Inventory:**"]
    for item, count in sorted(item_counts.items()):
        if count > 1:
            lines.append(f"  • {item} (×{count})")
        else:
            lines.append(f"  • {item}")
    
    return "\n".join(lines)


# =============================================================================
# CONDITION MANAGEMENT (Enhanced)
# =============================================================================

def apply_condition(user_id, condition_name, duration=None):
    """Apply a condition with optional duration tracking."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    # Validate condition if data available
    if EQUIPMENT_DATA_AVAILABLE:
        condition = get_condition(condition_name)
        if not condition and condition_name != "Exhaustion":
            # Allow custom conditions
            pass
    
    conditions = data.setdefault('conditions', [])
    
    # Check if already has condition
    if condition_name in conditions:
        return data, f"Already has {condition_name} condition"
    
    conditions.append(condition_name)
    
    # Track exhaustion level separately
    if condition_name == "Exhaustion":
        data['exhaustion_level'] = data.get('exhaustion_level', 0) + 1
        if data['exhaustion_level'] >= 6:
            conditions.append("Dead")
            save_character(user_id, data)
            return data, "💀 Exhaustion level 6 - Character has died"
    
    save_character(user_id, data)
    
    # Return condition effects
    effects_msg = ""
    if EQUIPMENT_DATA_AVAILABLE:
        effects = get_condition_effects(condition_name)
        if effects:
            effect_list = []
            if effects.get('attack_rolls') == 'disadvantage':
                effect_list.append("Disadvantage on attacks")
            if effects.get('ability_checks') == 'disadvantage':
                effect_list.append("Disadvantage on ability checks")
            if effects.get('speed') == 0:
                effect_list.append("Speed reduced to 0")
            if effects.get('incapacitated'):
                effect_list.append("Incapacitated")
            if effect_list:
                effects_msg = f" Effects: {', '.join(effect_list)}"
    
    return data, f"Applied {condition_name} condition.{effects_msg}"


def remove_condition_from_character(user_id, condition_name):
    """Remove a condition from a character."""
    data = load_character(user_id)
    if not data:
        return None, "Character not found"
    
    conditions = data.get('conditions', [])
    
    if condition_name not in conditions:
        return data, f"Doesn't have {condition_name} condition"
    
    conditions.remove(condition_name)
    
    # Handle exhaustion
    if condition_name == "Exhaustion":
        data['exhaustion_level'] = max(0, data.get('exhaustion_level', 1) - 1)
        if data['exhaustion_level'] > 0:
            # Still exhausted, add back
            conditions.append("Exhaustion")
    
    save_character(user_id, data)
    return data, f"Removed {condition_name} condition"


def get_attack_roll_modifiers(user_id):
    """Get advantage/disadvantage modifiers based on conditions."""
    data = load_character(user_id)
    if not data:
        return None
    
    conditions = data.get('conditions', [])
    
    if EQUIPMENT_DATA_AVAILABLE:
        return check_attack_modifiers(conditions)
    
    # Fallback
    result = {"advantage": False, "disadvantage": False}
    disadvantage_conditions = ["Blinded", "Frightened", "Poisoned", "Prone", "Restrained"]
    advantage_conditions = ["Invisible"]
    
    for cond in conditions:
        if cond in disadvantage_conditions:
            result["disadvantage"] = True
        if cond in advantage_conditions:
            result["advantage"] = True
    
    return result


def get_condition_summary(user_id):
    """Get a summary of current conditions and their effects."""
    data = load_character(user_id)
    if not data:
        return None
    
    conditions = data.get('conditions', [])
    if not conditions:
        return "✨ **Conditions:** None"
    
    lines = ["⚠️ **Conditions:**"]
    
    for cond in conditions:
        if cond == "Exhaustion":
            level = data.get('exhaustion_level', 1)
            if EQUIPMENT_DATA_AVAILABLE:
                effects = apply_exhaustion_effects(level)
                lines.append(f"  • Exhaustion (Level {level}): {', '.join(effects)}")
            else:
                lines.append(f"  • Exhaustion (Level {level})")
        else:
            if EQUIPMENT_DATA_AVAILABLE:
                condition_data = get_condition(cond)
                if condition_data:
                    lines.append(f"  • {cond}: {condition_data['description'][:100]}...")
                else:
                    lines.append(f"  • {cond}")
            else:
                lines.append(f"  • {cond}")
    
    return "\n".join(lines)