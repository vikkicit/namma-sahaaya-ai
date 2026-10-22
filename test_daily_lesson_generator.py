# test_daily_lesson_generator.py
# Automated Test Suite for Automatic Daily Kannada Lesson Generation
# Tests all 14 requirements using isolated temporary databases and mocks.
# Never modifies or pollutes user production databases.

import datetime
import json
import os
import pathlib
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = pathlib.Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from modules.lessons import LESSONS, LESSON_IDS
from modules.daily_lesson_generator import (
    get_connection,
    get_today_date_str,
    get_saved_daily_lesson,
    save_daily_lesson,
    get_all_daily_lessons,
    get_curated_fallback,
    validate_lesson_schema,
    generate_daily_lesson_from_gemini,
    get_daily_lesson,
    update_daily_lesson_source,
)
from modules.progress_dashboard import get_lesson_metrics
import modules.ai_coach as ai_coach
import modules.phrases as phrases
import modules.lesson_progress as lesson_progress
import modules.quiz_progress as quiz_progress
import modules.favourites as favourites


class TestDailyLessonGenerator(unittest.TestCase):

    def setUp(self):
        # Create an isolated temporary SQLite database for each test
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = pathlib.Path(self.temp_file.name)
        self.temp_file.close()

        # Record production DB state to verify it remains 100% untouched
        self.prod_lesson_db = PROJECT_ROOT / "lesson_progress.db"
        self.prod_quiz_db = PROJECT_ROOT / "quiz_progress.db"
        self.initial_prod_state = {}

        if self.prod_lesson_db.exists():
            conn = sqlite3.connect(str(self.prod_lesson_db))
            cur = conn.cursor()
            cl = cur.execute("SELECT lesson_id, completed_at FROM completed_lessons ORDER BY lesson_id").fetchall()
            fav = cur.execute("SELECT id, kn FROM favourites ORDER BY id").fetchall()
            self.initial_prod_state["completed_lessons"] = cl
            self.initial_prod_state["favourites"] = fav
            conn.close()

        if self.prod_quiz_db.exists():
            conn = sqlite3.connect(str(self.prod_quiz_db))
            cur = conn.cursor()
            qa = cur.execute("SELECT id, topic, score, total FROM quiz_attempts ORDER BY id").fetchall()
            qans = cur.execute("SELECT attempt_id, q_index, question FROM quiz_answers ORDER BY attempt_id, q_index").fetchall()
            self.initial_prod_state["quiz_attempts"] = qa
            self.initial_prod_state["quiz_answers"] = qans
            conn.close()

    def tearDown(self):
        # Clean up temporary database
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except Exception:
                pass

        # Verify production DB was not modified
        if self.prod_lesson_db.exists():
            conn = sqlite3.connect(str(self.prod_lesson_db))
            cur = conn.cursor()
            cl = cur.execute("SELECT lesson_id, completed_at FROM completed_lessons ORDER BY lesson_id").fetchall()
            fav = cur.execute("SELECT id, kn FROM favourites ORDER BY id").fetchall()
            self.assertEqual(cl, self.initial_prod_state.get("completed_lessons", []))
            self.assertEqual(fav, self.initial_prod_state.get("favourites", []))
            conn.close()

        if self.prod_quiz_db.exists():
            conn = sqlite3.connect(str(self.prod_quiz_db))
            cur = conn.cursor()
            qa = cur.execute("SELECT id, topic, score, total FROM quiz_attempts ORDER BY id").fetchall()
            qans = cur.execute("SELECT attempt_id, q_index, question FROM quiz_answers ORDER BY attempt_id, q_index").fetchall()
            self.assertEqual(qa, self.initial_prod_state.get("quiz_attempts", []))
            self.assertEqual(qans, self.initial_prod_state.get("quiz_answers", []))
            conn.close()

    def _sample_valid_ai_lesson(self, date_str="2026-10-20"):
        return {
            "id": f"daily-{date_str}",
            "date": date_str,
            "title": "At the Bengaluru Metro",
            "topic": "Transport",
            "difficulty": "Beginner",
            "objectives": [
                "Buy a metro token or smart card",
                "Ask which platform goes to MG Road",
                "Understand station announcements",
            ],
            "phrases": [
                {"kn": "ಮೆಟ್ರೋ ಟಿಕೆಟ್ ಎಲ್ಲಿ ಸಿಗುತ್ತದೆ?", "roman": "Metro ticket elli siguttade?", "meaning_en": "Where do I get a metro ticket?", "meaning_ta": "மெட்ரோ டிக்கெட் எங்கே கிடைக்கும்?"},
                {"kn": "ಎಂ.ಜಿ. ರಸ್ತೆಗೆ ಹೋಗುವ ರೈಲು ಯಾವುದು?", "roman": "M.G. Rasthege hōguva railu yāvudu?", "meaning_en": "Which train goes to MG Road?", "meaning_ta": "எம்.ஜி. சாலைக்கு செல்லும் ரயில் எது?"},
                {"kn": "ಇದು ಮುಂದಿನ ನಿಲ್ದಾಣವೇ?", "roman": "Idu mundina nildāṇavē?", "meaning_en": "Is this the next station?", "meaning_ta": "இது அடுத்த நிறுத்தமா?"},
                {"kn": "ದಯವಿಟ್ಟು ದಾರಿ ಬಿಡಿ", "roman": "Dayaviṭṭu dāri biḍi", "meaning_en": "Please make way / excuse me", "meaning_ta": "தயவுசெய்து வழி விடுங்கள்"},
                {"kn": "ಕಾರ್ಡ್ ರೀಚಾರ್ಜ್ ಮಾಡಬೇಕು", "roman": "Card recharge māḍabēku", "meaning_en": "I need to recharge my card", "meaning_ta": "கார்டை ரீசார்ஜ் செய்ய வேண்டும்"},
            ],
            "practice": "Practise asking an imaginary metro counter staff for a ticket to Indiranagar.",
            "review": {
                "question": "How do you ask 'Where do I get a metro ticket?' in Kannada?",
                "options": [
                    "ಮೆಟ್ರೋ ಟಿಕೆಟ್ ಎಲ್ಲಿ ಸಿಗುತ್ತದೆ?",
                    "ದಯವಿಟ್ಟು ದಾರಿ ಬಿಡಿ",
                    "ಎಂ.ಜಿ. ರಸ್ತೆಗೆ ಹೋಗುವ ರೈಲು ಯಾವುದು?",
                    "ಕಾರ್ಡ್ ರೀಚಾರ್ಜ್ ಮಾಡಬೇಕು",
                ],
                "answer": "ಮೆಟ್ರೋ ಟಿಕೆಟ್ ಎಲ್ಲಿ ಸಿಗುತ್ತದೆ?",
            },
            "source": "ai_generated",
        }

    # ── Test 1: First request on date with mocked Gemini success ─────────────
    @patch("modules.daily_lesson_generator.generate_daily_lesson_from_gemini")
    def test_01_first_request_gemini_success(self, mock_gen):
        sample = self._sample_valid_ai_lesson("2026-10-20")
        mock_gen.return_value = (sample, "Success")

        lesson = get_daily_lesson("2026-10-20", db_path=self.db_path)
        self.assertEqual(lesson["source"], "ai_generated")
        self.assertEqual(lesson["title"], "At the Bengaluru Metro")
        mock_gen.assert_called_once_with("2026-10-20")

        # Verify persisted in SQLite
        saved = get_saved_daily_lesson("2026-10-20", db_path=self.db_path)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["source"], "ai_generated")
        self.assertEqual(saved["id"], "daily-2026-10-20")

    # ── Test 2: Second request on same date reuses saved lesson ───────────────
    @patch("modules.daily_lesson_generator.generate_daily_lesson_from_gemini")
    def test_02_second_request_reuses_saved_without_gemini(self, mock_gen):
        sample = self._sample_valid_ai_lesson("2026-10-20")
        mock_gen.return_value = (sample, "Success")

        # First call: calls Gemini
        lesson1 = get_daily_lesson("2026-10-20", db_path=self.db_path)
        self.assertEqual(mock_gen.call_count, 1)

        # Second call: reads SQLite, does NOT call Gemini!
        lesson2 = get_daily_lesson("2026-10-20", db_path=self.db_path)
        self.assertEqual(mock_gen.call_count, 1)  # Still 1!
        self.assertEqual(lesson1["title"], lesson2["title"])
        self.assertEqual(lesson2["source"], "ai_generated")

    # ── Test 3: Application restart simulation retrieves saved lesson ────────
    def test_03_restart_simulation_retrieves_saved(self):
        sample = self._sample_valid_ai_lesson("2026-10-20")
        save_daily_lesson(sample, "ai_generated", db_path=self.db_path)

        # Fresh query simulating new process / restart
        retrieved = get_saved_daily_lesson("2026-10-20", db_path=self.db_path)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["id"], "daily-2026-10-20")
        self.assertEqual(retrieved["source"], "ai_generated")
        self.assertEqual(len(retrieved["phrases"]), 5)

    # ── Test 4: New date generates different record without overwriting prior ─
    @patch("modules.daily_lesson_generator.generate_daily_lesson_from_gemini")
    def test_04_new_date_preserves_prior_date(self, mock_gen):
        lesson_d1 = self._sample_valid_ai_lesson("2026-10-20")
        lesson_d2 = self._sample_valid_ai_lesson("2026-10-21")
        lesson_d2["title"] = "At the Coffee Darshini"

        mock_gen.side_effect = [
            (lesson_d1, "Success"),
            (lesson_d2, "Success"),
        ]

        # Day 1
        res1 = get_daily_lesson("2026-10-20", db_path=self.db_path)
        # Day 2
        res2 = get_daily_lesson("2026-10-21", db_path=self.db_path)

        self.assertEqual(res1["title"], "At the Bengaluru Metro")
        self.assertEqual(res2["title"], "At the Coffee Darshini")

        # Verify both exist simultaneously in SQLite
        all_lessons = get_all_daily_lessons(db_path=self.db_path)
        dates = [l["date"] for l in all_lessons]
        self.assertIn("2026-10-20", dates)
        self.assertIn("2026-10-21", dates)
        self.assertEqual(len(all_lessons), 2)

    # ── Test 5: Gemini quota exhaustion returns curated fallback ─────────────
    @patch("modules.daily_lesson_generator.generate_daily_lesson_from_gemini")
    def test_05_quota_exhaustion_returns_curated_fallback(self, mock_gen):
        mock_gen.return_value = (None, "Gemini API rate limit or quota exceeded (429 Resource Exhausted).")

        lesson = get_daily_lesson("2026-10-22", db_path=self.db_path)
        self.assertEqual(lesson["source"], "curated_fallback")
        self.assertIn("fallback_reason", lesson)
        self.assertIn("quota", lesson["fallback_reason"].lower())

        # Stored in SQLite as curated_fallback
        saved = get_saved_daily_lesson("2026-10-22", db_path=self.db_path)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["source"], "curated_fallback")

    # ── Test 6: Network failure returns curated fallback ─────────────────────
    @patch("modules.daily_lesson_generator.generate_daily_lesson_from_gemini")
    def test_06_network_failure_returns_curated_fallback(self, mock_gen):
        mock_gen.return_value = (None, "TimeoutError: Network connection timed out.")

        lesson = get_daily_lesson("2026-10-23", db_path=self.db_path)
        self.assertEqual(lesson["source"], "curated_fallback")
        self.assertIn("fallback_reason", lesson)

    # ── Test 7: Malformed JSON and missing fields are rejected ───────────────
    def test_07_malformed_json_and_missing_fields_rejected(self):
        # 1. Non-dict
        valid, _ = validate_lesson_schema("not a dict", "2026-10-20")
        self.assertFalse(valid)

        # 2. Missing title
        d = self._sample_valid_ai_lesson()
        del d["title"]
        valid, reason = validate_lesson_schema(d, "2026-10-20")
        self.assertFalse(valid)
        self.assertIn("title", reason)

        # 3. Objectives < 3
        d = self._sample_valid_ai_lesson()
        d["objectives"] = ["Only one"]
        valid, reason = validate_lesson_schema(d, "2026-10-20")
        self.assertFalse(valid)

        # 4. Phrases < 5
        d = self._sample_valid_ai_lesson()
        d["phrases"] = d["phrases"][:2]
        valid, reason = validate_lesson_schema(d, "2026-10-20")
        self.assertFalse(valid)

        # 5. Missing Kannada script (e.g. English text in kn field)
        d = self._sample_valid_ai_lesson()
        d["phrases"][0]["kn"] = "Hello where is bus stop"
        valid, reason = validate_lesson_schema(d, "2026-10-20")
        self.assertFalse(valid)

    # ── Test 8: Duplicate concurrent writes preserve one canonical lesson ────
    def test_08_concurrent_writes_preserve_canonical_lesson(self):
        lesson_a = self._sample_valid_ai_lesson("2026-10-24")
        lesson_a["title"] = "Version A"

        lesson_b = self._sample_valid_ai_lesson("2026-10-24")
        lesson_b["title"] = "Version B"

        # First write succeeds
        res_a, ins_a = save_daily_lesson(lesson_a, "ai_generated", db_path=self.db_path)
        self.assertTrue(ins_a)
        self.assertEqual(res_a["title"], "Version A")

        # Second write for same date encounters conflict and returns canonical Version A
        res_b, ins_b = save_daily_lesson(lesson_b, "ai_generated", db_path=self.db_path)
        self.assertFalse(ins_b)
        self.assertEqual(res_b["title"], "Version A")

        # SQLite table contains exactly 1 row for that date
        conn = get_connection(self.db_path)
        count = conn.execute("SELECT count(*) FROM daily_lessons WHERE lesson_date = '2026-10-24'").fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

    # ── Test 9: Stored lesson source is accurately labelled ──────────────────
    def test_09_stored_lesson_source_accurately_labelled(self):
        ai_l = self._sample_valid_ai_lesson("2026-10-25")
        save_daily_lesson(ai_l, "ai_generated", db_path=self.db_path)
        rec_ai = get_saved_daily_lesson("2026-10-25", db_path=self.db_path)
        self.assertEqual(rec_ai["source"], "ai_generated")

        fb_l = get_curated_fallback("2026-10-26")
        save_daily_lesson(fb_l, "curated_fallback", db_path=self.db_path)
        rec_fb = get_saved_daily_lesson("2026-10-26", db_path=self.db_path)
        self.assertEqual(rec_fb["source"], "curated_fallback")

    # ── Test 10: Daily lesson IDs do not collide with curated lesson IDs ─────
    def test_10_daily_lesson_ids_do_not_collide_with_curated(self):
        sample = self._sample_valid_ai_lesson("2026-10-20")
        self.assertTrue(sample["id"].startswith("daily-"))
        self.assertNotIn(sample["id"], LESSON_IDS)

        fallback = get_curated_fallback("2026-10-20")
        self.assertTrue(fallback["id"].startswith("daily-"))
        self.assertNotIn(fallback["id"], LESSON_IDS)

    # ── Test 11: Production DB remains unmodified ─────────────────────────────
    def test_11_production_data_unmodified(self):
        # Production DB assertions are also verified in setUp/tearDown
        self.assertTrue(self.prod_lesson_db.exists())
        conn = sqlite3.connect(str(self.prod_lesson_db))
        cl_count = conn.execute("SELECT count(*) FROM completed_lessons").fetchone()[0]
        fav_count = conn.execute("SELECT count(*) FROM favourites").fetchone()[0]
        conn.close()

        self.assertEqual(cl_count, 1)
        self.assertEqual(fav_count, 4)

    # ── Test 12: Dashboard does not count daily lessons as curated ───────────
    def test_12_dashboard_does_not_count_daily_lessons_as_curated(self):
        # Simulate completed_lessons table with 1 curated lesson and 1 daily lesson
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("CREATE TABLE completed_lessons (lesson_id TEXT PRIMARY KEY, completed_at TEXT)")
        conn.execute("INSERT INTO completed_lessons VALUES ('greetings-01', '2026-10-19 10:00:00')")
        conn.execute("INSERT INTO completed_lessons VALUES ('daily-2026-10-20', '2026-10-20 12:00:00')")
        conn.commit()
        conn.close()

        metrics = get_lesson_metrics(self.db_path)
        # Total curated is still 8
        self.assertEqual(metrics["total_curated"], 8)
        # Completed curated count is still strictly 1 (greetings-01)
        self.assertEqual(metrics["completed_curated_count"], 1)
        # Completion percentage is still 12.5% (1/8 * 100), not inflated to 25%!
        self.assertEqual(metrics["completion_percentage"], 12.5)
        # Other completed captures the daily lesson
        self.assertIn("daily-2026-10-20", metrics["other_completed_ids"])

    # ── Test 13: Existing application pages still work ───────────────────────
    def test_13_existing_app_pages_functional(self):
        self.assertGreater(len(phrases.PHRASES), 10)
        self.assertEqual(len(LESSONS), 8)
        self.assertTrue(hasattr(ai_coach, "generate_reply"))
        self.assertTrue(hasattr(lesson_progress, "get_completed_ids"))
        self.assertTrue(hasattr(quiz_progress, "get_recent_attempts"))
        self.assertTrue(hasattr(favourites, "get_all_favourites"))

    # ── Test 14: Python syntax compile passes on all modified files ──────────
    def test_14_syntax_compilation_all_files(self):
        import py_compile
        files = [
            PROJECT_ROOT / "modules" / "daily_lesson_generator.py",
            PROJECT_ROOT / "modules" / "progress_dashboard.py",
            PROJECT_ROOT / "modules" / "lessons.py",
            PROJECT_ROOT / "modules" / "lesson_progress.py",
            PROJECT_ROOT / "app.py",
        ]
        for f in files:
            self.assertTrue(py_compile.compile(str(f), doraise=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
