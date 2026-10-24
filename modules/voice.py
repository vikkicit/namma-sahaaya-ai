import logging
import time
from io import BytesIO
import streamlit as st

logger = logging.getLogger("namma_sahaaya.voice")

# Use st.cache_data in production; fallback to pass-through if mocked in test environments
_cache = (
    (lambda *args, **kwargs: (lambda fn: fn))
    if type(getattr(st, "cache_data", None)).__name__ == "MagicMock"
    else st.cache_data
)


@_cache(show_spinner=False, max_entries=500)
def make_audio(text: str):
    """Generate Kannada TTS MP3 audio bytes using gTTS with bounded timeout and caching."""
    if not text or not str(text).strip():
        return None

    clean_text = str(text).strip()
    t_start = time.perf_counter()

    try:
        from gtts import gTTS

        buf = BytesIO()
        # Set a bounded timeout of 6 seconds so audio generation never blocks indefinitely
        tts = gTTS(text=clean_text, lang="kn", slow=False, timeout=6)
        tts.write_to_fp(buf)
        audio_bytes = buf.getvalue()

        dur = time.perf_counter() - t_start
        logger.info(
            "Audio generated in %.3fs for text length %d (size: %d bytes)",
            dur,
            len(clean_text),
            len(audio_bytes),
        )
        return audio_bytes

    except Exception as e:
        dur = time.perf_counter() - t_start
        logger.warning(
            "Audio generation failed after %.3fs for text length %d (%s).",
            dur,
            len(clean_text),
            type(e).__name__,
        )
        st.warning("Audio could not be generated right now. Please try again.")
        return None
