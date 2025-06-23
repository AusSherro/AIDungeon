# Map voice tags to ElevenLabs voice IDs
# Add new voices as needed
VOICE_MAP = {
    'Grumpy Dwarf': 'elevenlabs-voice-id-1',
    'Elven Queen': 'elevenlabs-voice-id-2',
    'Narrator': 'dUercWozs0yhe4xBCgZ0',
    # Add more mappings here
}

def get_voice_id(tag):
    if not tag:
        return VOICE_MAP.get('Narrator')
    return VOICE_MAP.get(tag, VOICE_MAP.get('Narrator'))
