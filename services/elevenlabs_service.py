import requests
import os
from dotenv import load_dotenv

load_dotenv()
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')

API_URL = 'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'


def text_to_speech(text, voice_id):
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
