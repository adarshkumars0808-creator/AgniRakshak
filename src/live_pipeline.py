import os
import subprocess
import sys
from io import StringIO

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv


# ============================================================
# THERMOSCOPE
# LIVE NASA FIRMS → GRID → RISK PIPELINE
# ============================================================

print("=" * 70)
print("THERMOSCOPE - LIVE FIRE RISK PIPELINE")
print("=" * 70)


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

MAP_KEY = os.getenv("FIRMS_MAP_KEY")

SOURCE = "VIIRS_NOAA20_NRT"
DAY_RANGE = 5

# west, south, east, north
DELHI_BBOX = "76.8,28.4,77.4,28.9"

GRID_SIZE = 0.01

LIVE_FIRMS_FILE = "data/delhi_firms_live.csv"
LIVE_RISK_FILE = "data/delhi_risk_predictions_live.csv"


# ============================================================
# CHECK API KEY
# ============================================================

if not MAP_KEY:
    print("\nERROR: FIRMS_MAP_KEY not found in .env")
    print("Create/update .env with:")
    print("FIRMS_MAP_KEY=YOUR_NASA_FIRMS_MAP_KEY")
    sys.exit(1)


# ============================================================
# 1. FETCH LIVE NASA FIRMS DATA
# ============================================================

print("\n[1/4] Fetching latest NASA FIRMS observations...")

URL = (
    "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
    f"{MAP_KEY}/{SOURCE}/{DELHI_BBOX}/{DAY_RANGE}"
)

try:
    response = requests.get(
        URL,
        timeout=30
    )

    print("HTTP Status:", response.status_code)

    if response.status_code != 200:
        print("\nERROR: NASA FIRMS API request failed.")
        print(response.text[:500])
        sys.exit(1)

except requests.RequestException as exc:

    print("\nERROR connecting to NASA FIRMS:")
    print(exc)
    sys.exit(1)


try:

    live_df = pd.read_csv(
        StringIO(response.text)
    )

except Exception as exc:

    print("\nERROR reading FIRMS response:")
    print(exc)
    sys.exit(1)


print(
    "Live FIRMS observations:",
    len(live_df)
)


# ============================================================
# SAVE LIVE FIRMS DATA
# ============================================================

os.makedirs(
    "data",
    exist_ok=True
)

live_df.to_csv(
    LIVE_FIRMS_FILE,
    index=False
)

print(
    "Saved:",
    LIVE_FIRMS_FILE
)


if live_df.empty:

    print(
        "\nNo current FIRMS detections were returned "
        "for the selected monitoring region."
    )

    # Create an empty prediction file with expected columns.
    empty_columns = [
        "grid_id",
        "grid_lat",
        "grid_lon",
        "detection_count",
        "active_days",
        "avg_frp",
        "max_frp",
        "min_frp",
        "satellite_count",
        "satellite_source_count",
        "satellite_agreement",
        "satellite_score",
        "recurrence_ratio",
        "detections_per_active_day",
        "frp_intensity",
        "recurrence_score",
        "repeat_detection_score",
        "activity_score",
        "risk_score",
        "risk_percentage",
        "risk_category",
        "risk_priority",
        "first_detection",
        "last_detection",
    ]

    pd.DataFrame(
        columns=empty_columns
    ).to_csv(
        LIVE_RISK_FILE,
        index=False
    )

    print(
        "Created empty live prediction file:",
        LIVE_RISK_FILE
    )

    sys.exit(0)


# ============================================================
# 2. CLEAN LIVE DATA
# ============================================================

print("\n[2/4] Processing live FIRMS observations...")


required_columns = [
    "latitude",
    "longitude",
    "frp",
    "acq_date",
    "satellite",
]

missing = [
    column
    for column in required_columns
    if column not in live_df.columns
]

if missing:

    print(
        "\nERROR: FIRMS response missing columns:"
    )

    print(missing)

    sys.exit(1)


live_df["latitude"] = pd.to_numeric(
    live_df["latitude"],
    errors="coerce"
)

live_df["longitude"] = pd.to_numeric(
    live_df["longitude"],
    errors="coerce"
)

live_df["frp"] = pd.to_numeric(
    live_df["frp"],
    errors="coerce"
)

live_df["acq_date"] = pd.to_datetime(
    live_df["acq_date"],
    errors="coerce"
)


live_df = live_df.dropna(
    subset=[
        "latitude",
        "longitude",
        "frp",
        "acq_date",
        "satellite",
    ]
).copy()


print(
    "Valid live observations:",
    len(live_df)
)


# ============================================================
# 3. CREATE SPATIAL GRID
# ============================================================

live_df["grid_lat"] = (
    np.floor(
        live_df["latitude"] / GRID_SIZE
    )
    * GRID_SIZE
)

live_df["grid_lon"] = (
    np.floor(
        live_df["longitude"] / GRID_SIZE
    )
    * GRID_SIZE
)


