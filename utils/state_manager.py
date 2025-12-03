import os
import json
import shutil
from threading import Lock
import logging

logger = logging.getLogger(__name__)

STATE_DIR = os.path.join(os.path.dirname(__file__), '..', 'state')
os.makedirs(STATE_DIR, exist_ok=True)
_state_locks = {}

# Default structure for a channel's campaign state
DEFAULT_STATE = {
    "campaign_title": "",
    "realm": "",
    "plot_hook": "",
    "location": "",
    "players": [],
    "prompt_history": [],
    "difficulty": "normal",
    "turn_order": [],
    "current_turn_index": 0,
    "auto_advance": False,
    "tts_enabled": True,
}

def _get_state_path(session_id):
    return os.path.join(STATE_DIR, f'{session_id}.json')


def _ensure_defaults(state: dict) -> dict:
    """Ensure a state dict has the required default keys."""
    for key, val in DEFAULT_STATE.items():
        state.setdefault(key, val if not isinstance(val, list) else list(val))
    return state

def load_state(session_id):
    path = _get_state_path(session_id)
    if not os.path.exists(path):
        return _ensure_defaults({})
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return _ensure_defaults(data)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to load state for {session_id}: {e}")
        return _ensure_defaults({})
    except Exception as e:
        logger.error(f"Unexpected error loading state: {e}")
        return _ensure_defaults({})

def save_state(session_id, state):
    path = _get_state_path(session_id)
    lock = _state_locks.setdefault(session_id, Lock())
    
    try:
        with lock:
            # Create backup before saving
            if os.path.exists(path):
                shutil.copy2(path, f"{path}.backup")
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                
            # Clean up old backup after successful save
            backup_path = f"{path}.backup"
            if os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                except:
                    pass  # Ignore backup cleanup errors
                    
    except Exception as e:
        logger.error(f"Failed to save state for {session_id}: {e}")
        # Restore backup if save failed
        backup_path = f"{path}.backup"
        if os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, path)
                logger.info(f"Restored backup for {session_id}")
            except Exception as restore_error:
                logger.error(f"Failed to restore backup: {restore_error}")
        raise


def add_prompt_entry(state: dict, role: str, content: str, max_entries: int = 10):
    """Append a conversation entry and cap history length."""
    entry = {"role": role, "content": content}
    history = state.setdefault("prompt_history", [])
    history.append(entry)
    if len(history) > max_entries:
        state["prompt_history"] = history[-max_entries:]

def get_turn_order(state):
    return state.get('turn_order', [])

def set_turn_order(state, turn_order):
    state['turn_order'] = turn_order

def get_current_turn_index(state):
    return state.get('current_turn_index', 0)

def set_current_turn_index(state, idx):
    state['current_turn_index'] = idx

