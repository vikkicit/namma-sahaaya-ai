import os
import streamlit as st
from dotenv import load_dotenv

import random
from modules.phrases import PHRASES, SCENARIOS, get_phrases, filter_phrases
from modules.ai_coach import generate_reply
from modules.voice import make_audio
from modules.lessons import LESSONS, LESSON_IDS, LESSONS_BY_ID, LESSON_TOPICS
from modules.lesson_progress import get_completed_ids, mark_completed, mark_incomplete, is_completed
from modules.quiz_progress import save_quiz_attempt, get_recent_attempts
from modules.favourites import (
    add_favourite,
    remove_favourite,
    is_favourite,
    get_all_favourites,
    get_favourite_topics,
    get_favourite_count,
    generate_phrase_id,
)
from modules.progress_dashboard import render_learning_progress_dashboard
from modules.daily_lesson_generator import (
    get_daily_lesson,
    get_saved_daily_lesson,
    get_today_date_str,
)

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NammaSahaaya AI — Kannada made simple",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+Kannada:wght@400;600;700&display=swap');

/* ── Root tokens ── */
:root {
    --green-primary:  #176B55;
    --green-deep:     #104A3B;
    --green-soft:     #E8F4ED;
    --green-mid:      #1E7D62;
    --ivory:          #FAF9F5;
    --white:          #FFFFFF;
    --text-main:      #1F302B;
    --text-muted:     #718078;
    --border:         #D8E8DF;
    --shadow-sm:      0 1px 4px rgba(23,107,85,.08);
    --shadow-md:      0 4px 16px rgba(23,107,85,.12);
    --radius-sm:      8px;
    --radius-md:      14px;
    --radius-lg:      20px;
}

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', system-ui, sans-serif;
    color: var(--text-main);
}

.main .block-container {
    max-width: 1080px;
    padding: 1.5rem 2rem 3rem;
    background: var(--ivory);
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--green-deep) !important;
    border-right: 1px solid rgba(255,255,255,.08);
}
[data-testid="stSidebar"] * {
    color: #E8F4ED !important;
}
[data-testid="stSidebar"] .stRadio label {
    color: #E8F4ED !important;
    font-size: .92rem;
    padding: .25rem 0;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,.12) !important;
}
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small {
    color: rgba(232,244,237,.65) !important;
}

/* ── Hero ── */
.ns-hero {
    background: linear-gradient(135deg, var(--green-deep) 0%, var(--green-primary) 100%);
    border-radius: var(--radius-lg);
    padding: 2.2rem 2.4rem 2rem;
    margin-bottom: 1.8rem;
    color: #fff;
    position: relative;
    overflow: hidden;
}
.ns-hero::before {
    content: "ಕ";
    position: absolute;
    right: 2rem; top: -.6rem;
    font-family: 'Noto Sans Kannada', serif;
    font-size: 7rem;
    font-weight: 700;
    color: rgba(255,255,255,.07);
    line-height: 1;
    pointer-events: none;
}
.ns-hero-greeting {
    font-family: 'Noto Sans Kannada', serif;
    font-size: 1rem;
    letter-spacing: .1em;
    opacity: .75;
    margin-bottom: .5rem;
}
.ns-hero h1 {
    font-size: 2rem;
    font-weight: 700;
    margin: 0 0 .45rem;
    line-height: 1.25;
    color: #fff;
}
.ns-hero p {
    font-size: .95rem;
    opacity: .82;
    margin: 0;
    max-width: 560px;
    line-height: 1.6;
}
.ns-hero-badges {
    display: flex;
    gap: .5rem;
    flex-wrap: wrap;
    margin-top: 1rem;
}
.ns-badge {
    background: rgba(255,255,255,.15);
    border: 1px solid rgba(255,255,255,.22);
    color: #fff !important;
    font-size: .78rem;
    padding: .25rem .75rem;
    border-radius: 20px;
    font-weight: 500;
    letter-spacing: .02em;
}

/* ── Section headings ── */
.ns-section-label {
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: var(--green-primary);
    margin: 0 0 .6rem;
}
.ns-section-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-main);
    margin: 0 0 .25rem;
}
.ns-section-sub {
    font-size: .88rem;
    color: var(--text-muted);
    margin: 0 0 1.2rem;
}

/* ── Cards ── */
.ns-card {
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1.2rem 1.4rem;
    box-shadow: var(--shadow-sm);
    margin-bottom: 1rem;
}

/* ── Phrase card pieces ── */
.ns-kn {
    font-family: 'Noto Sans Kannada', serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--green-deep);
    line-height: 1.5;
    margin-bottom: .25rem;
}
.ns-roman {
    font-size: .88rem;
    color: var(--text-muted);
    font-style: italic;
    margin-bottom: .15rem;
}
.ns-meaning-label {
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: var(--green-primary);
    margin: .6rem 0 .2rem;
}
.ns-meaning {
    font-size: .95rem;
    color: var(--text-main);
}

/* ── Result card ── */
.ns-result-card {
    background: linear-gradient(135deg, var(--green-soft) 0%, #fff 60%);
    border: 1.5px solid var(--green-primary);
    border-radius: var(--radius-md);
    padding: 1.6rem;
    margin-top: 1rem;
    box-shadow: var(--shadow-md);
}
.ns-result-kn {
    font-family: 'Noto Sans Kannada', serif;
    font-size: 2rem;
    font-weight: 700;
    color: var(--green-deep);
    line-height: 1.5;
    margin-bottom: .3rem;
}
.ns-result-roman {
    font-size: .92rem;
    color: var(--text-muted);
    font-style: italic;
    margin-bottom: 1rem;
}
.ns-result-label {
    font-size: .7rem;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: var(--green-primary);
    margin-bottom: .3rem;
}
.ns-result-explanation {
    font-size: .97rem;
    color: var(--text-main);
    line-height: 1.65;
    background: rgba(255,255,255,.7);
    border-radius: var(--radius-sm);
    padding: .75rem 1rem;
    border-left: 3px solid var(--green-primary);
}

/* ── Feature overview grid ── */
.ns-feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem;
}
.ns-feature-card {
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1.2rem;
    text-align: center;
    box-shadow: var(--shadow-sm);
}
.ns-feature-icon { font-size: 2rem; margin-bottom: .5rem; }
.ns-feature-title { font-size: .95rem; font-weight: 700; color: var(--text-main); }
.ns-feature-desc  { font-size: .82rem; color: var(--text-muted); margin-top: .2rem; }

/* ── Pills ── */
.ns-pill-row { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: 1.2rem; }
.ns-pill {
    background: var(--green-soft);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: .3rem .9rem;
    font-size: .84rem;
    font-weight: 500;
    color: var(--green-primary);
}

/* ── Chat bubbles ── */
.ns-chat-user {
    background: var(--green-soft);
    border: 1px solid var(--border);
    border-radius: var(--radius-md) var(--radius-md) var(--radius-md) 4px;
    padding: .8rem 1.1rem;
    font-size: .93rem;
    margin-bottom: .6rem;
    max-width: 85%;
}
.ns-chat-ai {
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: var(--radius-md) var(--radius-md) 4px var(--radius-md);
    padding: .8rem 1.1rem;
    margin-bottom: .6rem;
    max-width: 90%;
    margin-left: auto;
    box-shadow: var(--shadow-sm);
}

/* ── Emergency notice ── */
.ns-emergency {
    background: #FEF3F2;
    border: 1px solid #FECDCA;
    border-radius: var(--radius-sm);
    padding: .75rem 1rem;
    font-size: .85rem;
    color: #912018;
    margin-top: 1rem;
}

/* ── Sidebar brand ── */
.ns-brand {
    display: flex;
    align-items: center;
    gap: .6rem;
    margin-bottom: 1.2rem;
}
.ns-brand-icon {
    width: 36px; height: 36px;
    background: rgba(255,255,255,.15);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem;
}
.ns-brand-name { font-size: .95rem; font-weight: 700; color: #E8F4ED; line-height: 1.2; }
.ns-brand-tag  { font-size: .72rem; color: rgba(232,244,237,.6); }
.ns-sidebar-tip {
    background: rgba(255,255,255,.07);
    border: 1px solid rgba(255,255,255,.12);
    border-radius: var(--radius-sm);
    padding: .6rem .8rem;
    font-size: .8rem;
    color: rgba(232,244,237,.75);
    margin-top: .8rem;
    line-height: 1.55;
}

/* ── Inputs ── */
.stTextInput input {
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    font-size: .95rem !important;
    color: var(--text-main) !important;
    background: var(--white) !important;
}
.stTextInput input:focus {
    border-color: var(--green-primary) !important;
    box-shadow: 0 0 0 3px rgba(23,107,85,.1) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--green-primary) !important;
    color: #fff !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: .92rem !important;
    padding: .55rem 1.5rem !important;
    transition: background .2s !important;
}
.stButton > button:hover {
    background: var(--green-mid) !important;
    box-shadow: 0 4px 12px rgba(23,107,85,.25) !important;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; opacity: 1 !important; }

