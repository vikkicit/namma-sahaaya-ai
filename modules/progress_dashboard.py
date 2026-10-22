# modules/progress_dashboard.py
# Learning Progress Dashboard data access, analytics calculation, and UI rendering.
# Adheres to strict data integrity: read-only access to existing SQLite databases,
# handles empty tables gracefully, avoids division by zero, and avoids any external API calls.

import datetime
import pathlib
import sqlite3
import pandas as pd
import streamlit as st

from modules.lessons import LESSONS, LESSON_IDS, LESSONS_BY_ID, LESSON_TOPICS

# Database paths match existing app modules
_DEFAULT_LESSON_DB = pathlib.Path(__file__).parent.parent / "lesson_progress.db"
_DEFAULT_QUIZ_DB = pathlib.Path(__file__).parent.parent / "quiz_progress.db"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DATABASE ACCESS (READ-ONLY)
# ═══════════════════════════════════════════════════════════════════════════════

def get_ro_connection(db_path: pathlib.Path | str) -> sqlite3.Connection | None:
    """
    Open a read-only SQLite connection.
    Uses URI mode where supported, falls back to standard connection if necessary.
    Returns None if file does not exist.
    """
    p = pathlib.Path(db_path) if isinstance(db_path, str) else db_path
    if str(p) == ":memory:":
        return sqlite3.connect(":memory:")
    if not p.exists():
        return None
    try:
        # Read-only URI mode ensures no accidental modifications
        return sqlite3.connect(f"file:{p.resolve().as_posix()}?mode=ro", uri=True)
    except Exception:
        # Fallback to standard connection if URI ro is unsupported
        return sqlite3.connect(str(p), check_same_thread=False)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. METRICS & ANALYTICS CALCULATIONS (PURE LOGIC)
# ═══════════════════════════════════════════════════════════════════════════════

def get_lesson_metrics(db_path: pathlib.Path | str = _DEFAULT_LESSON_DB) -> dict:
    """
    Calculate lesson completion statistics using existing completed_lessons table.
    Distinguishes curated lessons from any arbitrary IDs.
    Returns safe empty structures if database or table does not exist.
    """
    total_curated = len(LESSONS)
    completed_rows = []

    conn = get_ro_connection(db_path)
    if conn:
        try:
            # Check if table exists
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='completed_lessons'"
            )
            if cur.fetchone():
                cur.execute(
                    "SELECT lesson_id, completed_at FROM completed_lessons ORDER BY completed_at DESC"
                )
                completed_rows = cur.fetchall()
        except Exception as exc:
            # Fallback gracefully
            completed_rows = []
        finally:
            conn.close()

    # Map completed records: lesson_id -> completed_at
    completed_map = {row[0]: row[1] for row in completed_rows if row[0]}
    completed_ids = set(completed_map.keys())

    curated_ids_set = set(LESSON_IDS)
    completed_curated_ids = completed_ids.intersection(curated_ids_set)
    completed_curated_count = len(completed_curated_ids)

    # Calculate percentage safely
    completion_pct = (
        round((completed_curated_count / total_curated) * 100.0, 1)
        if total_curated > 0
        else 0.0
    )

    # Detailed lists
    completed_curated_list = []
    remaining_curated_list = []

    for lesson in LESSONS:
        lid = lesson["id"]
        item = {
            "id": lid,
            "title": lesson.get("title", lid),
            "topic": lesson.get("topic", "General"),
            "difficulty": lesson.get("difficulty", "Beginner"),
            "phrase_count": len(lesson.get("phrases", [])),
        }
        if lid in completed_curated_ids:
            item["completed_at"] = completed_map.get(lid, "")
            completed_curated_list.append(item)
        else:
            remaining_curated_list.append(item)

    # Other completed (non-curated if any exist)
    other_completed_ids = list(completed_ids - curated_ids_set)

    return {
        "total_curated": total_curated,
        "completed_curated_count": completed_curated_count,
        "remaining_curated_count": total_curated - completed_curated_count,
        "completion_percentage": completion_pct,
        "completed_curated_list": completed_curated_list,
        "remaining_curated_list": remaining_curated_list,
        "other_completed_ids": other_completed_ids,
        "has_completed": completed_curated_count > 0,
    }


