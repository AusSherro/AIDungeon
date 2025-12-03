"""
Handout Manager - Share text, images, and secrets with players
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from threading import Lock

HANDOUTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'handouts')
os.makedirs(HANDOUTS_DIR, exist_ok=True)

_handout_locks = {}


def _get_handouts_path(channel_id: str) -> str:
    """Get path to handouts file for a channel."""
    return os.path.join(HANDOUTS_DIR, f'{channel_id}.json')


def _load_handouts(channel_id: str) -> Dict[str, Any]:
    """Load handouts for a channel."""
    path = _get_handouts_path(channel_id)
    if not os.path.exists(path):
        return {"handouts": [], "player_secrets": {}}
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"handouts": [], "player_secrets": {}}


def _save_handouts(channel_id: str, data: Dict[str, Any]):
    """Save handouts for a channel."""
    path = _get_handouts_path(channel_id)
    lock = _handout_locks.setdefault(channel_id, Lock())
    
    with lock:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def create_handout(
    channel_id: str,
    title: str,
    content: str,
    handout_type: str = "note",  # note, letter, map, image, item, lore
    image_url: Optional[str] = None,
    visible_to: Optional[List[str]] = None,  # None = all players, list = specific player IDs
    created_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new handout.
    
    Args:
        channel_id: Discord channel ID
        title: Handout title
        content: Text content of the handout
        handout_type: Type of handout (note, letter, map, image, item, lore)
        image_url: Optional URL to an image
        visible_to: List of player IDs who can see this, or None for everyone
        created_by: ID of the DM/player who created it
    
    Returns:
        The created handout dict
    """
    data = _load_handouts(channel_id)
    
    handout = {
        "id": len(data["handouts"]) + 1,
        "title": title,
        "content": content,
        "type": handout_type,
        "image_url": image_url,
        "visible_to": visible_to,  # None = all, list = specific players
        "created_by": created_by,
        "created_at": datetime.now().isoformat(),
        "revealed": visible_to is None,  # True if visible to all
        "read_by": []  # Track who has read this
    }
    
    data["handouts"].append(handout)
    _save_handouts(channel_id, data)
    
    return handout


