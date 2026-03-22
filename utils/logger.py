import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)


def setup_logging():
    """Configure logging for the bot. Call once at startup."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Avoid adding duplicate handlers if called multiple times
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return

    # File handler (rotating, 5MB max, keep 3 backups)
    fh = RotatingFileHandler(
        os.path.join(LOGS_DIR, 'bot.log'),
        maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8'
    )
    fh.setFormatter(logging.Formatter(
        '%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s'
    ))
    root.addHandler(fh)

    # Console handler (warnings and errors only)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(levelname)-7s | %(name)-20s | %(message)s'))
    ch.setLevel(logging.WARNING)
    root.addHandler(ch)

def get_log_path(session_id):
    return os.path.join(LOGS_DIR, f'{session_id}.md')

def log_message(session_id, speaker, message):
    path = get_log_path(session_id)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(path, 'a', encoding='utf-8') as f:
        f.write(f'[{timestamp}] **{speaker}:** {message}\n\n')

def get_log_file(session_id):
    path = get_log_path(session_id)
    return path if os.path.exists(path) else None
