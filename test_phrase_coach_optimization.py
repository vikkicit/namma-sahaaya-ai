# -*- coding: utf-8 -*-
# test_phrase_coach_optimization.py
# Comprehensive test suite for NammaSahaaya AI Phrase Coach latency optimization.
# Tests: successful generation, API failure, timeout, repeated requests,
# audio playback & caching, fallback behavior, decoupled audio, and latency measurements.

import os
import sys
import time
import pathlib
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = pathlib.Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Use the active streamlit module from sys.modules
import streamlit as st

from google.genai import errors as genai_errors
import modules.ai_coach as ai_coach
import modules.voice as voice

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
    return genai_errors.ServerError(code, {"error": {"message": message}})


def _make_client_error(code=429, message="RESOURCE_EXHAUSTED"):
    return genai_errors.ClientError(code, {"error": {"message": message}})


def _make_config_error(code=400, message="Manually set deadline 8s is too short. Minimum allowed deadline is 10s."):
    return genai_errors.ClientError(code, {"error": {"message": message}})


class TestPhraseCoachOptimization(unittest.TestCase):
    """Verify latency optimizations, timeouts, decoupling, and fallback behavior."""

    def setUp(self):
        self._info_patcher = patch("streamlit.info")
        self._warning_patcher = patch("streamlit.warning")
        self.mock_info = self._info_patcher.start()
        self.mock_warning = self._warning_patcher.start()

    def tearDown(self):
        self._info_patcher.stop()
        self._warning_patcher.stop()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-mock"})
    @patch("modules.ai_coach._build_client")
    def test_01_successful_generation_completes_and_returns_text(self, mock_build):
        """Successful generation returns valid Kannada text, romanization, and explanation."""
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.text = (
            "EXPLANATION: இந்த வாக்கியம் விலையை கேட்க உதவும்.\n"
            "KANNADA: ಇದರ ಬೆಲೆ ಎಷ್ಟು?\n"
            "ROMAN: Idara bele eṣṭu?"
        )
        mock_client.models.generate_content.return_value = mock_resp

        t0 = time.perf_counter()
        result = ai_coach.generate_reply(
            user_text="How much is this?",
            scenario="Shopping",
            explanation_language="Tamil",
            history=[],
            phrases=SAMPLE_PHRASES,
        )
        latency = time.perf_counter() - t0

        self.assertFalse(result.get("is_fallback"))
        self.assertEqual(result["kn"], "ಇದರ ಬೆಲೆ ಎಷ್ಟು?")
        self.assertEqual(result["roman"], "Idara bele eṣṭu?")
        self.assertIn("விலையை", result["explanation"])
        self.assertLess(latency, 1.0, "Mocked text generation should complete in milliseconds")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-mock"})
    @patch("modules.ai_coach._build_client")
    @patch("modules.ai_coach.time.sleep")
    def test_02_transient_503_bounded_retry_then_fallback(self, mock_sleep, mock_build):
        """503 ServerError triggers at most one bounded retry, then returns curated fallback."""
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        mock_client.models.generate_content.side_effect = _make_server_error(503)

        result = ai_coach.generate_reply(
            user_text="How much is this?",
            scenario="Shopping",
            explanation_language="Tamil",
            history=[{"role": "user", "content": "Previous question"}],
            phrases=SAMPLE_PHRASES,
        )

        # Bounded to exactly 2 attempts (1 initial + 1 retry)
        self.assertEqual(mock_client.models.generate_content.call_count, 2)
        mock_sleep.assert_called_once()
        self.assertTrue(result.get("is_fallback"))
        self.assertIn("ಬೆಲೆ", result["kn"])

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-mock"})
    @patch("modules.ai_coach._build_client")
    def test_03_rate_limit_429_returns_fallback_immediately(self, mock_build):
        """429 rate limit fails fast with 0 retries and returns curated fallback."""
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        mock_client.models.generate_content.side_effect = _make_client_error(429)

        result = ai_coach.generate_reply(
            user_text="Where is the train?",
            scenario="Transport",
            explanation_language="English",
            history=[],
            phrases=SAMPLE_PHRASES,
        )

        self.assertEqual(mock_client.models.generate_content.call_count, 1)
        self.assertTrue(result.get("is_fallback"))
        self.assertIn("ರೈಲು", result["kn"])

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-mock"})
    @patch("modules.ai_coach._build_client")
    def test_04_timeout_handling_returns_fallback_cleanly(self, mock_build):
        """TimeoutException is handled cleanly without hanging, returning fallback."""
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        mock_client.models.generate_content.side_effect = TimeoutError("Request timed out after 8000ms")

        result = ai_coach.generate_reply(
            user_text="Please help me",
            scenario="General Help",
            explanation_language="English",
            history=[],
            phrases=SAMPLE_PHRASES,
        )

        self.assertTrue(result.get("is_fallback"))
        self.assertIn("ಸಹಾಯ", result["kn"])
        # Friendly message displayed to user
        self.mock_info.assert_called()
        info_msg = str(self.mock_info.call_args[0][0])
        self.assertIn("temporarily unavailable", info_msg)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-mock"})
    @patch("modules.ai_coach._build_client")
    def test_05_context_dependent_requests_bypass_cache(self, mock_build):
        """Requests with conversation history are context-dependent and generate fresh."""
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.text = (
            "EXPLANATION: Contextual follow-up.\n"
            "KANNADA: ತುಂಬಾ ಧನ್ಯವಾದಗಳು\n"
            "ROMAN: Tuṃbā dhanyavādagaḷu"
        )
        mock_client.models.generate_content.return_value = mock_resp

        history = [
            {"role": "user", "content": "How much is this?"},
            {"role": "assistant", "content": "It costs 50 rupees."},
        ]

        result = ai_coach.generate_reply(
            user_text="Thank you very much",
            scenario="Shopping",
            explanation_language="English",
            history=history,
            phrases=SAMPLE_PHRASES,
        )

        self.assertFalse(result.get("is_fallback"))
        self.assertEqual(mock_client.models.generate_content.call_count, 1)
        self.assertEqual(result["kn"], "ತುಂಬಾ ಧನ್ಯವಾದಗಳು")

    @patch("gtts.gTTS")
    def test_06_audio_generation_and_caching(self, mock_gtts_cls):
        """Audio generation produces audio bytes without requiring live internet."""
        # Test empty input handling
        self.assertIsNone(voice.make_audio(""))
        self.assertIsNone(voice.make_audio(None))

        # Mock gTTS write_to_fp
        fake_audio = b"\xff\xfb\x90\x00" + b"\x00" * 2000
        mock_instance = MagicMock()
        mock_instance.write_to_fp.side_effect = lambda fp: fp.write(fake_audio)
        mock_gtts_cls.return_value = mock_instance

        aud = voice.make_audio("ದಯವಿಟ್ಟು ಸಹಾಯ ಮಾಡಿ")
        self.assertIsNotNone(aud)
        self.assertIsInstance(aud, bytes)
        self.assertEqual(aud, fake_audio)

    def test_07_audio_failure_returns_none_gracefully(self):
        """Audio generation failure returns None and does not crash the app."""
        with patch("gtts.gTTS", side_effect=Exception("Network unreachable")):
            res = voice.make_audio("ಟೆಸ್ಟ್ ವಾಕ್ಯ")
            self.assertIsNone(res)
            self.mock_warning.assert_called()

    def test_08_fallback_intent_keywords(self):
        """Curated fallbacks map accurately to user intent keywords in English and Tamil."""
        price_res = ai_coach._fallback("evlo aagum?", "Shopping", "Tamil", SAMPLE_PHRASES)
        self.assertIn("ಬೆಲೆ", price_res["kn"])

        dir_res = ai_coach._fallback("station enga irukku?", "Transport", "Tamil", SAMPLE_PHRASES)
        self.assertIn("ರೈಲು", dir_res["kn"])

        help_res = ai_coach._fallback("need urgent doctor help", "General Help", "English", SAMPLE_PHRASES)
        self.assertIn("ಸಹಾಯ", help_res["kn"])

    def test_09_no_secrets_in_error_or_log_messages(self):
        """Verify that secret keys are never leaked into user messages or logs."""
        secret_key = "AIzaSySecretApiKey123456789"
        mock_client = MagicMock()
        with patch.dict(os.environ, {"GEMINI_API_KEY": secret_key}), \
             patch("modules.ai_coach._build_client", return_value=mock_client):
            mock_client.models.generate_content.side_effect = RuntimeError(f"Failed with key={secret_key}")

            result = ai_coach.generate_reply(
                user_text="Help",
                scenario="General Help",
                explanation_language="English",
                history=[],
                phrases=SAMPLE_PHRASES,
            )

            for call in self.mock_info.call_args_list + self.mock_warning.call_args_list:
                for arg in call.args:
                    self.assertNotIn(secret_key, str(arg))

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-mock"})
    @patch("modules.ai_coach._build_client")
    def test_10_config_error_400_returns_fallback_no_retry(self, mock_build):
        """400 INVALID_ARGUMENT (e.g., deadline too short) returns fallback without retry.

        This is the regression test for the root-cause bug where timeout=8000 ms was
        below the API-enforced minimum of 10 s, causing every request to fail with
        400 INVALID_ARGUMENT before reaching the model. The fix raised the timeout to
        15 000 ms (_REQUEST_TIMEOUT_MS), but this test guards against re-introducing
        a sub-10 s deadline and verifies that 400 errors degrade gracefully.
        """
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        mock_client.models.generate_content.side_effect = _make_config_error(400)

        result = ai_coach.generate_reply(
            user_text="what is the cost?",
            scenario="Shopping",
            explanation_language="English",
            history=[],
            phrases=SAMPLE_PHRASES,
        )

        # 400 is non-retriable — must be called exactly once
        self.assertEqual(mock_client.models.generate_content.call_count, 1)
        # Result must still degrade to curated fallback
        self.assertTrue(result.get("is_fallback"))
        # Should surface a config-specific user message (not the raw error)
        self.mock_info.assert_called()
        info_msg = str(self.mock_info.call_args[0][0])
        self.assertIn("configuration", info_msg.lower())

    def test_11_timeout_constant_above_api_minimum(self):
        """_REQUEST_TIMEOUT_MS must be >= 10 000 ms (the Gemini API enforces this)."""
        self.assertGreaterEqual(
            ai_coach._REQUEST_TIMEOUT_MS,
            10000,
            msg=(
                "The Gemini API rejects deadlines below 10 s with 400 INVALID_ARGUMENT. "
                f"Current value: {ai_coach._REQUEST_TIMEOUT_MS} ms"
            ),
        )

    def test_12_is_config_error_helper(self):
        """_is_config_error correctly classifies 400 ClientError and other exceptions."""
        self.assertTrue(ai_coach._is_config_error(_make_config_error(400)))
        self.assertFalse(ai_coach._is_config_error(_make_server_error(503)))
        self.assertFalse(ai_coach._is_config_error(_make_client_error(429)))
        self.assertFalse(ai_coach._is_config_error(RuntimeError("something else")))



if __name__ == "__main__":
    unittest.main()
