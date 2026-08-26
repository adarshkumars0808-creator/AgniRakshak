import pandas as pd
import numpy as np

# ============================================================
# THERMOSCOPE - STEP 3B
# RISK FEATURE ENGINEERING
# USING SIH PROVIDED NASA FIRMS DATA
# ============================================================

INPUT_FILE = "data/delhi_firms_live.csv"
OUTPUT_FILE = "data/delhi_risk_features_live.csv"

print("=" * 70)
print("THERMOSCOPE - RISK FEATURE ENGINEERING")
print("USING SIH PROVIDED NASA FIRMS DATA")
print("=" * 70)

# ------------------------------------------------------------
# 1. Load SIH FIRMS dataset
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print("\nLoaded SIH observations:", len(df))

# ------------------------------------------------------------
# 2. Clean important columns
# ------------------------------------------------------------

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
)

print("After cleaning:", len(df))

# ------------------------------------------------------------
# 3. Create same grid as Step 3A
# ------------------------------------------------------------

GRID_SIZE = 0.01

df["grid_lat"] = (
    np.floor(df["latitude"] / GRID_SIZE)
    * GRID_SIZE
)

df["grid_lon"] = (
    np.floor(df["longitude"] / GRID_SIZE)
    * GRID_SIZE
)

df["grid_lat"] = df["grid_lat"].round(2)
df["grid_lon"] = df["grid_lon"].round(2)

df["grid_id"] = (
    df["grid_lat"].astype(str)
    + "_"
    + df["grid_lon"].astype(str)
)

# ------------------------------------------------------------
# 4. Basic grid statistics
# ------------------------------------------------------------

grid = (
    df.groupby("grid_id")
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
        last_detection=("acq_date", "max")
    )
    .reset_index()
)

# ------------------------------------------------------------
# 5. Satellite source / agreement
# ------------------------------------------------------------

# Number of distinct satellite/source identifiers
grid["satellite_source_count"] = (
    grid["satellite_count"]
)

# True multi-source agreement is possible only when
# observations come from 2 or more independent sources.
grid["satellite_agreement"] = (
    grid["satellite_source_count"] >= 2
).astype(int)

# Satellite agreement score
# 0 = only one source, agreement cannot be established
# 1 = multiple independent sources detected
grid["satellite_score"] = (
    grid["satellite_agreement"]
)

# ------------------------------------------------------------
# 6. Recurrence / persistence
# ------------------------------------------------------------

# Overall observation period
global_start = df["acq_date"].min()
global_end = df["acq_date"].max()

total_days = (
    global_end - global_start
).days + 1

if total_days < 1:
    total_days = 1

# How many different days was each grid active?
grid["recurrence_ratio"] = (
    grid["active_days"] / total_days
).clip(upper=1)

# ------------------------------------------------------------
# 7. Detections per active day
# ------------------------------------------------------------

grid["detections_per_active_day"] = (
    grid["detection_count"]
    / grid["active_days"].clip(lower=1)
)

# ------------------------------------------------------------
# 8. FRP intensity
# ------------------------------------------------------------

max_frp = grid["max_frp"].max()

if pd.notna(max_frp) and max_frp > 0:

    grid["frp_intensity"] = (
        grid["max_frp"] / max_frp
    ).clip(upper=1)

else:

    grid["frp_intensity"] = 0.0

# ------------------------------------------------------------
# 9. Recurrence score
# ------------------------------------------------------------

max_active_days = grid["active_days"].max()

if pd.notna(max_active_days) and max_active_days > 0:

    grid["recurrence_score"] = (
        grid["active_days"]
        / max_active_days
    )

else:

    grid["recurrence_score"] = 0.0

# ------------------------------------------------------------
# 10. Repeat detection score
# ------------------------------------------------------------

max_detection_count = grid["detection_count"].max()

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

# ------------------------------------------------------------
# 11. Combined explainable activity / risk score
# ------------------------------------------------------------

# Current SIH dataset contains only one satellite source.
# Therefore satellite source coverage is not used as an
# independent risk-weighting factor.
#
# Risk score components:
#   45% - Recurrence / persistence
#   35% - FRP intensity
#   20% - Repeat detections

grid["activity_score"] = (
    0.45 * grid["recurrence_score"]
    +
    0.35 * grid["frp_intensity"]
    +
    0.20 * grid["repeat_detection_score"]
)

# ------------------------------------------------------------
# 12. Activity category
# ------------------------------------------------------------

def classify_activity(score):

    if score >= 0.75:
        return "HIGH"

    elif score >= 0.45:
        return "MEDIUM"

    else:
        return "LOW"


grid["activity_category"] = (
    grid["activity_score"]
    .apply(classify_activity)
)

# ------------------------------------------------------------
# 13. Sort by activity
# ------------------------------------------------------------

grid = grid.sort_values(
    by="activity_score",
    ascending=False
)

# ------------------------------------------------------------
# 14. Save
# ------------------------------------------------------------

grid.to_csv(
    OUTPUT_FILE,
    index=False
)

# ------------------------------------------------------------
# 15. Display results
# ------------------------------------------------------------

print("\nTotal grid cells:", len(grid))

print("\nObservation period:")
print(
    global_start.date(),
    "to",
    global_end.date()
)

print("\nAvailable satellite sources:")

available_satellites = (
    df["satellite"]
    .dropna()
    .unique()
)

print(available_satellites)

print(
    "Unique satellite sources:",
    len(available_satellites)
)

print("\nTOP GRID CELLS:")
print("-" * 70)

print(
    grid[
        [
            "grid_id",
            "detection_count",
            "active_days",
            "satellite_source_count",
            "satellite_agreement",
            "avg_frp",
            "max_frp",
            "recurrence_score",
            "frp_intensity",
            "repeat_detection_score",
            "activity_score",
            "activity_category"
        ]
    ]
    .head(15)
    .to_string(index=False)
)

print("\nActivity categories:")

print(
    grid["activity_category"]
    .value_counts()
)

print("\nSaved to:")
print(OUTPUT_FILE)

print("\n" + "=" * 70)
print("STEP 3B COMPLETE")
print("=" * 70)