import os
from io import StringIO

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv


# ============================================================
# THERMOSCOPE - LIVE FIRE RISK PIPELINE
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
    print("\nCreate a .env file in the project root containing:")
    print("FIRMS_MAP_KEY=YOUR_NASA_FIRMS_MAP_KEY")
    raise SystemExit(1)


# Delhi NCR bounding box
# west, south, east, north
DELHI_BBOX = "76.8,28.4,77.4,28.9"

# NASA FIRMS source
SOURCE = "VIIRS_NOAA20_NRT"

# Number of days requested
DAY_RANGE = 5

GRID_SIZE = 0.01


# Output files
LIVE_FIRMS_FILE = "data/delhi_firms_live.csv"
LIVE_GRID_FILE = "data/delhi_grid_live.csv"
LIVE_FEATURES_FILE = "data/delhi_risk_features_live.csv"
LIVE_PREDICTIONS_FILE = "data/delhi_risk_predictions_live.csv"


# ============================================================
# 1. FETCH LIVE NASA FIRMS DATA
# ============================================================

def fetch_live_firms():

    print("\n[1/5] Fetching live NASA FIRMS data...")

    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{MAP_KEY}/{SOURCE}/{DELHI_BBOX}/{DAY_RANGE}"
    )

    try:

        response = requests.get(
            url,
            timeout=30
        )

    except requests.RequestException as e:

        print("\nERROR connecting to NASA FIRMS:")
        print(e)

        raise SystemExit(1)

    print("HTTP Status:", response.status_code)

    if response.status_code != 200:

        print("\nERROR: NASA FIRMS API request failed.")
        print(response.text[:500])

        raise SystemExit(1)

    try:

        df = pd.read_csv(
            StringIO(response.text)
        )

    except Exception as e:

        print("\nERROR reading FIRMS response:")
        print(e)

        raise SystemExit(1)

    print("Live observations received:", len(df))

    if df.empty:

        print("\nWARNING: No FIRMS detections returned.")

        # Still save an empty file
        df.to_csv(
            LIVE_FIRMS_FILE,
            index=False
        )

        return df

    required = [
        "latitude",
        "longitude",
        "acq_date",
        "satellite",
        "frp"
    ]

    missing = [
        col for col in required
        if col not in df.columns
    ]

    if missing:

        print("\nERROR: Required FIRMS columns missing:")
        print(missing)

        raise SystemExit(1)

    df.to_csv(
        LIVE_FIRMS_FILE,
        index=False
    )

    print("Saved:")
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

    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce"
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce"
    )

    df["frp"] = pd.to_numeric(
        df["frp"],
        errors="coerce"
    )

    df["acq_date"] = pd.to_datetime(
        df["acq_date"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "latitude",
            "longitude",
            "frp",
            "acq_date",
            "satellite"
        ]
    ).copy()

    print("Valid observations:", len(df))

    return df


# ============================================================
# 3. CREATE SPATIAL GRID
# ============================================================

def create_grid(df):

    print("\n[3/5] Creating spatial grid...")

    if df.empty:

        empty = pd.DataFrame(
            columns=[
                "grid_id",
                "grid_lat",
                "grid_lon",
                "detection_count",
                "active_days",
                "avg_frp",
                "max_frp",
                "min_frp",
                "satellite_count",
                "first_detection",
                "last_detection"
            ]
        )

        empty.to_csv(
            LIVE_GRID_FILE,
            index=False
        )

        return empty

    df = df.copy()

    df["grid_lat"] = (
        np.floor(
            df["latitude"] / GRID_SIZE
        ) * GRID_SIZE
    )

    df["grid_lon"] = (
        np.floor(
            df["longitude"] / GRID_SIZE
        ) * GRID_SIZE
    )

    df["grid_lat"] = df[
        "grid_lat"
    ].round(2)

    df["grid_lon"] = df[
        "grid_lon"
    ].round(2)

    df["grid_id"] = (
        df["grid_lat"].astype(str)
        + "_"
        + df["grid_lon"].astype(str)
    )

    grid = (
        df.groupby("grid_id")
        .agg(
            grid_lat=("grid_lat", "first"),
            grid_lon=("grid_lon", "first"),

            detection_count=(
                "grid_id",
                "count"
            ),

            active_days=(
                "acq_date",
                "nunique"
            ),

            avg_frp=(
                "frp",
                "mean"
            ),

            max_frp=(
                "frp",
                "max"
            ),

            min_frp=(
                "frp",
                "min"
            ),

            satellite_count=(
                "satellite",
                "nunique"
            ),

            first_detection=(
                "acq_date",
                "min"
            ),

            last_detection=(
                "acq_date",
                "max"
            )
        )
        .reset_index()
    )

    grid["repeat_score"] = (
        grid["detection_count"]
        /
        grid["active_days"].clip(lower=1)
    )

    grid.to_csv(
        LIVE_GRID_FILE,
        index=False
    )

    print("Live grid cells:", len(grid))

    print("Saved:")
    print(LIVE_GRID_FILE)

    return grid


# ============================================================
# 4. ENGINEER LIVE RISK FEATURES
# ============================================================

