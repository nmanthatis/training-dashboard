import re
import json
import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
import requests

# ============================================================
# Nikos Training Dashboard — AI-Powered Coach
# ============================================================

st.set_page_config(
    page_title="Training Dashboard",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Space Mono', monospace !important; }
.stTabs [data-baseweb="tab"] {
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.metric-card {
    background: #0f1117;
    border: 1px solid #1e2a3a;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 8px;
}
.alert-box  { border-left:3px solid #ff4b4b; background:rgba(255,75,75,.08);  padding:12px 16px; border-radius:4px; margin:8px 0; font-size:.9rem; }
.ok-box     { border-left:3px solid #21c55d; background:rgba(33,197,93,.08);  padding:12px 16px; border-radius:4px; margin:8px 0; font-size:.9rem; }
.warn-box   { border-left:3px solid #f59e0b; background:rgba(245,158,11,.08); padding:12px 16px; border-radius:4px; margin:8px 0; font-size:.9rem; }
.ai-response { background:#0f1117; border:1px solid #1e3a5f; border-radius:8px; padding:24px; line-height:1.7; font-size:.95rem; }
.garmin-ok   { color:#21c55d; font-size:.8rem; font-family:'Space Mono',monospace; }
.garmin-err  { color:#ff4b4b; font-size:.8rem; font-family:'Space Mono',monospace; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────
DEFAULT_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSFkE9lirf4G5VLj2nlwvN-p8yE-V5wrcqZjJbarKschaBpNiD3xXKxlk2YL77hIn6O2Zbaqh36bQId/pub?output=csv"

ATHLETE_PROFILE = """
Athlete: Nikos, 30yo, Austin TX.
Goals: Olympic Triathlon June 20 2026 (immediate). Javelina Jundred 100-miler fall 2027 (long-term).
Gym split (4x/week): Chest Mon | Shoulders Tue | Back Wed or Thu 5pm | Legs Fri. 3 exercises x 3 sets.
Exercises — Back: machine row, weighted pull-ups, cable straight arm pulldown.
Shoulders: dumbbell press, cable lateral raises, cable rear delts.
Chest: dumbbell flat press, pec fly machine, incline dumbbell press.
Legs: deadlifts, calf raises, abductor machine, leg extension, leg curl.
Endurance: swim (weakest — priority in tri build), bike (strong, Cannondale SuperSix Evo), run.
Schedule: Mon/Tue/Fri mornings 6-8:30am free. Wed every other week. Thu 5pm backup.
Session order: cardio then gym. Exception: swim days = gym first, then pool.
Key limiter: soft tissue (tendons/fascia). NEVER ramp run volume >10%/week.
Behavioral pattern: skips inconvenient workouts, overconfident about preparation.
"""

GARMIN_SPORT_MAP = {
    "running": "Run", "trail_running": "Run", "treadmill_running": "Run",
    "cycling": "Bike", "road_cycling": "Bike", "indoor_cycling": "Bike", "virtual_ride": "Bike",
    "swimming": "Swim", "open_water_swimming": "Swim", "lap_swimming": "Swim", "pool_swimming": "Swim",
    "strength_training": "Strength", "cardio": "Cardio", "triathlon": "Triathlon",
}

# ── Garmin connection ─────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_garmin_activities(email: str, password: str, weeks: int) -> pd.DataFrame:
    """Fetch recent activities from Garmin Connect. Cached 30 min."""
    try:
        from garminconnect import Garmin
        client = Garmin(email=email, password=password)
        client.login()

        start_date = (datetime.date.today() - datetime.timedelta(weeks=weeks)).strftime("%Y-%m-%d")
        end_date = datetime.date.today().strftime("%Y-%m-%d")
        activities = client.get_activities_by_date(start_date, end_date)

        rows = []
        for act in activities:
            date = pd.to_datetime(act.get("startTimeLocal", act.get("startTimeGMT")), errors="coerce")
            activity_type = str(act.get("activityType", {}).get("typeKey", "other")).lower()
            sport = next((v for k, v in GARMIN_SPORT_MAP.items() if k in activity_type), "Other")

            distance_m = act.get("distance", 0) or 0
            duration_s = act.get("duration", 0) or 0
            avg_hr = act.get("averageHR")
            calories = act.get("calories")
            name = act.get("activityName", "")

            rows.append({
                "date": date,
                "sport": sport,
                "activity_raw": activity_type,
                "name": name,
                "distance_km": round(distance_m / 1000, 2),
                "duration_min": round(duration_s / 60, 1),
                "avg_hr": avg_hr,
                "calories": calories,
            })

        return pd.DataFrame(rows)

    except Exception as e:
        raise RuntimeError(str(e))

def get_garmin_credentials():
    """Read Garmin credentials from Streamlit secrets."""
    try:
        email = st.secrets.get("GARMIN_EMAIL", "")
        password = st.secrets.get("GARMIN_PASSWORD", "")
        return email, password
    except Exception:
        return "", ""

# ── Gym data helpers ──────────────────────────────────────────
def get_sheet_url():
    try:
        url = st.secrets.get("SHEET_CSV_URL", "")
    except Exception:
        url = ""
    return str(url).strip() or DEFAULT_SHEET_CSV_URL

@st.cache_data(ttl=600, show_spinner=False)
def load_from_url(url):
    return pd.read_csv(url)

def normalize_columns(raw_df):
    df = raw_df.copy()
    clean_cols = []
    counter = 1
    for col in df.columns:
        name = str(col).strip()
        if name == "" or name.lower().startswith("unnamed"):
            name = f"_blank_{counter}"
            counter += 1
        name = re.sub(r"\s+", " ", name)
        clean_cols.append(name)
    df.columns = clean_cols
    return df

def find_column(df, candidates):
    lower_map = {c.lower().strip(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower().strip() in lower_map:
            return lower_map[candidate.lower().strip()]
    return None

def extract_set_columns(df):
    columns = list(df.columns)
    set_columns = []
    for idx, col in enumerate(columns):
        match = re.fullmatch(r"w\s*\.?\s*(\d+)", str(col).strip().lower())
        if not match:
            continue
        set_number = int(match.group(1))
        reps_col = None
        for next_col in columns[idx + 1:]:
            next_clean = str(next_col).strip().lower()
            if re.fullmatch(r"w\s*\.?\s*\d+", next_clean):
                break
            if next_clean in {"reps", "rep", "r", f"r{set_number}", f"r {set_number}"}:
                reps_col = next_col
                break
        set_columns.append((set_number, col, reps_col))
    return sorted(set_columns, key=lambda x: x[0])

def parse_exercise_group(exercise):
    exercise = str(exercise).strip()
    if ":" in exercise:
        group, name = exercise.split(":", 1)
        return group.strip(), name.strip()
    ex_lower = exercise.lower()
    if any(x in ex_lower for x in ["press", "fly", "pec", "incline", "chest"]):
        return "Chest", exercise
    if any(x in ex_lower for x in ["lateral", "shoulder", "delt", "overhead"]):
        return "Shoulders", exercise
    if any(x in ex_lower for x in ["row", "pull", "pulldown", "pullup", "back", "lat", "straight arm"]):
        return "Back", exercise
    if any(x in ex_lower for x in ["squat", "deadlift", "lunge", "calf", "leg", "abductor", "extension", "curl"]):
        return "Legs", exercise
    return "Other", exercise

def clean_and_reshape(raw_df):
    df = normalize_columns(raw_df)
    date_col = find_column(df, ["Date"])
    exercise_col = find_column(df, ["Exercise", "Workout", "Movement"])
    comments_col = find_column(df, ["Comments", "Comment", "Notes"])
    body_weight_col = find_column(df, ["Weight", "BodyWeight", "Body Weight", "BW"])

    if date_col is None or exercise_col is None:
        st.error("Could not find required columns. Need at least `Date` and `Exercise`.")
        st.stop()

    set_columns = extract_set_columns(df)
    if not set_columns:
        st.error("Could not find set columns like `W 1`, `W 2`, etc.")
        st.stop()

    rows = []
    for _, row in df.iterrows():
        date = pd.to_datetime(row.get(date_col), errors="coerce")
        exercise = row.get(exercise_col)
        if pd.isna(date) or pd.isna(exercise) or str(exercise).strip() == "":
            continue
        group, exercise_name = parse_exercise_group(exercise)
        comment = row.get(comments_col, "") if comments_col else ""
        body_weight = pd.to_numeric(row.get(body_weight_col), errors="coerce") if body_weight_col else pd.NA

        for set_number, weight_col, reps_col in set_columns:
            weight = pd.to_numeric(row.get(weight_col), errors="coerce")
            reps = pd.to_numeric(row.get(reps_col), errors="coerce") if reps_col else pd.NA
            if pd.isna(weight) and pd.isna(reps):
                continue
            rows.append({
                "date": date, "exercise": str(exercise).strip(),
                "group": group, "exercise_name": exercise_name,
                "set_number": set_number, "weight": weight, "reps": reps,
                "comments": comment, "body_weight": body_weight,
            })

    long_df = pd.DataFrame(rows)
    if long_df.empty:
        return df, long_df
    long_df["weight"] = pd.to_numeric(long_df["weight"], errors="coerce")
    long_df["reps"] = pd.to_numeric(long_df["reps"], errors="coerce")
    long_df["volume"] = long_df["weight"] * long_df["reps"]
    long_df["estimated_1rm"] = long_df["weight"] * (1 + long_df["reps"] / 30)
    return df, long_df

# ── Analysis helpers ──────────────────────────────────────────
def get_recent(df, n_weeks):
    cutoff = pd.Timestamp.now() - pd.Timedelta(weeks=n_weeks)
    return df[df["date"] >= cutoff]

def build_gym_summary(df, n_weeks):
    recent = get_recent(df, n_weeks)
    if recent.empty:
        return {}
    summary = {}
    for group in ["Chest", "Shoulders", "Back", "Legs"]:
        gdf = recent[recent["group"] == group]
        sessions = gdf["date"].dt.date.nunique()
        spw = sessions / max(n_weeks, 1)
        summary[group] = {
            "sessions": sessions,
            "sets": len(gdf),
            "volume": round(gdf["volume"].sum(skipna=True), 0),
            "sessions_per_week": round(spw, 2),
            "compliance_pct": round(min(spw, 1.0) * 100),
        }
    return summary

def build_endurance_summary(garmin_df, n_weeks):
    recent = get_recent(garmin_df, n_weeks)
    if recent.empty:
        return {}
    expected = {"Swim": 2.0, "Bike": 2.0, "Run": 3.0}
    summary = {}
    for sport, exp in expected.items():
        sdf = recent[recent["sport"] == sport]
        sessions = len(sdf)
        spw = sessions / max(n_weeks, 1)
        summary[sport] = {
            "sessions": sessions,
            "total_km": round(sdf["distance_km"].sum(skipna=True), 1),
            "total_min": round(sdf["duration_min"].sum(skipna=True), 0),
            "sessions_per_week": round(spw, 2),
            "expected_per_week": exp,
            "compliance_pct": round(min(spw / exp, 1.0) * 100),
        }
    return summary

# ── Claude API ────────────────────────────────────────────────
def call_claude(prompt):
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        data = resp.json()
        if "content" in data:
            return data["content"][0]["text"]
        return f"API error: {data.get('error', {}).get('message', str(data))}"
    except Exception as e:
        return f"Error: {e}"

def build_coach_prompt(gym_summary, end_summary, n_weeks):
    return f"""You are a coaching AI for the following athlete:

{ATHLETE_PROFILE}

Training data from the last {n_weeks} weeks:

GYM (strength) by muscle group:
{json.dumps(gym_summary, indent=2) if gym_summary else "No gym data."}

ENDURANCE (swim/bike/run):
{json.dumps(end_summary, indent=2) if end_summary else "No endurance data."}

Respond in two sections:
1. ANALYSIS (3-5 bullets): gaps, imbalances, overtraining flags, anything concerning given goals and limiters.
2. NEXT WEEK PLAN: concrete day-by-day plan correcting the gaps. Use their exact schedule and exercise names. Flag any run volume increase >10% as a soft tissue risk.

Be direct, specific, no fluff."""

# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════
st.sidebar.markdown("## 🏃 Training Dashboard")
st.sidebar.markdown("---")
analysis_weeks = st.sidebar.slider("Analysis window (weeks)", 2, 8, 4)

# Garmin status
st.sidebar.markdown("**Garmin Connect**")
garmin_email, garmin_password = get_garmin_credentials()

garmin_df = None
if garmin_email and garmin_password:
    with st.sidebar:
        with st.spinner("Fetching Garmin..."):
            try:
                garmin_df = fetch_garmin_activities(garmin_email, garmin_password, analysis_weeks + 1)
                activity_count = len(garmin_df) if garmin_df is not None else 0
                st.markdown(f'<p class="garmin-ok">✓ Connected — {activity_count} activities loaded</p>', unsafe_allow_html=True)
            except Exception as e:
                err = str(e)
                st.markdown(f'<p class="garmin-err">✗ {err[:80]}</p>', unsafe_allow_html=True)
                garmin_df = None
    if st.sidebar.button("🔄 Refresh Garmin data"):
        st.cache_data.clear()
        st.rerun()
else:
    st.sidebar.markdown(
        '<p class="garmin-err">No credentials found.<br>Add GARMIN_EMAIL and GARMIN_PASSWORD to Streamlit secrets.</p>',
        unsafe_allow_html=True,
    )

st.sidebar.markdown("---")
st.sidebar.markdown("**Gym Data (Google Sheets)**")
gym_uploaded = st.sidebar.file_uploader("Override: upload CSV manually", type=["csv"], key="gym")

# ═══════════════════════════════════════════════════════════════
# LOAD GYM DATA
# ═══════════════════════════════════════════════════════════════
raw_gym_df = None
if gym_uploaded:
    raw_gym_df = pd.read_csv(gym_uploaded)
else:
    try:
        raw_gym_df = load_from_url(get_sheet_url())
    except Exception as e:
        st.sidebar.warning(f"Sheets error: {e}")

gym_df = None
if raw_gym_df is not None:
    _, gym_df = clean_and_reshape(raw_gym_df)

# ═══════════════════════════════════════════════════════════════
# MAIN UI
# ═══════════════════════════════════════════════════════════════
st.title("Training Dashboard")

if gym_df is None and garmin_df is None:
    st.info("Gym data loads automatically from Google Sheets. Add GARMIN_EMAIL + GARMIN_PASSWORD to Streamlit secrets for automatic Garmin sync.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["📊  Overview", "💪  Gym Analysis", "🤖  AI Coach"])

# ── TAB 1: OVERVIEW ───────────────────────────────────────────
with tab1:
    col_gym, col_end = st.columns(2)

    with col_gym:
        st.subheader("Gym")
        if gym_df is not None and not gym_df.empty:
            for group, stats in build_gym_summary(gym_df, analysis_weeks).items():
                pct = stats["compliance_pct"]
                icon = "🟢" if pct >= 80 else ("🟡" if pct >= 50 else "🔴")
                st.markdown(
                    f'<div class="metric-card"><strong>{icon} {group}</strong><br>'
                    f'{stats["sessions"]} sessions &nbsp;·&nbsp; {stats["sets"]} sets &nbsp;·&nbsp; '
                    f'{stats["sessions_per_week"]}x/wk &nbsp;·&nbsp; <strong>{pct}% compliance</strong></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No gym data.")

    with col_end:
        st.subheader("Endurance")
        if garmin_df is not None and not garmin_df.empty:
            for sport, stats in build_endurance_summary(garmin_df, analysis_weeks).items():
                pct = stats["compliance_pct"]
                icon = "🟢" if pct >= 80 else ("🟡" if pct >= 50 else "🔴")
                st.markdown(
                    f'<div class="metric-card"><strong>{icon} {sport}</strong><br>'
                    f'{stats["sessions"]} sessions &nbsp;·&nbsp; {stats["total_km"]} km &nbsp;·&nbsp; '
                    f'{stats["sessions_per_week"]}x/wk &nbsp;·&nbsp; <strong>{pct}% compliance</strong></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("Connect Garmin to see endurance data.")

    if garmin_df is not None and not garmin_df.empty:
        st.subheader(f"Endurance — Weekly Sessions (last {analysis_weeks} weeks)")
        end_weekly = (
            get_recent(garmin_df, analysis_weeks)
            .assign(week=lambda d: d["date"].dt.to_period("W").dt.start_time)
            .groupby(["week", "sport"]).size().reset_index(name="sessions")
        )
        fig = px.bar(
            end_weekly, x="week", y="sessions", color="sport",
            color_discrete_map={"Swim": "#3b82f6", "Bike": "#f59e0b", "Run": "#21c55d", "Other": "#6b7280"},
        )
        st.plotly_chart(fig, use_container_width=True)

# ── TAB 2: GYM ANALYSIS ───────────────────────────────────────
with tab2:
    if gym_df is None or gym_df.empty:
        st.info("No gym data loaded.")
    else:
        recent_gym = get_recent(gym_df, analysis_weeks)

        st.subheader("Volume by Muscle Group")
        group_vol = (
            recent_gym.groupby(["date", "group"])
            .agg(volume=("volume", "sum")).reset_index()
        )
        fig = px.bar(
            group_vol, x="date", y="volume", color="group",
            color_discrete_map={"Chest": "#ef4444", "Shoulders": "#f97316", "Back": "#3b82f6", "Legs": "#21c55d", "Other": "#6b7280"},
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Session Compliance")
        expected_days = {"Chest": "Monday", "Shoulders": "Tuesday", "Back": "Wed/Thu", "Legs": "Friday"}
        for group, stats in build_gym_summary(gym_df, analysis_weeks).items():
            pct = stats["compliance_pct"]
            spw = stats["sessions_per_week"]
            day = expected_days.get(group, "")
            if pct < 50:
                st.markdown(f'<div class="alert-box">🔴 <strong>{group}</strong> — {spw}x/wk ({day}). Significantly undertrained.</div>', unsafe_allow_html=True)
            elif pct < 80:
                st.markdown(f'<div class="warn-box">🟡 <strong>{group}</strong> — {spw}x/wk ({day}). Some sessions missed.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="ok-box">🟢 <strong>{group}</strong> — {spw}x/wk. On track.</div>', unsafe_allow_html=True)

        st.subheader("Exercise Progress")
        all_exercises = sorted(recent_gym["exercise"].dropna().unique())
        if all_exercises:
            selected = st.selectbox("Exercise", all_exercises)
            ex_df = recent_gym[recent_gym["exercise"] == selected]
            best = (
                ex_df.groupby("date", as_index=False)
                .agg(best_weight=("weight", "max"), est_1rm=("estimated_1rm", "max"))
                .sort_values("date")
            )
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(px.line(best, x="date", y="best_weight", markers=True, title="Best Weight"), use_container_width=True)
            with c2:
                st.plotly_chart(px.line(best, x="date", y="est_1rm", markers=True, title="Estimated 1RM"), use_container_width=True)

# ── TAB 3: AI COACH ───────────────────────────────────────────
with tab3:
    st.subheader("AI Coach")
    st.caption("Reads your actual training data and generates a gap analysis + next week plan.")

    gym_summary = build_gym_summary(gym_df, analysis_weeks) if (gym_df is not None and not gym_df.empty) else {}
    end_summary = build_endurance_summary(garmin_df, analysis_weeks) if (garmin_df is not None and not garmin_df.empty) else {}

    if not gym_summary and not end_summary:
        st.warning("Need at least one data source loaded.")
    else:
        with st.expander("Data being sent to AI"):
            if gym_summary:
                st.json(gym_summary)
            if end_summary:
                st.json(end_summary)

        if st.button("🤖 Generate Analysis + Next Week Plan", type="primary"):
            with st.spinner("Analyzing..."):
                result = call_claude(build_coach_prompt(gym_summary, end_summary, analysis_weeks))
            st.markdown(f'<div class="ai-response">{result}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Ask a specific question**")
        custom_q = st.text_area("e.g. 'My knee is sore — modify leg day this week?'", height=80)
        if st.button("Ask", type="secondary") and custom_q.strip():
            ctx = f"Athlete profile:\n{ATHLETE_PROFILE}\n\nRecent gym: {json.dumps(gym_summary)}\nRecent endurance: {json.dumps(end_summary)}\n\nQuestion: {custom_q}"
            with st.spinner("Thinking..."):
                result = call_claude(ctx)
            st.markdown(f'<div class="ai-response">{result}</div>', unsafe_allow_html=True)
