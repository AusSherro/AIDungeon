from flask import Flask, request, jsonify, send_file, make_response, redirect
from services.openai_service import get_dm_response
from services.elevenlabs_service import text_to_speech
from utils.voice_parser import extract_voice_tag, clean_text
from utils.voice_map import get_voice_id
from utils.state_manager import load_state, save_state
from openai import OpenAIError
import os
from dotenv import load_dotenv
import tempfile
from config import Config

load_dotenv()
Config.validate()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'ai-dm-secret-key-change-in-production')

# Register web portal blueprint
try:
    from webportal.routes import portal_bp
    app.register_blueprint(portal_bp, url_prefix='/portal')
except Exception as e:
    print(f"Failed to register portal blueprint: {e}")


@app.route('/')
def index():
    """Redirect root to the web portal."""
    return redirect('/portal/')


@app.route('/favicon.ico')
def favicon():
    """Return empty response for favicon to prevent 404 spam."""
    return '', 204

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
    except OpenAIError as e:
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


@app.route('/api/generate', methods=['POST'])
def api_generate():
    """
    Generate AI text response without TTS.
    
    Accepts JSON payload with:
    - prompt: the player's input or narration seed
    - action_type: how to treat the prompt (do, say, story, continue)
    - genre (optional): e.g. sci-fi, horror, fantasy
    - context (optional): array of prior messages for additional history
    """
    data = request.get_json(silent=True) or {}
    
    prompt = data.get('prompt')
    action_type = data.get('action_type', 'do')
    genre = data.get('genre', 'fantasy')
    context = data.get('context', [])
    
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({'error': 'Missing or malformed prompt'}), 400
    
    # Build action prefix based on action_type
    action_prefixes = {
        'do': 'You ',
        'say': 'You say: ',
        'story': '',
        'continue': 'Continue the story: '
    }
    prefix = action_prefixes.get(action_type, '')
    formatted_prompt = f"{prefix}{prompt}"
    
    # Build state with context
    state = {
        'prompt_history': [{"role": "user", "content": msg} for msg in context] if context else [],
        'genre': genre
    }
    
    # Build a genre-aware system prompt
    system_prompt = (
        f"You are a Dungeon Master AI running a {genre} adventure. "
        "Respond to player actions with immersive narration and character dialogue. "
        "Label all character speech with [Voice: Character Name] tags. "
        "Narration should be labeled [Voice: Narrator] or left untagged. "
        "Keep track of the story, locations, and NPCs."
    )
    
    try:
        gpt_response, updated_state = get_dm_response(formatted_prompt, state, None, system_prompt)
    except OpenAIError as e:
        return jsonify({'error': f'OpenAI API error: {e}'}), 500
    
    # Clean the response text
    text = clean_text(gpt_response)
    
    return jsonify({
        'text': text,
        'raw': gpt_response,
        'action_type': action_type,
        'genre': genre
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)