import json
import os
from config import Config

VOICE_MAP_FILE = os.path.join(os.path.dirname(__file__), '..', 'voice_profiles.json')


def _load_voice_map():
    if os.path.exists(VOICE_MAP_FILE):
        try:
            with open(VOICE_MAP_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_voice_map(mapping):
    try:
        with open(VOICE_MAP_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


VOICE_MAP = _load_voice_map()


def get_voice_id(tag: str):
    """Return the ElevenLabs voice ID for a tag."""
    if not VOICE_MAP:
        VOICE_MAP.update(_load_voice_map())
    if not tag:
        tag = Config.DEFAULT_VOICE
    return VOICE_MAP.get(tag, VOICE_MAP.get(Config.DEFAULT_VOICE, ''))


def set_voice_profile(tag: str, voice_id: str):
    """Add or update a voice profile."""
    VOICE_MAP[tag] = voice_id
    _save_voice_map(VOICE_MAP)


def list_voice_profiles():
    return dict(VOICE_MAP)
