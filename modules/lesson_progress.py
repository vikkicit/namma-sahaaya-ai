# modules/lesson_progress.py
# Persistent lesson-completion tracking using SQLite.
# Falls back gracefully to an empty set if the database cannot be opened.

import os
import sqlite3
import pathlib
import streamlit as st

# Store the database alongside the app so it persists across restarts.
_DB_PATH = pathlib.Path(__file__).parent.parent / "lesson_progress.db"


def _get_connection():
    """Open (or create) the SQLite database and return a connection."""
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS completed_lessons (
            lesson_id TEXT PRIMARY KEY,
            completed_at TEXT DEFAULT (datetime('now','localtime'))
        )
        """
    )
    conn.commit()
    return conn


def get_completed_ids() -> set:
    """Return the set of completed lesson IDs from the database."""
    try:
        conn = _get_connection()
        rows = conn.execute("SELECT lesson_id FROM completed_lessons").fetchall()
        conn.close()
        return {row[0] for row in rows}
    except Exception as exc:
        st.warning(f"Could not load lesson progress: {exc}")
        return set()


def mark_completed(lesson_id: str) -> bool:
    """
    Mark a lesson as completed.
    Returns True on success, False if the lesson was already completed or an
    error occurred.
    """
    try:
        conn = _get_connection()
        conn.execute(
            "INSERT OR IGNORE INTO completed_lessons (lesson_id) VALUES (?)",
            (lesson_id,),
        )
        conn.commit()
        changed = conn.total_changes > 0
        conn.close()
        return changed
    except Exception as exc:
        st.warning(f"Could not save lesson progress: {exc}")
        return False


def mark_incomplete(lesson_id: str) -> bool:
    """
    Remove a completed lesson record (undo completion).
    Returns True on success.
    """
    try:
        conn = _get_connection()
        conn.execute(
            "DELETE FROM completed_lessons WHERE lesson_id = ?",
            (lesson_id,),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        st.warning(f"Could not update lesson progress: {exc}")
        return False


def is_completed(lesson_id: str) -> bool:
    """Return True if the lesson has been marked completed."""
    return lesson_id in get_completed_ids()