def get_handout(channel_id: str, handout_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific handout by ID."""
    data = _load_handouts(channel_id)
    
    for handout in data["handouts"]:
        if handout["id"] == handout_id:
            return handout
    
    return None


def get_handouts_for_player(channel_id: str, player_id: str) -> List[Dict[str, Any]]:
    """
    Get all handouts visible to a specific player.
    
    Returns handouts that are either:
    - Visible to everyone (visible_to is None)
    - Specifically shared with this player (player_id in visible_to)
    """
    data = _load_handouts(channel_id)
    visible = []
    
    for handout in data["handouts"]:
        if handout["visible_to"] is None:
            # Visible to everyone
            visible.append(handout)
        elif player_id in (handout["visible_to"] or []):
            # Specifically shared with this player
            visible.append(handout)
    
    return visible


def get_all_handouts(channel_id: str) -> List[Dict[str, Any]]:
    """Get all handouts for DM view."""
    data = _load_handouts(channel_id)
    return data["handouts"]


def reveal_handout(channel_id: str, handout_id: int) -> Optional[Dict[str, Any]]:
    """Reveal a handout to all players."""
    data = _load_handouts(channel_id)
    
    for handout in data["handouts"]:
        if handout["id"] == handout_id:
            handout["visible_to"] = None
            handout["revealed"] = True
            _save_handouts(channel_id, data)
            return handout
    
    return None


def share_handout_with(
    channel_id: str, 
    handout_id: int, 
    player_ids: List[str]
) -> Optional[Dict[str, Any]]:
    """Share a handout with specific players (add to visible_to list)."""
    data = _load_handouts(channel_id)
    
    for handout in data["handouts"]:
        if handout["id"] == handout_id:
            if handout["visible_to"] is None:
                # Already visible to all
                return handout
            
            # Add new players to visible list
            current = set(handout["visible_to"] or [])
            current.update(player_ids)
            handout["visible_to"] = list(current)
            _save_handouts(channel_id, data)
            return handout
    
    return None


def mark_as_read(channel_id: str, handout_id: int, player_id: str):
    """Mark a handout as read by a player."""
    data = _load_handouts(channel_id)
    
    for handout in data["handouts"]:
        if handout["id"] == handout_id:
            if player_id not in handout.get("read_by", []):
                handout.setdefault("read_by", []).append(player_id)
                _save_handouts(channel_id, data)
            return True
    
    return False


def delete_handout(channel_id: str, handout_id: int) -> bool:
    """Delete a handout."""
    data = _load_handouts(channel_id)
    
    original_count = len(data["handouts"])
    data["handouts"] = [h for h in data["handouts"] if h["id"] != handout_id]
    
    if len(data["handouts"]) < original_count:
        _save_handouts(channel_id, data)
        return True
    
    return False


# ============ PLAYER SECRETS ============
# Individual secrets that only one player can see

def add_player_secret(
    channel_id: str,
    player_id: str,
    secret: str,
    title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a secret note visible only to one player.
    
    These are for things like:
    - "You notice the merchant is lying"
    - "Your character recognizes this symbol"
    - "You feel a dark presence watching you"
    """
    data = _load_handouts(channel_id)
    
    secrets = data.setdefault("player_secrets", {})
    player_secrets = secrets.setdefault(player_id, [])
    
    secret_entry = {
        "id": len(player_secrets) + 1,
        "title": title or "Secret",
        "content": secret,
        "created_at": datetime.now().isoformat(),
        "read": False
    }
    
    player_secrets.append(secret_entry)
    _save_handouts(channel_id, data)
    
    return secret_entry


def get_player_secrets(channel_id: str, player_id: str) -> List[Dict[str, Any]]:
    """Get all secrets for a specific player."""
    data = _load_handouts(channel_id)
    return data.get("player_secrets", {}).get(player_id, [])


def get_unread_secrets(channel_id: str, player_id: str) -> List[Dict[str, Any]]:
    """Get unread secrets for a player."""
    secrets = get_player_secrets(channel_id, player_id)
    return [s for s in secrets if not s.get("read", False)]


def mark_secret_read(channel_id: str, player_id: str, secret_id: int) -> bool:
    """Mark a secret as read."""
    data = _load_handouts(channel_id)
    
    secrets = data.get("player_secrets", {}).get(player_id, [])
    for secret in secrets:
        if secret["id"] == secret_id:
            secret["read"] = True
            _save_handouts(channel_id, data)
            return True
    
    return False


def clear_player_secrets(channel_id: str, player_id: str):
    """Clear all secrets for a player."""
    data = _load_handouts(channel_id)
    
    if player_id in data.get("player_secrets", {}):
        data["player_secrets"][player_id] = []
        _save_handouts(channel_id, data)


# ============ HANDOUT TYPES ============

HANDOUT_TYPES = {
    "note": {"emoji": "📝", "name": "Note"},
    "letter": {"emoji": "✉️", "name": "Letter"},
    "map": {"emoji": "🗺️", "name": "Map"},
    "image": {"emoji": "🖼️", "name": "Image"},
    "item": {"emoji": "📦", "name": "Item Description"},
    "lore": {"emoji": "📚", "name": "Lore"},
    "clue": {"emoji": "🔍", "name": "Clue"},
    "journal": {"emoji": "📖", "name": "Journal Entry"},
    "wanted": {"emoji": "🎯", "name": "Wanted Poster"},
    "secret": {"emoji": "🤫", "name": "Secret"},
}


def get_handout_emoji(handout_type: str) -> str:
    """Get the emoji for a handout type."""
    return HANDOUT_TYPES.get(handout_type, {}).get("emoji", "📄")


def format_handout_display(handout: Dict[str, Any], show_visibility: bool = False) -> str:
    """Format a handout for display."""
    emoji = get_handout_emoji(handout["type"])
    title = handout["title"]
    content = handout["content"]
    
    output = f"{emoji} **{title}**\n"
    output += f"───────────────────────\n"
    output += f"{content}\n"
    
    if handout.get("image_url"):
        output += f"\n🖼️ *Image attached*"
    
    if show_visibility:
        if handout["visible_to"] is None:
            output += f"\n*Visible to: Everyone*"
        else:
            visible_count = len(handout["visible_to"])
            output += f"\n*Visible to: {visible_count} player(s)*"
    
    return output
