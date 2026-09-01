from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# THERMOSCOPE
# STAGE 3 - SPATIAL GRID + HISTORICAL FEATURE ENGINEERING
#
# IMPORTANT COORDINATE RULE
# -------------------------
# FIRMS coordinates = FIRE DETECTION coordinates
# Grid coordinates  = RISK AGGREGATION coordinates
#
# These coordinates must NOT be treated as actual industry,
# forest or agricultural facility coordinates.
#
# Category-specific display coordinates are created later by
# fire-type classification / GIS layers.
# ============================================================


INPUT_FILE = Path(
    "data/processed/firms_clean_merged.csv"
)

OUTPUT_DIR = Path(
    "data/processed"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    OUTPUT_DIR /
    "grid_features.csv"
)


# ------------------------------------------------------------
# GRID CONFIGURATION
# ------------------------------------------------------------

GRID_SIZE = 0.05


# ------------------------------------------------------------
# FEATURE PERIOD
# ------------------------------------------------------------

HISTORICAL_START = pd.Timestamp(
    "2020-01-01"
)

HISTORICAL_END = pd.Timestamp.today().normalize()


# ============================================================
# CREATE GRID IDS
# ============================================================

def create_grid(df):

    """
    Convert every FIRMS detection into a spatial grid cell.

    IMPORTANT:
    latitude/longitude remain the ORIGINAL FIRMS detection
    coordinates.

    grid_lat/grid_lon are only aggregation coordinates.
    """

    df = df.copy()

    # --------------------------------------------------------
    # Validate coordinates
    # --------------------------------------------------------

    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce"
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "latitude",
            "longitude"
        ]
    )

    # --------------------------------------------------------
    # Create grid
    # --------------------------------------------------------

    df["grid_lat"] = (
        np.floor(
            df["latitude"] /
            GRID_SIZE
        ) * GRID_SIZE
    )

    df["grid_lon"] = (
        np.floor(
            df["longitude"] /
            GRID_SIZE
        ) * GRID_SIZE
    )

    df["grid_lat"] = (
        df["grid_lat"]
        .round(4)
    )

    df["grid_lon"] = (
        df["grid_lon"]
        .round(4)
    )

    # --------------------------------------------------------
    # Stable grid ID
    # --------------------------------------------------------

    df["grid_id"] = (
        df["grid_lat"].map(
            lambda x: f"{x:.2f}"
        )
        + "_"
        + df["grid_lon"].map(
            lambda x: f"{x:.2f}"
        )
    )

    return df


# ============================================================
# BASIC GRID FEATURES
# ============================================================

