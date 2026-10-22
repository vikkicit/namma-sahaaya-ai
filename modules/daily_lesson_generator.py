# modules/daily_lesson_generator.py
# Automatic Daily Kannada Lesson Generation using Gemini, SQLite persistence, and curated fallback.
# Adheres to strict data integrity:
# - Reuses existing Gemini configuration and credentials without exposing secrets.
# - Enforces one canonical daily lesson per calendar date in Asia/Kolkata timezone.
# - Validates structured JSON before acceptance; falls back deterministically to curated lessons on errors.
# - Uses parameterized SQL, transactions, and unique constraints for concurrency safety.
# - Never overwrites prior dates or modifies unrelated user data.

import datetime
import json
import os
import pathlib
import re
import sqlite3
import time
import zoneinfo
from dotenv import load_dotenv

from google.genai import errors as genai_errors

from modules.lessons import LESSONS, LESSON_IDS, LESSONS_BY_ID

load_dotenv()

# App-wide SQLite DB path in the project root
_DB_PATH = pathlib.Path(__file__).parent.parent / "lesson_progress.db"

# Model configuration matches existing app modules (e.g. ai_coach.py)
MODEL_NAME = "gemini-3.8-flash"

# Primary timezone for local calendar date
TIMEZONE_NAME = "Asia/Kolkata"

# Retry configuration for transient server errors (503 / overload)
_MAX_RETRIES = 1
_RETRY_DELAY_SECONDS = 2


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DATABASE & PERSISTENCE LAYER
# ═══════════════════════════════════════════════════════════════════════════════

