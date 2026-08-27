import os
from io import StringIO

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv


# ============================================================
# THERMOSCOPE - LIVE FIRE RISK PIPELINE
# SIH NASA FIRMS DATA
# ============================================================

load_dotenv()

print("=" * 70)
print("THERMOSCOPE - LIVE FIRE RISK PIPELINE")
print("=" * 70)


# ============================================================
# CONFIGURATION
# ============================================================

MAP_KEY = os.getenv("FIRMS_MAP_KEY")

if not MAP_KEY:
    print("\nERROR: FIRMS_MAP_KEY not found in .env")
    print("Create .env in project root:")
    print("FIRMS_MAP_KEY=YOUR_NASA_FIRMS_MAP_KEY")
    raise SystemExit(1)

# Delhi NCR bounding box: west, south, east, north.
# 77.6 is intentional because current FIRMS detections include
# a point around longitude 77.57.
DELHI_BBOX = "76.8,28.3,77.6,28.9"

FIRMS_SOURCES = [
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "VIIRS_SNPP_NRT",
]

DAY_RANGE = 5
GRID_SIZE = 0.01


# ============================================================
# OUTPUT FILES
# ============================================================

LIVE_FIRMS_FILE = "data/delhi_firms_live.csv"
LIVE_GRID_FILE = "data/delhi_grid_live.csv"
LIVE_FEATURES_FILE = "data/delhi_risk_features_live.csv"
LIVE_PREDICTIONS_FILE = "data/delhi_risk_predictions_live.csv"

os.makedirs("data", exist_ok=True)


# ============================================================
# 1. FETCH LIVE NASA FIRMS DATA
# ============================================================

def fetch_live_firms():

    print("\n[1/5] Fetching live NASA FIRMS data...")

    all_frames = []

    for source in FIRMS_SOURCES:

        print("\n" + "-" * 70)
        print(f"Fetching NASA FIRMS source: {source}")
        print("-" * 70)

        url = (
            "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            f"{MAP_KEY}/{source}/{DELHI_BBOX}/{DAY_RANGE}"
        )

        try:
            response = requests.get(url, timeout=30)
        except requests.RequestException as e:
            print(f"ERROR connecting to NASA FIRMS for {source}:")
            print(e)
            continue

        print("HTTP Status:", response.status_code)

        if response.status_code != 200:
            print(f"ERROR: FIRMS request failed for {source}")
            print(response.text[:500])
            continue

        try:
            source_df = pd.read_csv(StringIO(response.text))
        except Exception as e:
            print(f"ERROR reading FIRMS response for {source}:")
            print(e)
            continue

        if source_df.empty:
            print(f"No observations returned for {source}.")
            continue

        source_df["firms_source"] = source

        print(
            f"Observations received from {source}:",
            len(source_df)
        )

        all_frames.append(source_df)

    print("\n" + "=" * 70)
    print("COMBINED LIVE FIRMS DATA")
    print("=" * 70)

    if not all_frames:
        print("\nWARNING: No live FIRMS observations returned.")
        empty = pd.DataFrame()
        empty.to_csv(LIVE_FIRMS_FILE, index=False)
        return empty

    df = pd.concat(all_frames, ignore_index=True)

    required = ["latitude", "longitude", "acq_date"]
    missing = [col for col in required if col not in df.columns]

    if missing:
        print("\nERROR: Required FIRMS columns missing:")
        print(missing)
        raise SystemExit(1)

    if "satellite" not in df.columns:
        df["satellite"] = "UNKNOWN"

    if "frp" not in df.columns:
        df["frp"] = 0.0

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["frp"] = pd.to_numeric(df["frp"], errors="coerce").fillna(0.0)
    df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce")
    df["satellite"] = df["satellite"].fillna("UNKNOWN").astype(str)

    before = len(df)
    df = df.dropna(subset=["latitude", "longitude", "acq_date"]).copy()
    removed = before - len(df)

    if removed > 0:
        print(f"Removed {removed} rows with invalid coordinates/date.")

    # Remove exact duplicates only. Do NOT drop detections merely because
    # they are close to one another; spatial aggregation handles that later.
    duplicate_columns = [
        "latitude", "longitude", "acq_date",
        "satellite", "firms_source"
    ]
    duplicate_columns = [c for c in duplicate_columns if c in df.columns]

    before_duplicates = len(df)
    df = df.drop_duplicates(subset=duplicate_columns).copy()
    duplicates_removed = before_duplicates - len(df)

    if duplicates_removed > 0:
        print("Exact duplicate FIRMS records removed:", duplicates_removed)

    df = df.sort_values(
        ["acq_date", "latitude", "longitude"]
    ).reset_index(drop=True)

    df.to_csv(LIVE_FIRMS_FILE, index=False)

    print("\nTotal live observations:", len(df))

    print("\nObservations by NASA FIRMS source:")
    print(df["firms_source"].value_counts().to_string())

    print("\nAvailable acquisition dates:")
    print(
        df["acq_date"]
        .dt.strftime("%Y-%m-%d")
        .drop_duplicates()
        .sort_values()
        .to_string(index=False)
    )

    print(
        "\nLatest FIRMS acquisition date:",
        df["acq_date"].max().strftime("%Y-%m-%d")
    )

    print("\nSatellite field values:")
    print(df["satellite"].value_counts().to_string())

    print("\nSaved:")
    print(LIVE_FIRMS_FILE)

    return df


