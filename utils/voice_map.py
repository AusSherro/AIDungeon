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

# =============================================================================
# NPC VOICE ARCHETYPES
# Maps character descriptions/types to specific voices for variety
# =============================================================================

NPC_VOICE_ARCHETYPES = {
    # Gender-based defaults
    'male': ['Adam', 'Josh', 'Antoni', 'Arnold'],
    'female': ['Rachel', 'Bella', 'Domi', 'Elli'],
    
    # Race-based voices
    'dwarf': ['Arnold', 'Adam'],  # Gruff, deep voices
    'elf': ['Elli', 'Bella'],  # Elegant, smooth voices
    'halfling': ['Rachel', 'Josh'],  # Friendly, light voices
    'orc': ['Arnold', 'Adam'],  # Gruff, intimidating
    'goblin': ['Josh', 'Antoni'],  # Scratchy, quick
    'dragonborn': ['Arnold', 'Adam'],  # Deep, powerful
    
    # Role-based voices
    'wizard': ['Antoni', 'Elli'],  # Mysterious, learned
    'warrior': ['Arnold', 'Adam'],  # Strong, commanding
    'rogue': ['Josh', 'Domi'],  # Quick, sly
    'merchant': ['Rachel', 'Josh'],  # Friendly, persuasive
    'innkeeper': ['Adam', 'Rachel'],  # Warm, welcoming
    'noble': ['Antoni', 'Bella'],  # Refined, proper
    'peasant': ['Josh', 'Rachel'],  # Simple, humble
    'guard': ['Arnold', 'Adam'],  # Stern, authoritative
    'priest': ['Antoni', 'Elli'],  # Solemn, wise
    'bard': ['Josh', 'Bella'],  # Musical, charismatic
    
    # Personality-based voices
    'mysterious': ['Antoni', 'Domi'],
    'friendly': ['Rachel', 'Josh'],
    'gruff': ['Arnold', 'Adam'],
    'sinister': ['Arnold', 'Antoni'],
    'elderly': ['Adam', 'Elli'],
    'young': ['Josh', 'Rachel'],
    'wise': ['Antoni', 'Elli'],
    'scared': ['Rachel', 'Josh'],
    'angry': ['Arnold', 'Adam'],
    
    # Monster voices
    'dragon': ['Arnold'],
    'demon': ['Arnold', 'Adam'],
    'undead': ['Antoni', 'Arnold'],
    'giant': ['Arnold'],
    'fairy': ['Elli', 'Rachel'],
}

# Edge TTS voice mapping for NPC types (free alternative)
NPC_EDGE_VOICES = {
    'male': 'en-US-GuyNeural',
    'female': 'en-US-JennyNeural',
    'dwarf': 'en-GB-RyanNeural',  # British gruff
    'elf': 'en-US-AriaNeural',  # Elegant
    'wizard': 'en-GB-RyanNeural',
    'warrior': 'en-US-DavisNeural',
    'merchant': 'en-US-JasonNeural',
    'noble': 'en-GB-SoniaNeural',
    'elderly': 'en-GB-RyanNeural',
    'young': 'en-US-AnaNeural',
    'dragon': 'en-US-DavisNeural',
    'narrator': 'en-US-GuyNeural',
}


def get_voice_id(tag: str):
    """Return the ElevenLabs voice ID for a tag."""
    if not VOICE_MAP:
        VOICE_MAP.update(_load_voice_map())
    if not tag:
        tag = Config.DEFAULT_VOICE
    return VOICE_MAP.get(tag, VOICE_MAP.get(Config.DEFAULT_VOICE, ''))


def get_voice_for_npc(npc_description: str, npc_name: str = None) -> str:
    """
    Determine the best voice for an NPC based on their description.
    
    Args:
        npc_description: Description of the NPC (e.g., "old dwarf merchant")
        npc_name: Optional NPC name for consistent voice assignment
        
    Returns:
        Voice tag/ID to use
    """
    import random
    
    description_lower = npc_description.lower() if npc_description else ""
    
    # Check for matching archetypes
    matched_voices = []
    
    for archetype, voices in NPC_VOICE_ARCHETYPES.items():
        if archetype in description_lower:
            matched_voices.extend(voices)
    
    # If NPC name provided, use it for consistent voice selection
    if npc_name and matched_voices:
        # Use name hash for consistent selection
        name_hash = hash(npc_name.lower())
        return matched_voices[name_hash % len(matched_voices)]
    
    # Return a matched voice or default
    if matched_voices:
        return random.choice(matched_voices)
    
    # Default based on gender keywords
    if any(word in description_lower for word in ['she', 'her', 'woman', 'lady', 'girl', 'female', 'queen', 'princess', 'witch']):
        return random.choice(NPC_VOICE_ARCHETYPES['female'])
    elif any(word in description_lower for word in ['he', 'him', 'man', 'lord', 'boy', 'king', 'prince']):
        return random.choice(NPC_VOICE_ARCHETYPES['male'])
    
    # Fallback to narrator
    return 'Narrator'


def get_edge_voice_for_npc(npc_description: str) -> str:
    """
    Get Edge TTS voice for an NPC (free alternative).
    
    Args:
        npc_description: Description of the NPC
        
    Returns:
        Edge TTS voice name
    """
    description_lower = npc_description.lower() if npc_description else ""
    
    for archetype, voice in NPC_EDGE_VOICES.items():
        if archetype in description_lower:
            return voice
    
    # Gender detection
    if any(word in description_lower for word in ['she', 'her', 'woman', 'lady', 'girl', 'female']):
        return NPC_EDGE_VOICES['female']
    elif any(word in description_lower for word in ['he', 'him', 'man', 'lord', 'boy']):
        return NPC_EDGE_VOICES['male']
    
    return NPC_EDGE_VOICES['narrator']


def set_voice_profile(tag: str, voice_id: str):
    """Add or update a voice profile."""
    VOICE_MAP[tag] = voice_id
    _save_voice_map(VOICE_MAP)


def list_voice_profiles():
    return dict(VOICE_MAP)


def extract_npc_from_tag(voice_tag: str) -> tuple:
    """
    Extract NPC name and description from a voice tag.
    
    Voice tags can be formatted as:
    - "Narrator" (simple tag)
    - "Grizzled Dwarf Merchant" (description)
    - "Thorin:gruff dwarf" (name:description)
    
    Returns:
        Tuple of (npc_name, npc_description)
    """
    if not voice_tag:
        return (None, None)
    
    # Check for name:description format
    if ':' in voice_tag:
        parts = voice_tag.split(':', 1)
        return (parts[0].strip(), parts[1].strip())
    
    # Simple tag or just description
    return (None, voice_tag)
