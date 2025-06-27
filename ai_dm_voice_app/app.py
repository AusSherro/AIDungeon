from flask import Flask, request, jsonify, send_file, make_response
from services.openai_service import get_dm_response, generate_text
from services.elevenlabs_service import text_to_speech
from utils.voice_parser import extract_voice_tag, clean_text
from utils.voice_map import get_voice_id
from utils.state_manager import load_state, save_state
from services.story_manager import StoryManager
from services.context_manager import ContextManager
import os
from dotenv import load_dotenv
import tempfile
from config import Config

load_dotenv()
Config.validate()

app = Flask(__name__)

# Managers for new storytelling API
story_manager = StoryManager()
context_manager = ContextManager()

# Register web portal blueprint
try:
    from webportal.routes import portal_bp
    app.register_blueprint(portal_bp, url_prefix='/portal')
except Exception as e:
    print(f"Failed to register portal blueprint: {e}")

@app.route('/dm', methods=['POST'])
def dm():
    data = request.get_json()
    user_input = data.get('input', '')
    session_id = data.get('session_id', 'default')

    # Load session state
    state = load_state(session_id)

    # Get GPT-4o response
    gpt_response, updated_state = get_dm_response(user_input, state, None)

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


# --- New Storytelling API ---

@app.route('/api/story/start', methods=['POST'])
def start_story():
    data = request.json or {}
    story_id = data.get('story_id')
    genre = data.get('genre', 'fantasy')
    prompt = data.get('prompt', '')
    if not story_id or not prompt:
        return jsonify({'error': 'story_id and prompt required'}), 400

    story_manager.create_story(story_id, genre, prompt)
    ai_text = generate_text(prompt, action_type='story', genre=genre)
    story_manager.add_turn(story_id, 'story', prompt, ai_text)
    return jsonify({'story_id': story_id, 'text': ai_text})


@app.route('/api/story/continue', methods=['POST'])
def continue_story():
    data = request.json or {}
    story_id = data.get('story_id')
    prompt = data.get('prompt', '')
    action_type = data.get('action_type', 'continue')
    if not story_id or not prompt:
        return jsonify({'error': 'story_id and prompt required'}), 400

    story = story_manager.stories.get(story_id)
    if not story:
        return jsonify({'error': 'Story not found'}), 404
    context = context_manager.build_context(story['turns'])
    ai_text = generate_text(prompt, action_type=action_type, story_context=context, genre=story.get('genre'))
    story_manager.add_turn(story_id, action_type, prompt, ai_text)
    return jsonify({'story_id': story_id, 'text': ai_text})


@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json or {}
    prompt = data.get('prompt', '')
    action_type = data.get('action_type', 'continue')
    story_context = data.get('context', '')
    genre = data.get('genre', 'fantasy')
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    try:
        generated_text = generate_text(prompt, action_type, story_context, genre)
        return jsonify({'text': generated_text})
    except Exception as e:
        app.logger.error(f'Error generating text: {str(e)}')
        return jsonify({'error': 'Failed to generate text'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)