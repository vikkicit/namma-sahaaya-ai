
import logging
import os
import re
import time
import streamlit as st
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

logger = logging.getLogger("namma_sahaaya.ai_coach")

MODEL_NAME = "gemini-3.8-flash"

# Retry configuration for transient server errors (503 / overload)
_MAX_RETRIES = 1
# Note: 2 s gives the server a moment to recover before the single bounded retry.
_RETRY_DELAY_SECONDS = 2.0

# The Gemini API enforces a minimum deadline of 10 s; values below that cause an
# immediate 400 INVALID_ARGUMENT before the request even reaches the model.
# 15 s gives a comfortable margin while still bounding wall-clock wait time.
_REQUEST_TIMEOUT_MS = 15000

def _build_client(api_key):
    """Create a Gemini client with a bounded HTTP request timeout and bounded retries."""
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=_REQUEST_TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


def _fallback(user_text, scenario, explanation_language, phrases):
    """Return a relevant phrasebook response if Gemini fails."""
    text = (user_text or "").lower()

    keywords = {
        "price": ["price", "cost", "costs", "விலை", "evlo", "how much"],
        "directions": [
            "where", "station", "எங்கே", "enga", "direction",
            "bus", "hospital", "location",
        ],
        "help": ["help", "உதவி", "doctor", "pain", "வலி"],
        "menu": ["menu", "food", "சாப்பாடு", "water", "தண்ணீர்"],
        "thanks": ["thank", "நன்றி"],
    }

    chosen = None
    for intent, words in keywords.items():
        if any(word in text for word in words):
            chosen = next(
                (p for p in phrases if p.get("intent") == intent),
                None,
            )
            if chosen:
                break

    if not chosen and phrases:
        chosen = phrases[0]

    if chosen:
        explanation = (
            "AI பதில் கிடைக்கவில்லை. இந்த வாக்கியத்தைப் பயன்படுத்தலாம்."
            if explanation_language == "Tamil"
            else "AI is unavailable. Here is a phrase from the phrasebook."
        )
        return {
            "explanation": explanation,
            "kn": chosen.get("kn", "ದಯವಿಟ್ಟು ಸಹಾಯ ಮಾಡಿ"),
            "roman": chosen.get("roman", "Dayaviṭṭu sahāya māḍಿ"),
            "is_fallback": True,
        }

    return {
        "explanation": "Try asking for directions, a price, or help.",
        "kn": "ದಯವಿಟ್ಟು ಸಹಾಯ ಮಾಡಿ",
        "roman": "Dayaviṭṭu sahāya māḍಿ",
        "is_fallback": True,
    }


def _extract_field(text, label):
    """Extract one labelled line from Gemini's response."""
    pattern = rf"^\s*{re.escape(label)}\s*:\s*(.*?)\s*$"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


def _is_transient_error(exc):
    """Check whether an exception is a transient server error worth retrying."""
    if isinstance(exc, genai_errors.ServerError):
        code = getattr(exc, "code", None)
        return code in (503, 504)
    # Fallback: check string representation for legacy / unexpected wrappers
    err_str = str(exc)
    return "503" in err_str or "UNAVAILABLE" in err_str


def _is_rate_limit_error(exc):
    """Check whether an exception is a rate-limit / quota error."""
    if isinstance(exc, genai_errors.ClientError):
        code = getattr(exc, "code", None)
        return code == 429
    err_str = str(exc)
    return "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()


def _is_config_error(exc):
    """Check whether an exception indicates a client-side configuration problem.

    Examples: 400 INVALID_ARGUMENT (e.g. deadline too short, bad model name).
    These are NOT retried because a retry would fail the same way.
    """
    if isinstance(exc, genai_errors.ClientError):
        code = getattr(exc, "code", None)
        return code == 400
    err_str = str(exc)
    return "400" in err_str and "INVALID_ARGUMENT" in err_str


def _friendly_error_message(exc):
    """Return a safe, user-facing diagnostic string. Never exposes keys or raw traces."""
    if _is_transient_error(exc):
        return (
            "🔄 AI is temporarily busy due to high demand. "
            "We're showing a curated phrase instead. Please try again shortly."
        )
    if _is_rate_limit_error(exc):
        return (
            "⏳ AI request limit reached. "
            "We're showing a curated phrase instead. Please try again later."
        )
    if _is_config_error(exc):
        return (
            "⚙️ AI service configuration issue detected. "
            "We're showing a curated phrase instead. "
            "Please check your API settings and contact support."
        )
    return (
        "⚠️ AI is temporarily unavailable. "
        "We're showing a curated phrase instead. Please try again later."
    )


