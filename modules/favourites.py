# modules/favourites.py
# Persistent favourites management using SQLite.
# Stores user-favourited phrases with stable IDs, avoiding duplicates.

import hashlib
import pathlib
import sqlite3
import streamlit as st

# Reuse the existing database alongside the app to avoid unnecessary duplicate DBs.
_DB_PATH = pathlib.Path(__file__).parent.parent / "lesson_progress.db"


def generate_phrase_id(kn: str) -> str:
    """Generate a stable, deterministic identifier from the Kannada phrase text."""
    if not kn:
        return ""
    norm = kn.strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def _get_connection():
    """Open (or create) the SQLite database and ensure the favourites table exists."""
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS favourites (
            id TEXT PRIMARY KEY,
            kn TEXT NOT NULL UNIQUE,
            roman TEXT,
            meaning_en TEXT,
            meaning_ta TEXT,
            topic TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    conn.commit()
    return conn


def add_favourite(
    kn: str,
    roman: str = "",
    meaning_en: str = "",
    meaning_ta: str = "",
    topic: str = "",
    phrase_id: str = None,
) -> bool:
    """
    Persistently save a phrase to favourites using parameterized SQL.
    Prevents duplicates using stable unique IDs.
    Returns True on success, False on error.
    """
    if not kn or not kn.strip():
        return False

    kn_clean = kn.strip()
    pid = phrase_id or generate_phrase_id(kn_clean)
    roman_clean = (roman or "").strip()
    en_clean = (meaning_en or "").strip()
    ta_clean = (meaning_ta or "").strip()
    topic_clean = (topic or "").strip()

    try:
        conn = _get_connection()
        conn.execute(
            """
            INSERT INTO favourites (id, kn, roman, meaning_en, meaning_ta, topic)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(kn) DO UPDATE SET
                roman = CASE WHEN excluded.roman != '' THEN excluded.roman ELSE favourites.roman END,
                meaning_en = CASE WHEN excluded.meaning_en != '' THEN excluded.meaning_en ELSE favourites.meaning_en END,
                meaning_ta = CASE WHEN excluded.meaning_ta != '' THEN excluded.meaning_ta ELSE favourites.meaning_ta END,
                topic = CASE WHEN excluded.topic != '' THEN excluded.topic ELSE favourites.topic END
            """,
            (pid, kn_clean, roman_clean, en_clean, ta_clean, topic_clean),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        st.warning(f"Could not save favourite phrase: {exc}")
        return False


def remove_favourite(phrase_id_or_kn: str) -> bool:
    """
    Remove a phrase from favourites by its ID or Kannada text.
    Returns True on success, False on error.
    """
    if not phrase_id_or_kn or not phrase_id_or_kn.strip():
        return False

    target = phrase_id_or_kn.strip()
    pid = generate_phrase_id(target)

    try:
        conn = _get_connection()
        conn.execute(
            "DELETE FROM favourites WHERE id = ? OR id = ? OR kn = ?",
            (target, pid, target),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        st.warning(f"Could not remove favourite phrase: {exc}")
        return False


def is_favourite(phrase_id_or_kn: str) -> bool:
    """
    Check if a phrase is currently saved in favourites.
    Accepts either a phrase ID or the Kannada text.
    """
    if not phrase_id_or_kn or not phrase_id_or_kn.strip():
        return False

    target = phrase_id_or_kn.strip()
    pid = generate_phrase_id(target)

    try:
        conn = _get_connection()
        cur = conn.execute(
            "SELECT 1 FROM favourites WHERE id = ? OR id = ? OR kn = ? LIMIT 1",
            (target, pid, target),
        )
        row = cur.fetchone()
        conn.close()
        return row is not None
    except Exception as exc:
        return False


def get_all_favourites(topic: str = None, query: str = None) -> list[dict]:
    """
    Retrieve all saved favourite phrases from SQLite with optional topic & search filtering.
    Returns a list of dicts with keys: id, kn, roman, meaning_en, meaning_ta, topic, created_at.
    """
    try:
        conn = _get_connection()
        sql = "SELECT id, kn, roman, meaning_en, meaning_ta, topic, created_at FROM favourites WHERE 1=1"
        params = []

        if topic and topic.strip() and topic != "All topics" and topic != "All":
            sql += " AND topic = ?"
            params.append(topic.strip())

        sql += " ORDER BY created_at DESC, id DESC"

        rows = conn.execute(sql, params).fetchall()
        conn.close()

        from modules.phrases import normalize_text

        q_norm = normalize_text(query) if query and query.strip() else None

        results = []
        for r in rows:
            item = {
                "id": r[0],
                "kn": r[1],
                "roman": r[2] or "",
                "meaning_en": r[3] or "",
                "meaning_ta": r[4] or "",
                "topic": r[5] or "",
                "created_at": r[6] or "",
            }
            if q_norm:
                fields = [
                    item["kn"],
                    item["roman"],
                    item["meaning_en"],
                    item["meaning_ta"],
                    item["topic"],
                ]
                if not any(q_norm in normalize_text(f) for f in fields):
                    continue
            results.append(item)
        return results
    except Exception as exc:
        st.warning(f"Could not load favourites: {exc}")
        return []


def get_favourite_topics() -> list[str]:
    """Return a sorted list of unique non-empty topics from saved favourites."""
    try:
        conn = _get_connection()
        rows = conn.execute(
            "SELECT DISTINCT topic FROM favourites WHERE topic IS NOT NULL AND topic != '' ORDER BY topic ASC"
        ).fetchall()
        conn.close()
        return [r[0] for r in rows if r[0]]
    except Exception as exc:
        return []


def get_favourite_count() -> int:
    """Return the total number of saved favourite phrases."""
    try:
        conn = _get_connection()
        cur = conn.execute("SELECT COUNT(*) FROM favourites")
        row = cur.fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception:
        return 0
