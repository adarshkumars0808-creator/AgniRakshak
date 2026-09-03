import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from io import StringIO

import pandas as pd
import requests
from dotenv import load_dotenv


# ============================================================
# THERMOSCOPE — FIRMS NEAR REAL-TIME (NRT) FETCHER
#
# Fetches the most recent FIRMS NRT detections (last 24h)
# for the target region and saves them to a lightweight CSV
# that the dashboard can poll for live monitoring.
#
# Run this via a cron job / systemd timer, or call
# fetch_and_save() from dashboard.py on a schedule.
# ============================================================

load_dotenv()

MAP_KEY = os.getenv("FIRMS_MAP_KEY")

if not MAP_KEY:
    raise RuntimeError(
        "FIRMS_MAP_KEY not found in .env"
    )


# ============================================================
# TARGET REGION — same bounding box as fetch_firms.py
# ============================================================

WEST = 74.5
SOUTH = 23.5
EAST = 85.0
NORTH = 31.5

BBOX = f"{WEST},{SOUTH},{EAST},{NORTH}"


# ============================================================
# NRT SOURCES — only the NRT products
# ============================================================

NRT_SOURCES = [
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
]


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NRT_OUTPUT = OUTPUT_DIR / "nrt_detections.csv"
NRT_LATEST = OUTPUT_DIR / "nrt_latest_timestamp.txt"


# ============================================================
# NASA FIRMS MAP API — for NRT data
# ============================================================

MAP_API_URL = (
    "https://firms.modaps.eosdis.nasa.gov"
    "/api/area/csv"
)


# ============================================================
# SETTINGS
# ============================================================

REQUEST_TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 3


# ============================================================
# FETCH ONE NRT SOURCE (24h window)
# ============================================================

def fetch_nrt_source(source):
    """
    Fetch last 24h of NRT data for one satellite source.
    FIRMS Area API: day_range=1 fetches latest available data.
    """

    # Use day_range=2 to ensure we capture overnight passes
    day_range = 2

    url = (
        f"{MAP_API_URL}/"
        f"{MAP_KEY}/"
        f"{source}/"
        f"{BBOX}/"
        f"{day_range}"
    )

    print(
        f"[NRT] Fetching {source} "
        f"(last {day_range}d)..."
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                url,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code != 200:
                print(
                    f"  HTTP {response.status_code}: "
                    f"{response.text[:200]}"
                )
                response.raise_for_status()

            if not response.text.strip():
                print("  Empty response")
                return pd.DataFrame()

            df = pd.read_csv(
                StringIO(response.text)
            )

            if not df.empty:
                df["nrt_source"] = source
            df["fetched_at"] = (
                datetime.now(timezone.utc).isoformat()
            )

            print(
                f"  Received {len(df):,} NRT detections"
            )
            return df

        except Exception as exc:
            print(
                f"  Attempt {attempt}/{MAX_RETRIES} "
                f"failed: {exc}"
            )
            if attempt < MAX_RETRIES:
                import time
                time.sleep(RETRY_DELAY)

    print(f"  FAILED: {source}")
    return pd.DataFrame()


# ============================================================
# STANDARDIZE NRT COLUMNS
# ============================================================

def standardize_nrt(df):
    """
    Normalize NRT columns to match the dashboard schema.
    """

    df.columns = [
        str(c).strip().lower()
        for c in df.columns
    ]

    # Rename satellite -> sensor
    if "satellite" in df.columns:
        satellite_map = {
            "N": "SNPP",
            "1": "NOAA20",
            "2": "NOAA21",
            "SNPP": "SNPP",
            "NOAA-20": "NOAA20",
            "NOAA-21": "NOAA21",
        }
        df["sensor"] = (
            df["satellite"]
            .astype(str)
            .str.strip()
            .map(satellite_map)
            .fillna("UNKNOWN")
        )

    # Parse acquisition date
    if "acq_date" in df.columns:
        df["acq_date"] = pd.to_datetime(
            df["acq_date"], errors="coerce"
        )

    # Ensure numeric
    for col in [
        "latitude", "longitude",
        "frp", "brightness", "confidence",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col], errors="coerce"
            )

    # Confidence normalization
    if "confidence" in df.columns:
        text = (
            df["confidence"]
            .astype(str)
            .str.strip()
            .str.lower()
        )
        cat_map = {
            "l": 30, "n": 60, "h": 90,
            "low": 30, "nominal": 60, "high": 90,
        }
        cat_vals = text.map(cat_map)
        num_vals = pd.to_numeric(
            df["confidence"], errors="coerce"
        )
        df["confidence"] = num_vals.fillna(cat_vals)

    # Add age_hours — how many hours ago was detection
    if "acq_date" in df.columns:
        now = pd.Timestamp.now("UTC").tz_localize(None)
        df["age_hours"] = (
            (now - df["acq_date"])
            .dt.total_seconds() / 3600
        ).round(1)

    # Classify severity for alert engine
    df["nrt_severity"] = "normal"
    if "frp" in df.columns:
        df.loc[
            df["frp"] >= 50, "nrt_severity"
        ] = "high"
        df.loc[
            df["frp"] >= 100, "nrt_severity"
        ] = "critical"

    if "confidence" in df.columns:
        high_conf = df["confidence"] >= 80
        df.loc[
            high_conf & (df["nrt_severity"] == "normal"),
            "nrt_severity",
        ] = "elevated"

    return df


