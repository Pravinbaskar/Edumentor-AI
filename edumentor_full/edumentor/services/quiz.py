"""Quiz service for generating and managing quizzes."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import openai

logger = logging.getLogger("edumentor.quiz")


class QuizGenerator:
    """Generate quizzes based on subject and difficulty."""
    
    def __init__(self):
        self.model = "gpt-4o-mini"
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set - quiz generation will fail")
            self.client = None
        else:
            self.client = openai.OpenAI(api_key=api_key)
    
    def generate_quiz(
        self,
        subject: str,
        topic: str,
        difficulty: str,
        num_questions: int = 5,
        student_profile: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """Generate a quiz with multiple choice questions.
        
        Args:
            subject: Subject area (maths, science, evs)
            topic: Specific topic within the subject
            difficulty: beginner, intermediate, or advanced
            num_questions: Number of questions to generate (default 5)
            student_profile: Student profile information
            
        Returns:
            List of question dictionaries with structure:
            {
                "question": str,
                "options": List[str],  # 4 options
                "correct_answer": int,  # index of correct option (0-3)
                "explanation": str
            }
        """
        profile_context = ""
        if student_profile:
            grade = student_profile.get("grade", "")
            syllabus = student_profile.get("syllabus", "")
            if grade or syllabus:
                profile_context = f" for a {grade} grade student following {syllabus} syllabus"
        
        system_prompt = f"""You are an expert educator creating assessment questions{profile_context}.
Generate {num_questions} multiple choice questions about {topic} in {subject}.
Difficulty level: {difficulty}

IMPORTANT: Return ONLY a valid JSON array, no other text or markdown.

Each question must have:
- A clear question statement
- Exactly 4 options (A, B, C, D)
- The correct answer index (0-3)
- A brief explanation of why the answer is correct

Format as JSON array:
[
  {{
    "question": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": 0,
    "explanation": "Explanation of the correct answer"
  }}
]"""

        try:
            if not self.client:
                raise ValueError("OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.")
            
            user_message = f"Generate {num_questions} quiz questions about {topic} in {subject} at {difficulty} level."
            
            # Log the prompts being sent to LLM
            logger.info("=" * 80)
            logger.info("QUIZ GENERATION LLM PROMPT - System:")
            logger.info(system_prompt)
            logger.info("-" * 80)
            logger.info("QUIZ GENERATION LLM PROMPT - User:")
            logger.info(user_message)
            logger.info("=" * 80)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            
            content = response.choices[0].message.content.strip()
            
            # Log the response
            logger.info("QUIZ GENERATION LLM RESPONSE:")
            logger.info(content)
            logger.info("=" * 80)
            
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            questions = json.loads(content)
            
            # Validate structure
            for q in questions:
                if not all(key in q for key in ["question", "options", "correct_answer", "explanation"]):
                    raise ValueError("Invalid question structure")
                if len(q["options"]) != 4:
                    raise ValueError("Each question must have exactly 4 options")
                if not 0 <= q["correct_answer"] <= 3:
                    raise ValueError("correct_answer must be between 0 and 3")
            
            logger.info(f"Generated {len(questions)} quiz questions for {subject}/{topic}")
            return questions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse quiz JSON: {e}")
            logger.error(f"Response content: {content}")
            raise ValueError("Failed to generate valid quiz questions")
        except Exception as e:
            logger.error(f"Quiz generation failed: {e}")
            raise
