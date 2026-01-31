import json
import os
from datetime import datetime
import uuid

HISTORY_FILE = "quiz_history.json"

class QuizHistory:
    def __init__(self):
        self.file_path = HISTORY_FILE
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump([], f)

    def load_history(self):
        """Loads all past quizzes."""
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def save_quiz(self, topic, quiz_data, score, max_score):
        """Saves a completed quiz to history."""
        history = self.load_history()
        
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "topic": topic,
            "score": score,
            "max_score": max_score,
            "questions": quiz_data,
            # We don't save user_answers for simplicity in replay (start fresh), 
            # or we could if we wanted to show 'Past Attempt'.
            # For now, let's keep it simple: Replay means re-attempting the questions.
        }
        
        # Prepend to list (newest first)
        history.insert(0, entry)
        
        with open(self.file_path, 'w') as f:
            json.dump(history, f, indent=2)
            
        return entry["id"]

    def get_quiz(self, quiz_id):
        """Retrieves a specific quiz by ID."""
        history = self.load_history()
        for q in history:
            if q["id"] == quiz_id:
                return q
        return None
