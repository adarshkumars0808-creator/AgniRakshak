import re
from pathlib import Path

import pandas as pd


# ============================================================
# THERMOSCOPE
# NASA FIRMS RAW -> CLEAN + MERGED DATASET
# ============================================================

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = PROCESSED_DIR / "firms_clean_merged.csv"


# ------------------------------------------------------------
# SOURCE FILE PATTERNS
# ------------------------------------------------------------

FILE_PATTERNS = {
    "VIIRS_SNPP_SP": "VIIRS_SNPP_SP_*.csv",
    "VIIRS_NOAA20_SP": "VIIRS_NOAA20_SP_*.csv",
    # NOAA-21 historical files are NRT in the downloaded dataset
    "VIIRS_NOAA21_NRT": "VIIRS_NOAA21_NRT_*.csv",
}


# ------------------------------------------------------------
# REQUIRED FIRMS COLUMNS
# ------------------------------------------------------------

STANDARD_COLUMNS = [
    "latitude",
    "longitude",
    "brightness",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "bright_t31",
    "frp",
    "daynight",
]


# ------------------------------------------------------------
# REGION BOUNDING BOX
# Broad Delhi NCR + Uttar Pradesh coverage.
#
# IMPORTANT:
# Exact administrative filtering will be done later using GIS
# boundaries. We do NOT invent an artificial UP polygon here.
# ------------------------------------------------------------

WEST = 74.5
SOUTH = 23.5
EAST = 85.0
NORTH = 31.5


def detect_source(path: Path) -> str:
    """Identify FIRMS source from filename."""

    name = path.name

    if "VIIRS_SNPP_SP_" in name:
        return "VIIRS_SNPP_SP"

    if "VIIRS_NOAA20_SP_" in name:
        return "VIIRS_NOAA20_SP"

    if "VIIRS_NOAA21_NRT_" in name:
        return "VIIRS_NOAA21_NRT"

    return "UNKNOWN"


def clean_confidence(series):
    """
    FIRMS confidence can appear as:
    numeric values or categorical values such as
    l / n / h.

    Convert to a numeric confidence score where possible.
    """

    numeric = pd.to_numeric(series, errors="coerce")

    text = series.astype(str).str.strip().str.lower()

    categorical = text.map(
        {
            "l": 30,
            "n": 60,
            "h": 90,
            "low": 30,
            "nominal": 60,
            "high": 90,
        }
    )

    return numeric.fillna(categorical)


def standardize_columns(df):
    """
    Standardize slightly different FIRMS column layouts.
    """

    df.columns = [
        str(c).strip().lower()
        for c in df.columns
    ]

    # Some FIRMS products use bright_ti4 / bright_ti5.
    # Use bright_ti4 as the primary brightness measurement.
    if "brightness" not in df.columns:

        if "bright_ti4" in df.columns:
            df["brightness"] = df["bright_ti4"]

        elif "bright_ti5" in df.columns:
            df["brightness"] = df["bright_ti5"]

        else:
            df["brightness"] = pd.NA

    # Make sure expected columns exist.
    for column in STANDARD_COLUMNS:

        if column not in df.columns:
            df[column] = pd.NA

    return df