def basic_features(df):

    grouped = df.groupby(
        "grid_id",
        sort=False
    )

    features = grouped.agg(

        # ----------------------------------------------------
        # FIRMS representative coordinates
        #
        # These are average detection coordinates.
        # They are NOT facility coordinates.
        # ----------------------------------------------------

        latitude=(
            "latitude",
            "mean"
        ),

        longitude=(
            "longitude",
            "mean"
        ),

        # ----------------------------------------------------
        # Actual grid origin
        # ----------------------------------------------------

        grid_lat=(
            "grid_lat",
            "first"
        ),

        grid_lon=(
            "grid_lon",
            "first"
        ),

        total_detections=(
            "grid_id",
            "size"
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

        median_frp=(
            "frp",
            "median"
        ),

        frp_std=(
            "frp",
            "std"
        ),

        avg_brightness=(
            "brightness",
            "mean"
        ),

        max_brightness=(
            "brightness",
            "max"
        ),

        avg_confidence=(
            "confidence",
            "mean"
        ),

        satellite_count=(
            "sensor",
            "nunique"
        ),

        active_months=(
            "year_month",
            "nunique"
        ),

        active_years=(
            "year",
            "nunique"
        ),
    )

    return features.reset_index()


# ============================================================
# YEARLY RECURRENCE
# ============================================================

def recurrence_features(df):

    yearly = (
        df.groupby(
            [
                "grid_id",
                "year"
            ]
        )
        .size()
        .reset_index(
            name="year_detections"
        )
    )

    recurrence = (
        yearly.groupby(
            "grid_id"
        )
        .agg(
            years_with_activity=(
                "year",
                "nunique"
            ),

            avg_yearly_detections=(
                "year_detections",
                "mean"
            ),

            max_yearly_detections=(
                "year_detections",
                "max"
            ),

            yearly_detection_std=(
                "year_detections",
                "std"
            ),
        )
        .reset_index()
    )

    total_years = max(
        1,
        df["year"].nunique()
    )

    recurrence["recurrence_ratio"] = (
        recurrence["years_with_activity"]
        / total_years
    )

    return recurrence


# ============================================================
# MONTHLY PERSISTENCE
# ============================================================

def persistence_features(df):

    monthly = (
        df.groupby(
            [
                "grid_id",
                "year_month"
            ]
        )
        .size()
        .reset_index(
            name="monthly_detections"
        )
    )

    persistence = (
        monthly.groupby(
            "grid_id"
        )
        .agg(
            persistent_months=(
                "year_month",
                "nunique"
            ),

            avg_monthly_detections=(
                "monthly_detections",
                "mean"
            ),

            max_monthly_detections=(
                "monthly_detections",
                "max"
            ),
        )
        .reset_index()
    )

    return persistence


# ============================================================
# SATELLITE AGREEMENT
# ============================================================

def satellite_features(df):

    satellite = (
        df.groupby(
            "grid_id"
        )
        .agg(
            satellite_types=(
                "sensor",
                "nunique"
            ),

            snpp_detections=(
                "sensor",
                lambda x: (
                    x == "SNPP"
                ).sum()
            ),

            noaa20_detections=(
                "sensor",
                lambda x: (
                    x == "NOAA20"
                ).sum()
            ),

            noaa21_detections=(
                "sensor",
                lambda x: (
                    x == "NOAA21"
                ).sum()
            ),
        )
        .reset_index()
    )

    satellite["multi_satellite_activity"] = (
        satellite["satellite_types"] >= 2
    ).astype(int)

    return satellite


# ============================================================
# RECENT ACTIVITY
# ============================================================

def recent_features(df):

    latest_date = df["acq_date"].max()

    recent_30 = df[
        df["acq_date"]
        >= latest_date - pd.Timedelta(days=30)
    ]

    recent_90 = df[
        df["acq_date"]
        >= latest_date - pd.Timedelta(days=90)
    ]

    f30 = (
        recent_30.groupby("grid_id")
        .agg(
            detections_30d=(
                "grid_id",
                "size"
            ),

            active_days_30d=(
                "acq_date",
                "nunique"
            ),

            avg_frp_30d=(
                "frp",
                "mean"
            ),

            max_frp_30d=(
                "frp",
                "max"
            ),
        )
        .reset_index()
    )

    f90 = (
        recent_90.groupby("grid_id")
        .agg(
            detections_90d=(
                "grid_id",
                "size"
            ),

            active_days_90d=(
                "acq_date",
                "nunique"
            ),

            avg_frp_90d=(
                "frp",
                "mean"
            ),

            max_frp_90d=(
                "frp",
                "max"
            ),
        )
        .reset_index()
    )

    return f30, f90


# ============================================================
# SEASONAL FEATURES
# ============================================================

def seasonal_features(df):

    monthly = (
        df.groupby(
            [
                "grid_id",
                "month"
            ]
        )
        .size()
        .reset_index(
            name="monthly_count"
        )
    )

    seasonal = (
        monthly.groupby(
            "grid_id"
        )
        .agg(
            seasonal_peak=(
                "monthly_count",
                "max"
            ),

            seasonal_mean=(
                "monthly_count",
                "mean"
            ),

            seasonal_std=(
                "monthly_count",
                "std"
            ),
        )
        .reset_index()
    )

    seasonal["seasonality_strength"] = (
        seasonal["seasonal_peak"]
        /
        seasonal["seasonal_mean"].replace(
            0,
            np.nan
        )
    )

    seasonal["seasonality_strength"] = (
        seasonal["seasonality_strength"]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .fillna(0)
    )

    return seasonal


# ============================================================
# FINAL FEATURE ENGINEERING
# ============================================================

def build_features(df):

    print()
    print("=" * 70)
    print("CREATING SPATIAL GRID")
    print("=" * 70)

    df = create_grid(df)

    print(
        f"Unique grid cells: "
        f"{df['grid_id'].nunique():,}"
    )

    # --------------------------------------------------------
    # Date features
    # --------------------------------------------------------

    df["year"] = (
        df["acq_date"]
        .dt.year
    )

    df["month"] = (
        df["acq_date"]
        .dt.month
    )

    df["year_month"] = (
        df["acq_date"]
        .dt.to_period("M")
        .astype(str)
    )

    print()
    print("Creating basic features...")

    basic = basic_features(df)

    print("Creating recurrence features...")

    recurrence = recurrence_features(df)

    print("Creating persistence features...")

    persistence = persistence_features(df)

    print("Creating satellite features...")

    satellite = satellite_features(df)

    print("Creating recent activity features...")

    recent30, recent90 = recent_features(df)

    print("Creating seasonal features...")

    seasonal = seasonal_features(df)

    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    result = basic

    for feature_df in [
        recurrence,
        persistence,
        satellite,
        recent30,
        recent90,
        seasonal,
    ]:

        result = result.merge(
            feature_df,
            on="grid_id",
            how="left"
        )

    # --------------------------------------------------------
    # Derived features
    # --------------------------------------------------------

    result["detections_per_active_day"] = (
        result["total_detections"]
        /
        result["active_days"].replace(
            0,
            np.nan
        )
    )

    result["recent_activity_ratio"] = (
        result["detections_30d"]
        /
        result["total_detections"].replace(
            0,
            np.nan
        )
    )

    result["frp_intensity_ratio"] = (
        result["max_frp"]
        /
        result["avg_frp"].replace(
            0,
            np.nan
        )
    )

    result["persistence_ratio"] = (
        result["persistent_months"]
        /
        result["active_months"].replace(
            0,
            np.nan
        )
    )

    # --------------------------------------------------------
    # Invalid values
    # --------------------------------------------------------

    result = result.replace(
        [np.inf, -np.inf],
        np.nan
    )

    numeric_columns = result.select_dtypes(
        include=np.number
    ).columns

    result[numeric_columns] = (
        result[numeric_columns]
        .fillna(0)
    )

    # --------------------------------------------------------
    # IMPORTANT METADATA
    # --------------------------------------------------------

    result["coordinate_type"] = (
        "FIRMS_GRID_AGGREGATE"
    )

    result["coordinate_note"] = (
        "Coordinates represent aggregated FIRMS "
        "fire-detection activity and are not facility "
        "or land-use coordinates."
    )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    result = result.sort_values(
        "total_detections",
        ascending=False
    ).reset_index(drop=True)

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("THERMOSCOPE - SPATIAL GRID FEATURE ENGINEERING")
    print("=" * 70)

    print(
        f"Input: {INPUT_FILE}"
    )

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}\n"
            "Run clean_merge.py first."
        )

    print()
    print("Loading cleaned FIRMS dataset...")

    df = pd.read_csv(
        INPUT_FILE,
        low_memory=False,
        parse_dates=["acq_date"]
    )

    print(
        f"Rows loaded: {len(df):,}"
    )

    print(
        f"Date range: "
        f"{df['acq_date'].min().date()} "
        f"-> "
        f"{df['acq_date'].max().date()}"
    )

    features = build_features(df)

    features.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("=" * 70)
    print("GRID FEATURE ENGINEERING COMPLETE")
    print("=" * 70)

    print(
        f"Grid cells: "
        f"{len(features):,}"
    )

    print(
        f"Features: "
        f"{len(features.columns)}"
    )

    print(
        f"Saved to: {OUTPUT_FILE}"
    )

    print()
    print("TOP 10 BY HISTORICAL DETECTION COUNT")
    print("-" * 70)

    preview_columns = [
        "grid_id",
        "latitude",
        "longitude",
        "grid_lat",
        "grid_lon",
        "total_detections",
        "active_days",
        "recurrence_ratio",
        "avg_frp",
        "max_frp",
        "satellite_types",
        "coordinate_type",
    ]

    preview_columns = [
        col
        for col in preview_columns
        if col in features.columns
    ]

    print(
        features[
            preview_columns
        ]
        .head(10)
        .to_string(index=False)
    )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()