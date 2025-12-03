import re

def extract_voice_tag(text):
    """Extracts the [Voice: ...] tag from the text."""
    match = re.search(r'\[Voice: ([^\]]+)\]', text)
    return match.group(1).strip() if match else None

def clean_text(text):
    """Removes [Voice: ...] tags and redundant labels like 'Narrator:'."""
    text = re.sub(r'\[Voice: [^\]]+\]\s*', '', text)
    text = re.sub(r'^Narrator:\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    return text.strip()

def clean_for_tts(text):
    """
    Clean text for TTS - removes suggestions, formatting, and keeps only narration.
    """
    # Remove voice tags
    text = re.sub(r'\[Voice: [^\]]+\]\s*', '', text)
    
    # Remove "What will you do?" section and everything after
    text = re.sub(r'💡\s*\*?\*?What will you do\??\*?\*?.*', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'What will you do\?.*', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove numbered suggestions (1. 2. 3. at end)
    text = re.sub(r'\n\d+\.\s+\[?[^\n]+\]?\s*$', '', text, flags=re.MULTILINE)
    
    # Remove markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # Italic
    text = re.sub(r'#{1,3}\s*', '', text)            # Headers
    text = re.sub(r'─+', '', text)                   # Separator lines
    
    # Remove "Narrator:" prefix
    text = re.sub(r'^Narrator:\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Clean up extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    return text
