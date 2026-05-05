import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# Training Dashboard Starter
# ============================================================
# How to use:
# 1. Publish your Google Sheet as CSV, or upload a CSV manually.
# 2. Paste the CSV URL below, OR put it in .streamlit/secrets.toml:
#
#    SHEET_CSV_URL = "https://docs.google.com/spreadsheets/..."
#
# 3. Run:
#    streamlit run app.py
#
# The app is intentionally robust to your current wide format:
# Date | Exercise | W 1 | Reps | W 2 | Reps | W 3 | Reps ...
# including blank spacer columns.
# ============================================================


st.set_page_config(
    page_title="Training Dashboard",
    page_icon="🏋️",
    layout="wide",
)


DEFAULT_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSFkE9lirf4G5VLj2nlwvN-p8yE-V5wrcqZjJbarKschaBpNiD3xXKxlk2YL77hIn6O2Zbaqh36bQId/pub?output=csv"  # Optional: paste your published Google Sheets CSV link here.


def get_sheet_url() -> str:
    """Read CSV URL from Streamlit secrets first, then fallback constant."""
    try:
        url = st.secrets.get("SHEET_CSV_URL", "")
    except Exception:
        url = ""

    if not url:
        url = DEFAULT_SHEET_CSV_URL

    return str(url).strip()


@st.cache_data(ttl=600)
def load_from_url(url: str) -> pd.DataFrame:
    """Load the Google Sheet CSV. Cached for 1 hour."""
    return pd.read_csv(url)


def load_data() -> pd.DataFrame:
    """Load from uploaded CSV if provided, otherwise from Google Sheet URL."""
    st.sidebar.header("Data source")

    uploaded_file = st.sidebar.file_uploader(
        "Optional: upload CSV manually",
        type=["csv"],
        help="Useful for testing before connecting Google Sheets.",
    )

    if uploaded_file is not None:
        return pd.read_csv(uploaded_file)

    url = get_sheet_url()

    if not url:
        st.info(
            "Add your Google Sheets CSV URL in `DEFAULT_SHEET_CSV_URL`, "
            "or create `.streamlit/secrets.toml`, or upload a CSV from the sidebar."
        )
        st.stop()

    return load_from_url(url)


