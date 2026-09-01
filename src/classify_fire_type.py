from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# THERMOSCOPE / AGNIRAKSHAK
# STAGE 3.5 — FIRE-TYPE CLASSIFICATION
#
# IMPORTANT COORDINATE ARCHITECTURE
# ============================================================
#
# 1. NASA FIRMS
#       -> actual thermal detection
#
# 2. Grid
#       -> spatial aggregation
#
# 3. Industrial
#       -> REAL industrial facility coordinate
#
# 4. Forest
#       -> REAL forest/land-use coordinate from GIS layer
#
# 5. Agricultural
#       -> REAL agricultural/land-use coordinate from GIS layer
#
# The fields:
#
# latitude / longitude
#       = original FIRMS/grid coordinate
#
# display_latitude / display_longitude
#       = coordinate the dashboard should display
#
# coordinate_source
#       = tells exactly where display coordinate came from
#
# ============================================================


DATA_DIR = Path(
    "data/processed"
)

FIRMS_FILE = (
    DATA_DIR /
    "firms_clean_merged.csv"
)

GRID_FEATURES_FILE = (
    DATA_DIR /
    "grid_features.csv"
)

RISK_FILE = (
    DATA_DIR /
    "risk_predictions.csv"
)

INDUSTRIAL_SITES_FILE = (
    DATA_DIR /
    "industrial_sites.csv"
)

# Optional GIS category point layers.
#
# If these files are available, they should contain:
#
# latitude
# longitude
#
# Optional:
# name
# type
#
AGRICULTURAL_SITES_FILE = (
    DATA_DIR /
    "agricultural_sites.csv"
)

FOREST_SITES_FILE = (
    DATA_DIR /
    "forest_sites.csv"
)

OUTPUT_FILE = (
    DATA_DIR /
    "fire_type_predictions.csv"
)


GRID_SIZE = 0.05

STUBBLE_MONTHS = [
    4,
    5,
    10,
    11
]

DRY_SEASON_MONTHS = [
    3,
    4,
    5,
    6
]


# ============================================================
# THRESHOLDS
# ============================================================

FLAT_RATIO_MAX = 5.0

RECURRENCE_MIN_INDUSTRIAL = 0.71

STUBBLE_FRAC_MIN = 0.85

DRY_FRAC_MIN = 0.85

RECURRENCE_MAX_AGRICULTURE = 0.85

RECURRENCE_MAX_WILDFIRE = 0.60

INDUSTRIAL_PROXIMITY_KM = 3.0


# ============================================================
# GRID ID
# ============================================================

def make_grid_id(
    lat,
    lon
):

    grid_lat = (
        np.floor(
            lat /
            GRID_SIZE
        )
        *
        GRID_SIZE
    ).round(4)

    grid_lon = (
        np.floor(
            lon /
            GRID_SIZE
        )
        *
        GRID_SIZE
    ).round(4)

    return (
        grid_lat.map(
            lambda x: f"{x:.2f}"
        )
        +
        "_"
        +
        grid_lon.map(
            lambda x: f"{x:.2f}"
        )
    )


# ============================================================
# HAVERSINE
# ============================================================

def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2
):

    radius = 6371.0

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)

    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        +
        np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    return (
        2
        * radius
        * np.arcsin(
            np.sqrt(a)
        )
    )


# ============================================================
# MONTHLY PROFILE
# ============================================================