def get_quiz_metrics(db_path: pathlib.Path | str = _DEFAULT_QUIZ_DB) -> dict:
    """
    Calculate quiz performance statistics from quiz_attempts.
    Handles empty data safely and prevents division by zero.
    Identifies best-performing topics and topics needing improvement.
    """
    attempts = []
    conn = get_ro_connection(db_path)
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='quiz_attempts'"
            )
            if cur.fetchone():
                cur.execute(
                    "SELECT id, topic, score, total, timestamp FROM quiz_attempts ORDER BY id DESC"
                )
                rows = cur.fetchall()
                for r in rows:
                    attempts.append({
                        "id": r[0],
                        "topic": r[1] or "General",
                        "score": int(r[2]),
                        "total": int(r[3]),
                        "timestamp": r[4] or "",
                    })
        except Exception:
            attempts = []
        finally:
            conn.close()

    total_attempts = len(attempts)
    if total_attempts == 0:
        return {
            "has_attempts": False,
            "total_attempts": 0,
            "average_score_pct": 0.0,
            "best_score_pct": 0.0,
            "recent_attempts": [],
            "topic_stats": {},
            "best_topics": [],
            "needs_improvement_topics": [],
        }

    # Calculate percentages for each attempt
    processed_attempts = []
    percentages = []
    topic_data = {}

    for att in attempts:
        total = att["total"]
        score = att["score"]
        pct = round((score / total) * 100.0, 1) if total > 0 else 0.0
        percentages.append(pct)

        item = dict(att)
        item["percentage"] = pct
        processed_attempts.append(item)

        topic = att["topic"]
        if topic not in topic_data:
            topic_data[topic] = {
                "topic": topic,
                "attempts": 0,
                "total_score": 0,
                "total_possible": 0,
                "percentages": [],
            }
        topic_data[topic]["attempts"] += 1
        topic_data[topic]["total_score"] += score
        topic_data[topic]["total_possible"] += total
        topic_data[topic]["percentages"].append(pct)

    avg_pct = round(sum(percentages) / len(percentages), 1) if percentages else 0.0
    best_pct = round(max(percentages), 1) if percentages else 0.0

    # Aggregate topic statistics
    topic_stats = {}
    for topic, data in topic_data.items():
        t_attempts = data["attempts"]
        t_avg = round(sum(data["percentages"]) / t_attempts, 1) if t_attempts > 0 else 0.0
        t_best = round(max(data["percentages"]), 1) if data["percentages"] else 0.0
        topic_stats[topic] = {
            "topic": topic,
            "attempts": t_attempts,
            "avg_pct": t_avg,
            "best_pct": t_best,
            "total_score": data["total_score"],
            "total_possible": data["total_possible"],
        }

    # Best-performing topics: avg >= 80% (or highest avg topic)
    sorted_by_avg_desc = sorted(topic_stats.values(), key=lambda x: (x["avg_pct"], x["attempts"]), reverse=True)
    best_topics = [t for t in sorted_by_avg_desc if t["avg_pct"] >= 80.0]
    if not best_topics and sorted_by_avg_desc:
        # If none >= 80, the top scoring topic is highlighted
        best_topics = [sorted_by_avg_desc[0]]

    # Topics needing improvement: based on actual recorded scores and a reasonable minimum sample size (>= 1 attempt, avg < 70%)
    sorted_by_avg_asc = sorted(topic_stats.values(), key=lambda x: (x["avg_pct"], -x["attempts"]))
    needs_improvement_topics = [t for t in sorted_by_avg_asc if t["avg_pct"] < 70.0]

    return {
        "has_attempts": True,
        "total_attempts": total_attempts,
        "average_score_pct": avg_pct,
        "best_score_pct": best_pct,
        "recent_attempts": processed_attempts,
        "topic_stats": topic_stats,
        "best_topics": best_topics,
        "needs_improvement_topics": needs_improvement_topics,
    }


def get_favourites_and_revision_metrics(
    db_path: pathlib.Path | str = _DEFAULT_LESSON_DB,
    session_state: dict | None = None,
) -> dict:
    """
    Retrieve saved favourites from SQLite and inspect session-level revision activity.
    Explicitly reports that revision results are session-scoped and not persisted in SQLite.
    """
    favourites = []
    conn = get_ro_connection(db_path)
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='favourites'"
            )
            if cur.fetchone():
                cur.execute(
                    "SELECT id, kn, roman, meaning_en, meaning_ta, topic, created_at "
                    "FROM favourites ORDER BY created_at DESC, id DESC"
                )
                rows = cur.fetchall()
                for r in rows:
                    favourites.append({
                        "id": r[0],
                        "kn": r[1] or "",
                        "roman": r[2] or "",
                        "meaning_en": r[3] or "",
                        "meaning_ta": r[4] or "",
                        "topic": r[5] or "General",
                        "created_at": r[6] or "",
                    })
        except Exception:
            favourites = []
        finally:
            conn.close()

    total_favs = len(favourites)
    topic_counts = {}
    for fav in favourites:
        t = fav["topic"] or "General"
        topic_counts[t] = topic_counts.get(t, 0) + 1

    # In-session revision activity inspection (if session_state provided)
    session_known_count = 0
    session_again_count = 0
    has_session_revision = False
    if session_state:
        rev_k = session_state.get("rev_known")
        rev_a = session_state.get("rev_again")
        if isinstance(rev_k, (set, list)):
            session_known_count = len(rev_k)
        if isinstance(rev_a, (set, list)):
            session_again_count = len(rev_a)
        has_session_revision = (session_known_count + session_again_count) > 0

    return {
        "total_favourites": total_favs,
        "topic_counts": topic_counts,
        "recent_favourites": favourites[:5],
        "is_revision_persisted": False,
        "revision_persistence_note": (
            "Revision results are stored in-memory during your session and are not "
            "persisted to the SQLite database across restarts."
        ),
        "session_known_count": session_known_count,
        "session_again_count": session_again_count,
        "has_session_revision": has_session_revision,
    }


