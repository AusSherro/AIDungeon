"""Routes for the simple web portal."""

from flask import Blueprint, render_template, abort, request, redirect, url_for, flash, jsonify
import os
import uuid
from utils.character_manager import (
    load_character, save_character, register_character, 
    learn_spell, learn_cantrip, forget_spell, prepare_spell, unprepare_spell,
    get_class_features
)
from utils.state_manager import load_state, get_context_summary
from config import Config

# Try to import D&D 5e data
try:
    from utils.dnd5e_data import (
        get_class_data, get_spell_slots, get_features_at_level, get_all_features_up_to_level,
        get_spells_for_class, get_cantrips_for_class, SPELLS, CLASSES
    )
    DND_DATA_AVAILABLE = True
except ImportError:
    DND_DATA_AVAILABLE = False

def list_all_characters():
    """Return a list of all stored characters with full details."""
    files = [f for f in os.listdir(Config.CHARACTERS_DIR) if f.endswith('.json')]
    characters = []
    for f in files:
        char_id = f[:-5]
        data = load_character(char_id)
        if data:
            characters.append({
                'id': char_id,
                'name': data.get('name', char_id),
                'race': data.get('race', ''),
                'char_class': data.get('class', ''),
                'level': data.get('level', 1),
            })
    return characters

portal_bp = Blueprint('portal', __name__, template_folder='templates')

@portal_bp.route('/')
def list_characters():
    characters = list_all_characters()
    return render_template('character_list.html', characters=characters)


@portal_bp.route('/character/new', methods=['GET'])
def create_character():
    """Show character creation form."""
    return render_template('character_create.html')


@portal_bp.route('/character/new', methods=['POST'])
def create_character_submit():
    """Handle character creation form submission."""
    name = request.form.get('name', 'Unnamed Hero')
    char_class = request.form.get('char_class', 'Fighter')
    race = request.form.get('race', 'Human')
    discord_id = request.form.get('discord_id', '').strip()
    
    # Use Discord ID if provided, otherwise generate a random ID
    char_id = discord_id if discord_id else str(uuid.uuid4())[:8]
    
    # Create the character
    register_character(char_id, name, char_class, race)
    
    # Load and update with additional stats
    char = load_character(char_id)
    
    # Set ability scores
    for stat in ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']:
        try:
            char[stat] = int(request.form.get(stat, 10))
        except ValueError:
            char[stat] = 10
    
    # Calculate HP based on class and CON
    con_mod = (char['CON'] - 10) // 2
    class_hit_dice = {
        'Barbarian': 12, 'Fighter': 10, 'Paladin': 10, 'Ranger': 10,
        'Bard': 8, 'Cleric': 8, 'Druid': 8, 'Monk': 8, 'Rogue': 8, 'Warlock': 8,
        'Sorcerer': 6, 'Wizard': 6
    }
    hit_die = class_hit_dice.get(char_class, 8)
    char['max_hp'] = hit_die + con_mod
    char['hp'] = char['max_hp']
    char['hit_die'] = f"1d{hit_die}"
    
    # Calculate AC (base 10 + DEX mod)
    dex_mod = (char['DEX'] - 10) // 2
    char['ac'] = 10 + dex_mod
    
    # Set inventory
    inventory_str = request.form.get('inventory', '')
    if inventory_str:
        char['inventory'] = [item.strip() for item in inventory_str.split(',') if item.strip()]
    
    save_character(char_id, char)
    flash('Character created successfully!', 'success')
    return redirect(url_for('portal.character_detail', char_id=char_id))


@portal_bp.route('/character/<char_id>')
def character_detail(char_id: str):
    data = load_character(char_id)
    if not data:
        abort(404)
    return render_template('character_detail.html', char=data, char_id=char_id)


@portal_bp.route('/character/<char_id>/edit', methods=['GET'])
def edit_character(char_id: str):
    data = load_character(char_id)
    if not data:
        abort(404)
    return render_template('character_edit.html', char=data, char_id=char_id)


