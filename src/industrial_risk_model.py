from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# THERMOSCOPE
# ACTIVE INDUSTRIAL FIRE RISK MODEL
#
# NASA FIRMS = PRIMARY FIRE SIGNAL
# REAL INDUSTRIAL SITE = CONTEXTUAL EVIDENCE
#
# IMPORTANT:
# ------------------------------------------------------------
# Risk is calculated on spatial grid cells.
#
# Display coordinates for INDUSTRIAL category come from the
# actual industrial_sites.csv coordinates, NOT from the grid
# centroid / FIRMS average coordinate.
# ============================================================


INPUT_GRID = Path(
    "data/processed/grid_features.csv"
)

INPUT_INDUSTRIAL = Path(
    "data/processed/industrial_features.csv"
)

INDUSTRIAL_SITES_FILE = Path(
    "data/processed/industrial_sites.csv"
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
    "industrial_fire_risk.csv"
)

TOP10_FILE = (
    OUTPUT_DIR /
    "top10_industrial_risk.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

RECENT_DAYS = 30

MIN_RECENT_DETECTIONS = 1

INDUSTRIAL_WEIGHT = 0.30

THERMAL_WEIGHT = 0.70

INDUSTRIAL_MATCH_RADIUS_KM = 3.0


# ============================================================
# HELPERS
# ============================================================

def safe_minmax(series):

    series = pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(0)

    minimum = series.min()
    maximum = series.max()

    if maximum <= minimum:

        return pd.Series(
            0.0,
            index=series.index
        )

    return (
        (
            series - minimum
        )
        /
        (
            maximum - minimum
        )
        * 100.0
    )


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
# LOAD DATA
# ============================================================

def load_data():

    print("=" * 70)
    print("THERMOSCOPE - ACTIVE INDUSTRIAL FIRE RISK")
    print("=" * 70)

    if not INPUT_GRID.exists():

        raise FileNotFoundError(
            f"Missing file: {INPUT_GRID}"
        )

    grid = pd.read_csv(
        INPUT_GRID,
        low_memory=False
    )

    print(
        f"Grid cells: {len(grid):,}"
    )

    if not INPUT_INDUSTRIAL.exists():

        raise FileNotFoundError(
            f"Missing file: {INPUT_INDUSTRIAL}\n"
            "Run industrial_features.py first."
        )

    industrial = pd.read_csv(
        INPUT_INDUSTRIAL,
        low_memory=False
    )

    print(
        f"Industrial cells: {len(industrial):,}"
    )

    return grid, industrial


# ============================================================
# COMBINE DATA
# ============================================================

def combine_data(
    grid,
    industrial
):

    print()
    print(
        "Combining FIRMS + industrial context..."
    )

    industrial = industrial.loc[
        :,
        ~industrial.columns.duplicated()
    ].copy()

    grid = grid.loc[
        :,
        ~grid.columns.duplicated()
    ].copy()

    duplicate_columns = [
        col
        for col in industrial.columns
        if (
            col != "grid_id"
            and col in grid.columns
        )
    ]

    if duplicate_columns:

        industrial = industrial.drop(
            columns=duplicate_columns
        )

    combined = grid.merge(
        industrial,
        on="grid_id",
        how="left"
    )

    combined = combined.loc[
        :,
        ~combined.columns.duplicated()
    ].copy()

    print(
        f"Combined cells: {len(combined):,}"
    )

    return combined


# ============================================================
# REAL INDUSTRIAL SITE MATCHING
# ============================================================

def attach_real_industrial_coordinates(df):

    """
    Attach ACTUAL industrial facility coordinates.

    Priority:
        industrial_sites.csv

    The grid coordinates are NEVER used as the industrial
    facility coordinates when a real site is available.
    """

    print()
    print(
        "Attaching real industrial-site coordinates..."
    )

    if not INDUSTRIAL_SITES_FILE.exists():

        print(
            "WARNING: industrial_sites.csv not found."
        )

        df["industrial_site_latitude"] = np.nan
        df["industrial_site_longitude"] = np.nan
        df["industrial_site_name"] = ""
        df["industrial_site_type"] = ""
        df["distance_to_industrial_site_km"] = np.nan
        df["coordinate_source"] = "FIRMS_GRID_ONLY"

        return df

    sites = pd.read_csv(
        INDUSTRIAL_SITES_FILE,
        low_memory=False
    )

    required = {
        "latitude",
        "longitude"
    }

    if not required.issubset(
        sites.columns
    ):

        print(
            "WARNING: industrial_sites.csv "
            "does not contain latitude/longitude."
        )

        df["industrial_site_latitude"] = np.nan
        df["industrial_site_longitude"] = np.nan
        df["industrial_site_name"] = ""
        df["industrial_site_type"] = ""
        df["distance_to_industrial_site_km"] = np.nan
        df["coordinate_source"] = "FIRMS_GRID_ONLY"

        return df

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
    ).reset_index(drop=True)

    print(
        f"Real industrial sites loaded: "
        f"{len(sites):,}"
    )

    if len(sites) == 0:

        df["industrial_site_latitude"] = np.nan
        df["industrial_site_longitude"] = np.nan
        df["industrial_site_name"] = ""
        df["industrial_site_type"] = ""
        df["distance_to_industrial_site_km"] = np.nan
        df["coordinate_source"] = "FIRMS_GRID_ONLY"

        return df

    grid_lat = pd.to_numeric(
        df["latitude"],
        errors="coerce"
    ).to_numpy()

    grid_lon = pd.to_numeric(
        df["longitude"],
        errors="coerce"
    ).to_numpy()

    site_lat = sites[
        "latitude"
    ].to_numpy()

    site_lon = sites[
        "longitude"
    ].to_numpy()

    nearest_distance = np.full(
        len(df),
        np.inf
    )

    nearest_index = np.full(
        len(df),
        -1,
        dtype=int
    )

    # --------------------------------------------------------
    # Find nearest REAL industrial facility
    # --------------------------------------------------------

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
            grid_lat,
            grid_lon,
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

    df[
        "distance_to_industrial_site_km"
    ] = nearest_distance

    df[
        "industrial_site_latitude"
    ] = np.nan

    df[
        "industrial_site_longitude"
    ] = np.nan

    df[
        "industrial_site_name"
    ] = ""

    df[
        "industrial_site_type"
    ] = ""

    # --------------------------------------------------------
    # Attach actual coordinates only when reasonably close
    # --------------------------------------------------------

    matched = (
        (
            nearest_distance
            <= INDUSTRIAL_MATCH_RADIUS_KM
        )
        &
        (
            nearest_index >= 0
        )
    )

    if "name" in sites.columns:

        names = sites[
            "name"
        ].fillna("").astype(str).to_numpy()

    elif "site_name" in sites.columns:

        names = sites[
            "site_name"
        ].fillna("").astype(str).to_numpy()

    else:

        names = np.array(
            [
                "Industrial Site"
            ]
            * len(sites)
        )

    if "type" in sites.columns:

        types = sites[
            "type"
        ].fillna("").astype(str).to_numpy()

    elif "site_type" in sites.columns:

        types = sites[
            "site_type"
        ].fillna("").astype(str).to_numpy()

    else:

        types = np.array(
            [
                "Industrial"
            ]
            * len(sites)
        )

    valid_rows = np.where(
        matched
    )[0]

    for row_index in valid_rows:

        site_index = nearest_index[
            row_index
        ]

        df.at[
            row_index,
            "industrial_site_latitude"
        ] = sites.iloc[
            site_index
        ]["latitude"]

        df.at[
            row_index,
            "industrial_site_longitude"
        ] = sites.iloc[
            site_index
        ]["longitude"]

        df.at[
            row_index,
            "industrial_site_name"
        ] = names[
            site_index
        ]

        df.at[
            row_index,
            "industrial_site_type"
        ] = types[
            site_index
        ]

    df[
        "coordinate_source"
    ] = np.where(
        matched,
        "REAL_INDUSTRIAL_SITE",
        "FIRMS_GRID_ONLY"
    )

    print(
        "Grid cells matched to real "
        "industrial sites:",
        int(matched.sum())
    )

    return df


