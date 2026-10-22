# modules/quiz_progress.py
# SQLite-backed persistence for interactive quiz attempts.
# Separate from lesson_progress so we don't interfere with lesson completion data.

import pathlib
import sqlite3
import datetime
import streamlit as st

# DB file next to the app root (same folder as app.py)
_DB_PATH = pathlib.Path(__file__).parent.parent / "quiz_progress.db"


def _get_conn():
    """Open (or create) the SQLite DB and ensure tables exist."""
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    # Table for each quiz attempt
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    # Table for each answer in an attempt
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS quiz_answers (
            attempt_id INTEGER,
            q_index INTEGER,
            question TEXT,
            chosen TEXT,
            correct TEXT,
            is_correct INTEGER,
            FOREIGN KEY(attempt_id) REFERENCES quiz_attempts(id)
        )
        """
    )
    conn.commit()
    return conn


def save_quiz_attempt(topic: str, score: int, total: int, answers: list[dict]):
    """Persist a completed quiz.
    `answers` is a list of dicts with keys: q_index, question, chosen, correct, is_correct.
    Returns the attempt ID or None on error.
    """
    try:
        conn = _get_conn()
        ts = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
        cur = conn.execute(
            "INSERT INTO quiz_attempts (topic, score, total, timestamp) VALUES (?,?,?,?)",
            (topic, score, total, ts),
        )
        attempt_id = cur.lastrowid
        # Insert answers
        for a in answers:
            conn.execute(
                "INSERT INTO quiz_answers (attempt_id, q_index, question, chosen, correct, is_correct) VALUES (?,?,?,?,?,?)",
                (
                    attempt_id,
                    a.get("q_index"),
                    a.get("question"),
                    a.get("chosen"),
                    a.get("correct"),
                    int(a.get("is_correct", False)),
                ),
            )
        conn.commit()
        conn.close()
        return attempt_id
    except Exception as exc:
        st.warning(f"Failed to save quiz attempt: {exc}")
        return None


def get_recent_attempts(limit: int = 5) -> list[dict]:
    """Return the most recent quiz attempts (shallow info)."""
    try:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT id, topic, score, total, timestamp FROM quiz_attempts ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [
            {"id": r[0], "topic": r[1], "score": r[2], "total": r[3], "timestamp": r[4]}
            for r in rows
        ]
    except Exception as exc:
        st.warning(f"Could not load quiz attempts: {exc}")
        return []
