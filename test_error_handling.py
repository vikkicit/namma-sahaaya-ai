# test_error_handling.py
# Tests for Gemini API 503/rate-limit error handling, fallback behavior,
# and missing-key behavior in ai_coach.py and daily_lesson_generator.py.
# Uses isolated mocks — never calls the real Gemini API.

import os
import pathlib
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

PROJECT_ROOT = pathlib.Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# ──────────────────────────────────────────────────────────────────────────────
# Mock Streamlit before importing modules that use it at module level
# ──────────────────────────────────────────────────────────────────────────────
mock_st = MagicMock()
sys.modules.setdefault("streamlit", mock_st)

from google.genai import errors as genai_errors

from modules.daily_lesson_generator import (
    generate_daily_lesson_from_gemini,
    get_daily_lesson,
    get_curated_fallback,
    get_saved_daily_lesson,
)
import modules.ai_coach as ai_coach

# Sample phrasebook entries for AI Coach fallback tests
SAMPLE_PHRASES = [
    {
        "scenario": "Shopping",
        "kn": "ಇದರ ಬೆಲೆ ಎಷ್ಟು?",
        "roman": "Idara bele eṣṭu?",
        "meaning_en": "How much does this cost?",
        "meaning_ta": "இதன் விலை எவ்வளவு?",
        "intent": "price",
    },
    {
        "scenario": "Transport",
        "kn": "ರೈಲು ನಿಲ್ದಾಣ ಎಲ್ಲಿದೆ?",
        "roman": "Railu nildāṇa ellide?",
        "meaning_en": "Where is the railway station?",
        "meaning_ta": "ரயில் நிலையம் எங்கே உள்ளது?",
        "intent": "directions",
    },
    {
        "scenario": "General Help",
        "kn": "ದಯವಿಟ್ಟು ಸಹಾಯ ಮಾಡಿ",
        "roman": "Dayaviṭṭu sahāya māḍi",
        "meaning_en": "Please help me",
        "meaning_ta": "தயவுசெய்து எனக்கு உதவுங்கள்",
        "intent": "help",
    },
]


def _make_server_error(code=503, message="The model is overloaded"):
    """Create a google.genai.errors.ServerError with the given code."""
    response_json = {"error": {"message": message}}
    return genai_errors.ServerError(code, response_json)


def _make_client_error(code=429, message="RESOURCE_EXHAUSTED"):
    """Create a google.genai.errors.ClientError with the given code."""
    response_json = {"error": {"message": message}}
    return genai_errors.ClientError(code, response_json)


