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
    
    # Game Settings
    DEFAULT_VOICE = 'Narrator'
    MAX_COMBAT_ROUNDS = 100
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        required = ['OPENAI_API_KEY', 'ELEVENLABS_API_KEY', 'DISCORD_BOT_TOKEN']
        missing = [key for key in required if not getattr(cls, key)]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

# Validate on import (optional - comment out if you want to handle validation manually)
# Config.validate()