# ============================================================
# INDUSTRIAL CONTEXT SCORE
# ============================================================

def calculate_industrial_score(df):

    print()
    print(
        "Calculating industrial context..."
    )

    infrastructure_columns = [
        "industrial_area_count",
        "factory_count",
        "warehouse_count",
        "power_plant_count",
        "manufacturing_count",
        "refinery_count",
        "storage_count",
        "chemical_count",
        "steel_count",
        "oil_count",
        "gas_count",
    ]

    for column in infrastructure_columns:

        if column not in df.columns:

            df[column] = 0

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        ).fillna(0)

    raw_score = (
        df["industrial_area_count"] * 1.0
        + df["factory_count"] * 2.5
        + df["warehouse_count"] * 1.5
        + df["power_plant_count"] * 2.0
        + df["manufacturing_count"] * 2.5
        + df["refinery_count"] * 3.0
        + df["storage_count"] * 2.0
        + df["chemical_count"] * 3.0
        + df["steel_count"] * 2.5
        + df["oil_count"] * 3.0
        + df["gas_count"] * 3.0
    )

    df[
        "industrial_context_raw"
    ] = raw_score

    df[
        "industrial_context_score"
    ] = safe_minmax(
        raw_score
    )

    # A REAL SITE match is additional evidence.
    df[
        "has_real_industrial_site"
    ] = (
        df[
            "coordinate_source"
        ]
        ==
        "REAL_INDUSTRIAL_SITE"
    ).astype(int)

    df[
        "has_industrial_context"
    ] = (
        (
            raw_score > 0
        )
        |
        (
            df[
                "has_real_industrial_site"
            ] == 1
        )
    ).astype(int)

    print(
        "Industrial-context cells:",
        int(
            df[
                "has_industrial_context"
            ].sum()
        )
    )

    return df


