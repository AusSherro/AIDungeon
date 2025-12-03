"""
Database Manager - SQLite backend for persistent data storage

This module provides a SQLite-based storage layer that can be used
alongside or instead of JSON file storage for better querying,
reliability, and performance with large datasets.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from threading import Lock
from contextlib import contextmanager

DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DB_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, 'aidm.db')

_db_lock = Lock()


# ============ DATABASE CONNECTION ============

@contextmanager
def get_db():
    """Get a database connection with automatic cleanup."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """Initialize the database schema."""
    with _db_lock:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Characters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    user_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    char_class TEXT DEFAULT 'Fighter',
                    race TEXT DEFAULT 'Human',
                    level INTEGER DEFAULT 1,
                    hp INTEGER DEFAULT 10,
                    max_hp INTEGER DEFAULT 10,
                    temp_hp INTEGER DEFAULT 0,
                    proficiency INTEGER DEFAULT 2,
                    data TEXT,  -- JSON for complex nested data
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Campaign state table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS campaigns (
                    channel_id TEXT PRIMARY KEY,
                    title TEXT,
                    realm TEXT,
                    location TEXT,
                    summary TEXT,
                    data TEXT,  -- JSON for full state
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # NPCs table (normalized from campaign state)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS npcs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'alive',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(channel_id, name)
                )
            ''')
            
            # Quests table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(channel_id, name)
                )
            ''')
            
            # Key events log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    event_text TEXT NOT NULL,
                    event_type TEXT DEFAULT 'story',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Combat encounters
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS combat (
                    channel_id TEXT PRIMARY KEY,
                    round INTEGER DEFAULT 1,
                    current_turn INTEGER DEFAULT 0,
                    data TEXT,  -- JSON for full combat state
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Handouts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS handouts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    handout_type TEXT DEFAULT 'note',
                    image_url TEXT,
                    visible_to TEXT,  -- JSON array of player IDs or NULL for all
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Player secrets
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS secrets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    title TEXT,
                    content TEXT NOT NULL,
                    is_read INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tactical maps
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS maps (
                    channel_id TEXT PRIMARY KEY,
                    name TEXT DEFAULT 'Battle Map',
                    width INTEGER DEFAULT 20,
                    height INTEGER DEFAULT 15,
                    data TEXT,  -- JSON for grid and tokens
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Session logs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS session_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    speaker TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Indexes for common queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_npcs_channel ON npcs(channel_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_quests_channel ON quests(channel_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_channel ON events(channel_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_handouts_channel ON handouts(channel_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_secrets_player ON secrets(channel_id, player_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_channel ON session_logs(channel_id)')


# ============ CHARACTER OPERATIONS ============

def db_save_character(user_id: str, char_data: dict):
    """Save or update a character."""
    with _db_lock:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO characters 
                (user_id, name, char_class, race, level, hp, max_hp, temp_hp, proficiency, data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                char_data.get('name', 'Unknown'),
                char_data.get('char_class', 'Fighter'),
                char_data.get('race', 'Human'),
                char_data.get('level', 1),
                char_data.get('hp', 10),
                char_data.get('max_hp', 10),
                char_data.get('temp_hp', 0),
                char_data.get('proficiency', 2),
                json.dumps(char_data),
                datetime.now().isoformat()
            ))


def db_load_character(user_id: str) -> Optional[dict]:
    """Load a character by user ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM characters WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if row:
            return json.loads(row['data'])
        return None


def db_get_all_characters() -> List[dict]:
    """Get all characters."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, name, char_class, race, level, hp, max_hp FROM characters')
        
        return [dict(row) for row in cursor.fetchall()]


def db_delete_character(user_id: str) -> bool:
    """Delete a character."""
    with _db_lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM characters WHERE user_id = ?', (user_id,))
            return cursor.rowcount > 0


# ============ CAMPAIGN OPERATIONS ============

def db_save_campaign(channel_id: str, state: dict):
    """Save or update campaign state."""
    with _db_lock:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO campaigns
                (channel_id, title, realm, location, summary, data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                channel_id,
                state.get('campaign_title', ''),
                state.get('realm', ''),
                state.get('location', ''),
                state.get('campaign_summary', ''),
                json.dumps(state),
                datetime.now().isoformat()
            ))


def db_load_campaign(channel_id: str) -> Optional[dict]:
    """Load campaign state."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM campaigns WHERE channel_id = ?', (channel_id,))
        row = cursor.fetchone()
        
        if row:
            return json.loads(row['data'])
        return None


