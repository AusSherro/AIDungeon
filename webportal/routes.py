"""Routes for the simple web portal."""

from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
import os
import uuid
from utils.character_manager import load_character, save_character, register_character
from utils.state_manager import load_state, get_context_summary
from config import Config

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