def build_monthly_profile():

    print(
        "Building per-grid monthly detection profile..."
    )

    if not FIRMS_FILE.exists():

        raise FileNotFoundError(
            f"Missing file: {FIRMS_FILE}"
        )

    monthly_counts = {}

    chunks = pd.read_csv(
        FIRMS_FILE,
        usecols=[
            "latitude",
            "longitude",
            "acq_date"
        ],
        chunksize=500_000,
        low_memory=False,
    )

    for i, chunk in enumerate(
        chunks,
        start=1
    ):

        chunk["acq_date"] = pd.to_datetime(
            chunk["acq_date"],
            errors="coerce"
        )

        chunk = chunk.dropna(
            subset=[
                "acq_date",
                "latitude",
                "longitude"
            ]
        )

        grid_id = make_grid_id(
            chunk["latitude"],
            chunk["longitude"]
        )

        month = (
            chunk[
                "acq_date"
            ]
            .dt
            .month
        )

        counts = (
            pd.DataFrame(
                {
                    "grid_id": grid_id,
                    "month": month
                }
            )
            .groupby(
                [
                    "grid_id",
                    "month"
                ]
            )
            .size()
        )

        for (
            gid,
            month_number
        ), count in counts.items():

            key = (
                gid,
                month_number
            )

            monthly_counts[key] = (
                monthly_counts.get(
                    key,
                    0
                )
                +
                count
            )

        print(
            f"  [chunk {i}] "
            f"{len(chunk):,} rows processed"
        )

    series = pd.Series(
        monthly_counts
    )

    long_df = (
        series
        .reset_index()
    )

    long_df.columns = [
        "grid_id",
        "month",
        "count"
    ]

    profile = (
        long_df
        .pivot(
            index="grid_id",
            columns="month",
            values="count"
        )
        .fillna(0)
    )

    profile.columns = [
        f"m{c}"
        for c in profile.columns
    ]

    for month_number in range(
        1,
        13
    ):

        col = f"m{month_number}"

        if col not in profile.columns:

            profile[col] = 0.0

    profile = (
        profile
        .reset_index()
    )

    print(
        f"Monthly profile built for "
        f"{len(profile):,} grid cells."
    )

    return profile


# ============================================================
# SEASONAL SIGNALS
# ============================================================

def add_seasonal_signals(
    profile
):

    month_cols = [
        f"m{i}"
        for i in range(1, 13)
    ]

    profile[
        "total_from_profile"
    ] = (
        profile[
            month_cols
        ]
        .sum(axis=1)
    )

    safe_total = (
        profile[
            "total_from_profile"
        ]
        .replace(
            0,
            np.nan
        )
    )

    profile[
        "stubble_frac"
    ] = (
        profile[
            [
                f"m{m}"
                for m in STUBBLE_MONTHS
            ]
        ]
        .sum(axis=1)
        /
        safe_total
    )

    profile[
        "dry_season_frac"
    ] = (
        profile[
            [
                f"m{m}"
                for m in DRY_SEASON_MONTHS
            ]
        ]
        .sum(axis=1)
        /
        safe_total
    )

    month_mean = (
        profile[
            month_cols
        ]
        .mean(axis=1)
        .replace(
            0,
            np.nan
        )
    )

    profile[
        "flat_ratio"
    ] = (
        profile[
            month_cols
        ]
        .max(axis=1)
        /
        month_mean
    )

    profile[
        "peak_month"
    ] = (
        profile[
            month_cols
        ]
        .idxmax(
            axis=1
        )
    )

    return profile


# ============================================================
# LOAD REAL CATEGORY POINTS
# ============================================================

def load_site_file(
    filepath,
    category
):

    if not filepath.exists():

        print(
            f"NOTE: {filepath} not found."
        )

        return pd.DataFrame(
            columns=[
                "latitude",
                "longitude",
                "site_name",
                "site_type",
                "category"
            ]
        )

    sites = pd.read_csv(
        filepath,
        low_memory=False
    )

    if not {
        "latitude",
        "longitude"
    }.issubset(
        sites.columns
    ):

        print(
            f"WARNING: {filepath} "
            f"does not contain latitude/longitude."
        )

        return pd.DataFrame(
            columns=[
                "latitude",
                "longitude",
                "site_name",
                "site_type",
                "category"
            ]
        )

    sites["latitude"] = pd.to_numeric(
        sites["latitude"],
        errors="coerce"
    )

    sites["longitude"] = pd.to_numeric(
        sites["longitude"],
        errors="coerce"
    )

    sites = sites.dropna(
        subset=[
            "latitude",
            "longitude"
        ]
    ).copy()

    if "name" in sites.columns:

        sites["site_name"] = (
            sites["name"]
            .fillna("")
            .astype(str)
        )

    elif "site_name" not in sites.columns:

        sites["site_name"] = (
            category
            .replace("_", " ")
            .title()
        )

    if "type" in sites.columns:

        sites["site_type"] = (
            sites["type"]
            .fillna("")
            .astype(str)
        )

    elif "site_type" not in sites.columns:

        sites["site_type"] = (
            category
            .replace("_", " ")
            .title()
        )

    sites["category"] = category

    return sites[
        [
            "latitude",
            "longitude",
            "site_name",
            "site_type",
            "category"
        ]
    ].reset_index(
        drop=True
    )