# ============================================================
# RECENT NASA FIRMS ACTIVITY
# ============================================================

def calculate_recent_activity(df):

    print()
    print(
        f"Calculating recent NASA FIRMS "
        f"activity ({RECENT_DAYS} days)..."
    )

    required_columns = [
        "detections_30d",
        "active_days_30d",
        "avg_frp_30d",
        "max_frp_30d",
    ]

    for column in required_columns:

        if column not in df.columns:

            df[column] = 0

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        ).fillna(0)

    df[
        "has_recent_firms"
    ] = (
        df[
            "detections_30d"
        ]
        >= MIN_RECENT_DETECTIONS
    ).astype(int)

    print(
        "Cells with recent FIRMS activity:",
        int(
            df[
                "has_recent_firms"
            ].sum()
        )
    )

    detection_score = safe_minmax(
        np.log1p(
            df[
                "detections_30d"
            ]
        )
    )

    active_days_score = safe_minmax(
        df[
            "active_days_30d"
        ]
    )

    avg_frp_score = safe_minmax(
        df[
            "avg_frp_30d"
        ]
    )

    max_frp_score = safe_minmax(
        df[
            "max_frp_30d"
        ]
    )

    df[
        "recent_thermal_score"
    ] = (
        detection_score * 0.35
        + active_days_score * 0.20
        + avg_frp_score * 0.25
        + max_frp_score * 0.20
    )

    df.loc[
        df[
            "has_recent_firms"
        ] == 0,
        "recent_thermal_score"
    ] = 0

    return df


# ============================================================
# ACTIVE INDUSTRIAL FIRE RISK
# ============================================================