def generate_recommendations(
    lesson_metrics: dict,
    quiz_metrics: dict,
    fav_metrics: dict,
) -> list[dict]:
    """
    Generate transparent, rule-based recommendations from user's saved data.
    Does NOT call Gemini or external APIs.
    Returns prioritized list of actionable recommendations with navigation targets.
    """
    recs = []

    # Safe extraction of lesson metrics
    completed_curated_count = lesson_metrics.get("completed_curated_count", 0)
    total_curated = lesson_metrics.get("total_curated", len(LESSONS))
    completion_percentage = lesson_metrics.get("completion_percentage", 0.0)
    remaining_curated_count = lesson_metrics.get("remaining_curated_count", total_curated - completed_curated_count)
    remaining_curated_list = lesson_metrics.get("remaining_curated_list", [])

    # ── 1. Lesson Curriculum Recommendation ──────────────────────────────────
    if completed_curated_count == 0:
        first_lesson = LESSONS[0] if LESSONS else None
        lid = first_lesson["id"] if first_lesson else "greetings-01"
        ltitle = first_lesson["title"] if first_lesson else "First Hellos"
        recs.append({
            "id": "rec_lesson_start",
            "category": "Lessons",
            "icon": "📖",
            "title": f"Start Your First Lesson: {ltitle}",
            "reason": "You have not completed any curated lessons yet. Build your foundation with essential greetings and polite Kannada phrases.",
            "action_label": f"▶ Start '{ltitle}'",
            "nav_page": "Daily Lessons",
            "nav_kwargs": {"lesson_view": lid},
        })
    elif remaining_curated_count > 0 and remaining_curated_list:
        next_lesson = remaining_curated_list[0]
        recs.append({
            "id": "rec_lesson_continue",
            "category": "Lessons",
            "icon": "📖",
            "title": f"Continue Lesson: {next_lesson['title']}",
            "reason": (
                f"You have completed {completed_curated_count} of {total_curated} "
                f"curated lessons ({completion_percentage}%). Keep your momentum going with '{next_lesson['title']}'."
            ),
            "action_label": f"▶ Continue '{next_lesson['title']}'",
            "nav_page": "Daily Lessons",
            "nav_kwargs": {"lesson_view": next_lesson["id"]},
        })
    else:
        recs.append({
            "id": "rec_lesson_completed_all",
            "category": "Lessons",
            "icon": "🎉",
            "title": "All Curated Lessons Completed!",
            "reason": f"Outstanding! You completed all {total_curated} curated lessons. Revisit any lesson to refresh your vocabulary.",
            "action_label": "📖 Review Lessons",
            "nav_page": "Daily Lessons",
            "nav_kwargs": {"lesson_view": "index"},
        })

    # ── 2. Quiz Recommendation ───────────────────────────────────────────────
    has_quiz_attempts = quiz_metrics.get("has_attempts", False)
    needs_improvement_topics = quiz_metrics.get("needs_improvement_topics", [])
    average_score_pct = quiz_metrics.get("average_score_pct", 0.0)

    if not has_quiz_attempts:
        recs.append({
            "id": "rec_quiz_start",
            "category": "Quiz",
            "icon": "🎯",
            "title": "Take Your First Interactive Quiz",
            "reason": "You have no quiz attempts recorded yet. Challenge yourself with a quick 5-question scenario quiz to test your phrase retention.",
            "action_label": "🎲 Take a Quiz",
            "nav_page": "Interactive Quizzes",
            "nav_kwargs": {"quiz_questions": [], "quiz_submitted": False},
        })
    elif needs_improvement_topics:
        weak_topic = needs_improvement_topics[0]
        recs.append({
            "id": "rec_quiz_improve",
            "category": "Quiz",
            "icon": "🎯",
            "title": f"Targeted Practice: {weak_topic['topic']}",
            "reason": (
                f"Your average score in '{weak_topic['topic']}' is {weak_topic['avg_pct']}% across {weak_topic['attempts']} attempt(s). "
                f"A targeted practice quiz will strengthen your confidence in this scenario."
            ),
            "action_label": f"🎲 Practice '{weak_topic['topic']}' Quiz",
            "nav_page": "Interactive Quizzes",
            "nav_kwargs": {
                "quiz_topic_picker": weak_topic["topic"],
                "quiz_questions": [],
                "quiz_submitted": False,
            },
        })
    else:
        recs.append({
            "id": "rec_quiz_challenge",
            "category": "Quiz",
            "icon": "🎯",
            "title": "Mixed Scenario Challenge",
            "reason": (
                f"Great job! Your overall quiz accuracy is {average_score_pct}%. "
                f"Take an 'All Topics' mixed quiz to test your versatility across scenarios."
            ),
            "action_label": "🎲 Take Mixed Quiz",
            "nav_page": "Interactive Quizzes",
            "nav_kwargs": {
                "quiz_topic_picker": "All Topics",
                "quiz_questions": [],
                "quiz_submitted": False,
            },
        })

    # ── 3. Favourites & Revision Recommendation ───────────────────────────────
    total_favourites = fav_metrics.get("total_favourites", 0)
    has_session_revision = fav_metrics.get("has_session_revision", False)
    session_known_count = fav_metrics.get("session_known_count", 0)
    session_again_count = fav_metrics.get("session_again_count", 0)

    if total_favourites == 0:
        recs.append({
            "id": "rec_fav_bookmark",
            "category": "Favourites",
            "icon": "⭐",
            "title": "Bookmark Essential Phrases",
            "reason": "You have not saved any favourite phrases yet. Click '☆ Save' on phrases in lessons, phrasebook, or coach to build a personalized study deck.",
            "action_label": "📚 Browse Phrasebook",
            "nav_page": "Phrasebook",
            "nav_kwargs": {},
        })
    elif not has_session_revision:
        recs.append({
            "id": "rec_revision_start",
            "category": "Revision",
            "icon": "🧠",
            "title": "Revise Your Saved Phrases",
            "reason": f"You have {total_favourites} phrase(s) saved in your library. Test your active recall with flashcards in Revision Mode.",
            "action_label": "🧠 Start Revision Flashcards",
            "nav_page": "My Favourites",
            "nav_kwargs": {
                "rev_active": True,
                "rev_index": 0,
                "rev_revealed": False,
                "rev_known": set(),
                "rev_again": set(),
            },
        })
    else:
        recs.append({
            "id": "rec_fav_view",
            "category": "Revision",
            "icon": "⭐",
            "title": "Review Your Saved Library",
            "reason": (
                f"You have revised phrases in this session ({session_known_count} known, "
                f"{session_again_count} to practice). View your library to manage your deck."
            ),
            "action_label": "⭐ Open My Favourites",
            "nav_page": "My Favourites",
            "nav_kwargs": {"rev_active": False},
        })

    return recs


