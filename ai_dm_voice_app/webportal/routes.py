"""Routes for the simple web portal."""

from flask import Blueprint, render_template, abort
import os
from utils.character_manager import load_character
from config import Config

def list_all_characters():
    """Return a list of all stored characters."""
    files = [f for f in os.listdir(Config.CHARACTERS_DIR) if f.endswith('.json')]
    characters = []
    for f in files:
        char_id = f[:-5]
        data = load_character(char_id)
        if data:
            characters.append({
                'id': char_id,
                'name': data.get('name', char_id),
            })
    return characters

portal_bp = Blueprint('portal', __name__, template_folder='templates')

@portal_bp.route('/')
def list_characters():
    characters = list_all_characters()
    return render_template('character_list.html', characters=characters)

@portal_bp.route('/character/<char_id>')
def character_detail(char_id: str):
    data = load_character(char_id)
    if not data:
        abort(404)
    return render_template('character_detail.html', char=data, char_id=char_id)
