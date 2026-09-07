# AgniRakshak - AI-Enabled Fire Risk Intelligence

Real-time satellite-based fire risk monitoring, anomaly detection, and predictive analytics powered by NASA FIRMS satellite data across North India.

## Architecture



## Quick Start

### 1. Rebuild data (from CSVs)

```bash
python src/build_json.py
```

### 2. Run locally

```bash
python src/server.py
# Open http://localhost:5000
```

### 3. Deploy to GitHub Pages

Push the root files (index.html, style.css, script.js, data/) to your repo's main branch. Enable GitHub Pages in repo settings.

## Project Structure



## Data Pipeline

### One-time model builds (run locally)

1. **fetch_firms.py** - Downloads historical FIRMS data (2020-present)
2. **clean_merge.py** - Cleans and merges raw FIRMS CSVs
3. **grid_features.py** - Creates 5km grid cells and computes features
4. **risk_model.py** - ML risk scoring (Random Forest, 0-100)
5. **classify_fire_type.py** - Classifies fire sources (Industrial, Agricultural, Forest)
6. **merge_risk_zone.py** - Aggregates into ~30km regional risk zones
7. **forecast_engine.py** - Predictive fire season analysis

These read the full-history archive (`data/processed/firms_clean_merged.csv`, a
291 MB Git LFS file kept only on local machines).

### Automated daily loop (runs in CI every 6 hours)

1. **auto_update.py** - Fetches only the daily FIRMS delta and appends it to the
   rolling store (`data/processed/recent_detections.csv`, ~95 days), updates
   `daily_activity.csv` incrementally, refreshes 30d/90d grid features and risk
   feature columns, and re-runs the alert engine.
2. **fetch_nrt.py** - Near-real-time FIRMS detections (last 24h)
3. **alert_engine.py** - Generates alerts from NRT + risk data
4. **build_json.py** - Converts all CSVs to JSON for the dashboard (merges
   fire-type classifications + display coordinates into `grid_data.json`)

Seed the rolling store once (it self-fetches from the FIRMS API):

```bash
python src/auto_update.py --bootstrap
```

Or seed it from the local full-history archive:

```bash
python src/auto_update.py --bootstrap --from-csv data/processed/firms_clean_merged.csv
```

## Auto-Update

- **GitHub Actions**: Runs every 6 hours, fetches new FIRMS data, rebuilds JSON.
  Scheduled runs only fire on the **default branch (`main`)** — the workflow
  file must live there. Requires the `FIRMS_MAP_KEY` repository secret.
- **Flask Server**: On-demand update via POST /api/update (local dev)
- **Manual**: Run `python src/auto_update.py && python src/fetch_nrt.py && python src/build_json.py`

## Tech Stack

- **Frontend**: Leaflet.js, D3.js, Gemini AI (client-side)
- **Backend**: Python (pandas, scikit-learn, geopandas)
- **Data**: NASA FIRMS, ESA WorldCover, OpenStreetMap
- **Hosting**: GitHub Pages + Railway/Render

## License

Research project for Smart India Hackathon (SIH)
