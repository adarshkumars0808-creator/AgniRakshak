"""
auto_update.py — Automatic data pipeline for AgniRakshak.

Runs on a schedule (GitHub Actions cron, every 6 hours). Performs:
1. Fetch recent FIRMS detections since the last update anchor
2. Append them to the rolling detection store (recent_detections.csv, ~95 days)
3. Update daily_activity.csv incrementally
4. Clean NRT detections older than 24 hours
5. Recompute grid features for the rolling window (30d/90d columns only)
6. Recompute risk predictions (time-sensitive feature columns only)
7. Re-run the alert engine

IMPORTANT: the 291 MB full-history file (firms_clean_merged.csv, Git LFS)
is NOT touched by this script. It stays on local machines and is used only
for one-time model builds (risk_model.py, classify_fire_type.py,
forecast_engine.py). The daily automation works off the small committed
rolling store instead — this keeps CI runs fast, git pushes small, and
avoids exhausting the GitHub LFS bandwidth quota.

Usage:
    python src/auto_update.py                       # full pipeline
    python src/auto_update.py --nrt                 # NRT cleanup only (fast)
    python src/auto_update.py --bootstrap           # seed rolling store once (FIRMS API)
    python src/auto_update.py --bootstrap --from-csv <path>  # seed from a full-history CSV
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

# Full-history archive (Git LFS) — read-only, optional. Not used by CI.
HISTORICAL_FILE = PROC_DIR / "firms_clean_merged.csv"

# Rolling detection store — the small committed file the automation works from.
RECENT_FILE = PROC_DIR / "recent_detections.csv"
ANCHOR_FILE = PROC_DIR / "update_anchor.txt"

DAILY_FILE = PROC_DIR / "daily_activity.csv"
NRT_FILE = PROC_DIR / "nrt_detections.csv"
NRT_LATEST = PROC_DIR / "nrt_latest_timestamp.txt"
GRID_FEATURES_FILE = PROC_DIR / "grid_features.csv"
RISK_PRED_FILE = PROC_DIR / "risk_predictions.csv"
FIRE_TYPE_FILE = PROC_DIR / "fire_type_predictions.csv"
ALERTS_FILE = PROC_DIR / "alerts_log.csv"

# How many days of raw detections the rolling store keeps.
# Must comfortably cover the 90-day feature windows (95 >= 90 + margin).
ROLLING_DAYS = 95

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

# NRT = near-real-time products (~2-4h latency). Verified 2026-09:
# the SP (standard-processing) products no longer serve data newer than
# ~April 2026 via the Area API, so the rolling store must use the three
# NRT products, which retain a multi-month archive.
SOURCES = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]

REQUEST_TIMEOUT = 120
MAX_RETRIES = 3
RETRY_DELAY = 5
CHUNK_DAYS = 5


# ============================================================
# ANCHOR (last fully-updated date)
# ============================================================

def load_anchor():
    """Return the last date present in the rolling store, or None."""
    if not ANCHOR_FILE.exists():
        return None
    try:
        return date.fromisoformat(ANCHOR_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def save_anchor(d):
    ANCHOR_FILE.write_text(d.isoformat())


def is_lfs_pointer(path):
    """Detect a Git LFS pointer file (instead of the real CSV)."""
    try:
        with open(path) as f:
            return f.read(80).lstrip().startswith("version https://git-lfs")
    except OSError:
        return False


# ============================================================
# 1. FETCH RECENT FIRMS DATA (delta since anchor)
# ============================================================

def fetch_firms_chunk(source, start_date, end_date):
    """
    Fetch one chunk of FIRMS data.

    Area API semantics (verified): day_range days starting at start_date,
    i.e. the returned window is [start_date, start_date + day_range - 1].

    Returns (df, ok) where ok=True means the request succeeded (HTTP 200),
    even if the response contained no detections.
    """
    day_range = (end_date - start_date).days + 1
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{source}/{BBOX}/{day_range}/{start_date.isoformat()}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                print(f"    HTTP {resp.status_code} for {source} {start_date}→{end_date}")
                continue
            if not resp.text.strip():
                return pd.DataFrame(), True
            df = pd.read_csv(StringIO(resp.text))
            if not df.empty:
                df["source"] = source
            return df, True
        except Exception as e:
            print(f"    Attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    return pd.DataFrame(), False


def fetch_delta(start_date, end_date):
    """Fetch FIRMS data between two dates (inclusive). Returns merged DataFrame."""
    if start_date > end_date:
        print("  No gap to fill — store is up to date.")
        return pd.DataFrame()

    print(f"\n  Fetching FIRMS data: {start_date} → {end_date}")
    all_frames = []
    furthest_ok = None

    for source in SOURCES:
        source_start = start_date
        if source_start > end_date:
            continue

        current = source_start
        while current <= end_date:
            chunk_end = min(current + timedelta(days=CHUNK_DAYS - 1), end_date)
            df, ok = fetch_firms_chunk(source, current, chunk_end)
            if ok:
                furthest_ok = chunk_end
                if not df.empty:
                    all_frames.append(df)
                    print(f"    {source}: {current}→{chunk_end} = {len(df):,} detections")
            current = chunk_end + timedelta(days=1)
            time.sleep(0.5)  # Rate limit courtesy

    if furthest_ok is not None:
        print(f"  Data available through: {furthest_ok}")

    if not all_frames:
        print("  No new detections fetched.")
        return pd.DataFrame()

    merged = pd.concat(all_frames, ignore_index=True)
    print(f"\n  Total new detections: {len(merged):,}")
    return merged


# ============================================================
# 2. ROLLING STORE (append / dedupe / prune)
# ============================================================

def append_to_store(new_data):
    """
    Append new detections to the rolling store, deduplicate, prune to
    ROLLING_DAYS, and advance the anchor to the newest date present.
    """
    if new_data is None or new_data.empty:
        return

    if RECENT_FILE.exists():
        existing = pd.read_csv(RECENT_FILE, low_memory=False)
        combined = pd.concat([existing, new_data], ignore_index=True)
    else:
        combined = new_data.copy()

    # Normalize
    combined.columns = [str(c).strip().lower() for c in combined.columns]
    if "acq_date" in combined.columns:
        combined["acq_date"] = pd.to_datetime(combined["acq_date"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Deduplicate on key columns
    dedup_cols = ["latitude", "longitude", "acq_date", "acq_time", "satellite", "frp"]
    dedup_cols = [c for c in dedup_cols if c in combined.columns]
    before = len(combined)
    combined = combined.drop_duplicates(subset=dedup_cols).reset_index(drop=True)
    removed = before - len(combined)
    if removed > 0:
        print(f"  Dedup removed {removed:,} duplicate rows")

    # Prune to the rolling window
    cutoff = (pd.Timestamp.now("UTC").tz_localize(None) - pd.Timedelta(days=ROLLING_DAYS)).strftime("%Y-%m-%d")
    combined["_d"] = pd.to_datetime(combined["acq_date"], errors="coerce")
    combined = combined[combined["_d"] >= cutoff].drop(columns=["_d"]).reset_index(drop=True)

    combined = combined.sort_values("acq_date").reset_index(drop=True)
    combined.to_csv(RECENT_FILE, index=False)

    max_date = combined["acq_date"].max() if not combined.empty else None
    if pd.notna(max_date):
        save_anchor(pd.Timestamp(max_date).date())
        print(f"  Rolling store: {len(combined):,} detections ({combined['acq_date'].min()} → {max_date})")
        print(f"  Update anchor: {load_anchor()}")
    else:
        print("  Rolling store is empty after update.")


# ============================================================
# 3. UPDATE DAILY ACTIVITY (incremental)
# ============================================================

def update_daily_activity():
    """Refresh the rolling-window days in daily_activity.csv from the store."""
    if not RECENT_FILE.exists():
        print("  No rolling store — skipping daily activity update.")
        return

    print("\n  Updating daily_activity.csv (rolling window)...")
    df = pd.read_csv(RECENT_FILE, usecols=["acq_date", "frp"], low_memory=False)
    df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce")
    df = df.dropna(subset=["acq_date"])
    df["date"] = df["acq_date"].dt.strftime("%Y-%m-%d")

    daily = df.groupby("date").agg(
        detections=("frp", "count"),
        avg_frp=("frp", "mean"),
    ).reset_index()
    daily = daily.sort_values("date").reset_index(drop=True)

    if DAILY_FILE.exists():
        existing = pd.read_csv(DAILY_FILE, low_memory=False)
        existing["date"] = existing["date"].astype(str)
        existing = existing[~existing["date"].isin(daily["date"])]
        combined = pd.concat([existing, daily], ignore_index=True).sort_values("date").reset_index(drop=True)
    else:
        combined = daily

    combined.to_csv(DAILY_FILE, index=False)
    print(f"  daily_activity.csv: {len(combined)} days ({combined['date'].min()} → {combined['date'].max()})")


# ============================================================
# 4. CLEAN NRT DETECTIONS > 24h OLD
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
# 5. RECOMPUTE GRID FEATURES (lightweight, from rolling store)
# ============================================================

def recompute_grid_features():
    """
    Only update TIME-SENSITIVE columns in grid_features.csv.
    Do NOT overwrite historical stats (total_detections, avg_frp, etc.)
    or risk scores — those come from the ML model.

    Grids with no detections in the rolling window get 0 for the
    time-sensitive columns (previously their stale values lingered).
    """
    if not RECENT_FILE.exists() or not GRID_FEATURES_FILE.exists():
        print("  Missing rolling store or grid_features.csv — skipping.")
        return

    print("\n  Updating grid_features.csv (time-sensitive columns only)...")

    hist = pd.read_csv(RECENT_FILE, usecols=["latitude", "longitude", "acq_date", "frp"], low_memory=False)
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
    existing["grid_id"] = existing["grid_id"].astype(str)

    # Only overwrite time-sensitive columns — leave everything else untouched
    for col in TIME_SENSITIVE_COLS:
        if col in existing.columns and col in new_stats.columns:
            existing[col] = existing["grid_id"].map(new_stats[col]).fillna(existing[col])

    # Grids with zero detections in the rolling window → 0 (no stale values)
    missing = ~existing["grid_id"].isin(new_stats.index)
    if missing.any():
        cols = [c for c in TIME_SENSITIVE_COLS if c in existing.columns]
        existing.loc[missing, cols] = 0
        print(f"  Zeroed time-sensitive cols for {int(missing.sum()):,} inactive grids")

    existing.to_csv(GRID_FEATURES_FILE, index=False)
    print(f"  grid_features.csv updated for {len(new_stats)} active grids")


# ============================================================
# 6. RECOMPUTE RISK PREDICTIONS (lightweight)
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
    rp["grid_id"] = rp["grid_id"].astype(str)
    gf["grid_id"] = gf["grid_id"].astype(str)

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
# 7. RE-RUN ALERT ENGINE
# ============================================================

def rerun_alerts():
    """Re-run the alert engine to generate fresh alerts."""
    print("\n  Re-running alert engine...")

    # Import and run the alert engine directly
    sys.path.insert(0, str(BASE_DIR / "src"))
    try:
        from alert_engine import run_alert_engine
        run_alert_engine()
        print("  Alert engine completed.")
    except Exception as exc:
        print(f"  Alert engine error: {exc}")


# ============================================================
# BOOTSTRAP (one-time seeding of the rolling store)
# ============================================================

def bootstrap_from_csv(csv_path):
    """Extract the last ROLLING_DAYS of detections from a full-history CSV."""
    print(f"\n  Bootstrapping from CSV: {csv_path}")
    header = pd.read_csv(csv_path, nrows=0, low_memory=False).columns
    cols = [c for c in ["latitude", "longitude", "acq_date", "acq_time", "frp", "satellite", "instrument"] if c in header]

    cutoff = (pd.Timestamp.now("UTC").tz_localize(None) - pd.Timedelta(days=ROLLING_DAYS)).strftime("%Y-%m-%d")
    chunks = []
    for i, chunk in enumerate(pd.read_csv(csv_path, usecols=cols, chunksize=500_000, low_memory=False), 1):
        chunk["acq_date"] = pd.to_datetime(chunk["acq_date"], errors="coerce")
        chunk = chunk[chunk["acq_date"] >= cutoff]
        if not chunk.empty:
            chunks.append(chunk)
        print(f"    [chunk {i}] kept {len(chunk):,} rows")

    if not chunks:
        print("  No detections within the rolling window found in file.")
        return False

    df = pd.concat(chunks, ignore_index=True)
    df["source"] = "HISTORICAL"
    append_to_store(df)
    return True


def bootstrap_from_api():
    """Fetch the last ROLLING_DAYS directly from the FIRMS API (self-contained)."""
    print(f"\n  Bootstrapping last {ROLLING_DAYS} days from FIRMS API...")
    if not MAP_KEY:
        print("  [ERROR] FIRMS_MAP_KEY not found — cannot bootstrap from API.")
        return False

    start = date.today() - timedelta(days=ROLLING_DAYS)
    end = date.today()
    df = fetch_delta(start, end)

    if df.empty:
        print("  Nothing fetched — cannot bootstrap. Check the API key and try again.")
        return False

    append_to_store(df)
    return True


def run_bootstrap(from_csv=None):
    print("=" * 60)
    print("THERMOSCOPE — BOOTSTRAP ROLLING STORE")
    print("=" * 60)

    ok = False
    if from_csv:
        ok = bootstrap_from_csv(from_csv)
    elif HISTORICAL_FILE.exists() and not is_lfs_pointer(HISTORICAL_FILE):
        ok = bootstrap_from_csv(HISTORICAL_FILE)
    else:
        print("\n  Full-history CSV is missing or is a Git LFS pointer.")
        print("  Falling back to fetching the last 95 days directly from the FIRMS API.")
        ok = bootstrap_from_api()

    if ok:
        print("\n" + "=" * 60)
        print("BOOTSTRAP COMPLETE")
        print("=" * 60)
        anchor = load_anchor()
        print(f"  Rolling store: {RECENT_FILE}")
        if anchor:
            print(f"  Anchor: {anchor} (next run fetches from {anchor + timedelta(days=1)})")
        else:
            print("  Anchor: not set — bootstrap did not produce data.")
    else:
        print("\n  BOOTSTRAP FAILED — see messages above.")
    return ok


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
        print("  Set FIRMS_MAP_KEY in .env file or repository secret.")
        return

    # Step 1: Read anchor
    anchor = load_anchor()
    today = date.today()
    if anchor is None:
        print("\n[ERROR] No update anchor found. Seed the rolling store once:")
        print("  python src/auto_update.py --bootstrap")
        return
    print(f"\n  Last update anchor: {anchor}")
    print(f"  Today: {today}")

    # Step 2: Fetch delta and append to rolling store
    if anchor < today:
        new_data = fetch_delta(anchor + timedelta(days=1), today)
        append_to_store(new_data)
    else:
        print("\n  Rolling store is already up to date.")

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
    parser.add_argument("--bootstrap", action="store_true", help="Seed the rolling store once")
    parser.add_argument("--from-csv", metavar="PATH", help="Bootstrap from a full-history FIRMS CSV")
    args = parser.parse_args()

    if args.bootstrap or args.from_csv:
        run_bootstrap(args.from_csv)
    elif args.nrt:
        run_nrt_only()
    else:
        run_full_update()