# ============================================================
# GRID CELL ASSIGNMENT
# ============================================================

def assign_grid_cells(df, grid_size=0.05):
    """
    Assign each NRT detection to a grid cell matching
    the existing risk_predictions.csv grid.
    """

    import numpy as np

    df["grid_lat"] = (
        np.floor(df["latitude"] / grid_size)
        * grid_size
    ).round(4)

    df["grid_lon"] = (
        np.floor(df["longitude"] / grid_size)
        * grid_size
    ).round(4)

    df["grid_id"] = (
        df["grid_lat"].map(lambda x: f"{x:.2f}")
        + "_"
        + df["grid_lon"].map(lambda x: f"{x:.2f}")
    )

    return df


# ============================================================
# FIRE TYPE CLASSIFICATION FOR NRT
# ============================================================

FIRE_TYPE_FILE = OUTPUT_DIR / "fire_type_predictions.csv"


def classify_nrt_fire_type(df):
    """
    Classify each NRT detection's fire type by:
    1. Looking up grid_id in historical fire_type_predictions.csv
    2. Falling back to heuristics (month + FRP) if no match
    """

    # Load historical fire type classifications
    ft_lookup = {}
    if FIRE_TYPE_FILE.exists():
        try:
            ft_df = pd.read_csv(
                FIRE_TYPE_FILE,
                usecols=[
                    "grid_id", "fire_type",
                    "fire_type_confidence",
                ],
                low_memory=False,
            )
            for _, row in ft_df.iterrows():
                gid = str(row["grid_id"]).strip()
                if gid:
                    ft_lookup[gid] = {
                        "fire_type": str(
                            row.get(
                                "fire_type",
                                "UNCLASSIFIED"
                            )
                        ).upper().strip(),
                        "fire_type_confidence": float(
                            row.get(
                                "fire_type_confidence", 0
                            )
                        ),
                    }
            print(
                f"  Loaded {len(ft_lookup):,} "
                f"historical fire type mappings"
            )
        except Exception as exc:
            print(f"  [WARN] Could not load fire types: {exc}")

    # Classify each detection
    fire_types = []
    fire_confidences = []
    fire_reasons = []

    for _, row in df.iterrows():
        gid = str(row.get("grid_id", "")).strip()
        frp = float(row.get("frp", 0) or 0)
        acq_date = row.get("acq_date")

        # Try historical lookup first
        if gid in ft_lookup:
            info = ft_lookup[gid]
            fire_types.append(info["fire_type"])
            fire_confidences.append(
                info["fire_type_confidence"]
            )
            fire_reasons.append(
                f"Matched historical grid {gid}"
            )
            continue

        # Heuristic fallback based on month + FRP
        month = None
        if (
            hasattr(acq_date, "month")
            and acq_date is not None
        ):
            month = acq_date.month

        # Industrial: very high FRP (>80 MW)
        if frp >= 80:
            fire_types.append("INDUSTRIAL_PERSISTENT")
            fire_confidences.append(0.45)
            fire_reasons.append(
                f"High FRP ({frp:.0f} MW) — likely "
                f"industrial source"
            )
            continue

        # Agricultural: stubble burning months
        # (Apr-May, Oct-Nov) with moderate FRP
        if month in [4, 5, 10, 11] and frp >= 10:
            fire_types.append("AGRICULTURAL_BURNING")
            fire_confidences.append(0.40)
            fire_reasons.append(
                f"Detected in month {month} "
                f"(stubble season), FRP {frp:.0f} MW"
            )
            continue

        # Forest: dry season months
        # (Mar-Jun) with low-medium FRP
        if month in [3, 4, 5, 6] and frp < 80:
            fire_types.append("FOREST_WILDFIRE")
            fire_confidences.append(0.35)
            fire_reasons.append(
                f"Dry season month {month}, "
                f"FRP {frp:.0f} MW"
            )
            continue

        # Default
        fire_types.append("UNCLASSIFIED")
        fire_confidences.append(0.0)
        fire_reasons.append(
            "No historical match or heuristic rule"
        )

    df["fire_type"] = fire_types
    df["fire_type_confidence"] = fire_confidences
    df["fire_type_reason"] = fire_reasons

    return df