/* ── Footer ── */
.ns-footer {
    text-align: center;
    font-size: .78rem;
    color: var(--text-muted);
    padding: 1.5rem 0 .5rem;
    border-top: 1px solid var(--border);
    margin-top: 2rem;
}

/* ── Lessons: topic pills ── */
.ns-topic-pill {
    background: var(--green-soft);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: .28rem .8rem;
    font-size: .8rem;
    font-weight: 600;
    color: var(--green-primary);
    display: inline-block;
    margin: .15rem .2rem;
}
.ns-topic-pill.active {
    background: var(--green-primary);
    color: #fff;
    border-color: var(--green-primary);
}

/* ── Lessons: lesson card in index ── */
.ns-lesson-index-card {
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1.1rem 1.3rem;
    margin-bottom: .7rem;
    box-shadow: var(--shadow-sm);
    display: flex;
    align-items: flex-start;
    gap: 1rem;
}
.ns-lesson-index-card.completed {
    border-left: 4px solid var(--green-primary);
    background: #F4FCF8;
}
.ns-lesson-index-card.incomplete {
    border-left: 4px solid #D8E8DF;
}
.ns-lesson-badge {
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .06em;
    text-transform: uppercase;
    padding: .2rem .55rem;
    border-radius: 10px;
    display: inline-block;
    margin-bottom: .35rem;
}
.ns-lesson-badge.beginner   { background: #E8F4ED; color: #176B55; }
.ns-lesson-badge.elementary { background: #EDF4FF; color: #2563EB; }
.ns-lesson-badge.intermediate { background: #FFF7ED; color: #B45309; }

/* ── Lessons: phrase row inside lesson ── */
.ns-lesson-phrase {
    background: var(--ivory);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: .9rem 1.1rem;
    margin-bottom: .6rem;
}
.ns-lesson-kn {
    font-family: 'Noto Sans Kannada', serif;
    font-size: 1.45rem;
    font-weight: 700;
    color: var(--green-deep);
    line-height: 1.5;
}
.ns-lesson-roman {
    font-size: .85rem;
    color: var(--text-muted);
    font-style: italic;
    margin: .15rem 0 .4rem;
}
.ns-lesson-meaning {
    font-size: .9rem;
    color: var(--text-main);
}

/* ── Lessons: objectives ── */
.ns-objective-list {
    padding-left: 1.1rem;
    margin: .3rem 0 .5rem;
    color: var(--text-main);
    font-size: .92rem;
    line-height: 1.7;
}

/* ── Lessons: practice box ── */
.ns-practice-box {
    background: #FFF9EC;
    border: 1px solid #E8D5A3;
    border-radius: var(--radius-sm);
    padding: .85rem 1.1rem;
    font-size: .9rem;
    color: #7A6020;
    line-height: 1.6;
    margin-top: .4rem;
}

/* ── Lessons: completion banner ── */
.ns-done-banner {
    background: linear-gradient(90deg, #E8F4ED, #fff);
    border: 1.5px solid var(--green-primary);
    border-radius: var(--radius-md);
    padding: 1rem 1.3rem;
    display: flex;
    align-items: center;
    gap: .8rem;
    margin: 1rem 0;
}
.ns-done-icon { font-size: 1.8rem; }
.ns-done-text { font-size: .95rem; color: var(--green-deep); font-weight: 600; }
.ns-done-sub  { font-size: .8rem;  color: var(--text-muted); }

/* ── Responsive ── */
@media (max-width: 768px) {
    .main .block-container { padding: 1rem 1rem 2rem; }
    .ns-hero { padding: 1.4rem 1.2rem 1.2rem; }
    .ns-hero h1 { font-size: 1.5rem; }
    .ns-result-kn { font-size: 1.5rem; }
    .ns-lesson-kn { font-size: 1.2rem; }
}
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "chat" not in st.session_state:
    st.session_state.chat = []
if "scenario" not in st.session_state:
    st.session_state.scenario = "Shopping"

# ── Sidebar ───────────────────────────────────────────────────────────────────
SCENARIO_ICONS = {
    "Shopping":     "🛒",
    "Transport":    "🚌",
    "Restaurant":   "🍽️",
    "Hospital":     "🏥",
    "General Help": "💬",
}

LEARNING_TIPS = [
    "Start every conversation with ನಮಸ್ಕಾರ (Namaskara) — it goes a long way!",
    "ದಯವಿಟ್ಟು (Dayavittu) means 'please' — always appreciated.",
    "Even a few Kannada words show respect and open doors.",
    "Practice pronunciation by listening to the audio for each phrase.",
]

import random
_tip_idx = int(hash(str(st.session_state.get("_tip_seed", 0))) % len(LEARNING_TIPS))
_tip = LEARNING_TIPS[_tip_idx]
if "_tip_seed" not in st.session_state:
    st.session_state._tip_seed = random.randint(0, 1000)

with st.sidebar:
    st.markdown("""
    <div class="ns-brand">
      <div class="ns-brand-icon">🌿</div>
      <div>
        <div class="ns-brand-name">NammaSahaaya AI</div>
        <div class="ns-brand-tag">Kannada made simple.</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown(
        "<p style='font-size:.78rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;"
        "color:rgba(232,244,237,.6);margin-bottom:.4rem;'>Explain phrases in</p>",
        unsafe_allow_html=True,
    )
    language = st.radio(
        label="Explain in",
        options=["Tamil", "English"],
        horizontal=True,
        label_visibility="collapsed",
        key="explain_lang",
    )

    st.markdown("<div style='margin:.8rem 0;'></div>", unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:.78rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;"
        "color:rgba(232,244,237,.6);margin-bottom:.4rem;'>Navigate</p>",
        unsafe_allow_html=True,
    )
    page = st.radio(
        label="Go to",
        options=[
            "AI Phrase Coach",
            "Situation Simulator",
            "Rescue Mode",
            "Phrasebook",
            "My Favourites",
            "Daily Lessons",
            "Interactive Quizzes",
            "Learning Progress",
        ],
        label_visibility="collapsed",
        key="nav_page",
    )

    st.markdown("---")

    st.markdown(
        f'<div class="ns-sidebar-tip">💡 {_tip}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:.72rem;color:rgba(232,244,237,.4);text-align:center;'>"
        "MVP demo · Hackathon build<br>Validate phrases with native speakers.</p>",
        unsafe_allow_html=True,
    )


# ── Helper: meaning by language ───────────────────────────────────────────────
def meaning(p):
    return p.get("meaning_ta", "") if language == "Tamil" else p.get("meaning_en", "")


# ── Helper: phrase card ───────────────────────────────────────────────────────
def phrase_card(p, show_audio=True, scenario_badge=False, show_fav=True, key_prefix="card"):
    badge_html = ""
    scenario = p.get("scenario") or p.get("topic", "")
    if scenario_badge and scenario:
        icon = SCENARIO_ICONS.get(scenario, "📌")
        badge_html = (
            f'<span class="ns-pill" style="font-size:.73rem;padding:.15rem .55rem;">'
            f'{icon} {scenario}</span><br>'
        )
    lang_label = "Tamil meaning" if language == "Tamil" else "English meaning"
    meaning_text = meaning(p)
    st.markdown(
        f'<div class="ns-card">'
        f'{badge_html}'
        f'<div class="ns-kn">{p["kn"]}</div>'
        f'<div class="ns-roman">📣 {p.get("roman", "")}</div>'
        f'<div class="ns-meaning-label">{lang_label}</div>'
        f'<div class="ns-meaning">{meaning_text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    col_fav, col_audio = st.columns([1, 2])
    with col_fav:
        if show_fav:
            saved = is_favourite(p["kn"])
            fav_btn_label = "★ Saved" if saved else "☆ Save"
            pid = generate_phrase_id(p["kn"])
            if st.button(fav_btn_label, key=f"fav_{key_prefix}_{pid}"):
                if saved:
                    remove_favourite(p["kn"])
                    st.info(f"Removed '{p['kn']}' from favourites.")
                else:
                    add_favourite(
                        kn=p["kn"],
                        roman=p.get("roman", ""),
                        meaning_en=p.get("meaning_en", ""),
                        meaning_ta=p.get("meaning_ta", ""),
                        topic=scenario,
                    )
                    st.success(f"Saved '{p['kn']}' to favourites!")
                st.rerun()
    with col_audio:
        if show_audio:
            audio = make_audio(p["kn"])
            if audio:
                st.audio(audio, format="audio/mp3")
            else:
                st.caption("Audio unavailable right now.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: AI Phrase Coach
# ═══════════════════════════════════════════════════════════════════════════════
if page == "AI Phrase Coach":
    st.markdown("""
    <div class="ns-hero">
      <div class="ns-hero-greeting">ನಮಸ್ಕಾರ — Welcome</div>
      <h1>Kannada made simple.</h1>
      <p>Learn the Kannada you need for everyday life. Ask anything in English or Tamil
         and get a ready-to-use Kannada phrase with pronunciation and audio.</p>
      <div class="ns-hero-badges">
        <span class="ns-badge">🤖 Powered by Gemini</span>
        <span class="ns-badge">🔊 Audio playback</span>
        <span class="ns-badge">🌐 Tamil &amp; English</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Feature overview
    st.markdown("""
    <div class="ns-feature-grid">
      <div class="ns-feature-card">
        <div class="ns-feature-icon">🤖</div>
        <div class="ns-feature-title">AI Phrase Coach</div>
        <div class="ns-feature-desc">Generate context-aware Kannada phrases instantly.</div>
      </div>
      <div class="ns-feature-card">
        <div class="ns-feature-icon">🎭</div>
        <div class="ns-feature-title">Situation Simulator</div>
        <div class="ns-feature-desc">Practice real-life conversations by scenario.</div>
      </div>
      <div class="ns-feature-card">
        <div class="ns-feature-icon">🆘</div>
        <div class="ns-feature-title">Rescue Mode</div>
        <div class="ns-feature-desc">Offline-ready phrases for urgent situations.</div>
      </div>
      <div class="ns-feature-card">
        <div class="ns-feature-icon">📚</div>
        <div class="ns-feature-title">Phrasebook</div>
        <div class="ns-feature-desc">Searchable library of common Kannada phrases.</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="ns-section-label">AI Phrase Coach</div>', unsafe_allow_html=True)
    st.markdown('<div class="ns-section-title">Generate a Kannada Phrase</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ns-section-sub">Describe what you want to say in English or Tamil. '
        'The AI will generate the Kannada phrase, pronunciation, and a clear explanation.</div>',
        unsafe_allow_html=True,
    )

    col_input, col_scenario = st.columns([3, 2])
    with col_input:
        user_input = st.text_input(
            "What would you like to say?",
            placeholder="e.g. How much does this cost? / எனக்கு தண்ணீர் வேண்டும்",
            key="coach_input",
        )
    with col_scenario:
        coach_scenario = st.selectbox(
            "Situation",
            SCENARIOS,
            key="coach_scenario",
            help="Choose the context for a more relevant phrase.",
        )

    generate_btn = st.button("🌿 Generate Kannada Phrase", key="coach_generate")

    if generate_btn:
        if not user_input.strip():
            st.warning("Please enter something you'd like to say in Kannada.")
        else:
            current_phrases = get_phrases(coach_scenario)
            with st.spinner("Generating your Kannada phrase…"):
                result = generate_reply(
                    user_text=user_input,
                    scenario=coach_scenario,
                    explanation_language=language,
                    history=st.session_state.chat[-8:],
                    phrases=current_phrases,
                )

            audio = make_audio(result["kn"])
            st.session_state.last_coach_result = {
                "kn": result["kn"],
                "roman": result["roman"],
                "explanation": result["explanation"],
                "audio": audio,
                "user_input": user_input,
                "scenario": coach_scenario,
                "lang": language,
            }

            # Save to conversation history
            st.session_state.chat.append({"role": "user", "content": user_input})
            st.session_state.chat.append({
                "role": "assistant",
                "content": result["explanation"],
                "kn": result["kn"],
                "roman": result["roman"],
                "audio": audio,
                "scenario": coach_scenario,
            })

    if st.session_state.get("last_coach_result"):
        res = st.session_state.last_coach_result
        lang_label = "Tamil explanation" if res.get("lang") == "Tamil" else "English explanation"
        st.markdown(
            f'<div class="ns-result-card">'
            f'<div class="ns-result-label">Kannada Phrase</div>'
            f'<div class="ns-result-kn">{res["kn"]}</div>'
            f'<div class="ns-result-roman">📣 {res["roman"]}</div>'
            f'<div class="ns-result-label" style="margin-top:.8rem;">{lang_label}</div>'
            f'<div class="ns-result-explanation">{res["explanation"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        col_c_fav, col_c_audio = st.columns([1, 2])
        with col_c_fav:
            saved = is_favourite(res["kn"])
            c_lbl = "★ Saved" if saved else "☆ Save"
            pid = generate_phrase_id(res["kn"])
            if st.button(c_lbl, key=f"fav_coach_curr_{pid}"):
                if saved:
                    remove_favourite(res["kn"])
                    st.info(f"Removed '{res['kn']}' from favourites.")
                else:
                    add_favourite(
                        kn=res["kn"],
                        roman=res.get("roman", ""),
                        meaning_en=res.get("user_input", "") if res.get("lang") == "English" else res.get("explanation", ""),
                        meaning_ta=res.get("user_input", "") if res.get("lang") == "Tamil" else "",
                        topic=res.get("scenario", "AI Coach"),
                    )
                    st.success(f"Saved '{res['kn']}' to favourites!")
                st.rerun()
        with col_c_audio:
            if res.get("audio"):
                st.audio(res["audio"], format="audio/mp3")
            else:
                st.caption("Audio unavailable right now. The phrase text is still displayed above.")

    # Conversation history
    if st.session_state.chat:
        st.markdown("---")
        st.markdown('<div class="ns-section-label">Conversation History</div>', unsafe_allow_html=True)
        st.markdown('<div class="ns-section-title">Previous Phrases</div>', unsafe_allow_html=True)

        for i in range(0, len(st.session_state.chat), 2):
            user_msg = st.session_state.chat[i]
            st.markdown(
                f'<div class="ns-chat-user">🙋 <strong>You:</strong> {user_msg["content"]}</div>',
                unsafe_allow_html=True,
            )
            if i + 1 < len(st.session_state.chat):
                ai_msg = st.session_state.chat[i + 1]
                kn_html = (
                    f'<div class="ns-kn" style="margin-bottom:.15rem;">{ai_msg.get("kn","")}</div>'
                    if ai_msg.get("kn") else ""
                )
                roman_html = (
                    f'<div class="ns-roman">📣 {ai_msg.get("roman","")}</div>'
                    if ai_msg.get("roman") else ""
                )
                st.markdown(
                    f'<div class="ns-chat-ai">'
                    f'🌿 <strong>NammaSahaaya AI</strong><br>'
                    f'{kn_html}{roman_html}'
                    f'<div style="font-size:.88rem;color:var(--text-muted);margin-top:.3rem;">'
                    f'{ai_msg.get("content","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if ai_msg.get("kn"):
                    col_h_fav, col_h_aud = st.columns([1, 2])
                    with col_h_fav:
                        kn_h = ai_msg["kn"]
                        h_saved = is_favourite(kn_h)
                        h_lbl = "★ Saved" if h_saved else "☆ Save"
                        if st.button(h_lbl, key=f"fav_chat_{i}_{generate_phrase_id(kn_h)}"):
                            if h_saved:
                                remove_favourite(kn_h)
                                st.info(f"Removed '{kn_h}' from favourites.")
                            else:
                                add_favourite(
                                    kn=kn_h,
                                    roman=ai_msg.get("roman", ""),
                                    meaning_en=user_msg.get("content", ""),
                                    topic=ai_msg.get("scenario", "AI Coach"),
                                )
                                st.success(f"Saved '{kn_h}' to favourites!")
                            st.rerun()
                    with col_h_aud:
                        if ai_msg.get("audio"):
                            st.audio(ai_msg["audio"], format="audio/mp3")

        if st.button("🗑️ Clear conversation", key="clear_chat"):
            st.session_state.chat = []
            st.session_state.last_coach_result = None
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Situation Simulator
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Situation Simulator":
    st.markdown("""
    <div class="ns-hero">
      <div class="ns-hero-greeting">ಸ್ಥಿತಿ ಸಿಮ್ಯುಲೇಟರ್ — Situation Simulator</div>
      <h1>Practice real conversations.</h1>
      <p>Choose a situation, browse useful phrases, then practice a live conversation
         with the AI coach in that context.</p>
    </div>
    """, unsafe_allow_html=True)

    pills_html = "".join(
        f'<span class="ns-pill">{SCENARIO_ICONS.get(s,"📌")} {s}</span>'
        for s in SCENARIOS
    )
    st.markdown(f'<div class="ns-pill-row">{pills_html}</div>', unsafe_allow_html=True)

    scenario = st.selectbox("Select scenario", SCENARIOS, key="scenario")
    current = get_phrases(scenario)

    if current:
        st.markdown(f'<div class="ns-section-label">Phrases for {scenario}</div>', unsafe_allow_html=True)
        st.markdown('<div class="ns-section-title">Useful Phrases</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        for i, p in enumerate(current[:4]):
            with cols[i % 2]:
                phrase_card(p, key_prefix=f"sim_{i}")

    st.markdown("---")
    st.markdown('<div class="ns-section-label">Conversation practice</div>', unsafe_allow_html=True)
    st.markdown('<div class="ns-section-title">Chat with AI Coach</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ns-section-sub">Type what you want to say in this situation. '
        'Try: <em>"Ask how much this costs"</em> or <em>"I need to go to the railway station."</em></div>',
        unsafe_allow_html=True,
    )

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("kn"):
                st.markdown(f'<div class="ns-kn">{msg["kn"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="ns-roman">📣 {msg.get("roman","")}</div>', unsafe_allow_html=True)
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/mp3")

    user_text = st.chat_input("Type in Tamil or English…")
    if user_text:
        st.session_state.chat.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.write(user_text)
        with st.chat_message("assistant"):
            with st.spinner("Preparing a helpful Kannada response…"):
                result = generate_reply(
                    user_text=user_text,
                    scenario=scenario,
                    explanation_language=language,
                    history=st.session_state.chat[-8:],
                    phrases=current,
                )
            st.markdown(result["explanation"])
            st.markdown(f'<div class="ns-kn">{result["kn"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ns-roman">📣 {result["roman"]}</div>', unsafe_allow_html=True)
            audio = make_audio(result["kn"])
            if audio:
                st.audio(audio, format="audio/mp3")
            st.session_state.chat.append({
                "role": "assistant",
                "content": result["explanation"],
                "kn": result["kn"],
                "roman": result["roman"],
                "audio": audio,
            })

    if st.session_state.chat:
        if st.button("🗑️ Clear conversation", key="sim_clear"):
            st.session_state.chat = []
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Rescue Mode
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Rescue Mode":
    st.markdown("""
    <div class="ns-hero">
      <div class="ns-hero-greeting">ತುರ್ತು ಸಹಾಯ — Rescue Mode</div>
      <h1>Find a phrase fast.</h1>
      <p>These phrases are available without an AI API. Use them when you need help
         quickly in a real situation.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="ns-section-label">Select a situation</div>', unsafe_allow_html=True)
    situation = st.selectbox(
        "What do you need help with?",
        SCENARIOS,
        key="rescue_scenario",
    )

    rescue_phrases = get_phrases(situation)

    if rescue_phrases:
        icon = SCENARIO_ICONS.get(situation, "📌")
        st.markdown(
            f'<div class="ns-section-title">{icon} {situation} Phrases</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="ns-section-sub">{len(rescue_phrases)} phrase(s) available · '
            f'{language} explanations</div>',
            unsafe_allow_html=True,
        )
        for i, p in enumerate(rescue_phrases):
            phrase_card(p, key_prefix=f"rescue_{situation}_{i}")
    else:
        st.markdown(
            '<div class="ns-card" style="text-align:center;color:var(--text-muted);">'
            'No phrases available for this situation.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("""
    <div class="ns-emergency">
      ⚠️ <strong>Important:</strong> For immediate danger or a medical emergency,
      contact local emergency services or ask a nearby trusted person for help.
      This phrasebook is <strong>not a substitute</strong> for emergency care or
      professional assistance.
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Phrasebook
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Phrasebook":
    st.markdown("""
    <div class="ns-hero">
      <div class="ns-hero-greeting">ಪದಕೋಶ — Phrasebook</div>
      <h1>Your Kannada phrase library.</h1>
      <p>Browse and search all available phrases. Filter by situation or keyword.</p>
    </div>
    """, unsafe_allow_html=True)

    col_search, col_filter = st.columns([3, 2])
    with col_search:
        st.markdown('<div class="ns-section-label">Search</div>', unsafe_allow_html=True)
        query = st.text_input(
            "Search phrases",
            placeholder="Search by situation, English meaning, or Kannada…",
            label_visibility="collapsed",
            key="pb_search",
        )
    with col_filter:
        st.markdown('<div class="ns-section-label">Filter by situation</div>', unsafe_allow_html=True)
        filter_scenario = st.selectbox(
            "Filter",
            ["All situations"] + SCENARIOS,
            label_visibility="collapsed",
            key="pb_filter",
        )

    # Apply filters using Unicode-normalized, case-insensitive search
    filtered = filter_phrases(query=query, scenario=filter_scenario)

    if filtered:
        st.markdown(
            f'<div class="ns-section-sub">{len(filtered)} phrase(s) found</div>',
            unsafe_allow_html=True,
        )
        from collections import defaultdict
        grouped = defaultdict(list)
        for p in filtered:
            grouped[p["scenario"]].append(p)

        for sc, phrases in grouped.items():
            icon = SCENARIO_ICONS.get(sc, "📌")
            st.markdown(
                f'<div class="ns-section-label" style="margin-top:1rem;">{icon} {sc}</div>',
                unsafe_allow_html=True,
            )
            cols = st.columns(2)
            for i, p in enumerate(phrases):
                with cols[i % 2]:
                    phrase_card(p, key_prefix=f"pb_{sc}_{i}")
    else:
        st.markdown("""
        <div class="ns-card" style="text-align:center;padding:2.5rem 1.5rem;">
          <div style="font-size:2rem;margin-bottom:.5rem;">🔍</div>
          <div style="font-weight:700;color:var(--text-main);">No phrases found</div>
          <div style="font-size:.88rem;color:var(--text-muted);margin-top:.25rem;">
            Try a different search term or reset the filter.
          </div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: My Favourites & Revision Mode
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "My Favourites":
    fav_count = get_favourite_count()
    topics = get_favourite_topics()

    # Session state initialization for Revision Mode
    if "rev_active" not in st.session_state:
        st.session_state.rev_active = False
    if "rev_phrases" not in st.session_state:
        st.session_state.rev_phrases = []
    if "rev_index" not in st.session_state:
        st.session_state.rev_index = 0
    if "rev_revealed" not in st.session_state:
        st.session_state.rev_revealed = False
    if "rev_known" not in st.session_state:
        st.session_state.rev_known = set()
    if "rev_again" not in st.session_state:
        st.session_state.rev_again = set()
    if "rev_topic" not in st.session_state:
        st.session_state.rev_topic = "All Saved Phrases"

    # Hero Banner
    st.markdown(f"""
    <div class="ns-hero">
      <div class="ns-hero-greeting">ನನ್ನ ಮೆಚ್ಚಿನವುಗಳು — My Favourites</div>
      <h1>Your personal phrase library.</h1>
      <p>Save phrases across NammaSahaaya AI and practice them anytime using Revision Mode.</p>
      <div class="ns-hero-badges">
        <span class="ns-badge">⭐ {fav_count} saved phrase(s)</span>
        <span class="ns-badge">🏷️ {len(topics)} topic(s)</span>
        <span class="ns-badge">🧠 Revision Mode ready</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── REVISION MODE ─────────────────────────────────────────────────────────
    if st.session_state.rev_active:
        phrases = st.session_state.rev_phrases
        total = len(phrases)
        idx = st.session_state.rev_index

        if total == 0:
            st.warning("No saved phrases available to revise.")
            if st.button("← Return to Favourites", key="rev_empty_return"):
                st.session_state.rev_active = False
                st.rerun()
        elif idx < total:
            curr = phrases[idx]

            # Header & Exit
            col_exit, col_prog = st.columns([1, 3])
            with col_exit:
                if st.button("← Exit Revision", key="exit_rev_btn"):
                    st.session_state.rev_active = False
                    st.rerun()
            with col_prog:
                st.markdown(
                    f'<div style="text-align:right;font-size:.9rem;color:var(--text-muted);font-weight:600;padding-top:.4rem;">'
                    f'Phrase {idx + 1} of {total} &nbsp;·&nbsp; 🏷️ {st.session_state.rev_topic}</div>',
                    unsafe_allow_html=True,
                )

            st.progress((idx) / total)

            # Flashcard container
            st.markdown("""
            <div class="ns-card" style="margin-top:1.2rem;border:1.5px solid var(--green-primary);box-shadow:var(--shadow-md);">
              <div class="ns-section-label">Revision Flashcard</div>
              <div class="ns-section-title">How do you say this in Kannada?</div>
            """, unsafe_allow_html=True)

            # English meaning (prominently)
            en_meaning = curr.get("meaning_en") or "(No English meaning)"
            st.markdown(
                f'<div style="font-size:1.35rem;font-weight:700;color:var(--green-deep);margin:.6rem 0 .4rem;">'
                f'🇬🇧 {en_meaning}</div>',
                unsafe_allow_html=True,
            )

            # Tamil meaning if available
            if curr.get("meaning_ta"):
                st.markdown(
                    f'<div style="font-size:1.05rem;color:var(--green-mid);margin-bottom:.6rem;">'
                    f'🇮🇳 {curr["meaning_ta"]}</div>',
                    unsafe_allow_html=True,
                )

            # Topic pill if available
            if curr.get("topic"):
                st.markdown(
                    f'<div style="margin-bottom:.8rem;"><span class="ns-pill" style="font-size:.75rem;">'
                    f'📌 {curr["topic"]}</span></div>',
                    unsafe_allow_html=True,
                )

            # Answer reveal
            if not st.session_state.rev_revealed:
                st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
                if st.button("👁️ Reveal Kannada Answer", key=f"rev_reveal_{idx}_{curr['id']}"):
                    st.session_state.rev_revealed = True
                    st.rerun()
            else:
                st.markdown("<hr style='margin:1rem 0;'>", unsafe_allow_html=True)
                st.markdown(
                    f'<div class="ns-result-label">Kannada Answer</div>'
                    f'<div class="ns-result-kn" style="font-size:2rem;margin-bottom:.2rem;">{curr["kn"]}</div>'
                    f'<div class="ns-result-roman">📣 {curr.get("roman", "")}</div>',
                    unsafe_allow_html=True,
                )
                audio = make_audio(curr["kn"])
                if audio:
                    st.audio(audio, format="audio/mp3")

                st.markdown("<div style='margin-top:1.4rem;'></div>", unsafe_allow_html=True)
                st.markdown(
                    '<div style="font-size:.85rem;font-weight:700;color:var(--text-muted);text-transform:uppercase;margin-bottom:.5rem;">'
                    'How well did you know this?</div>',
                    unsafe_allow_html=True,
                )

                col_k, col_a = st.columns(2)
                with col_k:
                    if st.button("✅ Know it", key=f"rev_know_{idx}_{curr['id']}"):
                        st.session_state.rev_known.add(curr["id"])
                        st.session_state.rev_index += 1
                        st.session_state.rev_revealed = False
                        st.rerun()
                with col_a:
                    if st.button("🔁 Revise Again", key=f"rev_again_{idx}_{curr['id']}"):
                        st.session_state.rev_again.add(curr["id"])
                        st.session_state.rev_index += 1
                        st.session_state.rev_revealed = False
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        else:
            # ── SUMMARY SCREEN ────────────────────────────────────────────────
            k_count = len(st.session_state.rev_known)
            a_count = len(st.session_state.rev_again)
            pct = round((k_count / total) * 100) if total > 0 else 0

            st.markdown(f"""
            <div class="ns-result-card" style="text-align:center;padding:2.2rem 1.5rem;">
              <div style="font-size:3rem;margin-bottom:.5rem;">🎉</div>
              <div style="font-size:1.5rem;font-weight:700;color:var(--green-deep);">Revision Session Complete!</div>
              <div style="font-size:1rem;color:var(--text-main);margin:.6rem auto 1.2rem;max-width:500px;line-height:1.6;">
                You reviewed <strong>{total}</strong> phrase(s) with <strong>{pct}%</strong> recall.
              </div>
              <div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;margin-bottom:1.2rem;">
                <span class="ns-pill" style="background:#E8F4ED;color:#176B55;font-size:.9rem;padding:.4rem 1rem;">
                  ✅ {k_count} Marked as Known
                </span>
                <span class="ns-pill" style="background:#FEF3F2;color:#912018;font-size:.9rem;padding:.4rem 1rem;">
                  🔁 {a_count} Need More Revision
                </span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Weak phrases breakdown
            if a_count > 0:
                st.markdown('<div class="ns-section-label" style="margin-top:1.5rem;">Phrases to Revise Again</div>', unsafe_allow_html=True)
                weak_list = [p for p in phrases if p["id"] in st.session_state.rev_again]
                for p in weak_list:
                    st.markdown(
                        f'<div class="ns-card" style="padding:.8rem 1.1rem;margin-bottom:.5rem;">'
                        f'<div class="ns-kn" style="font-size:1.3rem;">{p["kn"]}</div>'
                        f'<div class="ns-roman">📣 {p.get("roman","")}</div>'
                        f'<div style="font-size:.85rem;color:var(--text-main);margin-top:.2rem;">🇬🇧 {p.get("meaning_en","")}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                if a_count > 0:
                    if st.button(f"🔁 Revise Weak Phrases ({a_count})", key="rev_restart_weak"):
                        weak_phrases = [p for p in phrases if p["id"] in st.session_state.rev_again]
                        random.shuffle(weak_phrases)
                        st.session_state.rev_phrases = weak_phrases
                        st.session_state.rev_index = 0
                        st.session_state.rev_revealed = False
                        st.session_state.rev_known = set()
                        st.session_state.rev_again = set()
                        st.rerun()
            with col_s2:
                if st.button("🔄 Restart Full Session", key="rev_restart_all"):
                    shuffled = list(phrases)
                    random.shuffle(shuffled)
                    st.session_state.rev_phrases = shuffled
                    st.session_state.rev_index = 0
                    st.session_state.rev_revealed = False
                    st.session_state.rev_known = set()
                    st.session_state.rev_again = set()
                    st.rerun()
            with col_s3:
                if st.button("← Return to Favourites", key="rev_return_done"):
                    st.session_state.rev_active = False
                    st.rerun()

    # ── CARD VIEW (FAVOURITES LIST) ───────────────────────────────────────────
    else:
        if fav_count == 0:
            st.markdown("""
            <div class="ns-card" style="text-align:center;padding:3rem 1.5rem;">
              <div style="font-size:3.5rem;margin-bottom:.8rem;">⭐</div>
              <div style="font-size:1.3rem;font-weight:700;color:var(--text-main);">No favourite phrases saved yet</div>
              <div style="font-size:.95rem;color:var(--text-muted);margin:.6rem auto 1.5rem;max-width:520px;line-height:1.65;">
                Start building your personalized Kannada revision deck! Click the <strong>☆ Save</strong> button on any phrase across the app:
              </div>
              <div style="display:flex;gap:.8rem;justify-content:center;flex-wrap:wrap;max-width:600px;margin:0 auto 1.5rem;">
                <span class="ns-pill">📖 Daily Lessons</span>
                <span class="ns-pill">📚 Phrasebook</span>
                <span class="ns-pill">🤖 AI Phrase Coach</span>
                <span class="ns-pill">🆘 Rescue Mode</span>
              </div>
              <div style="font-size:.85rem;color:var(--text-muted);">
                Once saved, your phrases persist safely and you can test yourself with <strong>Revision Mode</strong> anytime!
              </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            # Filter and Action Controls
            col_search, col_topic, col_btn = st.columns([3, 2, 2])
            with col_search:
                st.markdown('<div class="ns-section-label">Search</div>', unsafe_allow_html=True)
                fav_query = st.text_input(
                    "Search saved phrases",
                    placeholder="Search by Kannada, Roman, English, Tamil…",
                    label_visibility="collapsed",
                    key="fav_search_input",
                )
            with col_topic:
                st.markdown('<div class="ns-section-label">Filter by topic</div>', unsafe_allow_html=True)
                fav_topic_options = ["All topics"] + topics
                selected_fav_topic = st.selectbox(
                    "Topic filter",
                    fav_topic_options,
                    label_visibility="collapsed",
                    key="fav_topic_select",
                )
            with col_btn:
                st.markdown('<div class="ns-section-label">Revision Mode</div>', unsafe_allow_html=True)
                start_rev = st.button("🧠 Start Revision", key="start_rev_deck")

            filtered_favs = get_all_favourites(
                topic=selected_fav_topic if selected_fav_topic != "All topics" else None,
                query=fav_query,
            )

            if start_rev:
                if not filtered_favs:
                    st.warning("No phrases match current filter to start revision.")
                else:
                    shuffled = list(filtered_favs)
                    random.shuffle(shuffled)
                    st.session_state.rev_phrases = shuffled
                    st.session_state.rev_index = 0
                    st.session_state.rev_revealed = False
                    st.session_state.rev_known = set()
                    st.session_state.rev_again = set()
                    st.session_state.rev_topic = selected_fav_topic if selected_fav_topic != "All topics" else "All Saved Phrases"
                    st.session_state.rev_active = True
                    st.rerun()

            st.markdown(
                f'<div class="ns-section-sub" style="margin-top:.8rem;">'
                f'{len(filtered_favs)} phrase(s) saved · Click <strong>Revise this phrase</strong> or <strong>Start Revision</strong> above</div>',
                unsafe_allow_html=True,
            )

            if not filtered_favs:
                st.markdown("""
                <div class="ns-card" style="text-align:center;padding:2rem;">
                  <div style="font-size:2rem;margin-bottom:.5rem;">🔍</div>
                  <div style="font-weight:700;">No saved phrases match your filter.</div>
                  <div style="font-size:.85rem;color:var(--text-muted);margin-top:.25rem;">
                    Try clearing the search text or selecting "All topics".
                  </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                fav_cols = st.columns(2)
                for i, p in enumerate(filtered_favs):
                    with fav_cols[i % 2]:
                        badge_topic = p.get("topic") or "General"
                        date_str = p.get("created_at", "")[:10]
                        st.markdown(
                            f'<div class="ns-card">'
                            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.4rem;">'
                            f'<span class="ns-pill" style="font-size:.72rem;padding:.12rem .55rem;">📌 {badge_topic}</span>'
                            f'<span style="font-size:.75rem;color:var(--text-muted);">📅 {date_str}</span>'
                            f'</div>'
                            f'<div class="ns-kn">{p["kn"]}</div>'
                            f'<div class="ns-roman">📣 {p.get("roman", "")}</div>'
                            f'<div class="ns-meaning-label">English meaning</div>'
                            f'<div class="ns-meaning">🇬🇧 {p.get("meaning_en") or "—"}</div>'
                            + (f'<div class="ns-meaning-label">Tamil meaning</div><div class="ns-meaning">🇮🇳 {p.get("meaning_ta")}</div>' if p.get("meaning_ta") else '')
                            + f'</div>',
                            unsafe_allow_html=True,
                        )
                        c_audio, c_del, c_rev = st.columns([2, 1, 1])
                        with c_audio:
                            aud = make_audio(p["kn"])
                            if aud:
                                st.audio(aud, format="audio/mp3")
                            else:
                                st.caption("Audio unavailable.")
                        with c_del:
                            if st.button("🗑️ Remove", key=f"del_fav_{p['id']}"):
                                remove_favourite(p["id"])
                                st.info(f"Removed '{p['kn']}' from favourites.")
                                st.rerun()
                        with c_rev:
                            if st.button("🎯 Revise", key=f"rev_single_{p['id']}", help="Revise just this phrase"):
                                st.session_state.rev_phrases = [p]
                                st.session_state.rev_index = 0
                                st.session_state.rev_revealed = False
                                st.session_state.rev_known = set()
                                st.session_state.rev_again = set()
                                st.session_state.rev_topic = p.get("topic") or "Single Phrase"
                                st.session_state.rev_active = True
                                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Daily Lessons
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Daily Lessons":

    # ── Helpers ──────────────────────────────────────────────────────────────
    DIFFICULTY_CLASS = {
        "Beginner":     "beginner",
        "Elementary":   "elementary",
        "Intermediate": "intermediate",
    }
    DIFFICULTY_ICON = {
        "Beginner":     "🌱",
        "Elementary":   "🌿",
        "Intermediate": "🌳",
    }
    TOPIC_ICONS = {
        "Greetings":    "👋",
        "Introductions":"🤝",
        "Shopping":     "🛒",
        "Restaurant":   "🍽️",
        "Transport":    "🚌",
        "Directions":   "🗺️",
        "Numbers":      "🔢",
        "General Help": "💬",
    }

    # Load completed IDs fresh from SQLite on every run
    completed_ids = get_completed_ids()
    curated_ids_set = set(LESSON_IDS)
    total   = len(LESSONS)
    done    = len(completed_ids.intersection(curated_ids_set))

    # ── Decide view: index or detail ──────────────────────────────────────────
    if "lesson_view" not in st.session_state:
        st.session_state.lesson_view = "index"   # "index" | lesson_id string

    # ── HERO ─────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="ns-hero">
      <div class="ns-hero-greeting">ದೈನಂದಿನ ಪಾಠಗಳು — Daily Lessons</div>
      <h1>Structured Kannada learning.</h1>
      <p>Work through beginner-friendly lessons at your own pace.
         Each lesson has phrases, pronunciation, meanings and a short practice activity.</p>
      <div class="ns-hero-badges">
        <span class="ns-badge">📖 {total} curated lessons</span>
        <span class="ns-badge">✅ {done} completed</span>
        <span class="ns-badge">📅 Daily auto-generation active</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── INDEX VIEW ────────────────────────────────────────────────────────────
    if st.session_state.lesson_view == "index":

        # ── TODAY'S KANNADA LESSON ────────────────────────────────────────────
        today_lesson = get_daily_lesson()
        today_lid = today_lesson.get("id", f"daily-{get_today_date_str()}")
        is_today_done = is_completed(today_lid)
        today_diff_cls = DIFFICULTY_CLASS.get(today_lesson.get("difficulty", "Beginner"), "beginner")
        today_diff_icon = DIFFICULTY_ICON.get(today_lesson.get("difficulty", "Beginner"), "🌱")
        today_topic_icon = TOPIC_ICONS.get(today_lesson.get("topic", "General"), "📖")
        today_source = today_lesson.get("source", "curated_fallback")

        st.markdown('<div class="ns-section-label">Featured Daily Lesson</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="ns-section-title">Today\'s Kannada Lesson &nbsp;·&nbsp; {today_lesson.get("date", get_today_date_str())}</div>',
            unsafe_allow_html=True,
        )

        if today_source == "ai_generated":
            source_badge_html = '<span class="ns-badge" style="background:#176B55;color:#fff;">✨ AI-Generated</span>'
        else:
            source_badge_html = '<span class="ns-badge" style="background:#B45309;color:#fff;">📚 Curated Fallback</span>'

        status_badge_html = (
            '<span class="ns-badge" style="background:#E8F4ED;color:#176B55 !important;">✅ Completed</span>'
            if is_today_done
            else '<span class="ns-badge" style="background:#F4F4F5;color:#71717A !important;">○ Not yet completed</span>'
        )

        st.markdown(f"""
        <div class="ns-card" style="border:1.5px solid var(--green-primary);box-shadow:var(--shadow-md);margin-bottom:1rem;">
          <div style="font-size:1.35rem;font-weight:700;color:var(--green-deep);margin-bottom:.4rem;">
            {today_lesson.get('title', 'Daily Lesson')}
          </div>
          <div style="display:flex;gap:.4rem;flex-wrap:wrap;align-items:center;margin-bottom:.7rem;">
            <span class="ns-lesson-badge {today_diff_cls}">{today_diff_icon} {today_lesson.get('difficulty', 'Beginner')}</span>
            <span class="ns-topic-pill">{today_topic_icon} {today_lesson.get('topic', 'General')}</span>
            {source_badge_html}
            {status_badge_html}
          </div>
          <div style="font-size:.88rem;color:var(--text-main);line-height:1.6;margin-bottom:.5rem;">
            <strong>Practice:</strong> {today_lesson.get('practice', '')[:160]}...
          </div>
        </div>
        """, unsafe_allow_html=True)

        col_today_act1, col_today_act2 = st.columns([1, 1])
        with col_today_act1:
            if st.button("📖 Open Today's Lesson", key="open_today_lesson_btn"):
                st.session_state.lesson_view = today_lid
                st.rerun()

        with col_today_act2:
            if today_source == "curated_fallback":
                if st.button("🔄 Retry AI Generation", key="retry_daily_ai_gen_btn"):
                    import time
                    last_retry = st.session_state.get("_last_daily_retry", 0)
                    if time.time() - last_retry < 8:
                        st.warning("Please wait a few seconds before retrying.")
                    else:
                        st.session_state._last_daily_retry = time.time()
                        retried = get_daily_lesson(force_ai_retry=True)
                        if retried.get("source") == "ai_generated":
                            st.success("✨ Successfully generated fresh lesson with Gemini!")
                        else:
                            err_msg = retried.get("retry_error") or retried.get("fallback_reason", "AI unavailable")
                            st.error(f"Generation attempt: {err_msg}. Retaining curated fallback.")
                        st.rerun()

        if today_source == "curated_fallback" and today_lesson.get("fallback_reason"):
            st.markdown(
                f'<div class="ns-note-box" style="margin-top:.4rem;margin-bottom:1.5rem;">'
                f'ℹ️ <strong>Curated Fallback Active:</strong> {today_lesson["fallback_reason"]}<br>'
                f'<span style="font-size:.8rem;color:var(--text-muted);">'
                f'You have access to an authentic curated lesson for today. Click "Retry AI Generation" anytime to attempt fresh Gemini generation.'
                f'</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown('<div class="ns-section-label">Foundation Curriculum</div>', unsafe_allow_html=True)
        st.markdown('<div class="ns-section-title">8 Curated Foundational Lessons</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="ns-section-sub">Step-by-step beginner lessons with audio, practice, and completion tracking.</div>',
            unsafe_allow_html=True,
        )

        # Topic filter
        st.markdown('<div class="ns-section-label">Filter by topic</div>', unsafe_allow_html=True)
        topic_options = ["All topics"] + LESSON_TOPICS
        selected_topic = st.selectbox(
            "Topic filter",
            topic_options,
            label_visibility="collapsed",
            key="lesson_topic_filter",
        )

        # Status filter
        status_filter = st.radio(
            "Show",
            ["All", "Not yet completed", "Completed"],
            horizontal=True,
            key="lesson_status_filter",
        )

        st.markdown("---")

        # Filter lessons
        visible = LESSONS
        if selected_topic != "All topics":
            visible = [l for l in visible if l["topic"] == selected_topic]
        if status_filter == "Not yet completed":
            visible = [l for l in visible if l["id"] not in completed_ids]
        elif status_filter == "Completed":
            visible = [l for l in visible if l["id"] in completed_ids]

        if not visible:
            st.markdown("""
            <div class="ns-card" style="text-align:center;padding:2rem;">
              <div style="font-size:2rem;margin-bottom:.5rem;">📭</div>
              <div style="font-weight:700;">No lessons match your filter.</div>
              <div style="font-size:.85rem;color:var(--text-muted);margin-top:.25rem;">
                Try a different topic or status filter.
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="ns-section-sub">{len(visible)} lesson(s) shown</div>',
                unsafe_allow_html=True,
            )
            for lesson in visible:
                lid         = lesson["id"]
                is_done     = lid in completed_ids
                diff_cls    = DIFFICULTY_CLASS.get(lesson["difficulty"], "beginner")
                diff_icon   = DIFFICULTY_ICON.get(lesson["difficulty"], "🌱")
                topic_icon  = TOPIC_ICONS.get(lesson["topic"], "📖")
                done_html   = "✅ Completed" if is_done else "○ Not yet started"
                card_cls    = "completed" if is_done else "incomplete"

                st.markdown(
                    f'<div class="ns-lesson-index-card {card_cls}">'
                    f'<div style="flex:1;">'
                    f'<span class="ns-lesson-badge {diff_cls}">{diff_icon} {lesson["difficulty"]}</span>'
                    f'<span class="ns-topic-pill" style="margin-left:.4rem;">'
                    f'{topic_icon} {lesson["topic"]}</span><br>'
                    f'<strong style="font-size:1rem;">{lesson["title"]}</strong>'
                    f'<div style="font-size:.8rem;color:var(--text-muted);margin-top:.2rem;">'
                    f'{len(lesson["phrases"])} phrases &nbsp;·&nbsp; {done_html}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button(f"Open lesson", key=f"open_{lid}"):
                    st.session_state.lesson_view = lid
                    st.rerun()

    # ── DETAIL VIEW ───────────────────────────────────────────────────────────
    else:
        lesson_id = st.session_state.lesson_view
        is_daily = lesson_id.startswith("daily-")
        if is_daily:
            target_date = lesson_id.replace("daily-", "")
            lesson = get_saved_daily_lesson(target_date) or get_daily_lesson(target_date)
        else:
            lesson = LESSONS_BY_ID.get(lesson_id)

        if not lesson:
            st.error("Lesson not found. Returning to the lesson list.")
            st.session_state.lesson_view = "index"
            st.rerun()

        # Re-read completion state (may have changed via button press)
        completed_ids = get_completed_ids()
        is_done = is_completed(lesson_id)

        diff_cls   = DIFFICULTY_CLASS.get(lesson.get("difficulty", "Beginner"), "beginner")
        diff_icon  = DIFFICULTY_ICON.get(lesson.get("difficulty", "Beginner"), "🌱")
        topic_icon = TOPIC_ICONS.get(lesson.get("topic", "General"), "📖")

        # Back button
        if st.button("← Back to lessons", key="back_to_index"):
            st.session_state.lesson_view = "index"
            st.rerun()

        # Daily lesson source indicator
        if is_daily:
            d_source = lesson.get("source", "curated_fallback")
            if d_source == "ai_generated":
                st.markdown(
                    f'<div style="margin-bottom:.5rem;">'
                    f'<span class="ns-badge" style="background:#176B55;color:#fff;">✨ AI-Generated Daily Lesson ({lesson.get("date", "")})</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="margin-bottom:.5rem;">'
                    f'<span class="ns-badge" style="background:#B45309;color:#fff;">📚 Curated Fallback ({lesson.get("date", "")})</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if lesson.get("fallback_reason"):
                    st.markdown(
                        f'<div class="ns-note-box">'
                        f'ℹ️ <strong>Curated Fallback Active:</strong> {lesson["fallback_reason"]}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        # Lesson header
        st.markdown(
            f'<span class="ns-lesson-badge {diff_cls}">{diff_icon} {lesson["difficulty"]}</span>'
            f'&ensp;<span class="ns-topic-pill">{topic_icon} {lesson["topic"]}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="ns-section-title" style="margin-top:.6rem;font-size:1.4rem;">'
            f'{lesson["title"]}</div>',
            unsafe_allow_html=True,
        )

        # Completion banner
        if is_done:
            st.markdown("""
            <div class="ns-done-banner">
              <div class="ns-done-icon">✅</div>
              <div>
                <div class="ns-done-text">Lesson completed!</div>
                <div class="ns-done-sub">You can still review the phrases and replay audio below.</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        # Learning objectives
        st.markdown('<div class="ns-section-label" style="margin-top:.8rem;">Learning objectives</div>',
                    unsafe_allow_html=True)
        obj_items = "".join(f"<li>{obj}</li>" for obj in lesson["objectives"])
        st.markdown(f'<ul class="ns-objective-list">{obj_items}</ul>', unsafe_allow_html=True)

        st.markdown("---")

        # Phrases
        st.markdown('<div class="ns-section-label">Phrases in this lesson</div>', unsafe_allow_html=True)
        lang_label = "Tamil meaning" if language == "Tamil" else "English meaning"

        for idx, phrase in enumerate(lesson["phrases"]):
            meaning_text = phrase["meaning_ta"] if language == "Tamil" else phrase["meaning_en"]
            st.markdown(
                f'<div class="ns-lesson-phrase">'
                f'<div class="ns-lesson-kn">{phrase["kn"]}</div>'
                f'<div class="ns-lesson-roman">📣 {phrase["roman"]}</div>'
                f'<div style="font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;'
                f'color:var(--green-primary);margin-bottom:.15rem;">{lang_label}</div>'
                f'<div class="ns-lesson-meaning">{meaning_text}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            col_ls_fav, col_ls_aud = st.columns([1, 2])
            with col_ls_fav:
                saved = is_favourite(phrase["kn"])
                btn_label = "★ Saved" if saved else "☆ Save"
                pid = generate_phrase_id(phrase["kn"])
                if st.button(btn_label, key=f"fav_ls_{lesson_id}_{idx}_{pid}"):
                    if saved:
                        remove_favourite(phrase["kn"])
                        st.info(f"Removed '{phrase['kn']}' from favourites.")
                    else:
                        add_favourite(
                            kn=phrase["kn"],
                            roman=phrase.get("roman", ""),
                            meaning_en=phrase.get("meaning_en", ""),
                            meaning_ta=phrase.get("meaning_ta", ""),
                            topic=lesson.get("topic", ""),
                        )
                        st.success(f"Saved '{phrase['kn']}' to favourites!")
                    st.rerun()
            with col_ls_aud:
                audio = make_audio(phrase["kn"])
                if audio:
                    st.audio(audio, format="audio/mp3")
                else:
                    st.caption("Audio unavailable for this phrase.")

        st.markdown("---")

        # Practice activity
        st.markdown('<div class="ns-section-label">Practice activity</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="ns-practice-box">🎯 {lesson["practice"]}</div>',
            unsafe_allow_html=True,
        )

        # Review activity (if present in daily lesson)
        if lesson.get("review"):
            st.markdown("---")
            st.markdown('<div class="ns-section-label">Review Activity</div>', unsafe_allow_html=True)
            rev = lesson["review"]
            if isinstance(rev, dict) and rev.get("question"):
                st.markdown(
                    f'<div class="ns-card" style="margin-bottom:.8rem;">'
                    f'<strong style="color:var(--green-deep);font-size:1.05rem;">Quick Quiz:</strong>'
                    f'<div style="margin-top:.3rem;color:var(--text-main);font-size:1rem;">{rev["question"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                opts = rev.get("options", [])
                if opts:
                    ans_key = f"daily_rev_ans_{lesson_id}"
                    user_ans = st.radio("Choose the correct answer:", opts, key=ans_key)
                    if st.button("Check Answer", key=f"daily_rev_chk_{lesson_id}"):
                        if user_ans == rev.get("answer"):
                            st.success(f"✅ Correct! '{user_ans}' is the right answer.")
                        else:
                            st.error(f"❌ Incorrect. The correct answer is: {rev.get('answer')}")
            elif isinstance(rev, str):
                st.markdown(f'<div class="ns-practice-box">💡 {rev}</div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-top:1.2rem;'></div>", unsafe_allow_html=True)

        # Completion toggle
        if not is_done:
            if st.button("✅ Mark lesson as completed", key=f"mark_done_{lesson_id}"):
                mark_completed(lesson_id)
                st.success("Great work! Lesson marked as completed.")
                st.rerun()
        else:
            if st.button("↩️ Mark as not completed", key=f"mark_undone_{lesson_id}"):
                mark_incomplete(lesson_id)
                st.info("Lesson marked as not completed.")
                st.rerun()

        st.markdown("---")
        if st.button("← Back to all lessons", key="back_to_index_bottom"):
            st.session_state.lesson_view = "index"
            st.rerun()
# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Interactive Quizzes
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Interactive Quizzes":
    st.markdown("""
    <div class="ns-hero">
      <div class="ns-hero-greeting">ಪರಸ್ಪರ ರಸಪ್ರಶ್ನೆ — Interactive Quizzes</div>
      <h1>Test your everyday Kannada.</h1>
      <p>Challenge yourself with quick 5-question quizzes based on real-life scenarios.
         Save any phrase to your Favourites to revise later.</p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize Quiz session state
    if "quiz_questions" not in st.session_state:
        st.session_state.quiz_questions = []
    if "quiz_submitted" not in st.session_state:
        st.session_state.quiz_submitted = False
    if "quiz_score" not in st.session_state:
        st.session_state.quiz_score = 0
    if "quiz_topic" not in st.session_state:
        st.session_state.quiz_topic = "All Topics"
    if "quiz_answers" not in st.session_state:
        st.session_state.quiz_answers = []

    quiz_topics = ["All Topics"] + SCENARIOS
    col_t1, col_t2 = st.columns([3, 2])
    with col_t1:
        st.markdown('<div class="ns-section-label">Select Quiz Topic</div>', unsafe_allow_html=True)
        selected_q_topic = st.selectbox(
            "Quiz Topic",
            quiz_topics,
            label_visibility="collapsed",
            key="quiz_topic_picker",
        )
    with col_t2:
        st.markdown('<div class="ns-section-label">Action</div>', unsafe_allow_html=True)
        if st.button("🎲 Generate New Quiz", key="gen_quiz_btn"):
            pool = PHRASES if selected_q_topic == "All Topics" else [p for p in PHRASES if p.get("scenario") == selected_q_topic]
            if len(pool) < 2:
                pool = PHRASES

            num_q = min(5, len(pool))
            chosen_phrases = random.sample(pool, num_q)
            all_kns = [p["kn"] for p in PHRASES]

            new_questions = []
            for cp in chosen_phrases:
                meaning_display = cp.get("meaning_ta") if language == "Tamil" else cp.get("meaning_en")
                distractors = [k for k in all_kns if k != cp["kn"]]
                dist_sample = random.sample(distractors, min(3, len(distractors)))
                options = [cp["kn"]] + dist_sample
                random.shuffle(options)
                new_questions.append({
                    "prompt": f"What is the Kannada phrase for '{meaning_display}'?",
                    "correct": cp["kn"],
                    "roman": cp.get("roman", ""),
                    "meaning_en": cp.get("meaning_en", ""),
                    "meaning_ta": cp.get("meaning_ta", ""),
                    "scenario": cp.get("scenario", selected_q_topic),
                    "options": options,
                })

            st.session_state.quiz_questions = new_questions
            st.session_state.quiz_submitted = False
            st.session_state.quiz_score = 0
            st.session_state.quiz_answers = []
            st.session_state.quiz_topic = selected_q_topic
            st.rerun()

    # Generate initial quiz if empty
    if not st.session_state.quiz_questions:
        pool = PHRASES
        chosen_phrases = random.sample(pool, min(5, len(pool)))
        all_kns = [p["kn"] for p in PHRASES]
        new_questions = []
        for cp in chosen_phrases:
            meaning_display = cp.get("meaning_ta") if language == "Tamil" else cp.get("meaning_en")
            distractors = [k for k in all_kns if k != cp["kn"]]
            dist_sample = random.sample(distractors, min(3, len(distractors)))
            options = [cp["kn"]] + dist_sample
            random.shuffle(options)
            new_questions.append({
                "prompt": f"What is the Kannada phrase for '{meaning_display}'?",
                "correct": cp["kn"],
                "roman": cp.get("roman", ""),
                "meaning_en": cp.get("meaning_en", ""),
                "meaning_ta": cp.get("meaning_ta", ""),
                "scenario": cp.get("scenario", "All Topics"),
                "options": options,
            })
        st.session_state.quiz_questions = new_questions
        st.session_state.quiz_submitted = False
        st.session_state.quiz_score = 0
        st.session_state.quiz_answers = []
        st.session_state.quiz_topic = "All Topics"

    questions = st.session_state.quiz_questions

    # ── QUIZ NOT YET SUBMITTED ────────────────────────────────────────────────
    if not st.session_state.quiz_submitted:
        st.markdown(f'<div class="ns-section-sub" style="margin-top:.8rem;">Topic: <strong>{st.session_state.quiz_topic}</strong> · {len(questions)} Question(s)</div>', unsafe_allow_html=True)
        user_choices = {}
        for idx, q in enumerate(questions):
            st.markdown(
                f'<div class="ns-card" style="margin-bottom:.8rem;">'
                f'<strong style="font-size:1rem;color:var(--green-deep);">Question {idx + 1}:</strong> '
                f'<span style="font-size:1rem;color:var(--text-main);">{q["prompt"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            choice = st.radio(
                label=f"Options for question {idx + 1}",
                options=q["options"],
                key=f"quiz_ans_{idx}",
                label_visibility="collapsed",
            )
            user_choices[idx] = choice

        if st.button("🎯 Submit Answers", key="quiz_submit_btn"):
            score = 0
            answers_to_save = []
            for idx, q in enumerate(questions):
                chosen = user_choices.get(idx, "")
                is_correct = (chosen == q["correct"])
                if is_correct:
                    score += 1
                answers_to_save.append({
                    "q_index": idx,
                    "question": q["prompt"],
                    "chosen": chosen,
                    "correct": q["correct"],
                    "is_correct": is_correct,
                })

            st.session_state.quiz_score = score
            st.session_state.quiz_answers = answers_to_save
            st.session_state.quiz_submitted = True
            save_quiz_attempt(
                topic=st.session_state.quiz_topic,
                score=score,
                total=len(questions),
                answers=answers_to_save,
            )
            st.rerun()

    # ── QUIZ SUBMITTED: REVIEW & SAVE PHRASES ─────────────────────────────────
    else:
        score = st.session_state.quiz_score
        total = len(questions)
        pct = round((score / total) * 100) if total > 0 else 0

        st.markdown(f"""
        <div class="ns-result-card" style="text-align:center;padding:2rem;">
          <div style="font-size:3rem;margin-bottom:.5rem;">🏆</div>
          <div style="font-size:1.6rem;font-weight:700;color:var(--green-deep);">Quiz Complete!</div>
          <div style="font-size:1.1rem;color:var(--text-main);margin:.4rem 0 1rem;">
            You scored <strong>{score} out of {total}</strong> ({pct}%)
          </div>
          <span class="ns-pill" style="font-size:.85rem;background:#E8F4ED;color:#176B55;">
            Recorded in your Quiz History
          </span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="ns-section-label" style="margin-top:1.5rem;">Answer Review & Save to Favourites</div>', unsafe_allow_html=True)

        for idx, (q, ans) in enumerate(zip(questions, st.session_state.quiz_answers)):
            is_c = ans.get("is_correct", False)
            status_html = "✅ Correct" if is_c else f"❌ Incorrect (You chose: {ans.get('chosen', '')})"
            status_color = "#176B55" if is_c else "#912018"

            st.markdown(
                f'<div class="ns-card" style="margin-bottom:.8rem;border-left:4px solid {status_color};">'
                f'<div style="font-size:.85rem;font-weight:700;color:{status_color};">{status_html}</div>'
                f'<div style="font-size:1rem;color:var(--text-main);margin:.2rem 0 .5rem;">{q["prompt"]}</div>'
                f'<div class="ns-kn" style="font-size:1.4rem;">{q["correct"]}</div>'
                f'<div class="ns-roman">📣 {q.get("roman", "")}</div>'
                f'<div style="font-size:.82rem;color:var(--text-muted);margin-top:.2rem;">🇬🇧 {q.get("meaning_en", "")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            col_q_fav, col_q_aud = st.columns([1, 2])
            with col_q_fav:
                saved = is_favourite(q["correct"])
                btn_label = "★ Saved" if saved else "☆ Save"
                pid = generate_phrase_id(q["correct"])
                if st.button(btn_label, key=f"fav_quiz_{idx}_{pid}"):
                    if saved:
                        remove_favourite(q["correct"])
                        st.info(f"Removed '{q['correct']}' from favourites.")
                    else:
                        add_favourite(
                            kn=q["correct"],
                            roman=q.get("roman", ""),
                            meaning_en=q.get("meaning_en", ""),
                            meaning_ta=q.get("meaning_ta", ""),
                            topic=q.get("scenario", "Quiz"),
                        )
                        st.success(f"Saved '{q['correct']}' to favourites!")
                    st.rerun()
            with col_q_aud:
                aud = make_audio(q["correct"])
                if aud:
                    st.audio(aud, format="audio/mp3")

        st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Take Another Quiz", key="quiz_retry_btn"):
            st.session_state.quiz_questions = []
            st.session_state.quiz_submitted = False
            st.session_state.quiz_score = 0
            st.session_state.quiz_answers = []
            st.rerun()

    # ── RECENT QUIZ ATTEMPTS ──────────────────────────────────────────────────
    recent_attempts = get_recent_attempts(limit=5)
    if recent_attempts:
        st.markdown("---")
        st.markdown('<div class="ns-section-label">Your Quiz History</div>', unsafe_allow_html=True)
        st.markdown('<div class="ns-section-title">Recent Quiz Attempts</div>', unsafe_allow_html=True)
        for att in recent_attempts:
            pct_att = round((att["score"] / att["total"]) * 100) if att["total"] > 0 else 0
            st.markdown(
                f'<div class="ns-card" style="padding:.8rem 1.1rem;margin-bottom:.5rem;display:flex;justify-content:space-between;align-items:center;">'
                f'<div>'
                f'<strong>{att["topic"]}</strong> &nbsp;·&nbsp; '
                f'<span style="color:var(--green-primary);font-weight:700;">{att["score"]} / {att["total"]} ({pct_att}%)</span>'
                f'</div>'
                f'<div style="font-size:.8rem;color:var(--text-muted);">🕒 {att["timestamp"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Learning Progress Dashboard
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Learning Progress":
    render_learning_progress_dashboard(language=language)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="ns-footer">
  🌿 NammaSahaaya AI &nbsp;·&nbsp; MVP Hackathon Build &nbsp;·&nbsp;
  Kannada phrases and pronunciation should be reviewed by native speakers before
  real-world reliance.
</div>
""", unsafe_allow_html=True)