def clean_dataframe(df, source):
    """Clean one FIRMS dataframe."""

    df = standardize_columns(df)

    # --------------------------------------------------------
    # Numeric fields
    # --------------------------------------------------------

    numeric_columns = [
        "latitude",
        "longitude",
        "brightness",
        "scan",
        "track",
        "bright_t31",
        "frp",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    df["acq_date"] = pd.to_datetime(
        df["acq_date"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Time
    # --------------------------------------------------------

    df["acq_time"] = (
        df["acq_time"]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(4)
    )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    df["confidence"] = clean_confidence(
        df["confidence"]
    )

    # --------------------------------------------------------
    # Source metadata
    # --------------------------------------------------------

    df["source"] = source

    if source == "VIIRS_SNPP_SP":
        df["sensor"] = "SNPP"

    elif source == "VIIRS_NOAA20_SP":
        df["sensor"] = "NOAA20"

    elif source == "VIIRS_NOAA21_NRT":
        df["sensor"] = "NOAA21"

    else:
        df["sensor"] = "UNKNOWN"

    # --------------------------------------------------------
    # Remove invalid coordinates
    # --------------------------------------------------------

    df = df[
        df["latitude"].between(-90, 90)
        & df["longitude"].between(-180, 180)
    ]

    # --------------------------------------------------------
    # Broad Thermoscope region filter
    # --------------------------------------------------------

    df = df[
        df["longitude"].between(WEST, EAST)
        & df["latitude"].between(SOUTH, NORTH)
    ]

    # --------------------------------------------------------
    # Remove rows without acquisition date
    # --------------------------------------------------------

    df = df[df["acq_date"].notna()]

    # --------------------------------------------------------
    # Select standardized columns
    # --------------------------------------------------------

    output_columns = [
        "latitude",
        "longitude",
        "brightness",
        "scan",
        "track",
        "acq_date",
        "acq_time",
        "satellite",
        "instrument",
        "confidence",
        "version",
        "bright_t31",
        "frp",
        "daynight",
        "source",
        "sensor",
    ]

    return df[output_columns]


def process_file(path: Path, source: str):
    """Process one raw FIRMS file."""

    try:

        df = pd.read_csv(
            path,
            low_memory=False
        )

        before = len(df)

        df = clean_dataframe(
            df,
            source
        )

        print(
            f"[OK] {path.name} | "
            f"RAW={before:,} | "
            f"CLEAN={len(df):,}"
        )

        return df

    except Exception as exc:

        print(
            f"[ERROR] {path.name}: {exc}"
        )

        return pd.DataFrame()


def main():

    print("=" * 75)
    print("THERMOSCOPE - FIRMS CLEAN + MERGE")
    print("=" * 75)

    print(f"RAW DIRECTORY : {RAW_DIR}")
    print(f"OUTPUT        : {OUTPUT_FILE}")
    print()

    all_files = []

    for source, pattern in FILE_PATTERNS.items():

        files = sorted(
            RAW_DIR.glob(pattern)
        )

        print(
            f"{source}: {len(files):,} files"
        )

        for file in files:
            all_files.append(
                (file, source)
            )

    print()
    print(
        f"TOTAL RAW FILES: {len(all_files):,}"
    )
    print()

    if not all_files:
        raise RuntimeError(
            "No FIRMS CSV files found in data/raw"
        )

    # --------------------------------------------------------
    # Process files
    # --------------------------------------------------------

    frames = []

    for index, (path, source) in enumerate(
        all_files,
        start=1
    ):

        print(
            f"[{index}/{len(all_files)}]"
        )

        df = process_file(
            path,
            source
        )

        if not df.empty:
            frames.append(df)

    if not frames:
        raise RuntimeError(
            "No valid FIRMS data was processed."
        )

    print()
    print("=" * 75)
    print("MERGING DATA")
    print("=" * 75)

    merged = pd.concat(
        frames,
        ignore_index=True
    )

    print(
        f"Rows before duplicate removal: "
        f"{len(merged):,}"
    )

    # --------------------------------------------------------
    # Exact duplicate removal
    #
    # Same detection can occur in overlapping/duplicate files.
    # We remove exact duplicates without aggressively merging
    # nearby thermal detections.
    # --------------------------------------------------------

    duplicate_columns = [
        "latitude",
        "longitude",
        "acq_date",
        "acq_time",
        "satellite",
        "instrument",
        "frp",
        "brightness",
    ]

    before_duplicates = len(merged)

    merged = merged.drop_duplicates(
        subset=duplicate_columns
    ).reset_index(drop=True)

    removed = (
        before_duplicates
        - len(merged)
    )

    print(
        f"Exact duplicates removed: "
        f"{removed:,}"
    )

    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    merged = merged.sort_values(
        [
            "acq_date",
            "acq_time",
            "latitude",
            "longitude",
        ]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    merged.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("=" * 75)
    print("CLEANING COMPLETE")
    print("=" * 75)

    print(
        f"Final rows : {len(merged):,}"
    )

    print(
        f"Date range : "
        f"{merged['acq_date'].min().date()} "
        f"-> "
        f"{merged['acq_date'].max().date()}"
    )

    print()
    print("Sensor distribution:")

    print(
        merged["sensor"]
        .value_counts()
        .to_string()
    )

    print()
    print(
        f"Saved to: {OUTPUT_FILE}"
    )

    print("=" * 75)


if __name__ == "__main__":
    main() 