# ══════════════════════════════════════════════════════════════════════════════
# AI Coach — Error Handling Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestAiCoach503Handling(unittest.TestCase):
    """Verify AI Coach handles 503 UNAVAILABLE gracefully."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-never-used"})
    @patch("modules.ai_coach.genai")
    @patch("modules.ai_coach.time")
    def test_503_returns_fallback_with_friendly_message(self, mock_time, mock_genai):
        """A 503 ServerError should return a curated fallback phrase, not crash."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.side_effect = _make_server_error(503)

        result = ai_coach.generate_reply(
            user_text="How much is this?",
            scenario="Shopping",
            explanation_language="English",
            history=[],
            phrases=SAMPLE_PHRASES,
        )

        # Must return a valid fallback result, not raise
        self.assertIn("kn", result)
        self.assertIn("roman", result)
        self.assertIn("explanation", result)
        # Fallback flag must be set so UI knows this is not a Gemini response
        self.assertTrue(result.get("is_fallback", False))

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-never-used"})
    @patch("modules.ai_coach.genai")
    @patch("modules.ai_coach.time")
    def test_503_retries_once_then_falls_back(self, mock_time, mock_genai):
        """On 503, the coach should retry once (with short delay) then fall back."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        # Both attempts return 503
        err = _make_server_error(503)
        mock_client.models.generate_content.side_effect = [err, err]

        result = ai_coach.generate_reply(
            user_text="Where is the station?",
            scenario="Transport",
            explanation_language="English",
            history=[],
            phrases=SAMPLE_PHRASES,
        )

        # Should have attempted generation exactly twice (1 initial + 1 retry)
        self.assertEqual(mock_client.models.generate_content.call_count, 2)
        # Must still return a valid result
        self.assertIn("kn", result)
        self.assertTrue(result.get("is_fallback", False))
        # time.sleep should have been called once for the retry delay
        mock_time.sleep.assert_called_once()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-never-used"})
    @patch("modules.ai_coach.genai")
    @patch("modules.ai_coach.time")
    def test_503_retry_succeeds_on_second_attempt(self, mock_time, mock_genai):
        """If the retry after 503 succeeds, return the AI response (not fallback)."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = (
            "EXPLANATION: This phrase asks about the price.\n"
            "KANNADA: ಇದರ ಬೆಲೆ ಎಷ್ಟು?\n"
            "ROMAN: Idara bele eṣṭu?"
        )

        err_503 = _make_server_error(503)
        mock_client.models.generate_content.side_effect = [err_503, mock_response]

        result = ai_coach.generate_reply(
            user_text="How much is this?",
            scenario="Shopping",
            explanation_language="English",
            history=[],
            phrases=SAMPLE_PHRASES,
        )

        # Should be the real AI response, not a fallback
        self.assertIn("ಇದರ ಬೆಲೆ ಎಷ್ಟು?", result["kn"])
        self.assertFalse(result.get("is_fallback", False))

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-never-used"})
    @patch("modules.ai_coach.genai")
    def test_503_does_not_expose_raw_error(self, mock_genai):
        """The error message shown to users must not contain raw exception text."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.side_effect = _make_server_error(
            503, "Internal server error with api_key=AIzaSy..."
        )

        # Reset streamlit mock to capture calls
        mock_st.reset_mock()

        result = ai_coach.generate_reply(
            user_text="help me",
            scenario="General Help",
            explanation_language="English",
            history=[],
            phrases=SAMPLE_PHRASES,
        )

        # Check that st.error was NOT called (we use st.info for friendly messages)
        mock_st.error.assert_not_called()

        # Verify no call argument contains the fake API key
        for call in mock_st.info.call_args_list + mock_st.warning.call_args_list:
            for arg in call.args:
                self.assertNotIn("AIzaSy", str(arg))


class TestAiCoach429Handling(unittest.TestCase):
    """Verify AI Coach handles 429 rate-limit errors gracefully."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-never-used"})
    @patch("modules.ai_coach.genai")
    def test_429_returns_fallback_without_retry(self, mock_genai):
        """A 429 ClientError should NOT be retried — return fallback immediately."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.side_effect = _make_client_error(429)

        result = ai_coach.generate_reply(
            user_text="How much is this?",
            scenario="Shopping",
            explanation_language="English",
            history=[],
            phrases=SAMPLE_PHRASES,
        )

        # Only one attempt — no retry for rate limits
        self.assertEqual(mock_client.models.generate_content.call_count, 1)
        self.assertIn("kn", result)
        self.assertTrue(result.get("is_fallback", False))


class TestAiCoachMissingKey(unittest.TestCase):
    """Verify AI Coach handles missing GEMINI_API_KEY gracefully."""

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_key_returns_fallback(self):
        """When GEMINI_API_KEY is missing, return a curated fallback."""
        # Ensure the key is truly absent
        os.environ.pop("GEMINI_API_KEY", None)

        result = ai_coach.generate_reply(
            user_text="hello",
            scenario="General Help",
            explanation_language="English",
            history=[],
            phrases=SAMPLE_PHRASES,
        )

        self.assertIn("kn", result)
        self.assertIn("roman", result)
        self.assertTrue(result.get("is_fallback", False))


class TestAiCoachFallbackIntentMatching(unittest.TestCase):
    """Verify fallback returns a relevant phrase, not a random one."""

    def test_price_query_returns_price_phrase(self):
        result = ai_coach._fallback(
            "how much does this cost?",
            "Shopping",
            "English",
            SAMPLE_PHRASES,
        )
        self.assertIn("ಬೆಲೆ", result["kn"])  # price-related Kannada
        self.assertTrue(result.get("is_fallback", False))

    def test_directions_query_returns_directions_phrase(self):
        result = ai_coach._fallback(
            "where is the bus station?",
            "Transport",
            "English",
            SAMPLE_PHRASES,
        )
        self.assertIn("ನಿಲ್ದಾಣ", result["kn"])  # station-related Kannada
        self.assertTrue(result.get("is_fallback", False))


# ══════════════════════════════════════════════════════════════════════════════
# Daily Lesson Generator — Error Handling Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestDailyLessonGenerator503(unittest.TestCase):
    """Verify daily lesson generator handles 503 with curated fallback + SQLite."""

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = pathlib.Path(self.temp_file.name)
        self.temp_file.close()

    def tearDown(self):
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except Exception:
                pass

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-never-used"})
    @patch("modules.daily_lesson_generator.time")
    def test_503_returns_curated_fallback_with_reason(self, mock_time):
        """A 503 from Gemini should produce a curated fallback lesson with a diagnostic reason."""
        # daily_lesson_generator does a local `from google import genai` inside the function,
        # so we patch at the google.genai.Client level
        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.models.generate_content.side_effect = _make_server_error(503)

            lesson, error = generate_daily_lesson_from_gemini("2026-11-01")

        self.assertIsNone(lesson)
        self.assertIn("503", error)
        self.assertIn("high demand", error.lower())
        # Ensure no raw exception text leaked
        self.assertNotIn("test-key", error)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-never-used"})
    @patch("modules.daily_lesson_generator.time")
    def test_503_retries_once_before_failing(self, mock_time):
        """Generator should retry once on 503, then return error diagnostic."""
        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            err = _make_server_error(503)
            mock_client.models.generate_content.side_effect = [err, err]

            lesson, error = generate_daily_lesson_from_gemini("2026-11-01")

        # Should have tried twice
        self.assertEqual(mock_client.models.generate_content.call_count, 2)
        self.assertIsNone(lesson)
        self.assertIn("503", error)
        # time.sleep called once for the retry
        mock_time.sleep.assert_called_once()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-never-used"})
    def test_503_full_lifecycle_saves_curated_fallback_in_sqlite(self):
        """Full get_daily_lesson call on 503 should persist curated_fallback in SQLite."""
        with patch("modules.daily_lesson_generator.generate_daily_lesson_from_gemini") as mock_gen:
            mock_gen.return_value = (None, "Gemini model is currently experiencing high demand (503 Unavailable).")

            lesson = get_daily_lesson("2026-11-02", db_path=self.db_path)

        self.assertEqual(lesson["source"], "curated_fallback")
        self.assertIn("fallback_reason", lesson)
        self.assertIn("503", lesson["fallback_reason"])

        # Verify it's persisted in SQLite
        saved = get_saved_daily_lesson("2026-11-02", db_path=self.db_path)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["source"], "curated_fallback")


class TestDailyLessonGenerator429(unittest.TestCase):
    """Verify daily lesson generator handles 429 rate-limit errors."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-never-used"})
    def test_429_returns_rate_limit_diagnostic(self):
        """A 429 error should produce a clear rate-limit diagnostic, no retry."""
        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.models.generate_content.side_effect = _make_client_error(429)

            lesson, error = generate_daily_lesson_from_gemini("2026-11-03")

        # Only one attempt — no retry for rate limits
        self.assertEqual(mock_client.models.generate_content.call_count, 1)
        self.assertIsNone(lesson)
        self.assertIn("rate limit", error.lower())


