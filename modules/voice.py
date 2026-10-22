from io import BytesIO
import streamlit as st

def make_audio(text: str):
    try:
        from gtts import gTTS

        buf = BytesIO()
        gTTS(text=text, lang="kn", slow=False).write_to_fp(buf)
        return buf.getvalue()

    except Exception as e:
        st.warning(
            f"Audio generation failed: "
            f"{type(e).__name__}: {e}"
        )
        return None