# ============================================================
# 2. CLEAN LIVE DATA
# ============================================================

def clean_data(df):

    print("\n[2/5] Cleaning live FIRMS data...")

    if df.empty:
        return df

    df = df.copy()

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["frp"] = pd.to_numeric(df["frp"], errors="coerce").fillna(0.0)
    df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce")
    df["satellite"] = df["satellite"].fillna("UNKNOWN").astype(str)

    before = len(df)
    df = df.dropna(
        subset=["latitude", "longitude", "acq_date"]
    ).copy()

    print("Valid observations:", len(df))
    print("Observations removed:", before - len(df))

    # Safety check matching the configured bbox.
    inside = (
        (df["longitude"] >= 76.8)
        & (df["longitude"] <= 77.6)
        & (df["latitude"] >= 28.3)
        & (df["latitude"] <= 28.9)
    )

    outside_count = int((~inside).sum())

    if outside_count > 0:
        print(
            "WARNING:",
            outside_count,
            "observations outside configured Delhi NCR bbox."
        )
        df = df.loc[inside].copy()

    print("Final valid observations:", len(df))

    return df.reset_index(drop=True)


# ============================================================
# 3. CREATE SPATIAL GRID
# ============================================================

def create_grid(df):

    print("\n[3/5] Creating spatial grid...")

    if df.empty:
        empty = pd.DataFrame(
            columns=[
                "grid_id", "grid_lat", "grid_lon",
                "detection_count", "active_days",
                "avg_frp", "max_frp", "min_frp",
                "satellite_count", "first_detection",
                "last_detection", "repeat_score"
            ]
        )
        empty.to_csv(LIVE_GRID_FILE, index=False)
        return empty

    df = df.copy()

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["frp"] = pd.to_numeric(df["frp"], errors="coerce").fillna(0.0)

    before = len(df)
    df = df.dropna(subset=["latitude", "longitude"]).copy()

    print("Valid coordinate observations:", len(df), "/", before)

    # 0.01 degree spatial grid.
    df["grid_lat"] = (
        np.floor(df["latitude"] / GRID_SIZE) * GRID_SIZE
    ).round(2)

    df["grid_lon"] = (
        np.floor(df["longitude"] / GRID_SIZE) * GRID_SIZE
    ).round(2)

    # Stable IDs avoid values such as 28.7 vs 28.70 being treated
    # differently by downstream code.
    df["grid_id"] = (
        df["grid_lat"].map(lambda x: f"{x:.2f}")
        + "_"
        + df["grid_lon"].map(lambda x: f"{x:.2f}")
    )

    print("\nDetection -> Grid mapping:")
    print(
        df[
            [
                "latitude", "longitude",
                "grid_lat", "grid_lon", "grid_id"
            ]
        ].to_string(index=False)
    )

    grid = (
        df.groupby(
            "grid_id",
            as_index=False,
            dropna=False
        )
        .agg(
            grid_lat=("grid_lat", "first"),
            grid_lon=("grid_lon", "first"),
            detection_count=("latitude", "count"),
            active_days=("acq_date", "nunique"),
            avg_frp=("frp", "mean"),
            max_frp=("frp", "max"),
            min_frp=("frp", "min"),
            satellite_count=("satellite", "nunique"),
            first_detection=("acq_date", "min"),
            last_detection=("acq_date", "max")
        )
    )

    grid["repeat_score"] = (
        grid["detection_count"]
        / grid["active_days"].clip(lower=1)
    )

    grid = grid.sort_values(
        ["grid_lat", "grid_lon"]
    ).reset_index(drop=True)

    print("\nGrid summary:")
    print(
        grid[
            [
                "grid_id", "grid_lat", "grid_lon",
                "detection_count"
            ]
        ].to_string(index=False)
    )

    total_detections = len(df)
    total_grid_detections = int(grid["detection_count"].sum())

    print("\nTotal FIRMS detections:", total_detections)
    print("Total unique grid cells:", len(grid))
    print("Detections represented in grid:", total_grid_detections)

    if total_grid_detections != total_detections:
        print("\nWARNING: Grid aggregation lost observations!")
    else:
        print("\nOK: All FIRMS detections represented in grid.")

    grid.to_csv(LIVE_GRID_FILE, index=False)

    print("\nSaved:")
    print(LIVE_GRID_FILE)

    return grid


# ============================================================
# 4. ENGINEER LIVE RISK FEATURES
# ============================================================

