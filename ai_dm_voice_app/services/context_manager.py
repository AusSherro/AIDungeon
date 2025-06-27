class ContextManager:
    """Build conversation context from recent turns."""

    def __init__(self, max_turns=20, max_tokens=2000):
        self.max_turns = max_turns
        self.max_tokens = max_tokens

    def build_context(self, turns):
        selected = turns[-self.max_turns:]
        context_lines = []
        token_count = 0
        for turn in reversed(selected):
            lines = [
                f"Player ({turn.get('action_type','')}): {turn.get('user_input','')}",
                f"DM: {turn.get('ai_response','')}"
            ]
            tokens = sum(len(l.split()) for l in lines)
            if token_count + tokens > self.max_tokens:
                break
            context_lines = lines + context_lines
            token_count += tokens
        return "\n".join(context_lines)

    def summarize(self, turns):
        """Placeholder for summarizing characters, locations, and events."""
        return {
            "characters": [],
            "locations": [],
            "items": [],
        }