# ============================================================
# MAIN FETCH + SAVE
# ============================================================

def fetch_and_save():
    """
    Fetch NRT data from all sources, merge, deduplicate,
    and save. Returns the DataFrame for direct use.
    """

    print()
    print("=" * 60)
    print("THERMOSCOPE — FIRMS NRT LIVE FETCH")
    print(
        f"Time: "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    print("=" * 60)

    frames = []

    for source in NRT_SOURCES:
        try:
            df = fetch_nrt_source(source)
            if not df.empty:
                frames.append(df)
        except Exception as exc:
            print(f"[ERROR] {source}: {exc}")

    if not frames:
        print()
        print("No NRT data received from any source.")
        return pd.DataFrame()

    merged = pd.concat(frames, ignore_index=True)

    print()
    print(f"Merged NRT rows: {len(merged):,}")

    # Standardize
    merged = standardize_nrt(merged)
    merged = assign_grid_cells(merged)

    # Classify fire type for each detection
    merged = classify_nrt_fire_type(merged)

    # Remove invalid
    merged = merged.dropna(
        subset=["latitude", "longitude", "acq_date"]
    )
    merged = merged[
        merged["latitude"].between(-90, 90)
        & merged["longitude"].between(-180, 180)
    ]

    # Deduplicate
    dedup_cols = [
        "latitude", "longitude",
        "acq_date", "acq_time",
        "satellite", "instrument", "frp",
    ]
    dedup_cols = [
        c for c in dedup_cols if c in merged.columns
    ]
    before = len(merged)
    merged = merged.drop_duplicates(
        subset=dedup_cols
    ).reset_index(drop=True)

    print(
        f"After dedup: {len(merged):,} "
        f"(removed {before - len(merged):,})"
    )

    # Sort
    merged = merged.sort_values(
        "acq_date", ascending=False
    ).reset_index(drop=True)

    # Save
    merged.to_csv(NRT_OUTPUT, index=False)

    # Save timestamp
    NRT_LATEST.write_text(
        datetime.utcnow().isoformat()
    )

    # Summary
    print()
    print("=" * 60)
    print("NRT FETCH COMPLETE")
    print("=" * 60)

    print(f"Detections: {len(merged):,}")
    print(f"Unique grids: {merged['grid_id'].nunique():,}")

    if "nrt_severity" in merged.columns:
        print()
        print("Severity distribution:")
        print(
            merged["nrt_severity"]
            .value_counts()
            .to_string()
        )

    if "sensor" in merged.columns:
        print()
        print("Sensor distribution:")
        print(
            merged["sensor"]
            .value_counts()
            .to_string()
        )

    if "fire_type" in merged.columns:
        print()
        print("Fire type distribution:")
        print(
            merged["fire_type"]
            .value_counts()
            .to_string()
        )

    print()
    print(f"Saved: {NRT_OUTPUT}")

    return merged


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    fetch_and_save()