@portal_bp.route('/character/<char_id>/save', methods=['POST'])
def save_character_route(char_id: str):
    """Handle character edit form submission."""
    char = load_character(char_id)
    if not char:
        abort(404)
    
    # Update basic info
    char['name'] = request.form.get('name', char['name'])
    char['race'] = request.form.get('race', char.get('race', 'Human'))
    char['class'] = request.form.get('char_class', char.get('class', 'Fighter'))
    
    # Update numeric stats
    try:
        char['level'] = int(request.form.get('level', 1))
        char['hp'] = int(request.form.get('hp', 10))
        char['max_hp'] = int(request.form.get('max_hp', 10))
        char['ac'] = int(request.form.get('ac', 10))
        char['xp'] = int(request.form.get('xp', 0))
    except ValueError:
        pass
    
    # Update ability scores
    for stat in ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']:
        try:
            char[stat] = int(request.form.get(stat, 10))
        except ValueError:
            char[stat] = 10
    
    # Update inventory
    inventory_str = request.form.get('inventory', '')
    if inventory_str:
        char['inventory'] = [item.strip() for item in inventory_str.split(',') if item.strip()]
    else:
        char['inventory'] = []
    
    # Update proficiencies
    proficiencies = request.form.getlist('proficiencies')
    char['proficiencies'] = proficiencies
    
    save_character(char_id, char)
    flash('Character saved successfully!', 'success')
    return redirect(url_for('portal.character_detail', char_id=char_id))


@portal_bp.route('/campaign/<session_id>')
def campaign_summary(session_id: str):
    state = load_state(session_id)
    context = get_context_summary(state)
    return render_template('campaign_summary.html', state=state, session_id=session_id, context=context)


@portal_bp.route('/dm')
def dm_dashboard():
    sessions = []
    for f in os.listdir(Config.STATE_DIR):
        if f.endswith('.json'):
            session_id = f[:-5]
            state = load_state(session_id)
            sessions.append({
                'id': session_id,
                'title': state.get('campaign_title', 'Untitled Campaign'),
                'realm': state.get('realm', ''),
                'player_count': len(state.get('players', [])),
            })
    return render_template('dm_dashboard.html', sessions=sessions)


# ============ DELETE ROUTES ============

@portal_bp.route('/character/<char_id>/delete', methods=['POST'])
def delete_character(char_id: str):
    """Delete a character."""
    char_path = os.path.join(Config.CHARACTERS_DIR, f'{char_id}.json')
    if os.path.exists(char_path):
        os.remove(char_path)
        flash('Character deleted successfully.', 'success')
    else:
        flash('Character not found.', 'error')
    return redirect(url_for('portal.list_characters'))


@portal_bp.route('/campaign/<session_id>/delete', methods=['POST'])
def delete_campaign(session_id: str):
    """Delete a campaign/session."""
    state_path = os.path.join(Config.STATE_DIR, f'{session_id}.json')
    if os.path.exists(state_path):
        os.remove(state_path)
        flash('Campaign deleted successfully.', 'success')
    else:
        flash('Campaign not found.', 'error')
    return redirect(url_for('portal.dm_dashboard'))


# ============ SPELL & LEVEL SYNC ROUTES ============

@portal_bp.route('/character/<char_id>/sync', methods=['POST'])
def sync_character(char_id: str):
    """Sync character's spell slots and features with their class and level."""
    char = load_character(char_id)
    if not char:
        abort(404)
    
    if not DND_DATA_AVAILABLE:
        flash('D&D 5e data not available for sync.', 'error')
        return redirect(url_for('portal.character_detail', char_id=char_id))
    
    class_name = char.get('class', 'Fighter')
    level = char.get('level', 1)
    
    # Get class data
    class_data = get_class_data(class_name)
    if not class_data:
        flash(f'Class {class_name} not found in D&D data.', 'error')
        return redirect(url_for('portal.character_detail', char_id=char_id))
    
    # Update spell slots
    if class_data.get('spellcasting'):
        slots = get_spell_slots(class_name, level)
        for slot_level in range(1, 10):
            char['spell_slots'][str(slot_level)] = slots.get(slot_level, 0)
    
    # Update features
    all_features = get_all_features_up_to_level(class_name, level)
    for feature in all_features:
        if feature not in char.get('features', []):
            char.setdefault('features', []).append(feature)
    
    # Update proficiency bonus
    char['proficiency'] = 2 + (level - 1) // 4
    
    # Update hit dice
    hit_die = class_data.get('hit_die', 8)
    char['hit_dice'] = f"{level}d{hit_die}"
    
    save_character(char_id, char)
    flash(f'Synced {char["name"]} with {class_name} level {level} data!', 'success')
    return redirect(url_for('portal.character_detail', char_id=char_id))