def generate_reply(
    user_text,
    scenario,
    explanation_language,
    history,
    phrases,
):
    """Generate a Kannada learning response using Gemini."""
    t_start = time.perf_counter()
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        st.warning("GEMINI_API_KEY is missing from your .env file.")
        return _fallback(
            user_text, scenario, explanation_language, phrases
        )

    try:
        client = _build_client(api_key)

        phrase_context = "\n".join(
            f'Kannada: {p.get("kn", "")}; '
            f'Roman: {p.get("roman", "")}; '
            f'English: {p.get("meaning_en", "")}; '
            f'Tamil: {p.get("meaning_ta", "")}'
            for p in phrases
        )

        history_lines = []
        for item in (history or [])[-4:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            message = item.get("content")
            if role in ("user", "assistant") and message:
                history_lines.append(f"{role.upper()}: {message}")

        language = (
            "Tamil"
            if explanation_language == "Tamil"
            else "simple English"
        )

        history_text = "\n".join(history_lines) if history_lines else "None"

        prompt = f"""
You are NammaSahaaya AI, a Kannada language learning coach.

Situation: {scenario}
User request: {user_text}
Explain in {language}.

Recent conversation:
{history_text}

Phrasebook:
{phrase_context}

Return exactly three lines. Do not use Markdown or JSON.
EXPLANATION: A short explanation in {language}
KANNADA: One complete, relevant Kannada sentence in Kannada script
ROMAN: The Latin transliteration of that Kannada sentence

Important:
- Each label must appear at the beginning of its own line.
- Never leave a field empty.
- Do not put labels inside quotation marks.
- Use a relevant phrasebook entry when suitable.
- For hospital situations, help the user communicate; do not diagnose.
"""

        # Attempt generation with at most one short retry for transient errors
        last_error = None
        for attempt in range(_MAX_RETRIES + 1):
            t_req_start = time.perf_counter()
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                    config={
                        "temperature": 0.2,
                        "max_output_tokens": 1000,
                    },
                )
                req_dur = time.perf_counter() - t_req_start
                logger.info(
                    "Gemini request completed in %.3fs (attempt %d/%d, model: %s)",
                    req_dur,
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    MODEL_NAME,
                )
                last_error = None
                break  # Success — exit retry loop
            except (genai_errors.ServerError, genai_errors.ClientError) as api_err:
                req_dur = time.perf_counter() - t_req_start
                last_error = api_err
                if _is_transient_error(api_err) and attempt < _MAX_RETRIES:
                    logger.warning(
                        "Gemini request transient error on attempt %d/%d after %.3fs (%s). Retrying in %.1fs...",
                        attempt + 1,
                        _MAX_RETRIES + 1,
                        req_dur,
                        type(api_err).__name__,
                        _RETRY_DELAY_SECONDS,
                    )
                    time.sleep(_RETRY_DELAY_SECONDS)
                    continue
                break  # Non-retriable or final attempt
            except Exception as api_err:
                req_dur = time.perf_counter() - t_req_start
                last_error = api_err
                logger.warning(
                    "Gemini request failed on attempt %d/%d after %.3fs (%s)",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    req_dur,
                    type(api_err).__name__,
                )
                break  # Unknown errors are not retried

        if last_error is not None:
            raise last_error

        t_proc_start = time.perf_counter()
        content = (response.text or "").strip()

        explanation = _extract_field(content, "EXPLANATION")
        kannada = _extract_field(content, "KANNADA")
        roman = _extract_field(content, "ROMAN")

        # Reject incomplete output instead of displaying malformed text.
        valid_kannada = (
            bool(kannada)
            and bool(re.search(r"[\u0C80-\u0CFF]", kannada))
            and len(kannada) <= 300
        )
        proc_dur = time.perf_counter() - t_proc_start
        logger.info(
            "Text processing completed in %.4fs (valid_kannada=%s)",
            proc_dur,
            valid_kannada,
        )

        if not valid_kannada:
            st.warning(
                "Gemini returned an incomplete or unexpected response. "
                "Using the phrasebook instead."
            )

            with st.expander("Debug Gemini response"):
                st.write("Raw response:")
                st.code(repr(content) if content else "(Empty response)")
                st.write("Response finish reason:")
                try:
                    st.write(response.candidates[0].finish_reason)
                except (AttributeError, IndexError, TypeError):
                    st.write("Unavailable")

            logger.info("AI Coach returning fallback after %.3fs (invalid output)", time.perf_counter() - t_start)
            return _fallback(
                user_text, scenario, explanation_language, phrases
            )

        total_dur = time.perf_counter() - t_start
        logger.info("AI Coach reply completed in %.3fs (is_fallback=False)", total_dur)
        return {
            "explanation": explanation or "Here is a suggested Kannada phrase.",
            "kn": kannada,
            "roman": roman or "Check pronunciation with a fluent speaker.",
            "is_fallback": False,
        }

    except (genai_errors.ServerError, genai_errors.ClientError) as error:
        logger.info(
            "AI Coach returning fallback after %.3fs (%s)",
            time.perf_counter() - t_start,
            type(error).__name__,
        )
        # Friendly message for known API errors — never expose raw details
        st.info(_friendly_error_message(error))
        return _fallback(
            user_text, scenario, explanation_language, phrases
        )

    except Exception as error:
        logger.info(
            "AI Coach returning fallback after %.3fs (%s)",
            time.perf_counter() - t_start,
            type(error).__name__,
        )
        # Catch-all: generic friendly message; log type only, never credentials
        st.info(
            "⚠️ AI is temporarily unavailable. "
            "We're showing a curated phrase instead. Please try again later."
        )
        return _fallback(
            user_text, scenario, explanation_language, phrases
        )
