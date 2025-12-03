import os
from datetime import datetime

LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

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
