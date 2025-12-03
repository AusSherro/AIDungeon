import requests
import os
import asyncio
import tempfile
from dotenv import load_dotenv

load_dotenv()
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
TTS_PROVIDER = os.getenv('TTS_PROVIDER', 'elevenlabs').lower()  # 'elevenlabs', 'edge', or 'disabled'

API_URL = 'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'

# Edge TTS voice mapping (free Microsoft voices)
EDGE_VOICE_MAP = {
    'Narrator': 'en-US-GuyNeural',
    'default': 'en-US-GuyNeural',
    'female': 'en-US-JennyNeural',
    'male': 'en-US-GuyNeural',
    'old': 'en-GB-RyanNeural',
    'young': 'en-US-AnaNeural',
}


def text_to_speech(text: str, voice_id: str) -> bytes:
    """
    Generate TTS audio. Uses ElevenLabs by default, falls back to Edge TTS
    if ElevenLabs fails or TTS_PROVIDER is set to 'edge'.
    Returns empty bytes if TTS is disabled.
    """
    if TTS_PROVIDER == 'disabled':
        return b''
    
    if TTS_PROVIDER == 'edge':
        return _edge_tts_sync(text, voice_id)
    
    # Try ElevenLabs first
    try:
        return _elevenlabs_tts(text, voice_id)
    except Exception as e:
        print(f"ElevenLabs TTS failed: {e}, falling back to Edge TTS")
        return _edge_tts_sync(text, voice_id)


def _elevenlabs_tts(text: str, voice_id: str) -> bytes:
    """Generate speech using ElevenLabs API."""
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY not set")
    
    url = API_URL.format(voice_id=voice_id)
    headers = {
        'xi-api-key': ELEVENLABS_API_KEY,
        'Content-Type': 'application/json',
        'Accept': 'audio/mpeg',
    }
    payload = {
        'text': text,
        'voice_settings': {
            'stability': 0.5,
            'similarity_boost': 0.75
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.content


def _edge_tts_sync(text: str, voice_id: str) -> bytes:
    """Generate speech using Edge TTS (free Microsoft voices)."""
    try:
        import edge_tts
    except ImportError:
        print("edge-tts not installed. Run: pip install edge-tts")
        return b''
    
    # Map ElevenLabs voice ID to Edge voice
    edge_voice = EDGE_VOICE_MAP.get(voice_id, EDGE_VOICE_MAP['default'])
    
    # Run async edge_tts in sync context
    return asyncio.get_event_loop().run_until_complete(_edge_tts_async(text, edge_voice))


async def _edge_tts_async(text: str, voice: str) -> bytes:
    """Async Edge TTS generation."""
    try:
        import edge_tts
    except ImportError:
        return b''
    
    communicate = edge_tts.Communicate(text, voice)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
        tmp_path = tmp.name
    
    await communicate.save(tmp_path)
    
    with open(tmp_path, 'rb') as f:
        audio_bytes = f.read()
    
    os.unlink(tmp_path)
    return audio_bytes


async def text_to_speech_async(text: str, voice_id: str) -> bytes:
    """
    Async version for Discord bot usage.
    """
    if TTS_PROVIDER == 'disabled':
        return b''
    
    if TTS_PROVIDER == 'edge':
        edge_voice = EDGE_VOICE_MAP.get(voice_id, EDGE_VOICE_MAP['default'])
        return await _edge_tts_async(text, edge_voice)
    
    # Try ElevenLabs first (run in executor since it's sync)
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(None, _elevenlabs_tts, text, voice_id)
    except Exception as e:
        print(f"ElevenLabs TTS failed: {e}, falling back to Edge TTS")
        edge_voice = EDGE_VOICE_MAP.get(voice_id, EDGE_VOICE_MAP['default'])
        return await _edge_tts_async(text, edge_voice)
