from flask import Flask, request, jsonify, send_file, make_response
from services.openai_service import get_dm_response
from services.elevenlabs_service import text_to_speech
from utils.voice_parser import extract_voice_tag, clean_text
from utils.voice_map import get_voice_id
from utils.state_manager import load_state, save_state
import os
from dotenv import load_dotenv
import tempfile

load_dotenv()

app = Flask(__name__)

@app.route('/dm', methods=['POST'])
def dm():
    data = request.get_json()
    user_input = data.get('input', '')
    session_id = data.get('session_id', 'default')

    # Load session state
    state = load_state(session_id)

    # Get GPT-4o response
    gpt_response, updated_state = get_dm_response(user_input, state)

    # Extract voice tag and clean text
    voice_tag = extract_voice_tag(gpt_response)
    text = clean_text(gpt_response)
    voice_id = get_voice_id(voice_tag)

    # Generate TTS audio
    audio_bytes = text_to_speech(text, voice_id)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    # Save updated state
    save_state(session_id, updated_state)

    # Create response with custom headers
    response = make_response(send_file(tmp_path, mimetype='audio/mpeg', as_attachment=True, download_name='dm_response.mp3'))
    response.headers['X-Text'] = text
    response.headers['X-Voice-Tag'] = voice_tag or 'Narrator'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)