def calculate_risk(df):

    print()
    print(
        "Calculating ACTIVE INDUSTRIAL FIRE RISK..."
    )

    df[
        "industrial_fire_risk"
    ] = 0.0

    # --------------------------------------------------------
    # Recent FIRMS is mandatory.
    # --------------------------------------------------------

    active_mask = (
        (
            df[
                "has_recent_firms"
            ] == 1
        )
        &
        (
            df[
                "has_industrial_context"
            ] == 1
        )
    )

    raw_risk = (
        df[
            "recent_thermal_score"
        ]
        * THERMAL_WEIGHT
        +
        df[
            "industrial_context_score"
        ]
        * INDUSTRIAL_WEIGHT
    )

    df.loc[
        active_mask,
        "industrial_fire_risk"
    ] = raw_risk.loc[
        active_mask
    ]

    active_values = df.loc[
        active_mask,
        "industrial_fire_risk"
    ]

    if len(active_values) > 0:

        minimum = active_values.min()
        maximum = active_values.max()

        if maximum > minimum:

            df.loc[
                active_mask,
                "industrial_fire_risk"
            ] = (
                (
                    active_values - minimum
                )
                /
                (
                    maximum - minimum
                )
                * 100
            )

        else:

            df.loc[
                active_mask,
                "industrial_fire_risk"
            ] = 50.0

    # --------------------------------------------------------
    # Risk level
    # --------------------------------------------------------

    df[
        "risk_level"
    ] = "NO ACTIVE SIGNAL"

    df.loc[
        active_mask
        &
        (
            df[
                "industrial_fire_risk"
            ] < 25
        ),
        "risk_level"
    ] = "LOW"

    df.loc[
        active_mask
        &
        (
            df[
                "industrial_fire_risk"
            ] >= 25
        )
        &
        (
            df[
                "industrial_fire_risk"
            ] < 50
        ),
        "risk_level"
    ] = "MODERATE"

    df.loc[
        active_mask
        &
        (
            df[
                "industrial_fire_risk"
            ] >= 50
        )
        &
        (
            df[
                "industrial_fire_risk"
            ] < 75
        ),
        "risk_level"
    ] = "HIGH"

    df.loc[
        active_mask
        &
        (
            df[
                "industrial_fire_risk"
            ] >= 75
        ),
        "risk_level"
    ] = "CRITICAL"

    df[
        "industrial_fire_candidate"
    ] = (
        active_mask
    ).astype(int)

    print(
        "Potential active industrial-fire cells:",
        int(
            df[
                "industrial_fire_candidate"
            ].sum()
        )
    )

    return df


# ============================================================
# RANK
# ============================================================

def rank_candidates(df):

    print()
    print(
        "Ranking active industrial-fire candidates..."
    )

    df[
        "risk_rank"
    ] = np.nan

    active_mask = (
        df[
            "industrial_fire_candidate"
        ] == 1
    )

    active = df.loc[
        active_mask
    ].copy()

    if len(active) > 0:

        active = active.sort_values(
            "industrial_fire_risk",
            ascending=False
        )

        active[
            "risk_rank"
        ] = np.arange(
            1,
            len(active) + 1
        )

        df.loc[
            active.index,
            "risk_rank"
        ] = active[
            "risk_rank"
        ]

    return df


# ============================================================
# SAVE OUTPUTS
# ============================================================

def save_outputs(df):

    print()
    print(
        "Saving active industrial fire layer..."
    )

    preferred_columns = [

        "grid_id",

        # ----------------------------------------------------
        # Original FIRMS/grid coordinates
        # ----------------------------------------------------

        "latitude",
        "longitude",
        "grid_lat",
        "grid_lon",

        # ----------------------------------------------------
        # REAL INDUSTRIAL coordinates
        # ----------------------------------------------------

        "industrial_site_latitude",
        "industrial_site_longitude",
        "industrial_site_name",
        "industrial_site_type",

        "distance_to_industrial_site_km",

        "coordinate_source",

        # ----------------------------------------------------
        # Risk
        # ----------------------------------------------------

        "industrial_fire_risk",
        "risk_level",
        "risk_rank",
        "industrial_fire_candidate",

        # ----------------------------------------------------
        # FIRMS
        # ----------------------------------------------------

        "detections_30d",
        "active_days_30d",
        "avg_frp_30d",
        "max_frp_30d",

        # ----------------------------------------------------
        # Industrial context
        # ----------------------------------------------------

        "industrial_context_score",
        "industrial_area_count",
        "factory_count",
        "warehouse_count",
        "power_plant_count",
        "manufacturing_count",
        "refinery_count",
        "storage_count",
        "chemical_count",
        "steel_count",
        "oil_count",
        "gas_count",

        # ----------------------------------------------------
        # Supporting
        # ----------------------------------------------------

        "recent_thermal_score",
        "has_recent_firms",
        "has_industrial_context",
        "has_real_industrial_site",
    ]

    available = [
        col
        for col in preferred_columns
        if col in df.columns
    ]

    result = df[
        available
    ].copy()

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    top10 = result[
        result[
            "industrial_fire_candidate"
        ] == 1
    ].sort_values(
        "industrial_fire_risk",
        ascending=False
    ).head(10)

    top10.to_csv(
        TOP10_FILE,
        index=False
    )

    print(
        f"Saved: {OUTPUT_FILE}"
    )

    print(
        f"Saved: {TOP10_FILE}"
    )

    return result, top10


