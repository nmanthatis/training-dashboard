import re
import json
import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Training",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}
h1, h2, h3, .mono {
    font-family: 'IBM Plex Mono', monospace !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    text-transform: lowercase;
}
.stTabs [data-baseweb="tab-list"] {
    border-bottom: 0.5px solid rgba(0,0,0,0.12);
    gap: 0;
}

/* ── metric strip ── */
.metric-strip {
    display: flex;
    gap: 0;
    border: 0.5px solid var(--color-border-tertiary);
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 20px;
}
.metric-cell {
    flex: 1;
    padding: 12px 16px;
    border-right: 0.5px solid var(--color-border-tertiary);
}
.metric-cell:last-child { border-right: none; }
.metric-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.12em;
    color: var(--color-text-tertiary);
    margin-bottom: 4px;
    text-transform: lowercase;
}
.metric-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 22px;
    font-weight: 500;
    color: var(--color-text-primary);
    line-height: 1;
}
.metric-sub {
    font-size: 10px;
    color: var(--color-text-secondary);
    margin-top: 3px;
}

/* ── status rows ── */
.status-table { width: 100%; border-collapse: collapse; }
.status-table tr { border-bottom: 0.5px solid var(--color-border-tertiary); }
.status-table tr:last-child { border-bottom: none; }
.status-table td { padding: 8px 0; font-size: 12px; }
.status-table td:first-child {
    font-family: 'IBM Plex Mono', monospace;
    color: var(--color-text-secondary);
    width: 90px;
}
.status-table td:last-child {
    text-align: right;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 500;
}
.s-ok   { color: #22c55e; }
.s-warn { color: #f59e0b; }
.s-bad  { color: #ef4444; }

/* ── plan days ── */
.plan-day {
    border-bottom: 0.5px solid var(--color-border-tertiary);
    padding: 10px 0;
}
.plan-day:last-child { border-bottom: none; }
.plan-dayname {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.12em;
    color: var(--color-text-tertiary);
    margin-bottom: 4px;
}
.plan-content { font-size: 12px; color: var(--color-text-primary); line-height: 1.5; }
.badge {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    font-weight: 500;
    padding: 2px 7px;
    border-radius: 99px;
    margin-right: 4px;
    letter-spacing: 0.06em;
}
.badge-run   { background: #dcfce7; color: #166534; }
.badge-swim  { background: #dbeafe; color: #1e40af; }
.badge-bike  { background: #fef9c3; color: #854d0e; }
.badge-gym   { background: #f3e8ff; color: #6b21a8; }
.badge-brick { background: #ffedd5; color: #9a3412; }
.badge-rest  { background: var(--color-background-secondary); color: var(--color-text-tertiary); }

/* ── flag boxes ── */
.flag { padding: 8px 12px; border-radius: 0; border-left: 2px solid; margin-bottom: 6px; font-size: 12px; line-height: 1.5; }
.flag-ok   { border-color: #22c55e; background: rgba(34,197,94,.06);  color: var(--color-text-primary); }
.flag-warn { border-color: #f59e0b; background: rgba(245,158,11,.06); color: var(--color-text-primary); }
.flag-bad  { border-color: #ef4444; background: rgba(239,68,68,.06);  color: var(--color-text-primary); }

/* ── section header ── */
.section-head {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.14em;
    color: var(--color-text-tertiary);
    text-transform: lowercase;
    border-bottom: 0.5px solid var(--color-border-tertiary);
    padding-bottom: 6px;
    margin: 20px 0 12px;
}

/* ── MOBILE: hide desktop tabs, show stacked layout ── */
@media (max-width: 640px) {
    .desktop-only { display: none !important; }
    .mobile-only  { display: block !important; }
    section[data-testid="stSidebar"] { display: none !important; }
    .stTabs { display: none !important; }
    .block-container { padding: 1rem !important; }
    .metric-strip { flex-direction: column; }
    .metric-cell { border-right: none; border-bottom: 0.5px solid var(--color-border-tertiary); }
    .metric-cell:last-child { border-bottom: none; }
}
@media (min-width: 641px) {
    .mobile-only { display: none !important; }
}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────
DEFAULT_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSFkE9lirf4G5VLj2nlwvN-p8yE-V5wrcqZjJbarKschaBpNiD3xXKxlk2YL77hIn6O2Zbaqh36bQId/pub?output=csv"

GARMIN_SPORT_MAP = {
    "running": "Run", "trail_running": "Run", "treadmill_running": "Run",
    "cycling": "Bike", "road_cycling": "Bike", "indoor_cycling": "Bike", "virtual_ride": "Bike",
    "swimming": "Swim", "open_water_swimming": "Swim", "lap_swimming": "Swim", "pool_swimming": "Swim",
    "strength_training": "Strength", "cardio": "Cardio", "triathlon": "Triathlon",
}

GYM_EXERCISES = {
    "Chest":     ["DB flat press", "pec fly machine", "incline DB press"],
    "Shoulders": ["DB press", "cable lateral raises", "cable rear delts"],
    "Back":      ["machine row", "weighted pull-ups", "cable straight arm pulldown"],
    "Legs":      ["deadlifts", "calf raises", "leg extension"],
}
GYM_DAYS = {
    "Chest": "monday 6am", "Shoulders": "tuesday 6am",
    "Back": "wednesday 6am (or thursday 5pm)", "Legs": "friday 6am",
}
ENDURANCE_TARGETS = {"Swim": 2.0, "Bike": 2.0, "Run": 3.0}
RACE_DATE = datetime.date(2026, 6, 20)

# ── Garmin ────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_garmin_activities(email, password, weeks):
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
        rows.append({
            "date": date, "sport": sport, "activity_raw": activity_type,
            "name": act.get("activityName", ""),
            "distance_km": round((act.get("distance", 0) or 0) / 1000, 2),
            "duration_min": round((act.get("duration", 0) or 0) / 60, 1),
            "avg_hr": act.get("averageHR"), "calories": act.get("calories"),
        })
    return pd.DataFrame(rows)

def get_garmin_creds():
    try:
        return st.secrets.get("GARMIN_EMAIL", ""), st.secrets.get("GARMIN_PASSWORD", "")
    except Exception:
        return "", ""

# ── Gym data ──────────────────────────────────────────────────
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
            name = f"_blank_{counter}"; counter += 1
        name = re.sub(r"\s+", " ", name)
        clean_cols.append(name)
    df.columns = clean_cols
    return df

def find_column(df, candidates):
    lower_map = {c.lower().strip(): c for c in df.columns}
    for c in candidates:
        if c.lower().strip() in lower_map:
            return lower_map[c.lower().strip()]
    return None

def extract_set_columns(df):
    columns = list(df.columns)
    set_columns = []
    for idx, col in enumerate(columns):
        match = re.fullmatch(r"w\s*\.?\s*(\d+)", str(col).strip().lower())
        if not match: continue
        set_number = int(match.group(1))
        reps_col = None
        for next_col in columns[idx + 1:]:
            nc = str(next_col).strip().lower()
            if re.fullmatch(r"w\s*\.?\s*\d+", nc): break
            if nc in {"reps", "rep", "r", f"r{set_number}", f"r {set_number}"}:
                reps_col = next_col; break
        set_columns.append((set_number, col, reps_col))
    return sorted(set_columns, key=lambda x: x[0])

def parse_exercise_group(exercise):
    exercise = str(exercise).strip()
    if ":" in exercise:
        group, name = exercise.split(":", 1)
        return group.strip(), name.strip()
    ex = exercise.lower()
    if any(x in ex for x in ["press", "fly", "pec", "incline", "chest"]): return "Chest", exercise
    if any(x in ex for x in ["lateral", "shoulder", "delt", "overhead"]): return "Shoulders", exercise
    if any(x in ex for x in ["row", "pull", "pulldown", "pullup", "back", "lat", "straight arm"]): return "Back", exercise
    if any(x in ex for x in ["squat", "deadlift", "lunge", "calf", "leg", "abductor", "extension", "curl"]): return "Legs", exercise
    return "Other", exercise

def clean_and_reshape(raw_df):
    df = normalize_columns(raw_df)
    date_col = find_column(df, ["Date"])
    exercise_col = find_column(df, ["Exercise", "Workout", "Movement"])
    comments_col = find_column(df, ["Comments", "Comment", "Notes"])
    bw_col = find_column(df, ["Weight", "BodyWeight", "Body Weight", "BW"])
    if date_col is None or exercise_col is None:
        st.error("Need at least `Date` and `Exercise` columns."); st.stop()
    set_columns = extract_set_columns(df)
    if not set_columns:
        st.error("Need set columns like `W 1`, `W 2`..."); st.stop()
    rows = []
    for _, row in df.iterrows():
        date = pd.to_datetime(row.get(date_col), errors="coerce")
        exercise = row.get(exercise_col)
        if pd.isna(date) or pd.isna(exercise) or str(exercise).strip() == "": continue
        group, exercise_name = parse_exercise_group(exercise)
        comment = row.get(comments_col, "") if comments_col else ""
        bw = pd.to_numeric(row.get(bw_col), errors="coerce") if bw_col else pd.NA
        for set_number, weight_col, reps_col in set_columns:
            weight = pd.to_numeric(row.get(weight_col), errors="coerce")
            reps = pd.to_numeric(row.get(reps_col), errors="coerce") if reps_col else pd.NA
            if pd.isna(weight) and pd.isna(reps): continue
            rows.append({"date": date, "exercise": str(exercise).strip(), "group": group,
                         "exercise_name": exercise_name, "set_number": set_number,
                         "weight": weight, "reps": reps, "comments": comment, "body_weight": bw})
    long_df = pd.DataFrame(rows)
    if long_df.empty: return df, long_df
    long_df["weight"] = pd.to_numeric(long_df["weight"], errors="coerce")
    long_df["reps"] = pd.to_numeric(long_df["reps"], errors="coerce")
    long_df["volume"] = long_df["weight"] * long_df["reps"]
    long_df["estimated_1rm"] = long_df["weight"] * (1 + long_df["reps"] / 30)
    return df, long_df

# ── Analysis ──────────────────────────────────────────────────
def get_recent(df, n_weeks):
    cutoff = pd.Timestamp.now() - pd.Timedelta(weeks=n_weeks)
    return df[df["date"] >= cutoff]

def build_gym_summary(df, n_weeks):
    recent = get_recent(df, n_weeks)
    if recent.empty: return {}
    summary = {}
    for group in ["Chest", "Shoulders", "Back", "Legs"]:
        gdf = recent[recent["group"] == group]
        sessions = gdf["date"].dt.date.nunique()
        spw = sessions / max(n_weeks, 1)
        summary[group] = {
            "sessions": sessions, "sets": len(gdf),
            "volume": round(gdf["volume"].sum(skipna=True), 0),
            "sessions_per_week": round(spw, 2),
            "compliance_pct": round(min(spw, 1.0) * 100),
        }
    return summary

def build_endurance_summary(garmin_df, n_weeks):
    recent = get_recent(garmin_df, n_weeks)
    if recent.empty: return {}
    summary = {}
    for sport, exp in ENDURANCE_TARGETS.items():
        sdf = recent[recent["sport"] == sport]
        sessions = len(sdf)
        spw = sessions / max(n_weeks, 1)
        wow_warning = False
        if sport == "Run" and not sdf.empty:
            sc = sdf.copy()
            sc["week"] = sc["date"].dt.to_period("W")
            wkm = sc.groupby("week")["distance_km"].sum().sort_index()
            if len(wkm) >= 2 and wkm.iloc[-2] > 0:
                if (wkm.iloc[-1] - wkm.iloc[-2]) / wkm.iloc[-2] > 0.10:
                    wow_warning = True
        summary[sport] = {
            "sessions": sessions,
            "total_km": round(sdf["distance_km"].sum(skipna=True), 1),
            "total_min": round(sdf["duration_min"].sum(skipna=True), 0),
            "sessions_per_week": round(spw, 2),
            "expected_per_week": exp,
            "compliance_pct": round(min(spw / exp, 1.0) * 100),
            "soft_tissue_warning": wow_warning,
        }
    return summary

# ── Body map SVG ──────────────────────────────────────────────
def muscle_color(group, gym_summary):
    if group not in gym_summary: return "#e5e5e5"
    pct = gym_summary[group]["compliance_pct"]
    if pct >= 80: return "#22c55e"
    if pct >= 50: return "#f59e0b"
    return "#ef4444"

def body_map_svg(gym_summary, size=180):
    chest  = muscle_color("Chest", gym_summary)
    shldr  = muscle_color("Shoulders", gym_summary)
    back   = muscle_color("Back", gym_summary)
    legs   = muscle_color("Legs", gym_summary)
    scale  = size / 180
    w = int(130 * scale); h = int(210 * scale)
    def s(v): return round(v * scale)
    svg = f"""<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">
  <ellipse cx="{s(65)}" cy="{s(17)}" rx="{s(13)}" ry="{s(14)}" fill="#d1d5db"/>
  <rect x="{s(37)}" y="{s(31)}" width="{s(56)}" height="{s(52)}" rx="{s(5)}" fill="#e5e7eb"/>
  <rect x="{s(39)}" y="{s(34)}" width="{s(52)}" height="{s(16)}" rx="{s(3)}" fill="{chest}" opacity="0.9"/>
  <rect x="{s(40)}" y="{s(43)}" width="{s(11)}" height="{s(14)}" rx="{s(3)}" fill="{shldr}" opacity="0.85"/>
  <rect x="{s(79)}" y="{s(43)}" width="{s(11)}" height="{s(14)}" rx="{s(3)}" fill="{shldr}" opacity="0.85"/>
  <rect x="{s(39)}" y="{s(59)}" width="{s(52)}" height="{s(20)}" rx="{s(3)}" fill="{back}" opacity="0.9"/>
  <rect x="{s(18)}" y="{s(33)}" width="{s(17)}" height="{s(42)}" rx="{s(6)}" fill="#e5e7eb"/>
  <rect x="{s(19)}" y="{s(35)}" width="{s(15)}" height="{s(38)}" rx="{s(5)}" fill="{shldr}" opacity="0.7"/>
  <rect x="{s(95)}" y="{s(33)}" width="{s(17)}" height="{s(42)}" rx="{s(6)}" fill="#e5e7eb"/>
  <rect x="{s(96)}" y="{s(35)}" width="{s(15)}" height="{s(38)}" rx="{s(5)}" fill="{shldr}" opacity="0.7"/>
  <rect x="{s(38)}" y="{s(81)}" width="{s(24)}" height="{s(56)}" rx="{s(6)}" fill="#e5e7eb"/>
  <rect x="{s(39)}" y="{s(82)}" width="{s(22)}" height="{s(54)}" rx="{s(5)}" fill="{legs}" opacity="0.9"/>
  <rect x="{s(68)}" y="{s(81)}" width="{s(24)}" height="{s(56)}" rx="{s(6)}" fill="#e5e7eb"/>
  <rect x="{s(69)}" y="{s(82)}" width="{s(22)}" height="{s(54)}" rx="{s(5)}" fill="{legs}" opacity="0.9"/>
  <rect x="{s(38)}" y="{s(139)}" width="{s(24)}" height="{s(34)}" rx="{s(4)}" fill="#e5e7eb"/>
  <rect x="{s(39)}" y="{s(140)}" width="{s(22)}" height="{s(32)}" rx="{s(3)}" fill="{legs}" opacity="0.7"/>
  <rect x="{s(68)}" y="{s(139)}" width="{s(24)}" height="{s(34)}" rx="{s(4)}" fill="#e5e7eb"/>
  <rect x="{s(69)}" y="{s(140)}" width="{s(22)}" height="{s(32)}" rx="{s(3)}" fill="{legs}" opacity="0.7"/>
  <rect x="{s(2)}" y="{s(182)}" width="{s(8)}" height="{s(8)}" rx="{s(2)}" fill="#22c55e"/>
  <text x="{s(13)}" y="{s(190)}" font-size="{s(8)}" fill="#9ca3af" font-family="IBM Plex Mono,monospace">ok</text>
  <rect x="{s(38)}" y="{s(182)}" width="{s(8)}" height="{s(8)}" rx="{s(2)}" fill="#f59e0b"/>
  <text x="{s(49)}" y="{s(190)}" font-size="{s(8)}" fill="#9ca3af" font-family="IBM Plex Mono,monospace">low</text>
  <rect x="{s(78)}" y="{s(182)}" width="{s(8)}" height="{s(8)}" rx="{s(2)}" fill="#ef4444"/>
  <text x="{s(89)}" y="{s(190)}" font-size="{s(8)}" fill="#9ca3af" font-family="IBM Plex Mono,monospace">gap</text>
</svg>"""
    return svg

# ── Plan generator ────────────────────────────────────────────
def generate_plan(gym_summary, end_summary, is_wed_available):
    flags = []
    for group in ["Chest", "Shoulders", "Back", "Legs"]:
        if group not in gym_summary:
            flags.append(("bad", f"{group.lower()} — no data. session likely skipped.")); continue
        pct = gym_summary[group]["compliance_pct"]
        spw = gym_summary[group]["sessions_per_week"]
        if pct < 50:   flags.append(("bad",  f"{group.lower()} — {spw}x/wk ({GYM_DAYS[group]}). undertrained."))
        elif pct < 80: flags.append(("warn", f"{group.lower()} — {spw}x/wk. some sessions missed."))
        else:          flags.append(("ok",   f"{group.lower()} — {spw}x/wk. on track."))

    run_hold = False
    for sport, exp in ENDURANCE_TARGETS.items():
        if sport not in end_summary: continue
        stats = end_summary[sport]
        pct = stats["compliance_pct"]
        spw = stats["sessions_per_week"]
        if stats.get("soft_tissue_warning"):
            flags.append(("bad", "run volume >10% wk/wk — soft tissue risk. hold flat.")); run_hold = True
        if pct < 50:   flags.append(("bad",  f"{sport.lower()} — {spw}x/wk vs {exp}x target.{'  (priority: weakest tri leg)' if sport=='Swim' else ''}"))
        elif pct < 80: flags.append(("warn", f"{sport.lower()} — {spw}x/wk vs {exp}x target."))
        else:          flags.append(("ok",   f"{sport.lower()} — {spw}x/wk. on track."))

    swim_gap = (ENDURANCE_TARGETS["Swim"] - end_summary.get("Swim", {}).get("sessions_per_week", 0)) > 0
    back_ex = " · ".join(GYM_EXERCISES["Back"])

    plan = [
        {"day": "monday",    "time": "6am",     "sessions": [("Run", "20min easy"), ("Gym", f"chest — {' · '.join(GYM_EXERCISES['Chest'])} (3×12)")]},
        {"day": "tuesday",   "time": "6am",     "sessions": [("Gym", f"shoulders — {' · '.join(GYM_EXERCISES['Shoulders'])} (3×12)")] + ([("Swim", "2200y — drills + intervals")] if swim_gap else [])},
        {"day": "wednesday", "time": "6am" if is_wed_available else "—",
         "sessions": ([("Gym", f"back — {back_ex} (3×12)")] + ([("Swim", "2000y aerobic")] if swim_gap else [])) if is_wed_available else [("Rest", "wed unavailable → back moves thu 5pm")]},
        {"day": "thursday",  "time": "5pm" if not is_wed_available else "—",
         "sessions": [("Gym", f"back — {back_ex} (3×12)")] if not is_wed_available else [("Rest", "recovery")]},
        {"day": "friday",    "time": "6am",     "sessions": [("Run", "5mi easy" + (" — hold volume flat" if run_hold else "")), ("Gym", f"legs — {' · '.join(GYM_EXERCISES['Legs'])} (3×12)")]},
        {"day": "saturday",  "time": "morning", "sessions": [("Brick", "bike 1.5hr z2 → run 3mi (transition practice)")]},
        {"day": "sunday",    "time": "morning", "sessions": [("Swim", "2500y open water if possible") if swim_gap else ("Run", "long run z2 easy")]},
    ]
    return flags, plan

def badge(stype):
    cls = {"Run": "run", "Swim": "swim", "Bike": "bike", "Gym": "gym", "Brick": "brick", "Rest": "rest"}.get(stype, "rest")
    return f'<span class="badge badge-{cls}">{stype.lower()}</span>'

# ── Days to race ──────────────────────────────────────────────
def days_to_race():
    return (RACE_DATE - datetime.date.today()).days

# ═══════════════════════════════════════════════════════════════
# SIDEBAR (desktop only)
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<p class="mono" style="font-size:11px;letter-spacing:0.1em;color:var(--color-text-tertiary);">settings</p>', unsafe_allow_html=True)
    analysis_weeks = st.slider("analysis window (weeks)", 2, 8, 4)
    is_wed_available = st.checkbox("wednesday available?", value=True)
    st.markdown("---")
    garmin_email, garmin_password = get_garmin_creds()
    if garmin_email:
        st.markdown('<p style="font-size:11px;color:#22c55e;font-family:IBM Plex Mono,monospace;">● garmin connected</p>', unsafe_allow_html=True)
        if st.button("refresh garmin"):
            st.cache_data.clear(); st.rerun()
    else:
        st.markdown('<p style="font-size:11px;color:#ef4444;font-family:IBM Plex Mono,monospace;">✗ add GARMIN_EMAIL + GARMIN_PASSWORD to secrets</p>', unsafe_allow_html=True)

# ── Mobile settings (shown inline on mobile) ──────────────────
analysis_weeks = 4
is_wed_available = True

# ═══════════════════════════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════════════════════════
garmin_email, garmin_password = get_garmin_creds()
garmin_df = None
if garmin_email and garmin_password:
    try:
        garmin_df = fetch_garmin_activities(garmin_email, garmin_password, analysis_weeks + 1)
    except Exception:
        pass

raw_gym_df = None
try:
    raw_gym_df = load_from_url(get_sheet_url())
except Exception:
    pass

gym_df = None
if raw_gym_df is not None:
    _, gym_df = clean_and_reshape(raw_gym_df)

gym_summary  = build_gym_summary(gym_df, analysis_weeks)  if gym_df is not None and not gym_df.empty else {}
end_summary  = build_endurance_summary(garmin_df, analysis_weeks) if garmin_df is not None and not garmin_df.empty else {}

# ═══════════════════════════════════════════════════════════════
# HEADER (shared mobile + desktop)
# ═══════════════════════════════════════════════════════════════
total_sessions = sum(v["sessions"] for v in gym_summary.values()) + sum(v["sessions"] for v in end_summary.values())
avg_compliance = round(sum(v["compliance_pct"] for v in {**gym_summary, **end_summary}.values()) / max(len({**gym_summary, **end_summary}), 1))
garmin_status = "● live" if garmin_df is not None else "✗ offline"
garmin_color = "#22c55e" if garmin_df is not None else "#ef4444"

st.markdown(f"""
<div class="metric-strip">
  <div class="metric-cell">
    <div class="metric-label">training / week</div>
    <div class="metric-value">{datetime.date.today().isocalendar()[1]}</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">compliance</div>
    <div class="metric-value">{avg_compliance}%</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">sessions (4wk)</div>
    <div class="metric-value">{total_sessions}</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">days to race</div>
    <div class="metric-value" style="color:#f59e0b;">{days_to_race()}</div>
    <div class="metric-sub">olympic tri 6/20</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">garmin</div>
    <div class="metric-value" style="font-size:13px; color:{garmin_color}; padding-top:4px;">{garmin_status}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# MOBILE LAYOUT (overview + body map only, stacked)
# ═══════════════════════════════════════════════════════════════
mobile_col1, mobile_col2 = st.columns([3, 2])

with mobile_col1:
    st.markdown('<div class="mobile-only">', unsafe_allow_html=True)
    st.markdown('<div class="section-head">status</div>', unsafe_allow_html=True)

    rows_html = ""
    for group in ["Chest", "Shoulders", "Back", "Legs"]:
        if group not in gym_summary: continue
        pct = gym_summary[group]["compliance_pct"]
        spw = gym_summary[group]["sessions_per_week"]
        cls = "s-ok" if pct >= 80 else ("s-warn" if pct >= 50 else "s-bad")
        sym = "✓" if pct >= 80 else ("~" if pct >= 50 else "✗")
        rows_html += f'<tr><td>{group.lower()}</td><td class="{cls}">{sym} {spw}x/wk</td></tr>'

    for sport in ["Swim", "Bike", "Run"]:
        if sport not in end_summary: continue
        pct = end_summary[sport]["compliance_pct"]
        spw = end_summary[sport]["sessions_per_week"]
        cls = "s-ok" if pct >= 80 else ("s-warn" if pct >= 50 else "s-bad")
        sym = "✓" if pct >= 80 else ("~" if pct >= 50 else "✗")
        rows_html += f'<tr><td>{sport.lower()}</td><td class="{cls}">{sym} {pct}%</td></tr>'

    st.markdown(f'<table class="status-table">{rows_html}</table>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with mobile_col2:
    st.markdown('<div class="mobile-only">', unsafe_allow_html=True)
    st.markdown('<div class="section-head">muscle map</div>', unsafe_allow_html=True)
    if gym_summary:
        st.markdown(body_map_svg(gym_summary, size=150), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# DESKTOP TABS
# ═══════════════════════════════════════════════════════════════
st.markdown('<div class="desktop-only">', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["overview", "gym analysis", "next week"])

with tab1:
    c1, c2, c3 = st.columns([2, 2, 1])

    with c1:
        st.markdown('<div class="section-head">gym</div>', unsafe_allow_html=True)
        rows = ""
        for group in ["Chest", "Shoulders", "Back", "Legs"]:
            if group not in gym_summary: continue
            pct = gym_summary[group]["compliance_pct"]
            spw = gym_summary[group]["sessions_per_week"]
            cls = "s-ok" if pct >= 80 else ("s-warn" if pct >= 50 else "s-bad")
            sym = "✓" if pct >= 80 else ("~" if pct >= 50 else "✗")
            rows += f'<tr><td>{group.lower()}</td><td class="{cls}">{sym} {spw}x/wk &nbsp; {pct}%</td></tr>'
        st.markdown(f'<table class="status-table">{rows}</table>', unsafe_allow_html=True)

        st.markdown('<div class="section-head">endurance</div>', unsafe_allow_html=True)
        rows = ""
        for sport in ["Swim", "Bike", "Run"]:
            if sport not in end_summary: continue
            stats = end_summary[sport]
            pct = stats["compliance_pct"]
            spw = stats["sessions_per_week"]
            warn = " ⚠" if stats.get("soft_tissue_warning") else ""
            cls = "s-ok" if pct >= 80 else ("s-warn" if pct >= 50 else "s-bad")
            sym = "✓" if pct >= 80 else ("~" if pct >= 50 else "✗")
            rows += f'<tr><td>{sport.lower()}{warn}</td><td class="{cls}">{sym} {spw}x/wk &nbsp; {pct}%</td></tr>'
        st.markdown(f'<table class="status-table">{rows}</table>', unsafe_allow_html=True)

    with c2:
        if garmin_df is not None and not garmin_df.empty:
            st.markdown('<div class="section-head">weekly sessions</div>', unsafe_allow_html=True)
            end_weekly = (
                get_recent(garmin_df, analysis_weeks)
                .assign(week=lambda d: d["date"].dt.to_period("W").dt.start_time)
                .groupby(["week", "sport"]).size().reset_index(name="n")
            )
            fig = px.bar(end_weekly, x="week", y="n", color="sport",
                         color_discrete_map={"Swim": "#3b82f6", "Bike": "#f59e0b", "Run": "#22c55e", "Other": "#9ca3af"},
                         labels={"n": "", "week": "", "sport": ""})
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_family="IBM Plex Mono", font_size=10,
                margin=dict(l=0, r=0, t=4, b=0), height=180,
                legend=dict(orientation="h", y=-0.15, x=0, font_size=10),
                showlegend=True,
            )
            fig.update_xaxes(showgrid=False, tickfont_size=9)
            fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.06)", tickfont_size=9)
            st.plotly_chart(fig, use_container_width=True)

    with c3:
        st.markdown('<div class="section-head">muscle map</div>', unsafe_allow_html=True)
        if gym_summary:
            st.markdown(body_map_svg(gym_summary, size=180), unsafe_allow_html=True)

with tab2:
    if gym_df is None or gym_df.empty:
        st.info("No gym data loaded.")
    else:
        recent_gym = get_recent(gym_df, analysis_weeks)
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown('<div class="section-head">volume by muscle group</div>', unsafe_allow_html=True)
            group_vol = recent_gym.groupby(["date", "group"]).agg(volume=("volume", "sum")).reset_index()
            fig = px.bar(group_vol, x="date", y="volume", color="group",
                         color_discrete_map={"Chest": "#ef4444", "Shoulders": "#f97316", "Back": "#3b82f6", "Legs": "#22c55e", "Other": "#9ca3af"},
                         labels={"volume": "", "date": "", "group": ""})
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_family="IBM Plex Mono", font_size=10, height=200,
                margin=dict(l=0, r=0, t=4, b=0),
                legend=dict(orientation="h", y=-0.2, x=0, font_size=10),
            )
            fig.update_xaxes(showgrid=False, tickfont_size=9)
            fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.06)", tickfont_size=9)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown('<div class="section-head">exercise progress</div>', unsafe_allow_html=True)
            all_ex = sorted(recent_gym["exercise"].dropna().unique())
            if all_ex:
                selected = st.selectbox("", all_ex, label_visibility="collapsed")
                ex_df = recent_gym[recent_gym["exercise"] == selected]
                best = ex_df.groupby("date", as_index=False).agg(
                    best_weight=("weight", "max"), est_1rm=("estimated_1rm", "max")).sort_values("date")
                cc1, cc2 = st.columns(2)
                with cc1:
                    fig2 = px.line(best, x="date", y="best_weight", markers=True, labels={"best_weight": "kg", "date": ""})
                    fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                       font_family="IBM Plex Mono", font_size=10, height=140, margin=dict(l=0,r=0,t=4,b=0))
                    fig2.update_traces(line_color="#3b82f6", marker_color="#3b82f6")
                    fig2.update_xaxes(showgrid=False, tickfont_size=8)
                    fig2.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.06)", tickfont_size=8)
                    st.plotly_chart(fig2, use_container_width=True)
                with cc2:
                    fig3 = px.line(best, x="date", y="est_1rm", markers=True, labels={"est_1rm": "1rm", "date": ""})
                    fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                       font_family="IBM Plex Mono", font_size=10, height=140, margin=dict(l=0,r=0,t=4,b=0))
                    fig3.update_traces(line_color="#22c55e", marker_color="#22c55e")
                    fig3.update_xaxes(showgrid=False, tickfont_size=8)
                    fig3.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.06)", tickfont_size=8)
                    st.plotly_chart(fig3, use_container_width=True)
        with c2:
            st.markdown('<div class="section-head">compliance flags</div>', unsafe_allow_html=True)
            for group, stats in gym_summary.items():
                pct = stats["compliance_pct"]
                spw = stats["sessions_per_week"]
                day = GYM_DAYS.get(group, "")
                if pct < 50:   st.markdown(f'<div class="flag flag-bad">✗ {group.lower()} — {spw}x/wk ({day})</div>', unsafe_allow_html=True)
                elif pct < 80: st.markdown(f'<div class="flag flag-warn">~ {group.lower()} — {spw}x/wk ({day})</div>', unsafe_allow_html=True)
                else:          st.markdown(f'<div class="flag flag-ok">✓ {group.lower()} — on track</div>', unsafe_allow_html=True)

with tab3:
    if not gym_summary and not end_summary:
        st.warning("Need at least one data source.")
    else:
        flags, plan = generate_plan(gym_summary, end_summary, is_wed_available)
        c1, c2 = st.columns([2, 3])
        with c1:
            st.markdown('<div class="section-head">gap analysis</div>', unsafe_allow_html=True)
            for level, msg in flags:
                cls = {"ok": "flag-ok", "warn": "flag-warn", "bad": "flag-bad"}[level]
                sym = {"ok": "✓", "warn": "~", "bad": "✗"}[level]
                st.markdown(f'<div class="flag {cls}">{sym} {msg}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="section-head">next week</div>', unsafe_allow_html=True)
            for day_plan in plan:
                sessions_html = ""
                for stype, detail in day_plan["sessions"]:
                    sessions_html += f'{badge(stype)} '
                sessions_html += "<br>"
                for stype, detail in day_plan["sessions"]:
                    sessions_html += f'<span style="font-size:11px;color:var(--color-text-secondary);">{detail}</span><br>'
                st.markdown(
                    f'<div class="plan-day">'
                    f'<div class="plan-dayname">{day_plan["day"]} &nbsp;·&nbsp; {day_plan["time"]}</div>'
                    f'<div class="plan-content">{sessions_html}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

st.markdown('</div>', unsafe_allow_html=True)