live_df["grid_lat"] = (
    live_df["grid_lat"]
    .round(2)
)

live_df["grid_lon"] = (
    live_df["grid_lon"]
    .round(2)
)


live_df["grid_id"] = (
    live_df["grid_lat"].astype(str)
    + "_"
    + live_df["grid_lon"].astype(str)
)


print(
    "Live grid cells:",
    live_df["grid_id"].nunique()
)


# ============================================================
# 4. AGGREGATE GRID FEATURES
# ============================================================

print("\n[3/4] Calculating risk features...")


grid = (
    live_df
    .groupby("grid_id")
    .agg(
        grid_lat=("grid_lat", "first"),
        grid_lon=("grid_lon", "first"),

        detection_count=("grid_id", "count"),

        active_days=("acq_date", "nunique"),

        avg_frp=("frp", "mean"),

        max_frp=("frp", "max"),

        min_frp=("frp", "min"),

        satellite_count=("satellite", "nunique"),

        first_detection=("acq_date", "min"),

        last_detection=("acq_date", "max"),
    )
    .reset_index()
)


# ============================================================
# SATELLITE SIGNAL
# ============================================================

grid["satellite_source_count"] = (
    grid["satellite_count"]
)

grid["satellite_agreement"] = (
    grid["satellite_source_count"] >= 2
).astype(int)

grid["satellite_score"] = (
    grid["satellite_agreement"]
)


# ============================================================
# RECURRENCE
# ============================================================

global_start = (
    live_df["acq_date"].min()
)

global_end = (
    live_df["acq_date"].max()
)


total_days = (
    global_end - global_start
).days + 1


total_days = max(
    total_days,
    1
)


grid["recurrence_ratio"] = (
    grid["active_days"]
    / total_days
).clip(
    upper=1
)


# ============================================================
# DETECTIONS PER ACTIVE DAY
# ============================================================

grid["detections_per_active_day"] = (
    grid["detection_count"]
    /
    grid["active_days"].clip(
        lower=1
    )
)


# ============================================================
# FRP INTENSITY
# ============================================================

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
    ).clip(
        0,
        1
    )

else:

    grid["frp_intensity"] = 0.0


# ============================================================
# RECURRENCE SCORE
# ============================================================

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
    ).clip(
        0,
        1
    )

else:

    grid["recurrence_score"] = 0.0


# ============================================================
# REPEAT DETECTION SCORE
# ============================================================

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
    ).clip(
        0,
        1
    )

else:

    grid["repeat_detection_score"] = 0.0


# ============================================================
# EXPLAINABLE ACTIVITY SCORE
# ============================================================

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


# ============================================================
# RISK SCORE
# ============================================================

grid["risk_score"] = (
    0.45 * grid["recurrence_score"]
    +
    0.35 * grid["frp_intensity"]
    +
    0.20 * grid["repeat_detection_score"]
)


grid["risk_score"] = (
    grid["risk_score"]
    .clip(0, 1)
)


# ============================================================
# RISK PERCENTAGE
# ============================================================

grid["risk_percentage"] = (
    grid["risk_score"] * 100
).round(2)


# ============================================================
# RISK CLASSIFICATION
# ============================================================

def classify_risk(score):

    if score >= 0.75:
        return "HIGH"

    elif score >= 0.45:
        return "MEDIUM"

    return "LOW"


grid["risk_category"] = (
    grid["risk_score"]
    .apply(classify_risk)
)


# ============================================================
# RISK PRIORITY
# ============================================================

grid["risk_priority"] = (
    grid["risk_score"]
    .rank(
        ascending=False,
        method="dense"
    )
    .astype(int)
)


# ============================================================
# SORT
# ============================================================

grid = (
    grid
    .sort_values(
        "risk_score",
        ascending=False
    )
    .reset_index(drop=True)
)


# ============================================================
# SAVE LIVE RISK PREDICTIONS
# ============================================================

grid.to_csv(
    LIVE_RISK_FILE,
    index=False
)


print(
    "Saved:",
    LIVE_RISK_FILE
)


# ============================================================
# SUMMARY
# ============================================================

print("\n[4/4] LIVE RISK SUMMARY")
print("-" * 70)

print(
    "Total live detections:",
    len(live_df)
)

print(
    "Total risk cells:",
    len(grid)
)

print("\nRisk categories:")

print(
    grid["risk_category"]
    .value_counts()
)


print("\nTop live risk cells:")

print(
    grid[
        [
            "grid_id",
            "risk_score",
            "risk_percentage",
            "risk_category",
            "detection_count",
            "active_days",
            "avg_frp",
            "max_frp",
        ]
    ]
    .head(10)
    .to_string(index=False)
)


print("\n" + "=" * 70)
print("LIVE PIPELINE COMPLETE")
print("=" * 70)

print(
    "\nLive FIRMS:",
    LIVE_FIRMS_FILE
)

print(
    "Live Risk:",
    LIVE_RISK_FILE
)

print("=" * 70)