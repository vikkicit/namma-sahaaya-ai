
import os
import re
import streamlit as st
from google import genai


MODEL_NAME = "gemini-3.8-flash"


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
        }

    return {
        "explanation": "Try asking for directions, a price, or help.",
        "kn": "ದಯವಿಟ್ಟು ಸಹಾಯ ಮಾಡಿ",
        "roman": "Dayaviṭṭu sahāya māḍಿ",
    }


def _extract_field(text, label):
    """Extract one labelled line from Gemini's response."""
    pattern = rf"^\s*{re.escape(label)}\s*:\s*(.*?)\s*$"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


def generate_reply(
    user_text,
    scenario,
    explanation_language,
    history,
    phrases,
):
    """Generate a Kannada learning response using Gemini."""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        st.warning("GEMINI_API_KEY is missing from your .env file.")
        return _fallback(
            user_text, scenario, explanation_language, phrases
        )

    try:
        client = genai.Client(api_key=api_key)

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

        prompt = f"""
You are NammaSahaaya AI, a Kannada language learning coach.

Situation: {scenario}
User request: {user_text}
Explain in {language}.

Recent conversation:
{"chr(10)".join(history_lines) if history_lines else "None"}

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

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config={
                "temperature": 0.2,
                "max_output_tokens": 1000,
            },
        )

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

            return _fallback(
                user_text, scenario, explanation_language, phrases
            )

        return {
            "explanation": explanation or "Here is a suggested Kannada phrase.",
            "kn": kannada,
            "roman": roman or "Check pronunciation with a fluent speaker.",
        }

    except Exception as error:
        st.error(
            f"Gemini API error: {type(error).__name__}: {error}"
        )
        return _fallback(
            user_text, scenario, explanation_language, phrases
        )