def normalize_columns(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean column names while preserving the important pattern:
    Date, Exercise, W 1, Reps, W 2, Reps...
    """
    df = raw_df.copy()

    clean_cols = []
    unnamed_counter = 1

    for col in df.columns:
        name = str(col).strip()

        # Pandas often creates names like "Unnamed: 2" for blank columns.
        if name == "" or name.lower().startswith("unnamed"):
            name = f"_blank_{unnamed_counter}"
            unnamed_counter += 1

        # Collapse spaces, but keep human-readable names.
        name = re.sub(r"\s+", " ", name)
        clean_cols.append(name)

    df.columns = clean_cols
    return df


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Find a column by forgiving lower-case matching."""
    lower_map = {c.lower().strip(): c for c in df.columns}

    for candidate in candidates:
        key = candidate.lower().strip()
        if key in lower_map:
            return lower_map[key]

    return None


def extract_set_columns(df: pd.DataFrame) -> list[tuple[int, str, str | None]]:
    """
    Find W columns and pair each W column with the nearest Reps/R column after it.

    This is designed for sheets like:
    W 1 | Reps | W 2 | Reps | W 3 | Reps ...

    Returns:
        [(set_number, weight_col, reps_col_or_None), ...]
    """
    columns = list(df.columns)
    set_columns = []

    for idx, col in enumerate(columns):
        col_clean = str(col).strip().lower()

        match = re.fullmatch(r"w\s*\.?\s*(\d+)", col_clean)
        if not match:
            continue

        set_number = int(match.group(1))
        reps_col = None

        # Look ahead until the next W column. Pick the first reps-like column.
        for next_col in columns[idx + 1:]:
            next_clean = str(next_col).strip().lower()

            if re.fullmatch(r"w\s*\.?\s*\d+", next_clean):
                break

            if next_clean in {"reps", "rep", "r", f"r{set_number}", f"r {set_number}"}:
                reps_col = next_col
                break

        set_columns.append((set_number, col, reps_col))

    return sorted(set_columns, key=lambda x: x[0])


def parse_exercise_group(exercise: str) -> tuple[str, str]:
    """
    Split labels like 'L: Squat' into:
    group='L', exercise_name='Squat'
    """
    exercise = str(exercise).strip()

    if ":" in exercise:
        group, name = exercise.split(":", 1)
        return group.strip(), name.strip()

    return "Other", exercise


def clean_and_reshape(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convert the user's wide sheet into long format:
    date, exercise, group, exercise_name, set_number, weight, reps, volume, estimated_1rm
    """
    df = normalize_columns(raw_df)

    date_col = find_column(df, ["Date"])
    exercise_col = find_column(df, ["Exercise", "Workout", "Movement"])
    comments_col = find_column(df, ["Comments", "Comment", "Notes", "Note"])
    body_weight_col = find_column(df, ["Weight", "BodyWeight", "Body Weight", "BW"])

    if date_col is None or exercise_col is None:
        st.error("I could not find required columns. I need at least `Date` and `Exercise`.")
        st.write("Detected columns:", list(df.columns))
        st.stop()

    set_columns = extract_set_columns(df)

    if not set_columns:
        st.error("I could not find set columns like `W 1`, `W 2`, etc.")
        st.write("Detected columns:", list(df.columns))
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

            # Skip truly empty sets.
            if pd.isna(weight) and pd.isna(reps):
                continue

            rows.append(
                {
                    "date": date,
                    "exercise": str(exercise).strip(),
                    "group": group,
                    "exercise_name": exercise_name,
                    "set_number": set_number,
                    "weight": weight,
                    "reps": reps,
                    "comments": comment,
                    "body_weight": body_weight,
                }
            )

    long_df = pd.DataFrame(rows)

    if long_df.empty:
        return df, long_df

    long_df["weight"] = pd.to_numeric(long_df["weight"], errors="coerce")
    long_df["reps"] = pd.to_numeric(long_df["reps"], errors="coerce")

    # If reps are missing, volume and 1RM stay missing. That's okay.
    long_df["volume"] = long_df["weight"] * long_df["reps"]
    long_df["estimated_1rm"] = long_df["weight"] * (1 + long_df["reps"] / 30)

    return df, long_df


def format_number(value, decimals=0):
    if pd.isna(value):
        return "—"
    return f"{value:,.{decimals}f}"


# ============================================================
# App
# ============================================================

st.title("Training Dashboard")
st.caption("Automatic strength-training progress dashboard from your Google Sheet.")

raw_df = load_data()
wide_df, df = clean_and_reshape(raw_df)

if df.empty:
    st.warning("No valid workout sets found after cleaning.")
    st.stop()

# Sidebar controls
min_date = df["date"].min().date()
max_date = df["date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    df = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)]

groups = sorted(df["group"].dropna().unique())
selected_groups = st.sidebar.multiselect("Groups", groups, default=groups)

if selected_groups:
    df = df[df["group"].isin(selected_groups)]

exercise_options = sorted(df["exercise"].dropna().unique())
selected_exercise = st.sidebar.selectbox("Exercise", exercise_options)

exercise_df = df[df["exercise"] == selected_exercise].copy()

# Metrics
total_workouts = df["date"].nunique()
total_sets = len(df)
total_volume = df["volume"].sum(skipna=True)
date_span = (df["date"].max() - df["date"].min()).days + 1

col1, col2, col3, col4 = st.columns(4)
col1.metric("Workout days", format_number(total_workouts))
col2.metric("Logged sets", format_number(total_sets))
col3.metric("Total volume", format_number(total_volume))
col4.metric("Date span", f"{date_span} days")

st.divider()

# Exercise progress
st.subheader(f"Progress: {selected_exercise}")

best_sets = (
    exercise_df.groupby("date", as_index=False)
    .agg(
        best_weight=("weight", "max"),
        best_estimated_1rm=("estimated_1rm", "max"),
        total_volume=("volume", "sum"),
        total_sets=("set_number", "count"),
    )
    .sort_values("date")
)

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    fig = px.line(
        best_sets,
        x="date",
        y="best_weight",
        markers=True,
        title="Best Set Weight",
    )
    st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    fig = px.line(
        best_sets,
        x="date",
        y="best_estimated_1rm",
        markers=True,
        title="Estimated 1RM",
    )
    st.plotly_chart(fig, use_container_width=True)

fig = px.bar(
    best_sets,
    x="date",
    y="total_volume",
    title="Exercise Volume Per Workout",
)
st.plotly_chart(fig, use_container_width=True)

# Overall daily volume
st.subheader("Overall Daily Training Volume")

daily_summary = (
    df.groupby("date", as_index=False)
    .agg(
        total_volume=("volume", "sum"),
        total_sets=("set_number", "count"),
        exercises=("exercise", "nunique"),
    )
    .sort_values("date")
)

fig = px.bar(
    daily_summary,
    x="date",
    y="total_volume",
    title="Total Daily Volume",
)
st.plotly_chart(fig, use_container_width=True)

# Group volume
st.subheader("Volume by Group")

group_summary = (
    df.groupby(["date", "group"], as_index=False)
    .agg(total_volume=("volume", "sum"))
    .sort_values("date")
)

fig = px.bar(
    group_summary,
    x="date",
    y="total_volume",
    color="group",
    title="Daily Volume by Group",
)
st.plotly_chart(fig, use_container_width=True)

# Body weight if available
body_weight_df = (
    df[["date", "body_weight"]]
    .dropna()
    .drop_duplicates()
    .sort_values("date")
)

if not body_weight_df.empty:
    st.subheader("Body Weight")
    fig = px.line(
        body_weight_df,
        x="date",
        y="body_weight",
        markers=True,
        title="Body Weight Over Time",
    )
    st.plotly_chart(fig, use_container_width=True)

# Notes
comments_df = (
    df[df["comments"].notna() & (df["comments"].astype(str).str.strip() != "")]
    [["date", "exercise", "comments"]]
    .drop_duplicates()
    .sort_values("date", ascending=False)
)

if not comments_df.empty:
    st.subheader("Comments / Notes")
    st.dataframe(comments_df, use_container_width=True, hide_index=True)

# Tables
with st.expander("Cleaned long-format data"):
    st.dataframe(
        df.sort_values(["date", "exercise", "set_number"], ascending=[False, True, True]),
        use_container_width=True,
        hide_index=True,
    )

with st.expander("Original wide-format data"):
    st.dataframe(wide_df, use_container_width=True, hide_index=True)

st.caption(
    "Data refreshes from Google Sheets every 1 hour when using the CSV URL. "
    "Change `ttl=3600` in `load_from_url()` if you want a different refresh interval."
)
