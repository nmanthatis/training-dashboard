# Training Dashboard Starter

This is a first-pass automatic workout dashboard for your current Google Sheets format.

It supports a wide strength-training sheet like:

```text
Date | Exercise | W 1 | Reps | W 2 | Reps | W 3 | Reps | W 4 | Reps | W 5 | Reps | Comments | Weight
```

The app reshapes that into long format internally:

```text
date | exercise | group | set_number | weight | reps | volume | estimated_1rm
```

## 1. Install

```bash
cd training_dashboard_starter
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Test with manual CSV upload

Run:

```bash
streamlit run app.py
```

Then upload a CSV from the sidebar.

## 3. Connect Google Sheets

In Google Sheets:

```text
File → Share → Publish to web → choose the workout sheet → CSV
```

Then either:

### Option A: paste the link in `app.py`

Open `app.py` and set:

```python
DEFAULT_SHEET_CSV_URL = "your_csv_link_here"
```

### Option B: use Streamlit secrets

Create this file:

```text
.streamlit/secrets.toml
```

with:

```toml
SHEET_CSV_URL = "your_csv_link_here"
```

## 4. Run

```bash
streamlit run app.py
```

## 5. Automatic refresh

The app caches the Google Sheet for 1 hour:

```python
@st.cache_data(ttl=3600)
```

To refresh every 15 minutes, use:

```python
@st.cache_data(ttl=900)
```

## 6. Deploy later

A simple deployment path is:

1. Put this folder on GitHub.
2. Connect the repo to Streamlit Community Cloud.
3. Add `SHEET_CSV_URL` as a secret in the Streamlit app settings.
4. Open your dashboard link whenever you want updated plots.

## Notes

- `Weight` is treated as body weight.
- Exercise prefixes like `L: Squat`, `Ch: Dumbell Press`, `B: Cable Rows` are split into group and exercise name.
- Volume is calculated as `weight × reps`.
- Estimated 1RM uses the Epley formula: `weight × (1 + reps / 30)`.
- Missing reps are allowed, but volume and estimated 1RM require reps.
