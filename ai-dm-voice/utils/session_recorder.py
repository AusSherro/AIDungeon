from datetime import datetime

class SessionRecorder:
    """Simple session recorder for replaying games."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.events = []

    def record_event(self, event_type: str, data):
        self.events.append({
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'data': data,
        })

    def export_replay(self):
        return {
            'session_id': self.session_id,
            'events': list(self.events),
        }
