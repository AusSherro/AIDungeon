import os
import json
import tempfile
from threading import Lock
import logging

logger = logging.getLogger(__name__)

STATE_DIR = os.path.join(os.path.dirname(__file__), '..', 'state')
os.makedirs(STATE_DIR, exist_ok=True)
_state_locks = {}
_meta_lock = Lock()


def _get_lock(session_id):
    """Get or create a lock for a session, protected by a meta-lock."""
    with _meta_lock:
        if session_id not in _state_locks:
            _state_locks[session_id] = Lock()
        return _state_locks[session_id]

# Default structure for a channel's campaign state
DEFAULT_STATE = {
    "campaign_title": "",
    "realm": "",
    "plot_hook": "",
    "location": "",
    "players": [],
    "prompt_history": [],       # Recent conversation (rolling window)
    "campaign_summary": "",     # AI-generated summary of major events
    "key_npcs": [],             # Important NPCs: [{name, description, status}]
    "key_events": [],           # Major plot points
    "quests": [],               # Active/completed quests
    "difficulty": "normal",
    "turn_order": [],
    "current_turn_index": 0,
    "auto_advance": False,
    "tts_enabled": True,
    "pending_roll": None,       # {player_id, skill, dc, action} - waiting for a roll
    "in_combat": False,
    "free_form": True,          # If True, anyone can act. If False, strict turn order
    "session_active": False,
    "session_started_at": None,
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
    lock = _get_lock(session_id)
    with lock:
        if not os.path.exists(path):
            return _ensure_defaults({})
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return _ensure_defaults(data)
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted state file for {session_id}: {e}")
            # Preserve corrupted file for debugging
            corrupted_path = f"{path}.corrupted"
            try:
                os.replace(path, corrupted_path)
                logger.info(f"Renamed corrupted file to {corrupted_path}")
            except OSError as rename_err:
                logger.error(f"Failed to rename corrupted file: {rename_err}")
            return _ensure_defaults({})
        except Exception as e:
            logger.error(f"Unexpected error loading state for {session_id}: {e}")
            return _ensure_defaults({})

def save_state(session_id, state):
    path = _get_state_path(session_id)
    lock = _get_lock(session_id)
    
    with lock:
        temp_fd, temp_path = tempfile.mkstemp(dir=STATE_DIR, suffix='.tmp')
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, path)  # Atomic on all platforms
        except Exception as e:
            logger.error(f"Failed to save state for {session_id}: {e}")
            try:
                os.unlink(temp_path)
            except OSError:
                pass
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


# ============ CONTEXT MANAGEMENT ============

def get_context_summary(state: dict) -> str:
    """Build a comprehensive context summary for the AI to remember."""
    lines = []
    
    # Campaign basics
    if state.get("campaign_title"):
        lines.append(f"**Campaign:** {state['campaign_title']}")
    if state.get("realm"):
        lines.append(f"**Realm:** {state['realm']}")
    if state.get("location"):
        lines.append(f"**Current Location:** {state['location']}")
    
    # Campaign summary (the important long-term memory)
    if state.get("campaign_summary"):
        lines.append(f"\n**Story So Far:**\n{state['campaign_summary']}")
    
    # Key NPCs
    npcs = state.get("key_npcs", [])
    if npcs:
        lines.append("\n**Key NPCs:**")
        for npc in npcs:
            status = f" ({npc.get('status', 'alive')})" if npc.get('status') else ""
            lines.append(f"- {npc.get('name', 'Unknown')}: {npc.get('description', '')}{status}")
    
    # Active quests
    quests = state.get("quests", [])
    active_quests = [q for q in quests if q.get("status") == "active"]
    if active_quests:
        lines.append("\n**Active Quests:**")
        for q in active_quests:
            lines.append(f"- {q.get('name', 'Unknown')}: {q.get('description', '')}")
    
    # Key events
    events = state.get("key_events", [])
    if events:
        lines.append("\n**Major Events:**")
        for event in events[-5:]:  # Last 5 major events
            lines.append(f"- {event}")
    
    # Players in the party
    players = state.get("players", [])
    if players:
        lines.append(f"\n**Party Members:** {', '.join(players)}")
    
    return "\n".join(lines) if lines else "No campaign context yet."


def update_campaign_summary(state: dict, new_summary: str):
    """Update the campaign summary with new events."""
    state["campaign_summary"] = new_summary


def add_key_event(state: dict, event: str):
    """Add a major plot point to the key events list."""
    events = state.setdefault("key_events", [])
    events.append(event)
    # Keep last 20 major events
    if len(events) > 20:
        state["key_events"] = events[-20:]


def add_or_update_npc(state: dict, name: str, description: str, status: str = "alive"):
    """Add or update an NPC in the key_npcs list."""
    npcs = state.setdefault("key_npcs", [])
    for npc in npcs:
        if npc.get("name", "").lower() == name.lower():
            npc["description"] = description
            npc["status"] = status
            return
    npcs.append({"name": name, "description": description, "status": status})


def add_quest(state: dict, name: str, description: str, status: str = "active"):
    """Add a new quest."""
    quests = state.setdefault("quests", [])
    quests.append({"name": name, "description": description, "status": status})


def update_quest_status(state: dict, quest_name: str, status: str):
    """Update a quest's status (active, completed, failed)."""
    quests = state.get("quests", [])
    for quest in quests:
        if quest.get("name", "").lower() == quest_name.lower():
            quest["status"] = status
            return True
    return False


def get_prompt_context_for_ai(state: dict) -> list:
    """
    Build the context list to send to OpenAI.
    Includes campaign summary + recent conversation history.
    """
    messages = []
    
    # Add campaign context as a system-level memory
    context_summary = get_context_summary(state)
    if context_summary and context_summary != "No campaign context yet.":
        messages.append({
            "role": "system",
            "content": f"CAMPAIGN MEMORY (long-term context):\n{context_summary}"
        })
    
    # Add recent conversation history
    history = state.get("prompt_history", [])
    messages.extend(history)
    
    return messages