def create_risk_features(grid):

    print("\n[4/5] Creating live risk features...")

    if grid.empty:

        empty = grid.copy()

        empty.to_csv(
            LIVE_FEATURES_FILE,
            index=False
        )

        return empty

    grid = grid.copy()

    # --------------------------------------------------------
    # Satellite information
    # --------------------------------------------------------

    grid["satellite_source_count"] = (
        grid["satellite_count"]
    )

    grid["satellite_agreement"] = (
        grid["satellite_source_count"] >= 2
    ).astype(int)

    grid["satellite_score"] = (
        grid["satellite_agreement"]
    )

    # --------------------------------------------------------
    # Recurrence
    # --------------------------------------------------------

    max_active_days = (
        grid["active_days"].max()
    )

    if (
        pd.notna(max_active_days)
        and max_active_days > 0
    ):

        grid["recurrence_score"] = (
            grid["active_days"]
            / max_active_days
        )

    else:

        grid["recurrence_score"] = 0.0

    # --------------------------------------------------------
    # FRP intensity
    # --------------------------------------------------------

    max_frp = (
        grid["max_frp"].max()
    )

    if (
        pd.notna(max_frp)
        and max_frp > 0
    ):

        grid["frp_intensity"] = (
            grid["max_frp"]
            / max_frp
        )

    else:

        grid["frp_intensity"] = 0.0

    grid["frp_intensity"] = (
        grid["frp_intensity"]
        .clip(0, 1)
    )

    # --------------------------------------------------------
    # Repeat detection score
    # --------------------------------------------------------

    max_detection_count = (
        grid["detection_count"].max()
    )

    if (
        pd.notna(max_detection_count)
        and max_detection_count > 0
    ):

        grid["repeat_detection_score"] = (
            grid["detection_count"]
            / max_detection_count
        )

    else:

        grid["repeat_detection_score"] = 0.0

    grid["repeat_detection_score"] = (
        grid["repeat_detection_score"]
        .clip(0, 1)
    )

    # --------------------------------------------------------
    # Combined explainable activity score
    # --------------------------------------------------------

    grid["activity_score"] = (
        0.45 * grid["recurrence_score"]
        +
        0.35 * grid["frp_intensity"]
        +
        0.20 * grid["repeat_detection_score"]
    )

    grid["activity_score"] = (
        grid["activity_score"]
        .clip(0, 1)
    )

    # --------------------------------------------------------
    # Activity category
    # --------------------------------------------------------

    def classify_activity(score):

        if score >= 0.75:
            return "HIGH"

        elif score >= 0.45:
            return "MEDIUM"

        return "LOW"

    grid["activity_category"] = (
        grid["activity_score"]
        .apply(classify_activity)
    )

    grid = grid.sort_values(
        "activity_score",
        ascending=False
    ).reset_index(drop=True)

    grid.to_csv(
        LIVE_FEATURES_FILE,
        index=False
    )

    print("Live feature cells:", len(grid))

    print("Saved:")
    print(LIVE_FEATURES_FILE)

    return grid


# ============================================================
# 5. GENERATE LIVE RISK PREDICTIONS
# ============================================================

def generate_predictions(features):

    print("\n[5/5] Generating live risk predictions...")

    if features.empty:

        empty = features.copy()

        empty.to_csv(
            LIVE_PREDICTIONS_FILE,
            index=False
        )

        return empty

    df = features.copy()

    # --------------------------------------------------------
    # Explainable risk score
    # --------------------------------------------------------

    df["risk_score"] = (
        0.45 * df["recurrence_score"]
        +
        0.35 * df["frp_intensity"]
        +
        0.20 * df["repeat_detection_score"]
    )

    df["risk_score"] = (
        df["risk_score"]
        .clip(0, 1)
    )

    # --------------------------------------------------------
    # Percentage
    # --------------------------------------------------------

    df["risk_percentage"] = (
        df["risk_score"] * 100
    ).round(2)

    # --------------------------------------------------------
    # Risk category
    # --------------------------------------------------------

    def classify_risk(score):

        if score >= 0.75:
            return "HIGH"

        elif score >= 0.45:
            return "MEDIUM"

        return "LOW"

    df["risk_category"] = (
        df["risk_score"]
        .apply(classify_risk)
    )

    # --------------------------------------------------------
    # Risk priority
    # --------------------------------------------------------

    df["risk_priority"] = (
        df["risk_score"]
        .rank(
            ascending=False,
            method="dense"
        )
        .astype(int)
    )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    df = (
        df.sort_values(
            "risk_score",
            ascending=False
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    df.to_csv(
        LIVE_PREDICTIONS_FILE,
        index=False
    )

    print("\nLive risk results:")

    print(
        df[
            [
                "grid_id",
                "risk_score",
                "risk_percentage",
                "risk_category",
                "risk_priority"
            ]
        ]
        .to_string(index=False)
    )

    print("\nRisk categories:")

    print(
        df["risk_category"]
        .value_counts()
    )

    print("\nSaved:")
    print(LIVE_PREDICTIONS_FILE)

    return df


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():

    # 1. NASA FIRMS
    live_df = fetch_live_firms()

    # 2. Cleaning
    live_df = clean_data(
        live_df
    )

    # 3. Spatial grid
    grid = create_grid(
        live_df
    )

    # 4. Risk features
    features = create_risk_features(
        grid
    )

    # 5. Risk predictions
    predictions = generate_predictions(
        features
    )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

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

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()