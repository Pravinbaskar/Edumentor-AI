from __future__ import annotations

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger("edumentor.chat_history")


class ChatHistoryDB:
    """SQLite database for storing chat history."""

    def __init__(self, db_path: str = "data/chat_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database and create tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create chat_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                subject TEXT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_timestamp 
            ON chat_history(user_id, timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session 
            ON chat_history(session_id)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Chat history database initialized at {self.db_path}")

    def save_qa(
        self,
        user_id: str,
        session_id: str,
        question: str,
        answer: str,
        subject: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Save a question-answer pair to the database.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            question: User's question
            answer: System's answer
            subject: Subject (maths, science, evs)
            metadata: Additional metadata as dict
            
        Returns:
            ID of the inserted record
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute("""
            INSERT INTO chat_history (user_id, session_id, subject, question, answer, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, session_id, subject, question, answer, metadata_json))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Saved Q&A pair {record_id} for user {user_id}")
        return record_id

    def get_user_history(
        self,
        user_id: str,
        limit: int = 50,
        subject: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get chat history for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of records to return
            subject: Filter by subject (optional)
            
        Returns:
            List of chat history records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if subject:
            cursor.execute("""
                SELECT id, user_id, session_id, subject, question, answer, timestamp, metadata
                FROM chat_history
                WHERE user_id = ? AND subject = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, subject, limit))
        else:
            cursor.execute("""
                SELECT id, user_id, session_id, subject, question, answer, timestamp, metadata
                FROM chat_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
            history.append({
                'id': row['id'],
                'user_id': row['user_id'],
                'session_id': row['session_id'],
                'subject': row['subject'],
                'question': row['question'],
                'answer': row['answer'],
                'timestamp': row['timestamp'],
                'metadata': metadata
            })
        
        return history

    def get_recent_sessions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent sessions with their first question.
        
        Args:
            user_id: User identifier
            limit: Maximum number of sessions
            
        Returns:
            List of session summaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                session_id,
                subject,
                MIN(timestamp) as first_timestamp,
                (SELECT question FROM chat_history ch2 
                 WHERE ch2.session_id = chat_history.session_id 
                 ORDER BY timestamp ASC LIMIT 1) as first_question,
                COUNT(*) as message_count
            FROM chat_history
            WHERE user_id = ?
            GROUP BY session_id
            ORDER BY first_timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        sessions = []
        for row in rows:
            sessions.append({
                'session_id': row['session_id'],
                'subject': row['subject'],
                'first_timestamp': row['first_timestamp'],
                'first_question': row['first_question'],
                'message_count': row['message_count']
            })
        
        return sessions

    def search_history(
        self,
        user_id: str,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search chat history by question or answer content.
        
        Args:
            user_id: User identifier
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        search_pattern = f"%{query}%"
        cursor.execute("""
            SELECT id, user_id, session_id, subject, question, answer, timestamp
            FROM chat_history
            WHERE user_id = ? AND (question LIKE ? OR answer LIKE ?)
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, search_pattern, search_pattern, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                'id': row['id'],
                'user_id': row['user_id'],
                'session_id': row['session_id'],
                'subject': row['subject'],
                'question': row['question'],
                'answer': row['answer'],
                'timestamp': row['timestamp']
            })
        
        return results

    def delete_user_history(self, user_id: str) -> int:
        """
        Delete all history for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of records deleted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted {deleted_count} records for user {user_id}")
        return deleted_count

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for a user's chat history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total questions
        cursor.execute("""
            SELECT COUNT(*) FROM chat_history WHERE user_id = ?
        """, (user_id,))
        total_questions = cursor.fetchone()[0]
        
        # Questions by subject
        cursor.execute("""
            SELECT subject, COUNT(*) as count
            FROM chat_history
            WHERE user_id = ? AND subject IS NOT NULL
            GROUP BY subject
        """, (user_id,))
        by_subject = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Total sessions
        cursor.execute("""
            SELECT COUNT(DISTINCT session_id) FROM chat_history WHERE user_id = ?
        """, (user_id,))
        total_sessions = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_questions': total_questions,
            'total_sessions': total_sessions,
            'by_subject': by_subject
        }