def create_risk_features(grid):

    print("\n[4/5] Creating live risk features...")

    if grid.empty:
        empty = grid.copy()
        empty.to_csv(LIVE_FEATURES_FILE, index=False)
        return empty

    grid = grid.copy()

    # Satellite information.
    grid["satellite_source_count"] = (
        pd.to_numeric(
            grid["satellite_count"],
            errors="coerce"
        ).fillna(0)
    )

    grid["satellite_agreement"] = (
        grid["satellite_source_count"] >= 2
    ).astype(int)

    grid["satellite_score"] = grid["satellite_agreement"].astype(float)

    # Recurrence.
    max_active_days = grid["active_days"].max()

    if pd.notna(max_active_days) and max_active_days > 0:
        grid["recurrence_score"] = (
            grid["active_days"] / max_active_days
        )
    else:
        grid["recurrence_score"] = 0.0

    grid["recurrence_score"] = grid["recurrence_score"].clip(0, 1)

    # FRP intensity.
    max_frp = grid["max_frp"].max()

    if pd.notna(max_frp) and max_frp > 0:
        grid["frp_intensity"] = grid["max_frp"] / max_frp
    else:
        grid["frp_intensity"] = 0.0

    grid["frp_intensity"] = grid["frp_intensity"].clip(0, 1)

    # Repeat detection score.
    max_detection_count = grid["detection_count"].max()

    if pd.notna(max_detection_count) and max_detection_count > 0:
        grid["repeat_detection_score"] = (
            grid["detection_count"] / max_detection_count
        )
    else:
        grid["repeat_detection_score"] = 0.0

    grid["repeat_detection_score"] = (
        grid["repeat_detection_score"].clip(0, 1)
    )

    # Explainable activity score.
    grid["activity_score"] = (
        0.45 * grid["recurrence_score"]
        + 0.35 * grid["frp_intensity"]
        + 0.20 * grid["repeat_detection_score"]
    ).clip(0, 1)

    def classify_activity(score):
        if score >= 0.75:
            return "HIGH"
        elif score >= 0.45:
            return "MEDIUM"
        return "LOW"

    grid["activity_category"] = grid["activity_score"].apply(
        classify_activity
    )

    grid = grid.sort_values(
        "activity_score",
        ascending=False
    ).reset_index(drop=True)

    grid.to_csv(LIVE_FEATURES_FILE, index=False)

    print("Live feature cells:", len(grid))
    print("\nActivity categories:")
    print(grid["activity_category"].value_counts().to_string())
    print("\nSaved:")
    print(LIVE_FEATURES_FILE)

    return grid


# ============================================================
# 5. GENERATE LIVE RISK PREDICTIONS
# ============================================================

def generate_predictions(features):

    print("\n[5/5] Generating live risk predictions...")

    if features.empty:
        empty = features.copy()
        empty.to_csv(LIVE_PREDICTIONS_FILE, index=False)
        return empty

    df = features.copy()

    # Keep the risk score explainable and consistent with activity score.
    df["risk_score"] = (
        0.45 * df["recurrence_score"]
        + 0.35 * df["frp_intensity"]
        + 0.20 * df["repeat_detection_score"]
    ).clip(0, 1)

    df["risk_percentage"] = (
        df["risk_score"] * 100
    ).round(2)

    def classify_risk(score):
        if score >= 0.75:
            return "HIGH"
        elif score >= 0.45:
            return "MEDIUM"
        return "LOW"

    df["risk_category"] = df["risk_score"].apply(classify_risk)

    df["risk_priority"] = (
        df["risk_score"]
        .rank(ascending=False, method="dense")
        .astype(int)
    )

    df = df.sort_values(
        "risk_score",
        ascending=False
    ).reset_index(drop=True)

    df.to_csv(LIVE_PREDICTIONS_FILE, index=False)

    print("\nLive risk results:")

    display_columns = [
        "grid_id", "grid_lat", "grid_lon",
        "detection_count", "risk_score",
        "risk_percentage", "risk_category",
        "risk_priority"
    ]

    display_columns = [
        col for col in display_columns if col in df.columns
    ]

    print(df[display_columns].to_string(index=False))

    print("\nRisk categories:")
    print(df["risk_category"].value_counts().to_string())

    print("\nSaved:")
    print(LIVE_PREDICTIONS_FILE)

    return df


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():

    live_df = fetch_live_firms()
    live_df = clean_data(live_df)
    grid = create_grid(live_df)
    features = create_risk_features(grid)
    predictions = generate_predictions(features)

    print("\n" + "=" * 70)
    print("THERMOSCOPE LIVE PIPELINE COMPLETE")
    print("=" * 70)

    print("\nGenerated files:")
    print("1.", LIVE_FIRMS_FILE)
    print("2.", LIVE_GRID_FILE)
    print("3.", LIVE_FEATURES_FILE)
    print("4.", LIVE_PREDICTIONS_FILE)

    print("\nLive observations:", len(live_df))
    print("Live grid cells:", len(grid))
    print("Live predictions:", len(predictions))

    # Final detection/grid consistency check.
    if not live_df.empty and not grid.empty:

        represented = int(grid["detection_count"].sum())

        if represented == len(live_df):
            print("\nCONSISTENCY CHECK: PASS")
            print(
                f"{len(live_df)} FIRMS detections represented "
                f"by {len(grid)} grid cells."
            )
        else:
            print("\nCONSISTENCY CHECK: FAILED")
            print("FIRMS detections:", len(live_df))
            print("Grid represented detections:", represented)

    print("\n" + "=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