# ============================================================
# SUMMARY
# ============================================================

def display_summary(
    result,
    top10
):

    print()
    print("=" * 70)
    print(
        "ACTIVE INDUSTRIAL FIRE RISK SUMMARY"
    )
    print("=" * 70)

    print(
        "Cells with industrial context:",
        int(
            result[
                "has_industrial_context"
            ].sum()
        )
    )

    print(
        "Cells with recent FIRMS activity:",
        int(
            result[
                "has_recent_firms"
            ].sum()
        )
    )

    print(
        "Potential industrial-fire cells:",
        int(
            result[
                "industrial_fire_candidate"
            ].sum()
        )
    )

    print(
        "Cells linked to REAL industrial sites:",
        int(
            result[
                "has_real_industrial_site"
            ].sum()
        )
    )

    print()
    print("Risk distribution:")

    print(
        result[
            "risk_level"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print("=" * 70)
    print(
        "TOP ACTIVE INDUSTRIAL FIRE RISK ZONES"
    )
    print("=" * 70)

    if len(top10) > 0:

        display_columns = [

            "risk_rank",

            "grid_id",

            # Real facility coordinates
            "industrial_site_latitude",
            "industrial_site_longitude",

            "industrial_site_name",
            "industrial_site_type",

            "distance_to_industrial_site_km",

            "industrial_fire_risk",
            "risk_level",

            "detections_30d",
            "active_days_30d",
            "avg_frp_30d",
            "max_frp_30d",

            "factory_count",
            "power_plant_count",

            "coordinate_source",
        ]

        display_columns = [
            col
            for col in display_columns
            if col in top10.columns
        ]

        print(
            top10[
                display_columns
            ].to_string(
                index=False
            )
        )

    else:

        print(
            "No active industrial-fire candidates "
            "found in recent FIRMS window."
        )

    print()
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    grid, industrial = load_data()

    combined = combine_data(
        grid,
        industrial
    )

    # --------------------------------------------------------
    # FIRST attach real industrial coordinates
    # --------------------------------------------------------

    combined = (
        attach_real_industrial_coordinates(
            combined
        )
    )

    combined = calculate_industrial_score(
        combined
    )

    combined = calculate_recent_activity(
        combined
    )

    combined = calculate_risk(
        combined
    )

    combined = rank_candidates(
        combined
    )

    result, top10 = save_outputs(
        combined
    )

    display_summary(
        result,
        top10
    )

    print()
    print("MODEL LOGIC:")
    print(
        "NASA FIRMS recent thermal activity = PRIMARY SIGNAL"
    )
    print(
        "Industrial infrastructure = CONTEXTUAL EVIDENCE"
    )
    print(
        "Real industrial site coordinates = DISPLAY LOCATION"
    )
    print(
        "Historical-only cells = NO ACTIVE SIGNAL"
    )

    print()
    print("IMPORTANT:")
    print(
        "High/Critical means potential industrial-fire "
        "risk, NOT a confirmed fire."
    )

    print(
        "FIRMS remains the primary fire-detection source."
    )

    print(
        "Grid coordinates are NOT treated as industrial "
        "facility coordinates."
    )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()