from __future__ import annotations

from typing import List, Dict


def get_quiz_questions(topic: str, difficulty: str = "easy") -> List[Dict]:
    """Return a small, hard-coded quiz for demo purposes."""
    topic_lower = topic.lower()
    if "fraction" in topic_lower:
        return [
            {
                "question": "What is 1/2 + 1/3?",
                "options": ["2/5", "5/6", "1/6", "3/5"],
                "answer": "5/6",
            },
            {
                "question": "What is 3/4 - 1/8?",
                "options": ["1/8", "5/8", "3/8", "7/8"],
                "answer": "5/8",
            },
        ]
    return []
