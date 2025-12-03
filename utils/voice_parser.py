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
