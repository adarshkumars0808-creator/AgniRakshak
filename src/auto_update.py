"""
auto_update.py — Automatic data pipeline for AgniRakshak.

Runs on every dashboard refresh. Performs:
1. Fetch recent FIRMS data (from last historical date to today)
2. Append to historical dataset (firms_clean_merged.csv)
3. Update daily_activity.csv
4. Clean NRT detections older than 24 hours
5. Recompute grid features for affected cells
6. Recompute risk predictions
7. Re-run alert engine

Usage:
    python src/auto_update.py          # full pipeline
    python src/auto_update.py --nrt    # NRT cleanup only (fast)
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import date, timedelta, datetime, timezone
from io import StringIO

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROC_DIR = DATA_DIR / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROC_DIR.mkdir(parents=True, exist_ok=True)

HISTORICAL_FILE = PROC_DIR / "firms_clean_merged.csv"
DAILY_FILE = PROC_DIR / "daily_activity.csv"
NRT_FILE = PROC_DIR / "nrt_detections.csv"
NRT_LATEST = PROC_DIR / "nrt_latest_timestamp.txt"
GRID_FEATURES_FILE = PROC_DIR / "grid_features.csv"
RISK_PRED_FILE = PROC_DIR / "risk_predictions.csv"
FIRE_TYPE_FILE = PROC_DIR / "fire_type_predictions.csv"
ALERTS_FILE = PROC_DIR / "alerts_log.csv"

# ============================================================
# FIRMS API CONFIG
# ============================================================

MAP_KEY = os.getenv("FIRMS_MAP_KEY", "")
if not MAP_KEY:
    # Try to read from .env directly
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("FIRMS_MAP_KEY="):
                MAP_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

WEST, SOUTH, EAST, NORTH = 74.5, 23.5, 85.0, 31.5
BBOX = f"{WEST},{SOUTH},{EAST},{NORTH}"

SOURCES = ["VIIRS_SNPP_SP", "VIIRS_NOAA20_SP", "VIIRS_NOAA21_NRT"]

REQUEST_TIMEOUT = 120
MAX_RETRIES = 3
RETRY_DELAY = 5
CHUNK_DAYS = 5


# ============================================================
# 1. FETCH RECENT FIRMS DATA
# ============================================================

def get_last_historical_date():
    """Get the last date in the historical dataset."""
    if not HISTORICAL_FILE.exists():
        return date(2020, 1, 1)

    try:
        # Read just the acq_date column to find the max date
        df = pd.read_csv(HISTORICAL_FILE, usecols=["acq_date"], low_memory=False)
        df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce")
        max_date = df["acq_date"].max()
        if pd.notna(max_date):
            return max_date.date()
    except Exception as e:
        print(f"  [WARN] Could not read last date: {e}")

    return date(2020, 1, 1)


def fetch_firms_chunk(source, start_date, end_date):
    """Fetch one chunk of FIRMS historical data."""
    day_range = (end_date - start_date).days + 1
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{source}/{BBOX}/{day_range}/{start_date.isoformat()}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                print(f"    HTTP {resp.status_code} for {source} {start_date}→{end_date}")
                continue
            if not resp.text.strip():
                return pd.DataFrame()
            df = pd.read_csv(StringIO(resp.text))
            if not df.empty:
                df["source"] = source
            return df
        except Exception as e:
            print(f"    Attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    return pd.DataFrame()


def fetch_recent_data(start_date, end_date):
    """Fetch FIRMS data for the gap between last historical date and today."""
    if start_date >= end_date:
        print("  Historical data is up to date — no gap to fill.")
        return pd.DataFrame()

    print(f"\n  Fetching FIRMS data: {start_date} → {end_date}")
    all_frames = []

    for source in SOURCES:
        # NOAA-21 only from Jan 2024
        source_start = start_date
        if source == "VIIRS_NOAA21_NRT" and source_start < date(2024, 1, 17):
            source_start = date(2024, 1, 17)

        if source_start > end_date:
            continue

        current = source_start
        while current <= end_date:
            chunk_end = min(current + timedelta(days=CHUNK_DAYS - 1), end_date)
            df = fetch_firms_chunk(source, current, chunk_end)
            if not df.empty:
                all_frames.append(df)
                print(f"    {source}: {current}→{chunk_end} = {len(df):,} detections")
            current = chunk_end + timedelta(days=1)
            time.sleep(0.5)  # Rate limit courtesy

    if not all_frames:
        print("  No new detections fetched.")
        return pd.DataFrame()

    merged = pd.concat(all_frames, ignore_index=True)
    print(f"\n  Total new detections: {len(merged):,}")
    return merged


def merge_into_historical(new_data):
    """Append new data to the historical dataset, deduplicate, and save."""
    if new_data.empty:
        return

    if not HISTORICAL_FILE.exists():
        new_data.to_csv(HISTORICAL_FILE, index=False)
        print(f"  Created new historical file with {len(new_data):,} rows")
        return

    # Load existing
    existing = pd.read_csv(HISTORICAL_FILE, low_memory=False)
    print(f"  Existing historical: {len(existing):,} rows")

    # Normalize columns
    for df in [existing, new_data]:
        df.columns = [c.strip().lower() for c in df.columns]
        if "acq_date" in df.columns:
            df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Concat
    combined = pd.concat([existing, new_data], ignore_index=True)

    # Deduplicate on key columns
    dedup_cols = ["latitude", "longitude", "acq_date", "acq_time", "satellite", "frp"]
    dedup_cols = [c for c in dedup_cols if c in combined.columns]
    before = len(combined)
    combined = combined.drop_duplicates(subset=dedup_cols).reset_index(drop=True)
    removed = before - len(combined)
    if removed > 0:
        print(f"  Dedup removed {removed:,} duplicate rows")

    # Sort by date
    combined = combined.sort_values("acq_date", ascending=True).reset_index(drop=True)

    # Save
    combined.to_csv(HISTORICAL_FILE, index=False)
    print(f"  Updated historical: {len(combined):,} rows")
    print(f"  Date range: {combined['acq_date'].min()} → {combined['acq_date'].max()}")


# ============================================================
# 2. UPDATE DAILY ACTIVITY
# ============================================================

def update_daily_activity():
    """Recompute daily_activity.csv from the historical dataset."""
    if not HISTORICAL_FILE.exists():
        return

    print("\n  Updating daily_activity.csv...")
    df = pd.read_csv(HISTORICAL_FILE, usecols=["acq_date", "frp"], low_memory=False)
    df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce")
    df = df.dropna(subset=["acq_date"])
    df["date"] = df["acq_date"].dt.strftime("%Y-%m-%d")

    daily = df.groupby("date").agg(
        detections=("frp", "count"),
        avg_frp=("frp", "mean"),
    ).reset_index()
    daily = daily.sort_values("date").reset_index(drop=True)
    daily.to_csv(DAILY_FILE, index=False)
    print(f"  daily_activity.csv: {len(daily)} days ({daily['date'].min()} → {daily['date'].max()})")


# ============================================================
# 3. CLEAN NRT DETECTIONS > 24h OLD
# ============================================================

def clean_old_nrt():
    """Remove NRT detections older than 24 hours."""
    if not NRT_FILE.exists():
        print("  No NRT file to clean.")
        return

    df = pd.read_csv(NRT_FILE, low_memory=False)
    if df.empty:
        return

    if "acq_date" not in df.columns:
        return

    before = len(df)
    df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce")

    # Keep only detections from last 24 hours
    cutoff = pd.Timestamp.now("UTC").tz_localize(None) - timedelta(hours=24)
    df = df[df["acq_date"] >= cutoff].reset_index(drop=True)

    removed = before - len(df)
    if removed > 0:
        print(f"  NRT cleanup: removed {removed} detections older than 24h")
        df.to_csv(NRT_FILE, index=False)
    else:
        print(f"  NRT: all {len(df)} detections within 24h — nothing to remove")


# ============================================================
# 4. RECOMPUTE GRID FEATURES (lightweight)
# ============================================================

def recompute_grid_features():
    """
    Only update TIME-SENSITIVE columns in grid_features.csv.
    Do NOT overwrite historical stats (total_detections, avg_frp, etc.)
    or risk scores — those come from the ML model.
    """
    if not HISTORICAL_FILE.exists() or not GRID_FEATURES_FILE.exists():
        return

    print("\n  Updating grid_features.csv (time-sensitive columns only)...")

    hist = pd.read_csv(HISTORICAL_FILE, usecols=["latitude", "longitude", "acq_date", "frp"], low_memory=False)
    hist["acq_date"] = pd.to_datetime(hist["acq_date"], errors="coerce")
    hist = hist.dropna(subset=["acq_date"])

    grid_size = 0.05
    hist["grid_lat"] = (np.floor(hist["latitude"] / grid_size) * grid_size).round(4)
    hist["grid_lon"] = (np.floor(hist["longitude"] / grid_size) * grid_size).round(4)
    hist["grid_id"] = hist["grid_lat"].map(lambda x: f"{x:.2f}") + "_" + hist["grid_lon"].map(lambda x: f"{x:.2f}")

    now = pd.Timestamp.now("UTC").tz_localize(None)
    hist["days_ago"] = (now - hist["acq_date"]).dt.days

    # ONLY update these 6 time-sensitive columns
    TIME_SENSITIVE_COLS = [
        "detections_30d", "detections_90d",
        "active_days_30d", "active_days_90d",
        "avg_frp_30d", "avg_frp_90d",
    ]

    stats = []
    for gid, grp in hist.groupby("grid_id"):
        det_30 = len(grp[grp["days_ago"] <= 30])
        det_90 = len(grp[grp["days_ago"] <= 90])
        active_30 = grp[grp["days_ago"] <= 30]["acq_date"].dt.date.nunique()
        active_90 = grp[grp["days_ago"] <= 90]["acq_date"].dt.date.nunique()
        avg_frp_30 = grp[grp["days_ago"] <= 30]["frp"].mean()
        avg_frp_90 = grp[grp["days_ago"] <= 90]["frp"].mean()
        stats.append({
            "grid_id": gid,
            "detections_30d": det_30,
            "detections_90d": det_90,
            "active_days_30d": active_30,
            "active_days_90d": active_90,
            "avg_frp_30d": round(avg_frp_30, 2) if pd.notna(avg_frp_30) else 0,
            "avg_frp_90d": round(avg_frp_90, 2) if pd.notna(avg_frp_90) else 0,
        })

    new_stats = pd.DataFrame(stats).set_index("grid_id")
    existing = pd.read_csv(GRID_FEATURES_FILE, low_memory=False)

    # Only overwrite time-sensitive columns — leave everything else untouched
    for col in TIME_SENSITIVE_COLS:
        if col in existing.columns and col in new_stats.columns:
            existing[col] = existing["grid_id"].map(new_stats[col]).fillna(existing[col])

    existing.to_csv(GRID_FEATURES_FILE, index=False)
    print(f"  grid_features.csv updated for {len(new_stats)} grids")


# ============================================================
# 5. RECOMPUTE RISK PREDICTIONS (lightweight)
# ============================================================

def recompute_risk_predictions():
    """
    ONLY update time-sensitive feature columns in risk_predictions.csv.
    NEVER recompute risk_score or risk_level — those come from the ML model
    (risk_model.py) and must NOT be overwritten by a naive formula.
    """
    if not GRID_FEATURES_FILE.exists() or not RISK_PRED_FILE.exists():
        return

    print("\n  Updating risk_predictions.csv (features only, preserving ML scores)...")

    gf = pd.read_csv(GRID_FEATURES_FILE, low_memory=False)
    rp = pd.read_csv(RISK_PRED_FILE, low_memory=False)

    # ONLY update these time-sensitive columns — risk_score/risk_level stay untouched
    SAFE_COLS = ["detections_30d", "detections_90d"]

    gf_lookup = gf.set_index("grid_id")
    for col in SAFE_COLS:
        if col in rp.columns and col in gf_lookup.columns:
            rp[col] = rp["grid_id"].map(gf_lookup[col]).fillna(rp[col])

    # Recompute recent_activity_ratio if the column exists
    if "detections_30d" in rp.columns and "detections_90d" in rp.columns:
        rp["recent_activity_ratio"] = (rp["detections_30d"] / rp["detections_90d"].clip(lower=1)).round(3)

    # DO NOT touch: risk_score, risk_level, risk_rank — those are from the ML model

    rp.to_csv(RISK_PRED_FILE, index=False)
    print(f"  risk_predictions.csv updated: {len(rp)} grids")


# ============================================================
# 6. RE-RUN ALERT ENGINE
# ============================================================

def rerun_alerts():
    """Re-run the alert engine to generate fresh alerts."""
    print("\n  Re-running alert engine...")

    # Import and run the alert engine
    sys.path.insert(0, str(BASE_DIR / "src"))
    try:
        from alert_engine import generate_alerts
        generate_alerts()
        print("  Alert engine completed.")
    except ImportError:
        # Fallback: run as subprocess
        import subprocess
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "alert_engine.py")],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            print("  Alert engine completed.")
        else:
            print(f"  Alert engine error: {result.stderr[:500]}")


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_full_update():
    """Run the complete automation pipeline."""
    print("=" * 60)
    print("THERMOSCOPE — AUTO UPDATE PIPELINE")
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    if not MAP_KEY:
        print("\n[ERROR] FIRMS_MAP_KEY not found — cannot fetch new data.")
        print("  Set FIRMS_MAP_KEY in .env file.")
        return

    # Step 1: Find gap
    last_date = get_last_historical_date()
    today = date.today()
    print(f"\n  Last historical date: {last_date}")
    print(f"  Today: {today}")

    # Step 2: Fetch recent data
    if last_date < today:
        new_data = fetch_recent_data(last_date + timedelta(days=1), today)
        merge_into_historical(new_data)
    else:
        print("\n  Historical data is already up to date.")

    # Step 3: Update daily activity
    update_daily_activity()

    # Step 4: Clean old NRT
    clean_old_nrt()

    # Step 5: Recompute grid features
    recompute_grid_features()

    # Step 6: Recompute risk predictions
    recompute_risk_predictions()

    # Step 7: Re-run alerts
    rerun_alerts()

    print("\n" + "=" * 60)
    print("AUTO UPDATE COMPLETE")
    print("=" * 60)


def run_nrt_only():
    """Fast mode: just clean old NRT detections."""
    print("NRT Cleanup Only")
    clean_old_nrt()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgniRakshak Auto Update")
    parser.add_argument("--nrt", action="store_true", help="NRT cleanup only (fast)")
    args = parser.parse_args()

    if args.nrt:
        run_nrt_only()
    else:
        run_full_update()
