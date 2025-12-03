from flask import Flask, request, jsonify, send_file, make_response
from services.openai_service import get_dm_response
from services.elevenlabs_service import text_to_speech
from utils.voice_parser import extract_voice_tag, clean_text
from utils.voice_map import get_voice_id
from utils.state_manager import load_state, save_state
import openai
import os
from dotenv import load_dotenv
import tempfile
from config import Config

load_dotenv()
Config.validate()

app = Flask(__name__)

# Register web portal blueprint
try:
    from webportal.routes import portal_bp
    app.register_blueprint(portal_bp, url_prefix='/portal')
except Exception as e:
    print(f"Failed to register portal blueprint: {e}")

@app.route('/dm', methods=['POST'])
def dm():
    data = request.get_json(silent=True) or {}

    story_id = data.get('story_id')
    prompt = data.get('prompt')

    if not isinstance(story_id, str) or not story_id.strip():
        return jsonify({'error': 'Missing or malformed story_id'}), 400
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({'error': 'Missing or malformed prompt'}), 400

    user_input = prompt
    session_id = story_id

    # Load session state
    state = load_state(session_id)

    # Get GPT-4o response
    try:
        gpt_response, updated_state = get_dm_response(user_input, state, None)
    except openai.error.OpenAIError as e:
        return jsonify({'error': f'OpenAI API error: {e}'}), 500

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