def db_get_all_campaigns() -> List[dict]:
    """Get all campaigns (summary only)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT channel_id, title, realm, location, created_at, updated_at 
            FROM campaigns 
            WHERE title IS NOT NULL AND title != ''
        ''')
        
        return [dict(row) for row in cursor.fetchall()]


# ============ NPC OPERATIONS ============

def db_add_npc(channel_id: str, name: str, description: str = "", status: str = "alive"):
    """Add or update an NPC."""
    with _db_lock:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO npcs (channel_id, name, description, status)
                VALUES (?, ?, ?, ?)
            ''', (channel_id, name, description, status))


def db_get_npcs(channel_id: str) -> List[dict]:
    """Get all NPCs for a campaign."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT name, description, status FROM npcs WHERE channel_id = ?',
            (channel_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def db_update_npc_status(channel_id: str, name: str, status: str) -> bool:
    """Update NPC status."""
    with _db_lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE npcs SET status = ? WHERE channel_id = ? AND name = ?',
                (status, channel_id, name)
            )
            return cursor.rowcount > 0


# ============ QUEST OPERATIONS ============

def db_add_quest(channel_id: str, name: str, description: str = "", status: str = "active"):
    """Add a quest."""
    with _db_lock:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO quests (channel_id, name, description, status, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (channel_id, name, description, status, datetime.now().isoformat()))


def db_get_quests(channel_id: str, status: Optional[str] = None) -> List[dict]:
    """Get quests for a campaign, optionally filtered by status."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        if status:
            cursor.execute(
                'SELECT name, description, status FROM quests WHERE channel_id = ? AND status = ?',
                (channel_id, status)
            )
        else:
            cursor.execute(
                'SELECT name, description, status FROM quests WHERE channel_id = ?',
                (channel_id,)
            )
        
        return [dict(row) for row in cursor.fetchall()]


def db_update_quest_status(channel_id: str, name: str, status: str) -> bool:
    """Update quest status (active, completed, failed)."""
    with _db_lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE quests SET status = ?, updated_at = ? WHERE channel_id = ? AND name = ?',
                (status, datetime.now().isoformat(), channel_id, name)
            )
            return cursor.rowcount > 0


# ============ EVENT LOG OPERATIONS ============

def db_add_event(channel_id: str, event_text: str, event_type: str = "story"):
    """Log a key event."""
    with _db_lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO events (channel_id, event_text, event_type) VALUES (?, ?, ?)',
                (channel_id, event_text, event_type)
            )


def db_get_events(channel_id: str, limit: int = 20) -> List[dict]:
    """Get recent events for a campaign."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT event_text, event_type, created_at FROM events WHERE channel_id = ? ORDER BY created_at DESC LIMIT ?',
            (channel_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]


# ============ HANDOUT OPERATIONS ============

def db_create_handout(
    channel_id: str,
    title: str,
    content: str,
    handout_type: str = "note",
    image_url: Optional[str] = None,
    visible_to: Optional[List[str]] = None,
    created_by: Optional[str] = None
) -> int:
    """Create a handout and return its ID."""
    with _db_lock:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO handouts (channel_id, title, content, handout_type, image_url, visible_to, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                channel_id,
                title,
                content,
                handout_type,
                image_url,
                json.dumps(visible_to) if visible_to else None,
                created_by
            ))
            
            return cursor.lastrowid