class TestDailyLessonGeneratorMissingKey(unittest.TestCase):
    """Verify daily lesson generator handles missing API key gracefully."""

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_key_returns_error(self):
        """When GEMINI_API_KEY is absent, return None + clear error message."""
        os.environ.pop("GEMINI_API_KEY", None)
        lesson, error = generate_daily_lesson_from_gemini("2026-11-04")
        self.assertIsNone(lesson)
        self.assertIn("GEMINI_API_KEY", error)
        # Must NOT contain any actual key value
        self.assertNotIn("AIzaSy", error)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_key_full_lifecycle_gives_curated_fallback(self):
        """Full get_daily_lesson with missing key should still return a curated lesson."""
        os.environ.pop("GEMINI_API_KEY", None)
        temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = pathlib.Path(temp_file.name)
        temp_file.close()

        try:
            lesson = get_daily_lesson("2026-11-05", db_path=db_path)
            self.assertEqual(lesson["source"], "curated_fallback")
            self.assertIn("phrases", lesson)
            self.assertGreater(len(lesson["phrases"]), 0)
        finally:
            if db_path.exists():
                db_path.unlink()


class TestCuratedFallbackConsistency(unittest.TestCase):
    """Verify curated fallback is deterministic and well-structured."""

    def test_same_date_returns_same_fallback(self):
        """Curated fallback for the same date should always pick the same lesson."""
        fb1 = get_curated_fallback("2026-11-10")
        fb2 = get_curated_fallback("2026-11-10")
        self.assertEqual(fb1["title"], fb2["title"])
        self.assertEqual(fb1["id"], fb2["id"])

    def test_fallback_has_required_fields(self):
        """Curated fallback must include all fields the UI expects."""
        fb = get_curated_fallback("2026-11-11", reason="Test reason")
        required_fields = ["id", "date", "title", "topic", "difficulty",
                           "objectives", "phrases", "practice", "review",
                           "source", "fallback_reason"]
        for field in required_fields:
            self.assertIn(field, fb, f"Missing required field: {field}")
        self.assertEqual(fb["source"], "curated_fallback")
        self.assertEqual(fb["fallback_reason"], "Test reason")


class TestNoRawErrorExposure(unittest.TestCase):
    """Ensure no raw API errors, credentials, or secret values leak to users."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "super-secret-key-12345"})
    @patch("modules.ai_coach.genai")
    def test_ai_coach_generic_error_hides_details(self, mock_genai):
        """A generic Exception should not expose its message to the user."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.side_effect = RuntimeError(
            "Connection failed with api_key=super-secret-key-12345"
        )

        mock_st.reset_mock()
        result = ai_coach.generate_reply(
            user_text="test",
            scenario="General Help",
            explanation_language="English",
            history=[],
            phrases=SAMPLE_PHRASES,
        )

        # st.error should NOT have been called
        mock_st.error.assert_not_called()

        # No call should contain the secret key
        for call in (mock_st.info.call_args_list +
                     mock_st.warning.call_args_list +
                     mock_st.error.call_args_list):
            for arg in call.args:
                self.assertNotIn("super-secret-key", str(arg))

    @patch.dict(os.environ, {"GEMINI_API_KEY": "super-secret-key-12345"})
    def test_daily_gen_generic_error_hides_details(self):
        """Daily lesson generator should not leak API key in error diagnostics."""
        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.models.generate_content.side_effect = RuntimeError(
                "SSL error with api_key=super-secret-key-12345"
            )

            lesson, error = generate_daily_lesson_from_gemini("2026-11-06")

        self.assertIsNone(lesson)
        self.assertNotIn("super-secret-key", error)
        self.assertNotIn("api_key=", error)


if __name__ == "__main__":
    unittest.main(verbosity=2)