# ============================================================
# ATTACH REAL CATEGORY COORDINATE
# ============================================================

def attach_real_category_coordinate(
    df,
    category,
    sites,
    radius_km
):

    """
    Match each classified grid cell to the nearest REAL
    category-specific GIS point.

    The display coordinate is changed only if a real point
    exists within the configured radius.
    """

    if len(sites) == 0:

        return df

    category_mask = (
        df["fire_type"]
        ==
        category
    )

    if not category_mask.any():

        return df

    target_indices = (
        df.index[
            category_mask
        ]
        .to_numpy()
    )

    target_lat = (
        df.loc[
            target_indices,
            "latitude"
        ]
        .to_numpy()
    )

    target_lon = (
        df.loc[
            target_indices,
            "longitude"
        ]
        .to_numpy()
    )

    site_lat = (
        sites[
            "latitude"
        ]
        .to_numpy()
    )

    site_lon = (
        sites[
            "longitude"
        ]
        .to_numpy()
    )

    nearest_distance = np.full(
        len(target_indices),
        np.inf
    )

    nearest_index = np.full(
        len(target_indices),
        -1,
        dtype=int
    )

    for i, (
        lat,
        lon
    ) in enumerate(
        zip(
            site_lat,
            site_lon
        )
    ):

        distances = haversine_km(
            target_lat,
            target_lon,
            lat,
            lon
        )

        mask = (
            distances
            <
            nearest_distance
        )

        nearest_distance[mask] = (
            distances[mask]
        )

        nearest_index[mask] = i

    matched = (
        (
            nearest_distance
            <= radius_km
        )
        &
        (
            nearest_index >= 0
        )
    )

    for local_i, row_index in enumerate(
        target_indices
    ):

        if not matched[local_i]:

            continue

        site_index = (
            nearest_index[
                local_i
            ]
        )

        site = sites.iloc[
            site_index
        ]

        df.at[
            row_index,
            "display_latitude"
        ] = site[
            "latitude"
        ]

        df.at[
            row_index,
            "display_longitude"
        ] = site[
            "longitude"
        ]

        df.at[
            row_index,
            "display_site_name"
        ] = site[
            "site_name"
        ]

        df.at[
            row_index,
            "display_site_type"
        ] = site[
            "site_type"
        ]

        df.at[
            row_index,
            "coordinate_source"
        ] = (
            category
            + "_REAL_GIS_COORDINATE"
        )

        df.at[
            row_index,
            "display_coordinate_distance_km"
        ] = nearest_distance[
            local_i
        ]

    print(
        f"{category}: "
        f"{int(matched.sum())} grid cells "
        f"matched to real GIS coordinates."
    )

    return df


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_row(
    row
):

    # --------------------------------------------------------
    # Industrial real-site evidence
    # --------------------------------------------------------

    distance = row.get(
        "distance_to_industrial_site_km",
        np.nan
    )

    near_industrial = (
        pd.notna(distance)
        and
        distance
        <= INDUSTRIAL_PROXIMITY_KM
    )

    if (
        near_industrial
        and
        row["total_detections"] >= 5
    ):

        confidence = min(
            1.0,
            0.60
            +
            (
                (
                    INDUSTRIAL_PROXIMITY_KM
                    -
                    distance
                )
                /
                INDUSTRIAL_PROXIMITY_KM
                *
                0.40
            )
        )

        return (
            "INDUSTRIAL_PERSISTENT",
            round(
                confidence,
                2
            ),
            (
                f"Within {distance:.1f} km "
                f"of a real industrial facility "
                f"with {int(row['total_detections'])} "
                f"historical FIRMS detections."
            ),
        )

    # --------------------------------------------------------
    # Persistent industrial pattern
    # --------------------------------------------------------

    if (
        row["flat_ratio"]
        <= FLAT_RATIO_MAX
        and
        row["recurrence_ratio"]
        >= RECURRENCE_MIN_INDUSTRIAL
        and
        row["active_years"]
        >= 3
    ):

        return (
            "INDUSTRIAL_PERSISTENT",
            round(
                min(
                    1.0,
                    row[
                        "recurrence_ratio"
                    ]
                ),
                2
            ),
            (
                f"Persistent thermal activity "
                f"across {int(row['active_years'])} "
                f"years at the same grid location."
            ),
        )

    # --------------------------------------------------------
    # Agricultural burning
    # --------------------------------------------------------

    if (
        row["stubble_frac"]
        >= STUBBLE_FRAC_MIN
        and
        row["recurrence_ratio"]
        <
        RECURRENCE_MAX_AGRICULTURE
    ):

        return (
            "AGRICULTURAL_BURNING",
            round(
                min(
                    1.0,
                    row[
                        "stubble_frac"
                    ]
                ),
                2
            ),
            (
                f"{row['stubble_frac'] * 100:.0f}% "
                f"of detections occur during "
                f"Apr-May / Oct-Nov agricultural "
                f"burning windows."
            ),
        )

    # --------------------------------------------------------
    # Forest wildfire
    # --------------------------------------------------------

    if (
        row["dry_season_frac"]
        >= DRY_FRAC_MIN
        and
        row["stubble_frac"]
        <
        STUBBLE_FRAC_MIN
        and
        row["recurrence_ratio"]
        <
        RECURRENCE_MAX_WILDFIRE
    ):

        return (
            "FOREST_WILDFIRE",
            round(
                min(
                    1.0,
                    row[
                        "dry_season_frac"
                    ]
                ),
                2
            ),
            (
                f"{row['dry_season_frac'] * 100:.0f}% "
                f"of detections occur during the "
                f"Mar-Jun dry season."
            ),
        )

    return (
        "UNCLASSIFIED",
        0.0,
        (
            "No single seasonal or recurrence "
            "pattern was strong enough."
        ),
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print(
        "THERMOSCOPE / AGNIRAKSHAK"
    )
    print(
        "FIRE-TYPE CLASSIFICATION + REAL COORDINATES"
    )
    print("=" * 70)

    if not GRID_FEATURES_FILE.exists():

        raise FileNotFoundError(
            f"Input file not found: "
            f"{GRID_FEATURES_FILE}"
        )

    grid_df = pd.read_csv(
        GRID_FEATURES_FILE,
        low_memory=False
    )

    print(
        f"Grid cells loaded: "
        f"{len(grid_df):,}"
    )

    # --------------------------------------------------------
    # Monthly profile
    # --------------------------------------------------------

    profile = build_monthly_profile()

    profile = add_seasonal_signals(
        profile
    )

    # --------------------------------------------------------
    # Merge profile
    # --------------------------------------------------------

    df = grid_df.merge(
        profile[
            [
                "grid_id",
                "stubble_frac",
                "dry_season_frac",
                "flat_ratio",
                "peak_month"
            ]
        ],
        on="grid_id",
        how="left"
    )

    # --------------------------------------------------------
    # Industrial real-site distance
    # --------------------------------------------------------

    industrial_sites = load_site_file(
        INDUSTRIAL_SITES_FILE,
        "INDUSTRIAL"
    )

    df[
        "distance_to_industrial_site_km"
    ] = np.nan

    if len(industrial_sites) > 0:

        grid_lat = (
            df[
                "latitude"
            ]
            .to_numpy()
        )

        grid_lon = (
            df[
                "longitude"
            ]
            .to_numpy()
        )

        site_lat = (
            industrial_sites[
                "latitude"
            ]
            .to_numpy()
        )

        site_lon = (
            industrial_sites[
                "longitude"
            ]
            .to_numpy()
        )

        min_distance = np.full(
            len(df),
            np.inf
        )

        for lat, lon in zip(
            site_lat,
            site_lon
        ):

            distances = haversine_km(
                grid_lat,
                grid_lon,
                lat,
                lon
            )

            min_distance = np.minimum(
                min_distance,
                distances
            )

        df[
            "distance_to_industrial_site_km"
        ] = min_distance

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    print()
    print(
        "Applying fire-type classification..."
    )

    classified = df.apply(
        classify_row,
        axis=1,
        result_type="expand"
    )

    classified.columns = [
        "fire_type",
        "fire_type_confidence",
        "fire_type_reason"
    ]

    df = pd.concat(
        [
            df,
            classified
        ],
        axis=1
    )

    # --------------------------------------------------------
    # DISPLAY COORDINATES
    # --------------------------------------------------------

    #
    # DEFAULT:
    # FIRMS/grid coordinate.
    #
    df[
        "display_latitude"
    ] = df[
        "latitude"
    ]

    df[
        "display_longitude"
    ] = df[
        "longitude"
    ]

    df[
        "display_site_name"
    ] = ""

    df[
        "display_site_type"
    ] = ""

    df[
        "display_coordinate_distance_km"
    ] = np.nan

    df[
        "coordinate_source"
    ] = "NASA_FIRMS_GRID"

    # --------------------------------------------------------
    # Industrial
    # --------------------------------------------------------

    df = attach_real_category_coordinate(
        df,
        "INDUSTRIAL_PERSISTENT",
        industrial_sites,
        INDUSTRIAL_PROXIMITY_KM
    )

    # --------------------------------------------------------
    # Agriculture
    #
    # Expected:
    # data/processed/agricultural_sites.csv
    # --------------------------------------------------------

    agricultural_sites = load_site_file(
        AGRICULTURAL_SITES_FILE,
        "AGRICULTURAL_BURNING"
    )

    df = attach_real_category_coordinate(
        df,
        "AGRICULTURAL_BURNING",
        agricultural_sites,
        5.0
    )

    # --------------------------------------------------------
    # Forest
    #
    # Expected:
    # data/processed/forest_sites.csv
    # --------------------------------------------------------

    forest_sites = load_site_file(
        FOREST_SITES_FILE,
        "FOREST_WILDFIRE"
    )

    df = attach_real_category_coordinate(
        df,
        "FOREST_WILDFIRE",
        forest_sites,
        5.0
    )

    # --------------------------------------------------------
    # Risk
    # --------------------------------------------------------

    if RISK_FILE.exists():

        risk_df = pd.read_csv(
            RISK_FILE,
            low_memory=False
        )

        risk_columns = [
            "grid_id",
            "risk_score",
            "risk_level"
        ]

        risk_columns = [
            col
            for col in risk_columns
            if col in risk_df.columns
        ]

        if "grid_id" in risk_columns:

            df = df.merge(
                risk_df[
                    risk_columns
                ],
                on="grid_id",
                how="left"
            )

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    output_columns = [

        "grid_id",

        # Original FIRMS/grid
        "latitude",
        "longitude",

        # IMPORTANT:
        # Dashboard should use these
        "display_latitude",
        "display_longitude",

        "coordinate_source",
        "display_coordinate_distance_km",

        "display_site_name",
        "display_site_type",

        # Classification
        "fire_type",
        "fire_type_confidence",
        "fire_type_reason",

        # Seasonal
        "stubble_frac",
        "dry_season_frac",
        "flat_ratio",

        # Industrial evidence
        "distance_to_industrial_site_km",

        # FIRMS history
        "total_detections",
        "active_years",
        "recurrence_ratio",
    ]

    if "risk_score" in df.columns:

        output_columns.append(
            "risk_score"
        )

    if "risk_level" in df.columns:

        output_columns.append(
            "risk_level"
        )

    output_columns = [
        col
        for col in output_columns
        if col in df.columns
    ]

    result = (
        df[
            output_columns
        ]
        .sort_values(
            "fire_type_confidence",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "CLASSIFICATION COMPLETE"
    )
    print("=" * 70)

    print(
        result[
            "fire_type"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print(
        "COORDINATE SOURCES:"
    )

    print(
        result[
            "coordinate_source"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print(
        f"Saved to: {OUTPUT_FILE}"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "NASA FIRMS remains the primary fire-detection source."
    )

    print(
        "Grid coordinates are used for spatial risk aggregation."
    )

    print(
        "Industrial display coordinates come from real "
        "industrial-site records when available."
    )

    print(
        "Agricultural/forest display coordinates come from "
        "their dedicated GIS point layers when available."
    )

    print(
        "If a real category GIS layer is unavailable, the "
        "system safely falls back to the FIRMS coordinate and "
        "labels the source accordingly."
    )

    print("=" * 70)


if __name__ == "__main__":
    main()