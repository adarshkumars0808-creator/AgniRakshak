import pandas as pd
import numpy as np

# ============================================================
# THERMOSCOPE - STEP 3A
# DELHI FIRMS SPATIAL GRID
# SIH PROVIDED DATASET
# ============================================================

INPUT_FILE = "data/delhi_firms_sih.csv"
OUTPUT_FILE = "data/delhi_grid.csv"

# 0.01 degree latitude ≈ 1.1 km
GRID_SIZE = 0.01

print("=" * 70)
print("THERMOSCOPE - SPATIAL GRID CREATION")
print("USING SIH PROVIDED NASA FIRMS DATA")
print("=" * 70)

# ------------------------------------------------------------
# 1. Load SIH FIRMS data
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print("\nLoaded SIH observations:", len(df))

# ------------------------------------------------------------
# 2. Basic cleaning
# ------------------------------------------------------------

required_columns = [
    "latitude",
    "longitude",
    "frp",
    "acq_date",
    "satellite"
]

missing = [
    col for col in required_columns
    if col not in df.columns
]

if missing:
    print("\nERROR: Missing columns:")
    print(missing)
    raise ValueError("SIH dataset does not contain required columns.")

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
        "acq_date"
    ]
)

print("After cleaning:", len(df))

# ------------------------------------------------------------
# 3. Create geographic grid
# ------------------------------------------------------------

df["grid_lat"] = (
    np.floor(df["latitude"] / GRID_SIZE)
    * GRID_SIZE
)

df["grid_lon"] = (
    np.floor(df["longitude"] / GRID_SIZE)
    * GRID_SIZE
)

# Avoid floating point issues
df["grid_lat"] = df["grid_lat"].round(2)
df["grid_lon"] = df["grid_lon"].round(2)

# Unique grid ID
df["grid_id"] = (
    df["grid_lat"].astype(str)
    + "_"
    + df["grid_lon"].astype(str)
)

print(
    "\nUnique grid cells:",
    df["grid_id"].nunique()
)

# ------------------------------------------------------------
# 4. Aggregate each grid cell
# ------------------------------------------------------------

grid = (
    df.groupby("grid_id")
    .agg(
        grid_lat=("grid_lat", "first"),
        grid_lon=("grid_lon", "first"),

        detection_count=("grid_id", "count"),

        avg_frp=("frp", "mean"),
        max_frp=("frp", "max"),
        min_frp=("frp", "min"),

        first_detection=("acq_date", "min"),
        last_detection=("acq_date", "max"),

        satellite_count=("satellite", "nunique"),

        latitude_mean=("latitude", "mean"),
        longitude_mean=("longitude", "mean")
    )
    .reset_index()
)

# ------------------------------------------------------------
# 5. Calculate active days SAFELY
# ------------------------------------------------------------

active_days = (
    df.groupby("grid_id")["acq_date"]
    .nunique()
    .rename("active_days")
)

grid = grid.merge(
    active_days,
    on="grid_id",
    how="left"
)

# ------------------------------------------------------------
# 6. Calculate repeat activity score
# ------------------------------------------------------------

grid["repeat_score"] = (
    grid["detection_count"]
    / grid["active_days"].clip(lower=1)
)

# ------------------------------------------------------------
# 7. Sort by activity
# ------------------------------------------------------------

grid = grid.sort_values(
    by="detection_count",
    ascending=False
)

# ------------------------------------------------------------
# 8. Save grid dataset
# ------------------------------------------------------------

grid.to_csv(
    OUTPUT_FILE,
    index=False
)

# ------------------------------------------------------------
# 9. Display results
# ------------------------------------------------------------

print("\nTop active grid cells:")

print(
    grid[
        [
            "grid_id",
            "detection_count",
            "active_days",
            "avg_frp",
            "max_frp",
            "satellite_count"
        ]
    ]
    .head(10)
    .to_string(index=False)
)

print("\nTotal grid cells:", len(grid))

print("\nSaved to:")
print(OUTPUT_FILE)

print("\n" + "=" * 70)
print("STEP 3A COMPLETE")
print("=" * 70)