# ═══════════════════════════════════════════════════════════════════════════════
# 3. STREAMLIT NAVIGATION HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def set_page_navigation(target_page: str, state_dict: dict | None = None, **kwargs):
    """Callback to update session state for page routing."""
    target = state_dict if state_dict is not None else st.session_state
    target["nav_page"] = target_page
    for k, v in kwargs.items():
        target[k] = v


# ═══════════════════════════════════════════════════════════════════════════════
# 4. DASHBOARD UI RENDERING
# ═══════════════════════════════════════════════════════════════════════════════

def render_learning_progress_dashboard(language: str = "English"):
    """
    Render the complete Learning Progress Dashboard.
    Incorporates summary metric cards, quiz analytics, lesson progress,
    favourites/revision status, and data-driven recommendations.
    """
    # ── Fetch fresh metrics from local SQLite databases ───────────────────────
    lesson_met = get_lesson_metrics()
    quiz_met = get_quiz_metrics()
    fav_met = get_favourites_and_revision_metrics(session_state=st.session_state)
    recs = generate_recommendations(lesson_met, quiz_met, fav_met)

    # ── Dashboard Specific CSS ────────────────────────────────────────────────
    st.markdown("""
    <style>
    .ns-stat-card {
        background: var(--white);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1.1rem 1.2rem;
        box-shadow: var(--shadow-sm);
        text-align: center;
        margin-bottom: .8rem;
        transition: transform .15s ease, box-shadow .15s ease;
    }
    .ns-stat-card:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }
    .ns-stat-label {
        font-size: .72rem;
        font-weight: 700;
        letter-spacing: .08em;
        text-transform: uppercase;
        color: var(--green-primary);
        margin-bottom: .3rem;
    }
    .ns-stat-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: var(--green-deep);
        line-height: 1.15;
    }
    .ns-stat-sub {
        font-size: .8rem;
        color: var(--text-muted);
        margin-top: .3rem;
    }
    .ns-rec-card {
        background: var(--white);
        border: 1.5px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1.1rem 1.3rem;
        margin-bottom: .8rem;
        box-shadow: var(--shadow-sm);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .ns-rec-badge {
        font-size: .7rem;
        font-weight: 700;
        letter-spacing: .08em;
        text-transform: uppercase;
        color: var(--green-primary);
        background: var(--green-soft);
        padding: .2rem .6rem;
        border-radius: 12px;
        display: inline-block;
        margin-bottom: .4rem;
    }
    .ns-rec-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--green-deep);
        margin-bottom: .3rem;
    }
    .ns-rec-desc {
        font-size: .85rem;
        color: var(--text-main);
        line-height: 1.5;
        margin-bottom: .8rem;
    }
    .ns-list-row {
        background: var(--white);
        border: 1px solid var(--border);
        border-radius: var(--radius-sm);
        padding: .75rem 1rem;
        margin-bottom: .5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .ns-note-box {
        background: #F4FBF7;
        border-left: 4px solid var(--green-primary);
        border-radius: var(--radius-sm);
        padding: .8rem 1.1rem;
        font-size: .85rem;
        color: var(--text-main);
        line-height: 1.55;
        margin: .8rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── HERO BANNER ───────────────────────────────────────────────────────────
    avg_score_text = f"{quiz_met['average_score_pct']}%" if quiz_met["has_attempts"] else "No quizzes yet"
    st.markdown(f"""
    <div class="ns-hero">
      <div class="ns-hero-greeting">ಕಲಿಕೆಯ ಪ್ರಗತಿ — Learning Progress</div>
      <h1>Your personal learning dashboard.</h1>
      <p>Monitor your progress across curated Kannada lessons, quiz accuracy, saved vocabulary, and rule-based study recommendations.</p>
      <div class="ns-hero-badges">
        <span class="ns-badge">📖 {lesson_met['completed_curated_count']}/{lesson_met['total_curated']} Curated Lessons</span>
        <span class="ns-badge">🎯 {avg_score_text} Avg Quiz Score</span>
        <span class="ns-badge">⭐ {fav_met['total_favourites']} Saved Favourites</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 1. SUMMARY CARDS ──────────────────────────────────────────────────────
    st.markdown('<div class="ns-section-label">Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="ns-section-title">Key Learning Metrics</div>', unsafe_allow_html=True)

    # Row 1 of metrics
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)

    with col_m1:
        st.markdown(f"""
        <div class="ns-stat-card">
          <div class="ns-stat-label">Curated Lessons</div>
          <div class="ns-stat-value">{lesson_met['completed_curated_count']} <span style="font-size:1.1rem;font-weight:400;color:var(--text-muted);">/ {lesson_met['total_curated']}</span></div>
          <div class="ns-stat-sub">{lesson_met['remaining_curated_count']} remaining to finish</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m2:
        st.markdown(f"""
        <div class="ns-stat-card">
          <div class="ns-stat-label">Curriculum Progress</div>
          <div class="ns-stat-value">{lesson_met['completion_percentage']}%</div>
          <div class="ns-stat-sub">{lesson_met['completed_curated_count']} distinct completed</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m3:
        quiz_att_display = str(quiz_met["total_attempts"])
        st.markdown(f"""
        <div class="ns-stat-card">
          <div class="ns-stat-label">Total Quizzes</div>
          <div class="ns-stat-value">{quiz_att_display}</div>
          <div class="ns-stat-sub">{'Recorded attempts' if quiz_met['has_attempts'] else 'No attempts recorded'}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m4:
        avg_disp = f"{quiz_met['average_score_pct']}%" if quiz_met["has_attempts"] else "—"
        best_sub = f"Best: {quiz_met['best_score_pct']}%" if quiz_met["has_attempts"] else "Take a quiz to start"
        st.markdown(f"""
        <div class="ns-stat-card">
          <div class="ns-stat-label">Average Quiz Score</div>
          <div class="ns-stat-value">{avg_disp}</div>
          <div class="ns-stat-sub">{best_sub}</div>
        </div>
        """, unsafe_allow_html=True)

    # Row 2 of metrics
    col_m5, col_m6, col_m7, col_m8 = st.columns(4)

    with col_m5:
        best_disp = f"{quiz_met['best_score_pct']}%" if quiz_met["has_attempts"] else "—"
        st.markdown(f"""
        <div class="ns-stat-card">
          <div class="ns-stat-label">Best Quiz Score</div>
          <div class="ns-stat-value">{best_disp}</div>
          <div class="ns-stat-sub">{'Peak accuracy' if quiz_met['has_attempts'] else 'No attempts yet'}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m6:
        st.markdown(f"""
        <div class="ns-stat-card">
          <div class="ns-stat-label">Saved Favourites</div>
          <div class="ns-stat-value">{fav_met['total_favourites']}</div>
          <div class="ns-stat-sub">Across {len(fav_met['topic_counts'])} topic(s)</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m7:
        if fav_met["has_session_revision"]:
            rev_val = f"{fav_met['session_known_count']} <span style='font-size:1rem;color:var(--text-muted);'>known</span>"
            rev_sub = f"{fav_met['session_again_count']} need practice"
        else:
            rev_val = "0"
            rev_sub = "No revisions this session"
        st.markdown(f"""
        <div class="ns-stat-card">
          <div class="ns-stat-label">Session Revision</div>
          <div class="ns-stat-value">{rev_val}</div>
          <div class="ns-stat-sub">{rev_sub}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m8:
        st.markdown(f"""
        <div class="ns-stat-card">
          <div class="ns-stat-label">Revision Persistence</div>
          <div class="ns-stat-value" style="font-size:1.35rem;padding-top:.35rem;">Session-Only</div>
          <div class="ns-stat-sub">Phrases persist, scores reset</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # ── 2. PERSONALIZED RECOMMENDATIONS ───────────────────────────────────────
    st.markdown('<div class="ns-section-label">Next Steps</div>', unsafe_allow_html=True)
    st.markdown('<div class="ns-section-title">Recommended Actions</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ns-section-sub">Transparent, rule-based suggestions generated directly from your saved progress.</div>',
        unsafe_allow_html=True,
    )

    rec_cols = st.columns(len(recs))
    for idx, (col, r) in enumerate(zip(rec_cols, recs)):
        with col:
            st.markdown(f"""
            <div class="ns-rec-card">
              <div>
                <span class="ns-rec-badge">{r['icon']} {r['category']}</span>
                <div class="ns-rec-title">{r['title']}</div>
                <div class="ns-rec-desc">{r['reason']}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(r["action_label"], key=f"rec_btn_{idx}_{r['id']}"):
                set_page_navigation(r["nav_page"], **r.get("nav_kwargs", {}))
                st.rerun()

    st.markdown("---")

    # ── 3. QUIZ PERFORMANCE & TOPIC MASTERY ───────────────────────────────────
    st.markdown('<div class="ns-section-label">Knowledge Checks</div>', unsafe_allow_html=True)
    st.markdown('<div class="ns-section-title">Interactive Quiz Performance</div>', unsafe_allow_html=True)

    if not quiz_met["has_attempts"]:
        st.markdown("""
        <div class="ns-card" style="text-align:center;padding:2.5rem 1.5rem;">
          <div style="font-size:2.8rem;margin-bottom:.6rem;">🎯</div>
          <div style="font-size:1.15rem;font-weight:700;color:var(--text-main);">No quiz attempts recorded yet</div>
          <div style="font-size:.88rem;color:var(--text-muted);margin:.4rem auto 1.2rem;max-width:480px;line-height:1.6;">
            Quizzes test your memory of common phrases across everyday situations like Shopping, Transport, and Restaurants.
          </div>
        </div>
        """, unsafe_allow_html=True)
        col_qc1, col_qc2, col_qc3 = st.columns([1, 1, 1])
        with col_qc2:
            if st.button("🎲 Take a Quiz Now", key="dash_first_quiz_btn"):
                set_page_navigation("Interactive Quizzes", quiz_questions=[], quiz_submitted=False)
                st.rerun()
    else:
        col_q_left, col_q_right = st.columns([1, 1])

        with col_q_left:
            st.markdown('<div class="ns-section-sub" style="font-weight:700;color:var(--green-deep);">Topic Performance Analysis</div>', unsafe_allow_html=True)

            # Best-performing topics
            if quiz_met["best_topics"]:
                st.markdown('<div style="font-size:.82rem;font-weight:700;color:var(--green-primary);margin-bottom:.3rem;">🌟 Strong Topics (Accuracy ≥ 80%)</div>', unsafe_allow_html=True)
                for bt in quiz_met["best_topics"]:
                    st.markdown(
                        f'<div class="ns-list-row">'
                        f'<div><strong>{bt["topic"]}</strong> &nbsp;·&nbsp; <span style="font-size:.8rem;color:var(--text-muted);">{bt["attempts"]} attempt(s)</span></div>'
                        f'<div style="font-weight:700;color:#176B55;">{bt["avg_pct"]}% avg</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            # Topics needing improvement
            st.markdown("<div style='margin-top:.8rem;'></div>", unsafe_allow_html=True)
            if quiz_met["needs_improvement_topics"]:
                st.markdown(
                    '<div style="font-size:.82rem;font-weight:700;color:#B45309;margin-bottom:.3rem;">'
                    '⚠️ Topics Needing Review (Accuracy &lt; 70%)</div>',
                    unsafe_allow_html=True,
                )
                for wt in quiz_met["needs_improvement_topics"]:
                    st.markdown(
                        f'<div class="ns-list-row" style="border-left:3px solid #F59E0B;">'
                        f'<div><strong>{wt["topic"]}</strong> &nbsp;·&nbsp; <span style="font-size:.8rem;color:var(--text-muted);">{wt["attempts"]} attempt(s)</span></div>'
                        f'<div style="font-weight:700;color:#912018;">{wt["avg_pct"]}% avg</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    '<div class="ns-note-box" style="margin:.6rem 0;">'
                    '✅ <strong>Solid Mastery!</strong> All tested quiz topics currently score at or above 70% accuracy.'
                    '</div>',
                    unsafe_allow_html=True,
                )

            # Visual Chart of recent quiz scores
            st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
            st.markdown('<div style="font-size:.82rem;font-weight:700;color:var(--text-main);margin-bottom:.4rem;">📈 Recent Scores by Attempt</div>', unsafe_allow_html=True)
            recent_for_chart = list(reversed(quiz_met["recent_attempts"]))
            chart_data = pd.DataFrame({
                "Attempt": [f"#{a['id']} {a['topic'][:12]}" for a in recent_for_chart],
                "Score (%)": [a["percentage"] for a in recent_for_chart],
            })
            st.bar_chart(chart_data.set_index("Attempt"), color="#176B55", height=200)

        with col_q_right:
            st.markdown(
                '<div class="ns-section-sub" style="font-weight:700;color:var(--green-deep);">'
                f'Recent Quiz Attempts ({len(quiz_met["recent_attempts"])})</div>',
                unsafe_allow_html=True,
            )
            for att in quiz_met["recent_attempts"][:6]:
                score_color = "#176B55" if att["percentage"] >= 70.0 else "#912018"
                st.markdown(
                    f'<div class="ns-list-row">'
                    f'<div>'
                    f'<div style="font-weight:700;color:var(--text-main);">{att["topic"]}</div>'
                    f'<div style="font-size:.78rem;color:var(--text-muted);">🕒 {att["timestamp"]}</div>'
                    f'</div>'
                    f'<div style="text-align:right;">'
                    f'<div style="font-weight:700;color:{score_color};font-size:1.05rem;">{att["score"]} / {att["total"]}</div>'
                    f'<div style="font-size:.8rem;color:{score_color};font-weight:600;">{att["percentage"]}%</div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='margin-top:.8rem;'></div>", unsafe_allow_html=True)
            if st.button("🎲 Practice Another Quiz", key="dash_practice_quiz_btn"):
                set_page_navigation("Interactive Quizzes", quiz_questions=[], quiz_submitted=False)
                st.rerun()

    st.markdown("---")

    # ── 4. CURATED LESSON PROGRESS ────────────────────────────────────────────
    st.markdown('<div class="ns-section-label">Curriculum Tracking</div>', unsafe_allow_html=True)
    st.markdown('<div class="ns-section-title">Daily Kannada Lessons</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="ns-section-sub">Completed <strong>{lesson_met["completed_curated_count"]}</strong> of '
        f'<strong>{lesson_met["total_curated"]}</strong> curated foundational lessons '
        f'({lesson_met["completion_percentage"]}%).</div>',
        unsafe_allow_html=True,
    )

    # Progress bar
    prog_val = (
        lesson_met["completed_curated_count"] / lesson_met["total_curated"]
        if lesson_met["total_curated"] > 0
        else 0.0
    )
    st.progress(prog_val)

    col_ls_done, col_ls_rem = st.columns(2)

    with col_ls_done:
        st.markdown(
            f'<div style="font-size:.85rem;font-weight:700;color:#176B55;margin:.8rem 0 .4rem;">'
            f'✅ Completed Lessons ({lesson_met["completed_curated_count"]})</div>',
            unsafe_allow_html=True,
        )
        if not lesson_met["completed_curated_list"]:
            st.markdown(
                '<div class="ns-card" style="padding:1rem;color:var(--text-muted);font-size:.85rem;text-align:center;">'
                'No lessons marked completed yet. Open Daily Lessons below to begin!</div>',
                unsafe_allow_html=True,
            )
        else:
            for l in lesson_met["completed_curated_list"]:
                date_str = f" · Completed: {l['completed_at']}" if l.get("completed_at") else ""
                st.markdown(
                    f'<div class="ns-list-row" style="border-left:3px solid #176B55;">'
                    f'<div>'
                    f'<strong>{l["title"]}</strong><br>'
                    f'<span style="font-size:.78rem;color:var(--text-muted);">🏷️ {l["topic"]} &nbsp;·&nbsp; {l["difficulty"]}{date_str}</span>'
                    f'</div>'
                    f'<span class="ns-badge" style="background:#E8F4ED;color:#176B55 !important;font-weight:700;">Completed</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    with col_ls_rem:
        st.markdown(
            f'<div style="font-size:.85rem;font-weight:700;color:var(--text-muted);margin:.8rem 0 .4rem;">'
            f'⏳ Remaining Curated Lessons ({lesson_met["remaining_curated_count"]})</div>',
            unsafe_allow_html=True,
        )
        if not lesson_met["remaining_curated_list"]:
            st.markdown(
                '<div class="ns-card" style="padding:1rem;color:#176B55;font-size:.85rem;text-align:center;">'
                '🎉 All curated lessons have been completed!</div>',
                unsafe_allow_html=True,
            )
        else:
            for l in lesson_met["remaining_curated_list"]:
                col_rem_info, col_rem_btn = st.columns([3, 1])
                with col_rem_info:
                    st.markdown(
                        f'<div style="padding:.5rem 0;">'
                        f'<strong>{l["title"]}</strong><br>'
                        f'<span style="font-size:.78rem;color:var(--text-muted);">🏷️ {l["topic"]} &nbsp;·&nbsp; {l["difficulty"]} ({l["phrase_count"]} phrases)</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with col_rem_btn:
                    if st.button("Open", key=f"dash_open_lesson_{l['id']}"):
                        set_page_navigation("Daily Lessons", lesson_view=l["id"])
                        st.rerun()

    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    if st.button("📖 Go to Daily Lessons Curriculum", key="dash_nav_daily_lessons"):
        set_page_navigation("Daily Lessons", lesson_view="index")
        st.rerun()

    st.markdown("---")

    # ── 5. FAVOURITES & REVISION MODE ─────────────────────────────────────────
    st.markdown('<div class="ns-section-label">Vocabulary Retention</div>', unsafe_allow_html=True)
    st.markdown('<div class="ns-section-title">Saved Favourites & Revision</div>', unsafe_allow_html=True)

    col_fav_left, col_fav_right = st.columns([1, 1])

    with col_fav_left:
        st.markdown(
            f'<div class="ns-section-sub" style="font-weight:700;color:var(--green-deep);">'
            f'Saved Favourites ({fav_met["total_favourites"]})</div>',
            unsafe_allow_html=True,
        )

        if fav_met["total_favourites"] == 0:
            st.markdown(
                '<div class="ns-card" style="padding:1.2rem;text-align:center;color:var(--text-muted);font-size:.85rem;">'
                'You have not saved any favourite phrases yet.<br>'
                'Save phrases from lessons or the phrasebook to build your personal flashcard deck.'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            # Topic badges
            st.markdown('<div style="font-size:.8rem;font-weight:700;color:var(--text-muted);margin-bottom:.4rem;">Breakdown by Topic:</div>', unsafe_allow_html=True)
            pills_html = " ".join([
                f'<span class="ns-pill" style="font-size:.78rem;margin:0 .25rem .25rem 0;">{t} ({cnt})</span>'
                for t, cnt in sorted(fav_met["topic_counts"].items(), key=lambda x: x[1], reverse=True)
            ])
            st.markdown(f'<div style="margin-bottom:1rem;">{pills_html}</div>', unsafe_allow_html=True)

            # Recent favourites list
            st.markdown('<div style="font-size:.8rem;font-weight:700;color:var(--text-muted);margin-bottom:.4rem;">Recently Saved Phrases:</div>', unsafe_allow_html=True)
            for rf in fav_met["recent_favourites"]:
                m_txt = rf["meaning_ta"] if language == "Tamil" and rf["meaning_ta"] else rf["meaning_en"]
                st.markdown(
                    f'<div class="ns-list-row">'
                    f'<div>'
                    f'<div class="ns-kn" style="font-size:1.15rem;margin-bottom:0;">{rf["kn"]}</div>'
                    f'<div class="ns-roman" style="font-size:.8rem;">📣 {rf["roman"]} &nbsp;·&nbsp; {m_txt}</div>'
                    f'</div>'
                    f'<span class="ns-pill" style="font-size:.72rem;">{rf["topic"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    with col_fav_right:
        st.markdown(
            '<div class="ns-section-sub" style="font-weight:700;color:var(--green-deep);">'
            'Revision Mode Activity</div>',
            unsafe_allow_html=True,
        )

        # Clear transparency regarding persistence
        st.markdown(f"""
        <div class="ns-note-box">
          <strong>ℹ️ Data Persistence Notice:</strong><br>
          {fav_met['revision_persistence_note']}<br>
          Your saved favourite phrases are permanently preserved in <code>lesson_progress.db</code>, so you can practice them whenever you open the app.
        </div>
        """, unsafe_allow_html=True)

        if fav_met["has_session_revision"]:
            st.markdown(f"""
            <div class="ns-card" style="padding:1.1rem;margin-top:.8rem;">
              <div style="font-size:.85rem;font-weight:700;color:var(--green-deep);margin-bottom:.4rem;">Current Active Session:</div>
              <div style="display:flex;gap:.8rem;align-items:center;">
                <span class="ns-pill" style="background:#E8F4ED;color:#176B55;font-weight:700;">
                  ✅ {fav_met['session_known_count']} Marked Known
                </span>
                <span class="ns-pill" style="background:#FEF3F2;color:#912018;font-weight:700;">
                  🔁 {fav_met['session_again_count']} To Revise Again
                </span>
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="font-size:.85rem;color:var(--text-muted);margin:1rem 0;">'
                'No flashcards reviewed in the current session. Launch Revision Mode to practice your saved phrases.'
                '</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:1.2rem;'></div>", unsafe_allow_html=True)
        col_fb1, col_fb2 = st.columns(2)
        with col_fb1:
            if st.button("⭐ View Favourites", key="dash_view_favs"):
                set_page_navigation("My Favourites", rev_active=False)
                st.rerun()
        with col_fb2:
            if st.button("🧠 Start Revision Mode", key="dash_start_rev"):
                set_page_navigation(
                    "My Favourites",
                    rev_active=True,
                    rev_index=0,
                    rev_revealed=False,
                    rev_known=set(),
                    rev_again=set(),
                )
                st.rerun()
