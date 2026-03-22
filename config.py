import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    DEV_GUILD_ID = os.getenv('DEV_GUILD_ID')
    
    # Directories
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    STATE_DIR = os.path.join(BASE_DIR, 'state')
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')
    CHARACTERS_DIR = os.path.join(BASE_DIR, 'characters')
    COMBAT_DIR = os.path.join(BASE_DIR, 'combat')
    
    # Ensure directories exist
    for dir_path in [STATE_DIR, LOGS_DIR, CHARACTERS_DIR, COMBAT_DIR]:
        os.makedirs(dir_path, exist_ok=True)
    
    # Bot Settings
    COMMAND_PREFIX = '!'
    MAX_MESSAGE_LENGTH = 2000
    
    # === Game Settings ===
    MAX_PROMPT_HISTORY = 20          # Rolling window of conversation exchanges
    DEFAULT_DIFFICULTY = "normal"
    DEFAULT_VOICE = 'Narrator'
    
    # === Combat Settings ===
    COMBAT_TURN_TIMEOUT = 90         # Seconds before auto-advance
    COMBAT_TURN_WARNING = 30         # Seconds before timeout to send warning
    MAX_COMBAT_ROUNDS = 100

    # === Session Settings ===
    AUTO_SAVE_INTERVAL = 300         # Seconds between auto-saves
    INACTIVITY_TIMEOUT = 1800        # Seconds before session auto-pause
    SKILL_CHECK_TIMEOUT = 60         # Seconds to respond to skill check

    # === AI Settings ===
    AI_MODEL = "gpt-4o"
    AI_MAX_TOKENS = 500
    AI_TEMPERATURE = 0.9

    # === TTS Settings ===
    TTS_ENABLED = os.environ.get("TTS_ENABLED", "true").lower() == "true"

    # === NPC Settings ===
    MAX_NPC_MEMORY_FACTS = 50        # Cap on NPC knows_facts list
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        required = ['OPENAI_API_KEY', 'ELEVENLABS_API_KEY', 'DISCORD_BOT_TOKEN']
        missing = [key for key in required if not getattr(cls, key)]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

# Validate on import (optional - comment out if you want to handle validation manually)
# Config.validate()
