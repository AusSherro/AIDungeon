import os
import json
from threading import Lock

STATE_DIR = os.path.join(os.path.dirname(__file__), '..', 'state')
os.makedirs(STATE_DIR, exist_ok=True)

_story_locks = {}

def _get_story_path(session_id: str) -> str:
    """Return the path for storing a session's story."""
    return os.path.join(STATE_DIR, f"{session_id}_story.json")


def load_from_file(session_id: str):
    """Load a story from disk. Returns an empty list if none exists."""
    path = _get_story_path(session_id)
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_to_file(session_id: str, story):
    """Persist a story to disk as JSON."""
    path = _get_story_path(session_id)
    lock = _story_locks.setdefault(session_id, Lock())
    with lock:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(story, f, indent=2, ensure_ascii=False)