@portal_bp.route('/character/<char_id>/spells', methods=['GET'])
def manage_spells(char_id: str):
    """Show spell management page."""
    char = load_character(char_id)
    if not char:
        abort(404)
    
    available_spells = []
    available_cantrips = []
    
    if DND_DATA_AVAILABLE:
        class_name = char.get('class', 'Fighter')
        
        # Get spells for this class
        for spell_name, spell_data in SPELLS.items():
            if class_name in spell_data.get('classes', []):
                spell_info = {
                    'name': spell_name,
                    'level': spell_data.get('level', 0),
                    'school': spell_data.get('school', ''),
                    'ritual': spell_data.get('ritual', False),
                    'concentration': spell_data.get('concentration', False),
                    'known': spell_name in char.get('spells_known', []),
                    'prepared': spell_name in char.get('prepared_spells', []),
                    'is_cantrip': spell_data.get('level', 0) == 0,
                    'cantrip_known': spell_name in char.get('cantrips_known', [])
                }
                if spell_data.get('level', 0) == 0:
                    available_cantrips.append(spell_info)
                else:
                    available_spells.append(spell_info)
        
        # Sort by level then name
        available_spells.sort(key=lambda x: (x['level'], x['name']))
        available_cantrips.sort(key=lambda x: x['name'])
    
    return render_template('spell_management.html', 
                          char=char, 
                          char_id=char_id,
                          available_spells=available_spells,
                          available_cantrips=available_cantrips)


@portal_bp.route('/character/<char_id>/spells/learn', methods=['POST'])
def learn_spell_route(char_id: str):
    """Learn a spell or cantrip."""
    spell_name = request.form.get('spell_name', '')
    is_cantrip = request.form.get('is_cantrip') == 'true'
    
    if is_cantrip:
        result, message = learn_cantrip(char_id, spell_name)
    else:
        result, message = learn_spell(char_id, spell_name)
    
    if result:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('portal.manage_spells', char_id=char_id))


@portal_bp.route('/character/<char_id>/spells/forget', methods=['POST'])
def forget_spell_route(char_id: str):
    """Forget a spell."""
    spell_name = request.form.get('spell_name', '')
    is_cantrip = request.form.get('is_cantrip') == 'true'
    
    char = load_character(char_id)
    if not char:
        abort(404)
    
    if is_cantrip:
        if spell_name in char.get('cantrips_known', []):
            char['cantrips_known'].remove(spell_name)
            save_character(char_id, char)
            flash(f'Forgot cantrip: {spell_name}', 'success')
        else:
            flash(f"Doesn't know cantrip: {spell_name}", 'error')
    else:
        result, message = forget_spell(char_id, spell_name)
        if result:
            flash(message, 'success')
        else:
            flash(message, 'error')
    
    return redirect(url_for('portal.manage_spells', char_id=char_id))


@portal_bp.route('/character/<char_id>/spells/prepare', methods=['POST'])
def prepare_spell_route(char_id: str):
    """Prepare or unprepare a spell."""
    spell_name = request.form.get('spell_name', '')
    action = request.form.get('action', 'prepare')
    
    if action == 'prepare':
        result, message = prepare_spell(char_id, spell_name)
    else:
        result, message = unprepare_spell(char_id, spell_name)
    
    if result:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('portal.manage_spells', char_id=char_id))
