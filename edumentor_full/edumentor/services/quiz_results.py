"""SQLite database for storing quiz results."""

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("edumentor.quiz_results")


class QuizResultsDB:
    """Manage quiz results in SQLite database."""
    
    def __init__(self, db_path: str = "data/quiz_results.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                total_questions INTEGER NOT NULL,
                correct_answers INTEGER NOT NULL,
                score_percentage REAL NOT NULL,
                questions_data TEXT NOT NULL,
                user_answers TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                time_taken_seconds INTEGER
            )
        """)
        
        # Migration: Add topic column if it doesn't exist (for existing databases)
        cursor.execute("PRAGMA table_info(quiz_results)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'topic' not in columns:
            logger.info("Adding topic column to quiz_results table")
            cursor.execute("ALTER TABLE quiz_results ADD COLUMN topic TEXT DEFAULT ''")
            logger.info("Successfully added topic column to existing database")
        
        # Create indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quiz_user_timestamp 
            ON quiz_results(user_id, timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quiz_subject 
            ON quiz_results(subject)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Quiz results database initialized at {self.db_path}")
    
    def save_result(
        self,
        user_id: str,
        subject: str,
        topic: str,
        difficulty: str,
        questions: List[Dict[str, Any]],
        user_answers: List[int],
        time_taken_seconds: int | None = None
    ) -> int:
        """Save quiz result to database.
        
        Args:
            user_id: User identifier
            subject: Subject area
            topic: Quiz topic
            difficulty: Difficulty level
            questions: List of question dictionaries
            user_answers: List of user's answer indices
            time_taken_seconds: Time taken to complete quiz
            
        Returns:
            ID of the saved record
        """
        total_questions = len(questions)
        correct_answers = sum(
            1 for i, q in enumerate(questions)
            if i < len(user_answers) and user_answers[i] == q["correct_answer"]
        )
        score_percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO quiz_results (
                user_id, subject, topic, difficulty, total_questions,
                correct_answers, score_percentage, questions_data, user_answers,
                time_taken_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            subject,
            topic,
            difficulty,
            total_questions,
            correct_answers,
            score_percentage,
            json.dumps(questions),
            json.dumps(user_answers),
            time_taken_seconds
        ))
        
        result_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Saved quiz result {result_id} for user {user_id}: {correct_answers}/{total_questions}")
        return result_id
    
    def get_user_results(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get quiz results for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of results to return
            
        Returns:
            List of result dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, user_id, subject, topic, difficulty,
                total_questions, correct_answers, score_percentage,
                timestamp, time_taken_seconds
            FROM quiz_results
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_result_details(self, result_id: int) -> Dict[str, Any] | None:
        """Get detailed quiz result including questions and answers.
        
        Args:
            result_id: Result record ID
            
        Returns:
            Complete result dictionary or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM quiz_results WHERE id = ?
        """, (result_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        result = dict(row)
        result["questions"] = json.loads(result["questions_data"])
        result["user_answers"] = json.loads(result["user_answers"])
        del result["questions_data"]  # Remove raw JSON
        
        return result
    
    def get_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get quiz statistics for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Statistics dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_quizzes,
                AVG(score_percentage) as avg_score,
                MAX(score_percentage) as best_score,
                SUM(total_questions) as total_questions_answered,
                SUM(correct_answers) as total_correct
            FROM quiz_results
            WHERE user_id = ?
        """, (user_id,))
        
        overall = cursor.fetchone()
        
        # Stats by subject
        cursor.execute("""
            SELECT 
                subject,
                COUNT(*) as quiz_count,
                AVG(score_percentage) as avg_score
            FROM quiz_results
            WHERE user_id = ?
            GROUP BY subject
        """, (user_id,))
        
        by_subject = cursor.fetchall()
        
        conn.close()
        
        return {
            "total_quizzes": overall[0] or 0,
            "average_score": round(overall[1] or 0, 2),
            "best_score": round(overall[2] or 0, 2),
            "total_questions_answered": overall[3] or 0,
            "total_correct": overall[4] or 0,
            "by_subject": [
                {
                    "subject": row[0],
                    "quiz_count": row[1],
                    "avg_score": round(row[2], 2)
                }
                for row in by_subject
            ]
        }
    
    def delete_user_results(self, user_id: str) -> int:
        """Delete all quiz results for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of records deleted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM quiz_results WHERE user_id = ?", (user_id,))
        deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted {deleted} quiz results for user {user_id}")
        return deleted
