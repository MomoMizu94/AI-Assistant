import json, os

class ConversationManager:
    # Handle everything related to chat history
    def __init__(self, history_path):
        self.history_path = history_path
        self.history = self._load_history()

    def _load_history(self):
        # Load conversation history from the file
        if os.path.exists(self.history_path):
            with open(self.history_path) as f:
                return json.load(f)
        # Default prompt if no history file exists
        else:
            return [
                {"role": "system", "content": "You are a concise and friendly AI assistant that gives answers without emojis."}
            ]

    def save(self):
        with open(self.history_path, "w") as f:
            json.dump(self.history, f)

    def append(self, role, content):
        self.history.append({"role": role, "content": content.strip()})
        self.save()

    def clear(self, keep_system=True):
        if keep_system:
            self.history = self.history[:1]
        else:
            self.history = []
        self.save()

    def get(self):
        return self.history