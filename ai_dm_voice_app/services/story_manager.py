from datetime import datetime

class StoryManager:
    """Manage multiple interactive stories."""

    def __init__(self):
        self.stories = {}

    def create_story(self, story_id, genre, initial_prompt):
        """Create a new story with metadata and initial context."""
        self.stories[story_id] = {
            "genre": genre,
            "created_at": datetime.utcnow().isoformat(),
            "context": initial_prompt,
            "turns": [],
            "metadata": {
                "characters": [],
                "locations": [],
                "items": [],
            },
        }
        return self.stories[story_id]

    def add_turn(self, story_id, action_type, user_input, ai_response):
        story = self.stories.get(story_id)
        if not story:
            raise ValueError("Story not found")
        story["turns"].append(
            {
                "action_type": action_type,
                "user_input": user_input,
                "ai_response": ai_response,
            }
        )

    def get_context(self, story_id, max_turns=10):
        story = self.stories.get(story_id)
        if not story:
            return ""
        turns = story["turns"][-max_turns:]
        lines = []
        for t in turns:
            if t["action_type"] == "say":
                prefix = "Player says"
            elif t["action_type"] == "do":
                prefix = "Player attempts"
            else:
                prefix = "Player"
            lines.append(f"{prefix}: {t['user_input']}")
            lines.append(f"DM: {t['ai_response']}")
        return "\n".join(lines)
