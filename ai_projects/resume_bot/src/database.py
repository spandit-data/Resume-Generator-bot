"""SQLite database for storing resume data."""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "resumes.db"


def get_connection():
    """Get database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT,
            age TEXT,
            city TEXT,
            job_target TEXT,
            is_fresher INTEGER DEFAULT 0,
            previous_company TEXT,
            previous_role TEXT,
            experience_duration TEXT,
            vehicle TEXT,
            education TEXT,
            education_year TEXT,
            phone TEXT,
            work_bullets TEXT,
            skills TEXT,
            objective TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_id ON resumes(user_id)
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized")


def save_resume(user_id: int, data: dict, is_fresher: bool = False) -> int:
    """Save a completed resume to the database. Returns resume ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO resumes (
            user_id, name, age, city, job_target, is_fresher,
            previous_company, previous_role, experience_duration,
            vehicle, education, education_year, phone,
            work_bullets, skills, objective
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data.get("name", ""),
        data.get("age", ""),
        data.get("city", ""),
        data.get("job_target", ""),
        1 if is_fresher else 0,
        data.get("previous_company", ""),
        data.get("previous_role", ""),
        data.get("experience_duration", ""),
        data.get("vehicle", ""),
        data.get("education", ""),
        data.get("education_year", ""),
        data.get("phone", ""),
        str(data.get("work_bullets", [])),
        str(data.get("skills", [])),
        data.get("objective", ""),
    ))

    resume_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Resume saved for user {user_id}, ID: {resume_id}")
    return resume_id


def get_user_resumes(user_id: int) -> list[dict]:
    """Get all resumes for a specific user."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM resumes WHERE user_id = ? ORDER BY created_at DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_all_resumes(limit: int = 100, offset: int = 0) -> list[dict]:
    """Get all resumes (for admin)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM resumes ORDER BY created_at DESC LIMIT ? OFFSET ?
    """, (limit, offset))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_resume_by_id(resume_id: int) -> Optional[dict]:
    """Get a specific resume by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_stats() -> dict:
    """Get database statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM resumes")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(DISTINCT user_id) as unique_users FROM resumes")
    unique_users = cursor.fetchone()["unique_users"]

    conn.close()

    return {
        "total_resumes": total,
        "unique_users": unique_users,
    }


# Initialize database on import
init_db()