def db_get_handouts(channel_id: str, player_id: Optional[str] = None) -> List[dict]:
    """Get handouts for a channel, optionally filtered by player visibility."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, title, content, handout_type, image_url, visible_to, created_by, created_at FROM handouts WHERE channel_id = ?',
            (channel_id,)
        )
        
        handouts = []
        for row in cursor.fetchall():
            handout = dict(row)
            visible_to = json.loads(handout['visible_to']) if handout['visible_to'] else None
            handout['visible_to'] = visible_to
            
            # Filter by player if specified
            if player_id:
                if visible_to is None or player_id in visible_to:
                    handouts.append(handout)
            else:
                handouts.append(handout)
        
        return handouts


def db_reveal_handout(channel_id: str, handout_id: int) -> bool:
    """Reveal a handout to all players."""
    with _db_lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE handouts SET visible_to = NULL WHERE id = ? AND channel_id = ?',
                (handout_id, channel_id)
            )
            return cursor.rowcount > 0


# ============ SECRET OPERATIONS ============

def db_add_secret(channel_id: str, player_id: str, content: str, title: Optional[str] = None) -> int:
    """Add a secret for a player."""
    with _db_lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO secrets (channel_id, player_id, title, content) VALUES (?, ?, ?, ?)',
                (channel_id, player_id, title, content)
            )
            return cursor.lastrowid


def db_get_secrets(channel_id: str, player_id: str, unread_only: bool = False) -> List[dict]:
    """Get secrets for a player."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        if unread_only:
            cursor.execute(
                'SELECT id, title, content, is_read, created_at FROM secrets WHERE channel_id = ? AND player_id = ? AND is_read = 0',
                (channel_id, player_id)
            )
        else:
            cursor.execute(
                'SELECT id, title, content, is_read, created_at FROM secrets WHERE channel_id = ? AND player_id = ?',
                (channel_id, player_id)
            )
        
        return [dict(row) for row in cursor.fetchall()]


def db_mark_secret_read(secret_id: int) -> bool:
    """Mark a secret as read."""
    with _db_lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE secrets SET is_read = 1 WHERE id = ?', (secret_id,))
            return cursor.rowcount > 0


# ============ SESSION LOG OPERATIONS ============

def db_log_message(channel_id: str, speaker: str, message: str):
    """Log a message to the session log."""
    with _db_lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO session_logs (channel_id, speaker, message) VALUES (?, ?, ?)',
                (channel_id, speaker, message)
            )


def db_get_session_log(channel_id: str, limit: int = 100) -> List[dict]:
    """Get recent session log entries."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT speaker, message, created_at FROM session_logs WHERE channel_id = ? ORDER BY created_at DESC LIMIT ?',
            (channel_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]


def db_export_session_log(channel_id: str) -> str:
    """Export session log as markdown."""
    logs = db_get_session_log(channel_id, limit=1000)
    logs.reverse()  # Oldest first
    
    lines = [f"# Session Log\n"]
    current_date = None
    
    for log in logs:
        timestamp = log['created_at']
        date = timestamp.split('T')[0] if 'T' in timestamp else timestamp.split(' ')[0]
        
        if date != current_date:
            lines.append(f"\n## {date}\n")
            current_date = date
        
        lines.append(f"**{log['speaker']}:** {log['message']}\n")
    
    return "\n".join(lines)


# ============ MIGRATION UTILITIES ============

def migrate_json_to_db():
    """
    Migrate existing JSON files to SQLite database.
    This is a one-time operation to import existing data.
    """
    import glob
    
    # Migrate characters
    chars_dir = os.path.join(os.path.dirname(__file__), '..', 'characters')
    if os.path.exists(chars_dir):
        for filepath in glob.glob(os.path.join(chars_dir, '*.json')):
            try:
                user_id = os.path.basename(filepath).replace('.json', '')
                with open(filepath, 'r', encoding='utf-8') as f:
                    char_data = json.load(f)
                    db_save_character(user_id, char_data)
                    print(f"Migrated character: {user_id}")
            except Exception as e:
                print(f"Failed to migrate {filepath}: {e}")
    
    # Migrate campaigns
    state_dir = os.path.join(os.path.dirname(__file__), '..', 'state')
    if os.path.exists(state_dir):
        for filepath in glob.glob(os.path.join(state_dir, '*.json')):
            try:
                channel_id = os.path.basename(filepath).replace('.json', '')
                with open(filepath, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    db_save_campaign(channel_id, state)
                    
                    # Also migrate NPCs and quests
                    for npc in state.get('key_npcs', []):
                        db_add_npc(channel_id, npc['name'], npc.get('description', ''), npc.get('status', 'alive'))
                    
                    for quest in state.get('quests', []):
                        db_add_quest(channel_id, quest['name'], quest.get('description', ''), quest.get('status', 'active'))
                    
                    for event in state.get('key_events', []):
                        db_add_event(channel_id, event)
                    
                    print(f"Migrated campaign: {channel_id}")
            except Exception as e:
                print(f"Failed to migrate {filepath}: {e}")
    
    print("Migration complete!")


# Initialize database on import
init_database()
