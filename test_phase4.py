# test_phase4.py
# Automated Regression Test Suite for Phase 4: Learning Progress Dashboard
# Adheres strictly to test integrity: uses temporary databases for edge-case tests,
# verifies production databases remain completely unmodified.

import os
import sys
import sqlite3
import tempfile
import pathlib
import unittest

# Ensure project root is in sys.path
PROJECT_ROOT = pathlib.Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from modules.lessons import LESSONS, LESSON_IDS, LESSONS_BY_ID, LESSON_TOPICS
from modules.progress_dashboard import (
    get_ro_connection,
    get_lesson_metrics,
    get_quiz_metrics,
    get_favourites_and_revision_metrics,
    generate_recommendations,
    set_page_navigation,
)
import modules.ai_coach as ai_coach
import modules.phrases as phrases
import modules.voice as voice
import modules.lesson_progress as lesson_progress
import modules.quiz_progress as quiz_progress
import modules.favourites as favourites


class TestPhase4Dashboard(unittest.TestCase):

    def setUp(self):
        # Record production DB state before any test
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
        # Verify production DB is completely untouched
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

    def test_01_read_only_connection(self):
        """Test get_ro_connection works and prevents mutations."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            tf_path = pathlib.Path(tf.name)
        try:
            # Initialize table
            conn = sqlite3.connect(str(tf_path))
            conn.execute("CREATE TABLE test (id INT)")
            conn.execute("INSERT INTO test VALUES (1)")
            conn.commit()
            conn.close()

            # Open with read-only helper
            ro_conn = get_ro_connection(tf_path)
            self.assertIsNotNone(ro_conn)
            cur = ro_conn.cursor()
            row = cur.execute("SELECT count(*) FROM test").fetchone()
            self.assertEqual(row[0], 1)

            # Attempting insert on URI read-only connection must raise OperationalError
            with self.assertRaises(sqlite3.OperationalError):
                ro_conn.execute("INSERT INTO test VALUES (2)")
            ro_conn.close()
        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_02_dashboard_no_quiz_attempts(self):
        """Test dashboard calculations with zero quiz attempts."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            tf_path = pathlib.Path(tf.name)
        try:
            conn = sqlite3.connect(str(tf_path))
            conn.execute("CREATE TABLE quiz_attempts (id INTEGER PRIMARY KEY, topic TEXT, score INTEGER, total INTEGER, timestamp TEXT)")
            conn.commit()
            conn.close()

            qm = get_quiz_metrics(tf_path)
            self.assertFalse(qm["has_attempts"])
            self.assertEqual(qm["total_attempts"], 0)
            self.assertEqual(qm["average_score_pct"], 0.0)
            self.assertEqual(qm["best_score_pct"], 0.0)
            self.assertEqual(qm["recent_attempts"], [])
            self.assertEqual(qm["best_topics"], [])
            self.assertEqual(qm["needs_improvement_topics"], [])

            # Recommendation should suggest taking first quiz
            lm = {"completed_curated_count": 0, "total_curated": 8, "remaining_curated_count": 8, "remaining_curated_list": LESSONS}
            fm = {"total_favourites": 0}
            recs = generate_recommendations(lm, qm, fm)
            quiz_rec = [r for r in recs if r["category"] == "Quiz"][0]
            self.assertEqual(quiz_rec["id"], "rec_quiz_start")
            self.assertEqual(quiz_rec["nav_page"], "Interactive Quizzes")
        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_03_dashboard_completed_and_incomplete_lessons(self):
        """Test dashboard calculations with various lesson completion states."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            tf_path = pathlib.Path(tf.name)
        try:
            conn = sqlite3.connect(str(tf_path))
            conn.execute("CREATE TABLE completed_lessons (lesson_id TEXT PRIMARY KEY, completed_at TEXT)")
            conn.execute("INSERT INTO completed_lessons VALUES ('greetings-01', '2026-10-19 10:00:00')")
            conn.execute("INSERT INTO completed_lessons VALUES ('shopping-01', '2026-10-19 12:00:00')")
            conn.commit()
            conn.close()

            lm = get_lesson_metrics(tf_path)
            self.assertEqual(lm["total_curated"], len(LESSONS))
            self.assertEqual(lm["completed_curated_count"], 2)
            self.assertEqual(lm["remaining_curated_count"], len(LESSONS) - 2)
            self.assertEqual(lm["completion_percentage"], round((2 / len(LESSONS)) * 100.0, 1))
            self.assertTrue(lm["has_completed"])
            self.assertEqual(len(lm["completed_curated_list"]), 2)
            self.assertEqual(len(lm["remaining_curated_list"]), len(LESSONS) - 2)

            # Recommendations should recommend next uncompleted lesson
            qm = {"has_attempts": False}
            fm = {"total_favourites": 0}
            recs = generate_recommendations(lm, qm, fm)
            lesson_rec = [r for r in recs if r["category"] == "Lessons"][0]
            self.assertEqual(lesson_rec["id"], "rec_lesson_continue")
            self.assertEqual(lesson_rec["nav_page"], "Daily Lessons")
            # Next lesson in sequence that was not completed: 'introductions-01'
            self.assertEqual(lesson_rec["nav_kwargs"]["lesson_view"], "introductions-01")

            # Test 0 lessons completed
            conn = sqlite3.connect(str(tf_path))
            conn.execute("DELETE FROM completed_lessons")
            conn.commit()
            conn.close()

            lm_empty = get_lesson_metrics(tf_path)
            self.assertEqual(lm_empty["completed_curated_count"], 0)
            self.assertEqual(lm_empty["completion_percentage"], 0.0)
            recs_empty = generate_recommendations(lm_empty, qm, fm)
            rec_start = [r for r in recs_empty if r["category"] == "Lessons"][0]
            self.assertEqual(rec_start["id"], "rec_lesson_start")
            self.assertEqual(rec_start["nav_kwargs"]["lesson_view"], "greetings-01")

            # Test all lessons completed
            conn = sqlite3.connect(str(tf_path))
            for lid in LESSON_IDS:
                conn.execute("INSERT INTO completed_lessons VALUES (?, '2026-10-20')", (lid,))
            conn.commit()
            conn.close()

            lm_all = get_lesson_metrics(tf_path)
            self.assertEqual(lm_all["completed_curated_count"], len(LESSONS))
            self.assertEqual(lm_all["completion_percentage"], 100.0)
            self.assertEqual(lm_all["remaining_curated_count"], 0)
            recs_all = generate_recommendations(lm_all, qm, fm)
            rec_all = [r for r in recs_all if r["category"] == "Lessons"][0]
            self.assertEqual(rec_all["id"], "rec_lesson_completed_all")
        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_04_dashboard_multiple_quiz_attempts(self):
        """Test quiz score averages, best score, and topic breakdown."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            tf_path = pathlib.Path(tf.name)
        try:
            conn = sqlite3.connect(str(tf_path))
            conn.execute("CREATE TABLE quiz_attempts (id INTEGER PRIMARY KEY, topic TEXT, score INTEGER, total INTEGER, timestamp TEXT)")
            # Attempt 1: Shopping 5/5 = 100%
            conn.execute("INSERT INTO quiz_attempts VALUES (1, 'Shopping', 5, 5, '2026-10-18 10:00:00')")
            # Attempt 2: Transport 2/5 = 40%
            conn.execute("INSERT INTO quiz_attempts VALUES (2, 'Transport', 2, 5, '2026-10-19 11:00:00')")
            # Attempt 3: Restaurant 4/5 = 80%
            conn.execute("INSERT INTO quiz_attempts VALUES (3, 'Restaurant', 4, 5, '2026-10-20 09:00:00')")
            conn.commit()
            conn.close()

            qm = get_quiz_metrics(tf_path)
            self.assertTrue(qm["has_attempts"])
            self.assertEqual(qm["total_attempts"], 3)
            # (100 + 40 + 80) / 3 = 73.3%
            self.assertEqual(qm["average_score_pct"], 73.3)
            self.assertEqual(qm["best_score_pct"], 100.0)
            self.assertEqual(len(qm["recent_attempts"]), 3)

            # Topics:
            # Shopping: 100%
            # Restaurant: 80%
            # Transport: 40% (needs improvement, < 70%)
            self.assertEqual(len(qm["best_topics"]), 2)  # Shopping and Restaurant (>= 80%)
            self.assertEqual(len(qm["needs_improvement_topics"]), 1)
            self.assertEqual(qm["needs_improvement_topics"][0]["topic"], "Transport")
            self.assertEqual(qm["needs_improvement_topics"][0]["avg_pct"], 40.0)

            # Recommendations should specifically target Transport
            lm = {"completed_curated_count": 1, "total_curated": 8, "remaining_curated_count": 7, "remaining_curated_list": LESSONS[1:]}
            fm = {"total_favourites": 2, "has_session_revision": False}
            recs = generate_recommendations(lm, qm, fm)
            q_rec = [r for r in recs if r["category"] == "Quiz"][0]
            self.assertEqual(q_rec["id"], "rec_quiz_improve")
            self.assertIn("Transport", q_rec["title"])
            self.assertEqual(q_rec["nav_kwargs"]["quiz_topic_picker"], "Transport")
        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_05_dashboard_no_favourites(self):
        """Test favourites metrics when no phrases are favourited."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            tf_path = pathlib.Path(tf.name)
        try:
            conn = sqlite3.connect(str(tf_path))
            conn.execute("CREATE TABLE favourites (id TEXT PRIMARY KEY, kn TEXT UNIQUE, roman TEXT, meaning_en TEXT, meaning_ta TEXT, topic TEXT, created_at TEXT)")
            conn.commit()
            conn.close()

            fm = get_favourites_and_revision_metrics(tf_path)
            self.assertEqual(fm["total_favourites"], 0)
            self.assertEqual(fm["topic_counts"], {})
            self.assertEqual(fm["recent_favourites"], [])
            self.assertFalse(fm["is_revision_persisted"])

            lm = {"completed_curated_count": 1, "total_curated": 8, "remaining_curated_count": 7, "remaining_curated_list": LESSONS[1:]}
            qm = {"has_attempts": False}
            recs = generate_recommendations(lm, qm, fm)
            fav_rec = [r for r in recs if r["category"] == "Favourites"][0]
            self.assertEqual(fav_rec["id"], "rec_fav_bookmark")
            self.assertEqual(fav_rec["nav_page"], "Phrasebook")
        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_06_dashboard_with_favourites(self):
        """Test favourites metrics with saved favourites."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            tf_path = pathlib.Path(tf.name)
        try:
            conn = sqlite3.connect(str(tf_path))
            conn.execute("CREATE TABLE favourites (id TEXT PRIMARY KEY, kn TEXT UNIQUE, roman TEXT, meaning_en TEXT, meaning_ta TEXT, topic TEXT, created_at TEXT)")
            conn.execute("INSERT INTO favourites VALUES ('f1', 'ನಮಸ್ಕಾರ', 'Namaskara', 'Hello', 'வணக்கம்', 'Greetings', '2026-10-20 10:00:00')")
            conn.execute("INSERT INTO favourites VALUES ('f2', 'ಧನ್ಯವಾದಗಳು', 'Dhanyavadagalu', 'Thank you', 'நன்றி', 'Greetings', '2026-10-20 10:05:00')")
            conn.execute("INSERT INTO favourites VALUES ('f3', 'ಬೆಲೆ ಎಷ್ಟು?', 'Bele eshtu?', 'How much?', 'விலை எவ்வளவு?', 'Shopping', '2026-10-20 10:10:00')")
            conn.commit()
            conn.close()

            fm = get_favourites_and_revision_metrics(tf_path)
            self.assertEqual(fm["total_favourites"], 3)
            self.assertEqual(fm["topic_counts"]["Greetings"], 2)
            self.assertEqual(fm["topic_counts"]["Shopping"], 1)
            self.assertEqual(len(fm["recent_favourites"]), 3)
        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_07_revision_persistence_transparency(self):
        """Verify revision data is clearly reported as session-scoped and not fabricated."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            tf_path = pathlib.Path(tf.name)
        try:
            conn = sqlite3.connect(str(tf_path))
            conn.execute("CREATE TABLE favourites (id TEXT PRIMARY KEY, kn TEXT UNIQUE, roman TEXT, meaning_en TEXT, meaning_ta TEXT, topic TEXT, created_at TEXT)")
            conn.commit()
            conn.close()

            # Test without session revision
            fm_no_rev = get_favourites_and_revision_metrics(tf_path, session_state={})
            self.assertFalse(fm_no_rev["is_revision_persisted"])
            self.assertIn("session", fm_no_rev["revision_persistence_note"].lower())
            self.assertEqual(fm_no_rev["session_known_count"], 0)
            self.assertEqual(fm_no_rev["session_again_count"], 0)
            self.assertFalse(fm_no_rev["has_session_revision"])

            # Test with mock in-session revision state
            mock_session = {"rev_known": {"f1", "f2"}, "rev_again": {"f3"}}
            fm_with_rev = get_favourites_and_revision_metrics(tf_path, session_state=mock_session)
            self.assertFalse(fm_with_rev["is_revision_persisted"])
            self.assertEqual(fm_with_rev["session_known_count"], 2)
            self.assertEqual(fm_with_rev["session_again_count"], 1)
            self.assertTrue(fm_with_rev["has_session_revision"])
        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_08_navigation_state_routing(self):
        """Test set_page_navigation function accurately updates session state dictionary."""
        mock_state = {}

        set_page_navigation("Daily Lessons", state_dict=mock_state, lesson_view="restaurant-01")
        self.assertEqual(mock_state["nav_page"], "Daily Lessons")
        self.assertEqual(mock_state["lesson_view"], "restaurant-01")

        set_page_navigation("My Favourites", state_dict=mock_state, rev_active=True, rev_index=0)
        self.assertEqual(mock_state["nav_page"], "My Favourites")
        self.assertTrue(mock_state["rev_active"])
        self.assertEqual(mock_state["rev_index"], 0)

        set_page_navigation("Interactive Quizzes", state_dict=mock_state, quiz_topic_picker="Shopping")
        self.assertEqual(mock_state["nav_page"], "Interactive Quizzes")
        self.assertEqual(mock_state["quiz_topic_picker"], "Shopping")

    def test_08b_pending_navigation_live_path(self):
        """Live Streamlit path stages nav into _pending_nav_page, not nav_page.

        Regression test for StreamlitWidgetAlreadyInstantiatedError — the
        live path must never write directly to the widget-bound 'nav_page' key.
        """
        from unittest.mock import MagicMock, patch

        mock_ss = {}

        class FakeSessionState(dict):
            """Minimal stand-in for st.session_state."""
            def __setitem__(self, key, value):
                super().__setitem__(key, value)
            def pop(self, key, *args):
                return super().pop(key, *args)

        fake_ss = FakeSessionState()

        with patch("modules.progress_dashboard.st") as mock_st:
            mock_st.session_state = fake_ss
            # Call WITHOUT state_dict → live path
            set_page_navigation("Daily Lessons", lesson_view="index")
            self.assertEqual(fake_ss["_pending_nav_page"], "Daily Lessons")
            self.assertEqual(fake_ss["_pending_nav_kwargs"], {"lesson_view": "index"})
            # Must NOT have written to nav_page directly
            self.assertNotIn("nav_page", fake_ss)

    def test_08c_pending_navigation_kwargs(self):
        """Verify all kwargs are correctly staged in _pending_nav_kwargs."""
        from unittest.mock import patch

        class FakeSessionState(dict):
            pass

        fake_ss = FakeSessionState()

        with patch("modules.progress_dashboard.st") as mock_st:
            mock_st.session_state = fake_ss
            set_page_navigation(
                "My Favourites",
                rev_active=True,
                rev_index=0,
                rev_revealed=False,
                rev_known=set(),
                rev_again=set(),
            )
            self.assertEqual(fake_ss["_pending_nav_page"], "My Favourites")
            kw = fake_ss["_pending_nav_kwargs"]
            self.assertTrue(kw["rev_active"])
            self.assertEqual(kw["rev_index"], 0)
            self.assertFalse(kw["rev_revealed"])
            self.assertEqual(kw["rev_known"], set())
            self.assertEqual(kw["rev_again"], set())
            self.assertNotIn("nav_page", fake_ss)

    def test_08d_daily_lessons_curriculum_navigation(self):
        """'Go to Daily Lessons Curriculum' must navigate to Daily Lessons with lesson_view=index."""
        from unittest.mock import patch

        class FakeSessionState(dict):
            pass

        fake_ss = FakeSessionState()

        with patch("modules.progress_dashboard.st") as mock_st:
            mock_st.session_state = fake_ss
            set_page_navigation("Daily Lessons", lesson_view="index")
            self.assertEqual(fake_ss["_pending_nav_page"], "Daily Lessons")
            self.assertEqual(fake_ss["_pending_nav_kwargs"]["lesson_view"], "index")

    def test_08e_quiz_navigation_pending(self):
        """Quiz navigation from dashboard must use pending path."""
        from unittest.mock import patch

        class FakeSessionState(dict):
            pass

        fake_ss = FakeSessionState()

        with patch("modules.progress_dashboard.st") as mock_st:
            mock_st.session_state = fake_ss
            set_page_navigation("Interactive Quizzes", quiz_questions=[], quiz_submitted=False)
            self.assertEqual(fake_ss["_pending_nav_page"], "Interactive Quizzes")
            self.assertEqual(fake_ss["_pending_nav_kwargs"]["quiz_questions"], [])
            self.assertFalse(fake_ss["_pending_nav_kwargs"]["quiz_submitted"])
            self.assertNotIn("nav_page", fake_ss)


    def test_09_production_data_safely_readable(self):
        """Read metrics on actual production DBs without altering any records."""
        lm = get_lesson_metrics(self.prod_lesson_db)
        qm = get_quiz_metrics(self.prod_quiz_db)
        fm = get_favourites_and_revision_metrics(self.prod_lesson_db)

        self.assertEqual(lm["total_curated"], 8)
        self.assertEqual(lm["completed_curated_count"], 1)  # 'greetings-01'
        self.assertEqual(lm["completion_percentage"], 12.5)  # 1/8 * 100

        self.assertTrue(qm["has_attempts"])
        self.assertEqual(qm["total_attempts"], 1)
        self.assertEqual(qm["average_score_pct"], 80.0)  # 4/5 * 100

        self.assertEqual(fm["total_favourites"], 4)
        self.assertFalse(fm["is_revision_persisted"])

    def test_10_regression_all_modules(self):
        """Verify all existing modules remain functional."""
        # 1. Phrases
        self.assertGreater(len(phrases.PHRASES), 10)
        self.assertIn("Shopping", phrases.SCENARIOS)

        # 2. Lessons
        self.assertEqual(len(LESSONS), 8)
        self.assertEqual(len(LESSON_IDS), 8)

        # 3. Lesson Progress
        self.assertTrue(hasattr(lesson_progress, "get_completed_ids"))
        self.assertTrue(hasattr(lesson_progress, "mark_completed"))

        # 4. Quiz Progress
        self.assertTrue(hasattr(quiz_progress, "save_quiz_attempt"))
        self.assertTrue(hasattr(quiz_progress, "get_recent_attempts"))

        # 5. Favourites
        self.assertTrue(hasattr(favourites, "add_favourite"))
        self.assertTrue(hasattr(favourites, "get_all_favourites"))

        # 6. Voice
        self.assertTrue(hasattr(voice, "make_audio"))

        # 7. AI Coach
        self.assertTrue(hasattr(ai_coach, "generate_reply"))

        # 8. Check app.py navigation options
        app_path = PROJECT_ROOT / "app.py"
        app_code = app_path.read_text(encoding="utf-8")
        self.assertIn('"Learning Progress"', app_code)
        self.assertIn('render_learning_progress_dashboard', app_code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
