import pandas as pd
import os

# ============================================================
# THERMOSCOPE - SIH FIRMS DATA LOADER
# ============================================================

INPUT_FILE = "data/delhi_firms_sih.csv"
OUTPUT_FILE = "data/delhi_master.csv"

print("=" * 70)
print("THERMOSCOPE - SIH FIRMS DATA LOADER")
print("=" * 70)

# ------------------------------------------------------------
# LOAD SIH DATASET
# ------------------------------------------------------------

print(f"\nLoading SIH dataset:")
print(INPUT_FILE)

if not os.path.exists(INPUT_FILE):
    print("\nERROR: SIH dataset not found!")
    print(f"Please make sure this file exists:")
    print(INPUT_FILE)
    raise SystemExit

df = pd.read_csv(INPUT_FILE)

print("\nLoaded observations:", len(df))

# ------------------------------------------------------------
# CHECK REQUIRED COLUMNS
# ------------------------------------------------------------

required_columns = [
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "frp"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    print("\nERROR: Missing columns:")
    print(missing_columns)
    raise SystemExit

print("\nRequired columns verified.")

# ------------------------------------------------------------
# CLEAN DATA
# ------------------------------------------------------------

print("\nCleaning data...")

before = len(df)

# Remove exact duplicate rows
df = df.drop_duplicates()

# Remove rows with missing coordinates
df = df.dropna(
    subset=["latitude", "longitude"]
)

# Convert date
df["acq_date"] = pd.to_datetime(
    df["acq_date"],
    errors="coerce"
)

# Convert FRP to numeric
df["frp"] = pd.to_numeric(
    df["frp"],
    errors="coerce"
)

# Remove invalid dates
df = df.dropna(
    subset=["acq_date"]
)

after = len(df)

print("Rows before cleaning :", before)
print("Rows after cleaning  :", after)
print("Duplicates/invalid rows removed:", before - after)

# ------------------------------------------------------------
# SORT DATA
# ------------------------------------------------------------

df = df.sort_values(
    by=["acq_date", "acq_time"]
).reset_index(drop=True)

# ------------------------------------------------------------
# SAVE MASTER DATASET
# ------------------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n" + "=" * 70)
print("DATASET SUMMARY")
print("=" * 70)

print("\nFinal observations:", len(df))

print("\nColumns:")
print(df.columns.tolist())

print("\nDate range:")

if len(df) > 0:
    print(
        df["acq_date"].min().date(),
        "to",
        df["acq_date"].max().date()
    )

print("\nSatellite distribution:")
print(
    df["satellite"].value_counts()
)

print("\nObservations:")
print(
    df[
        [
            "latitude",
            "longitude",
            "acq_date",
            "acq_time",
            "satellite",
            "confidence",
            "frp"
        ]
    ].to_string(index=False)
)

print("\nSaved to:")
print(OUTPUT_FILE)

print("\n" + "=" * 70)
print("SIH DATA LOADING COMPLETE")
print("=" * 70)