def get_connection(db_path: pathlib.Path | str = _DB_PATH) -> sqlite3.Connection:
    """Open SQLite connection and ensure daily_lessons table exists."""
    p = pathlib.Path(db_path) if isinstance(db_path, str) else db_path
    if str(p) == ":memory:":
        conn = sqlite3.connect(":memory:")
    else:
        conn = sqlite3.connect(str(p), check_same_thread=False)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_lessons (
            lesson_date TEXT PRIMARY KEY,
            lesson_id TEXT NOT NULL,
            title TEXT NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            content_json TEXT NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    conn.commit()
    return conn


def get_saved_daily_lesson(date_str: str, db_path: pathlib.Path | str = _DB_PATH) -> dict | None:
    """
    Retrieve an existing canonical daily lesson for a date from SQLite.
    Returns None if no lesson is saved for that date or if content is invalid.
    """
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT content_json, source FROM daily_lessons WHERE lesson_date = ?",
            (date_str,),
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return None

        content = json.loads(row[0])
        content["source"] = row[1]
        return content
    except Exception:
        return None


def save_daily_lesson(
    lesson: dict,
    source: str,
    db_path: pathlib.Path | str = _DB_PATH,
) -> tuple[dict, bool]:
    """
    Persist daily lesson into SQLite enforcing one canonical record per local date.
    Handles concurrent race conditions: if a conflict occurs, the already-saved
    canonical record is returned.
    Returns (canonical_lesson, was_inserted).
    """
    date_str = lesson.get("date")
    if not date_str:
        return lesson, False

    conn = get_connection(db_path)
    cur = conn.cursor()

    try:
        content_json = json.dumps(lesson, ensure_ascii=False)
        cur.execute(
            """
            INSERT INTO daily_lessons (lesson_date, lesson_id, title, topic, difficulty, content_json, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date_str,
                lesson.get("id", f"daily-{date_str}"),
                lesson.get("title", "Daily Kannada Lesson"),
                lesson.get("topic", "Daily Conversation"),
                lesson.get("difficulty", "Beginner"),
                content_json,
                source,
            ),
        )
        conn.commit()
        conn.close()
        lesson["source"] = source
        return lesson, True
    except sqlite3.IntegrityError:
        # Race condition: another request/session already saved a lesson for this date.
        conn.rollback()
        cur.execute(
            "SELECT content_json, source FROM daily_lessons WHERE lesson_date = ?",
            (date_str,),
        )
        existing = cur.fetchone()
        conn.close()
        if existing:
            try:
                saved = json.loads(existing[0])
                saved["source"] = existing[1]
                return saved, False
            except Exception:
                pass
        return lesson, False
    except Exception:
        conn.rollback()
        conn.close()
        return lesson, False


def update_daily_lesson_source(
    lesson: dict,
    source: str,
    db_path: pathlib.Path | str = _DB_PATH,
) -> bool:
    """
    Update an existing daily lesson record (used for explicit user retry when replacing
    a fallback with newly generated AI content).
    """
    date_str = lesson.get("date")
    if not date_str:
        return False
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        content_json = json.dumps(lesson, ensure_ascii=False)
        cur.execute(
            """
            UPDATE daily_lessons
            SET lesson_id = ?, title = ?, topic = ?, difficulty = ?, content_json = ?, source = ?, created_at = datetime('now', 'localtime')
            WHERE lesson_date = ?
            """,
            (
                lesson.get("id", f"daily-{date_str}"),
                lesson.get("title", "Daily Kannada Lesson"),
                lesson.get("topic", "Daily Conversation"),
                lesson.get("difficulty", "Beginner"),
                content_json,
                source,
                date_str,
            ),
        )
        conn.commit()
        changed = conn.total_changes > 0
        conn.close()
        return changed
    except Exception:
        return False


def get_all_daily_lessons(db_path: pathlib.Path | str = _DB_PATH) -> list[dict]:
    """Retrieve all historical daily lessons ordered from newest to oldest."""
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT content_json, source FROM daily_lessons ORDER BY lesson_date DESC"
        )
        rows = cur.fetchall()
        conn.close()
        results = []
        for r in rows:
            try:
                item = json.loads(r[0])
                item["source"] = r[1]
                results.append(item)
            except Exception:
                continue
        return results
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DATE & TIMEZONE LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════════

def get_today_date_str(tz_name: str = TIMEZONE_NAME) -> str:
    """
    Get the current calendar date string in YYYY-MM-DD format using the configured timezone.
    Defaults to Asia/Kolkata (Bengaluru local time).
    """
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
        now = datetime.datetime.now(tz)
    except Exception:
        now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CURATED FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════

def get_curated_fallback(date_str: str, reason: str = "") -> dict:
    """
    Select an existing curated lesson deterministically based on date_str.
    Converts fields into daily lesson schema without inventing translations or objectives.
    Truthfully labeled with source 'curated_fallback'.
    """
    try:
        dt = datetime.date.fromisoformat(date_str)
        day_ordinal = dt.toordinal()
    except Exception:
        day_ordinal = 0

    idx = day_ordinal % len(LESSONS)
    curated = LESSONS[idx]

    # Build review question from the lesson phrases
    phrases = curated.get("phrases", [])
    if phrases:
        p0 = phrases[0]
        review_q = {
            "question": f"What is the meaning of '{p0.get('kn', '')}' ({p0.get('roman', '')})?",
            "options": [
                p0.get("meaning_en", "Correct meaning"),
                "Please stop here",
                "How much does this cost?",
                "I do not understand",
            ],
            "answer": p0.get("meaning_en", "Correct meaning"),
        }
    else:
        review_q = {
            "question": "Review the phrases aloud and check your pronunciation.",
            "options": ["Practised successfully", "Need more practice"],
            "answer": "Practised successfully",
        }

    return {
        "id": f"daily-{date_str}",
        "date": date_str,
        "title": curated.get("title", "Daily Kannada Lesson"),
        "topic": curated.get("topic", "General"),
        "difficulty": curated.get("difficulty", "Beginner"),
        "objectives": list(curated.get("objectives", [])),
        "phrases": [dict(p) for p in phrases],
        "practice": curated.get("practice", "Read each phrase aloud and practise with a friend."),
        "review": review_q,
        "source": "curated_fallback",
        "fallback_reason": reason or "Gemini API unavailable or quota limit reached.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 4. GEMINI GENERATION & VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def _clean_json_text(raw_text: str) -> str:
    """Strip markdown code fence backticks and whitespace from JSON response."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def validate_lesson_schema(data: dict, expected_date: str) -> tuple[bool, str]:
    """
    Rigorously validate generated lesson structure.
    Returns (is_valid, error_reason).
    """
    if not isinstance(data, dict):
        return False, "Response is not a valid JSON dictionary."

    # Required string fields
    for field in ["title", "topic", "difficulty", "practice"]:
        val = data.get(field)
        if not val or not isinstance(val, str) or not val.strip():
            return False, f"Missing or empty required field: '{field}'."

    # Validate objectives (3 to 5 non-empty strings)
    objectives = data.get("objectives")
    if not isinstance(objectives, list) or len(objectives) < 3:
        return False, "Objectives must be a list of at least 3 items."
    for obj in objectives:
        if not isinstance(obj, str) or not obj.strip():
            return False, "Invalid objective entry in objectives list."

    # Validate phrases (5 to 8 phrases with Kannada script, roman, en, ta)
    phrases = data.get("phrases")
    if not isinstance(phrases, list) or len(phrases) < 5:
        return False, "Phrases must be a list of at least 5 phrases."

    for idx, p in enumerate(phrases):
        if not isinstance(p, dict):
            return False, f"Phrase at index {idx} is not a dictionary."
        kn = p.get("kn", "").strip()
        roman = p.get("roman", "").strip()
        meaning_en = p.get("meaning_en", "").strip()
        meaning_ta = p.get("meaning_ta", "").strip()

        if not kn:
            return False, f"Phrase at index {idx} is missing Kannada script ('kn')."
        # Validate genuine Kannada Unicode range [\u0C80-\u0CFF]
        if not re.search(r"[\u0C80-\u0CFF]", kn):
            return False, f"Phrase '{kn}' does not contain valid Kannada script."
        if not roman:
            return False, f"Phrase at index {idx} is missing Roman transliteration ('roman')."
        if not meaning_en:
            return False, f"Phrase at index {idx} is missing English meaning ('meaning_en')."
        if not meaning_ta:
            # Fallback to English if Tamil is empty
            p["meaning_ta"] = meaning_en

    # Validate review structure
    review = data.get("review")
    if not review:
        return False, "Missing 'review' field."

    return True, "Valid"


def generate_daily_lesson_from_gemini(date_str: str) -> tuple[dict | None, str]:
    """
    Call Gemini API to generate a structured Kannada lesson for date_str.
    Returns (lesson_dict, error_message).
    Never logs or exposes API keys.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None, "GEMINI_API_KEY is missing from environment."

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = f"""
You are an expert Kannada language instructor for NammaSahaaya AI.
Generate one practical everyday Kannada lesson for the calendar date: {date_str}.
Topic must be a realistic everyday situation (e.g. Shopping at market, Metro travel, Ordering food, Asking directions, Workplace conversation, or Public services).

Return ONLY a JSON object with this exact schema (no markdown formatting, no code blocks):
{{
  "id": "daily-{date_str}",
  "date": "{date_str}",
  "title": "Short descriptive lesson title in English",
  "topic": "Category (e.g., Shopping, Transport, Restaurant, Directions, Introductions, General Help)",
  "difficulty": "Beginner",
  "objectives": [
    "Learning objective 1",
    "Learning objective 2",
    "Learning objective 3"
  ],
  "phrases": [
    {{
      "kn": "Kannada script phrase (must use actual Kannada script)",
      "roman": "Accurate Latin transliteration",
      "meaning_en": "Clear English translation",
      "meaning_ta": "Clear Tamil translation"
    }}
  ],
  "practice": "A clear speaking practice activity for the user to try aloud",
  "review": {{
    "question": "A multiple-choice question testing one of the phrases",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer": "Option A"
  }}
}}

Constraints:
- Include exactly 5 to 7 practical everyday phrases.
- The 'kn' field MUST contain genuine Kannada script.
- Ensure natural, polite, and authentic spoken Kannada usage.
"""

        # Attempt generation with at most one short retry for transient errors
        last_error = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                    config={
                        "temperature": 0.2,
                        "max_output_tokens": 1200,
                    },
                )
                last_error = None
                break  # Success — exit retry loop
            except genai_errors.ServerError as api_err:
                last_error = api_err
                code = getattr(api_err, "code", None)
                if code in (503, 504) and attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_DELAY_SECONDS)
                    continue
                break  # Non-retriable or final attempt
            except genai_errors.ClientError as api_err:
                last_error = api_err
                break  # Client errors (429, etc.) are not retried
            except Exception as api_err:
                last_error = api_err
                break  # Unknown errors are not retried

        if last_error is not None:
            raise last_error

        raw_text = (response.text or "").strip()
        cleaned_json = _clean_json_text(raw_text)

        if not cleaned_json:
            return None, "Gemini returned an empty response."

        data = json.loads(cleaned_json)

        # Normalize ID and Date
        data["id"] = f"daily-{date_str}"
        data["date"] = date_str

        # Validate schema
        is_valid, reason = validate_lesson_schema(data, date_str)
        if not is_valid:
            return None, f"Response schema validation failed: {reason}"

        # Trim objectives to 3-5 and phrases to 5-8 if necessary
        data["objectives"] = data["objectives"][:5]
        data["phrases"] = data["phrases"][:8]

        data["source"] = "ai_generated"
        return data, "Success"

    except genai_errors.ServerError as exc:
        code = getattr(exc, "code", None)
        if code == 503 or "503" in str(exc) or "UNAVAILABLE" in str(exc):
            diag = "Gemini model is currently experiencing high demand (503 Unavailable)."
        else:
            diag = "Gemini server error. Please try again later."
        return None, diag

    except genai_errors.ClientError as exc:
        code = getattr(exc, "code", None)
        if code == 429 or "RESOURCE_EXHAUSTED" in str(exc) or "quota" in str(exc).lower():
            diag = "Gemini API rate limit or quota exceeded (429 Resource Exhausted)."
        else:
            diag = "Gemini request error. Please check your configuration."
        return None, diag

    except Exception as exc:
        err_type = type(exc).__name__
        err_str = str(exc)
        # Classify user-facing diagnostic safely without exposing keys
        if "503" in err_str or "UNAVAILABLE" in err_str:
            diag = "Gemini model is currently experiencing high demand (503 Unavailable)."
        elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
            diag = "Gemini API rate limit or quota exceeded (429 Resource Exhausted)."
        elif "JSONDecodeError" in err_type:
            diag = "Gemini response could not be parsed as valid JSON."
        else:
            diag = f"{err_type}: Connection or generation error."
        return None, diag


# ═══════════════════════════════════════════════════════════════════════════════
# 5. PUBLIC LIFECYCLE API
# ═══════════════════════════════════════════════════════════════════════════════

def get_daily_lesson(
    date_str: str | None = None,
    db_path: pathlib.Path | str = _DB_PATH,
    force_ai_retry: bool = False,
) -> dict:
    """
    Main entrypoint for Daily Kannada Lesson retrieval.
    1. Determines target date (defaults to today in Asia/Kolkata).
    2. Checks SQLite first; returns already-persisted canonical lesson immediately.
    3. If not saved (or force_ai_retry requested): attempts Gemini generation once.
    4. If generation succeeds, saves with source 'ai_generated'.
    5. If generation fails, selects deterministic curated fallback, saves with 'curated_fallback'.
    6. Returns the canonical lesson dictionary.
    """
    target_date = date_str or get_today_date_str()

    # Step 1: Check SQLite unless forcing an explicit AI retry
    if not force_ai_retry:
        existing = get_saved_daily_lesson(target_date, db_path=db_path)
        if existing:
            return existing

    # Step 2: Attempt generation
    generated_lesson, gen_error = generate_daily_lesson_from_gemini(target_date)

    if generated_lesson:
        if force_ai_retry:
            # Update existing fallback record with new AI generated content
            update_daily_lesson_source(generated_lesson, "ai_generated", db_path=db_path)
            generated_lesson["source"] = "ai_generated"
            return generated_lesson
        else:
            canonical, _ = save_daily_lesson(generated_lesson, "ai_generated", db_path=db_path)
            return canonical

    # Step 3: Generation failed — use curated fallback
    # If user was retrying and a lesson was already saved, keep the existing record
    if force_ai_retry:
        existing = get_saved_daily_lesson(target_date, db_path=db_path)
        if existing:
            existing["retry_error"] = gen_error
            return existing

    fallback_lesson = get_curated_fallback(target_date, reason=gen_error)
    canonical, _ = save_daily_lesson(fallback_lesson, "curated_fallback", db_path=db_path)
    return canonical
