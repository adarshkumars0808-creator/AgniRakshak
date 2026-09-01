from pathlib import Path
import time
import requests
import numpy as np
import pandas as pd
import geopandas as gpd

from shapely.geometry import Point


# ============================================================
# THERMOSCOPE
# INDUSTRIAL CONTEXT LAYER
# ============================================================
#
# Purpose:
# Combine FIRMS thermal-risk grids with industrial context.
#
# IMPORTANT:
# FIRMS remains the primary fire-data source.
# OpenStreetMap is used ONLY as contextual information
# to determine whether a thermal-risk grid is near
# industrial infrastructure.
# ============================================================


# ============================================================
# FILES
# ============================================================

INPUT_FILE = Path(
    "data/processed/grid_features.csv"
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
    "industrial_features.csv"
)


# ============================================================
# SETTINGS
# ============================================================

# Distance around each grid centre used to detect
# nearby industrial infrastructure.
#
# 5000 metres = approximately 5 km.
INDUSTRIAL_RADIUS_METERS = 5000


# Overpass API
OVERPASS_URL = (
    "https://overpass-api.de/api/interpreter"
)


# ============================================================
# INDUSTRIAL OSM TAGS
# ============================================================

INDUSTRIAL_QUERIES = {

    "industrial_areas": """
        nwr["landuse"="industrial"]({bbox});
    """,

    "factories": """
        nwr["industrial"="factory"]({bbox});
    """,

    "manufacturing": """
        nwr["industrial"="manufacture"]({bbox});
    """,

    "refineries": """
        nwr["industrial"="refinery"]({bbox});
    """,

    "power_plants": """
        nwr["power"="plant"]({bbox});
    """,

    "warehouses": """
        nwr["building"="warehouse"]({bbox});
    """,

    "storage": """
        nwr["industrial"="storage"]({bbox});
    """,

    "chemical": """
        nwr["industrial"="chemical"]({bbox});
    """,

    "steel": """
        nwr["industrial"="steelmaking"]({bbox});
    """,

    "oil": """
        nwr["industrial"="oil"]({bbox});
    """,

    "gas": """
        nwr["industrial"="gas"]({bbox});
    """,
}


# ============================================================
# LOAD GRID
# ============================================================

def load_grid():

    print("=" * 70)
    print("THERMOSCOPE - INDUSTRIAL CONTEXT LAYER")
    print("=" * 70)

    print()
    print(f"Input: {INPUT_FILE}")

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}\n"
            "Run grid_features.py first."
        )

    df = pd.read_csv(
        INPUT_FILE,
        low_memory=False
    )

    print(
        f"Grid cells loaded: {len(df):,}"
    )

    required = [
        "grid_id",
        "latitude",
        "longitude",
    ]

    missing = [
        col for col in required
        if col not in df.columns
    ]

    if missing:

        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing)
        )

    return df


# ============================================================
# BUILD BOUNDING BOX
# ============================================================

def get_bbox(df):

    min_lat = float(
        df["latitude"].min()
    )

    max_lat = float(
        df["latitude"].max()
    )

    min_lon = float(
        df["longitude"].min()
    )

    max_lon = float(
        df["longitude"].max()
    )

    # Small buffer
    buffer = 0.10

    min_lat -= buffer
    max_lat += buffer
    min_lon -= buffer
    max_lon += buffer

    print()
    print(
        "Bounding box:"
    )

    print(
        f"{min_lat}, "
        f"{min_lon}, "
        f"{max_lat}, "
        f"{max_lon}"
    )

    return (
        min_lat,
        min_lon,
        max_lat,
        max_lon
    )


# ============================================================
# OVERPASS QUERY
# ============================================================

def build_query(
    min_lat,
    min_lon,
    max_lat,
    max_lon
):

    bbox = (
        f"{min_lat},"
        f"{min_lon},"
        f"{max_lat},"
        f"{max_lon}"
    )

    parts = []

    for query in INDUSTRIAL_QUERIES.values():

        parts.append(
            query.format(
                bbox=bbox
            )
        )

    query = f"""
    [out:json][timeout:180];

    (
        {"".join(parts)}
    );

    out center tags;
    """

    return query


# ============================================================
# DOWNLOAD OSM DATA
# ============================================================

def download_industrial_data(
    df
):

    print()
    print(
        "Downloading industrial context "
        "from OpenStreetMap..."
    )

    (
        min_lat,
        min_lon,
        max_lat,
        max_lon
    ) = get_bbox(df)

    query = build_query(
        min_lat,
        min_lon,
        max_lat,
        max_lon
    )

    headers = {
        "User-Agent":
            "Thermoscope-SIH2026/1.0",
        "Accept":
            "application/json",
        "Content-Type":
            "application/x-www-form-urlencoded",
    }

    # --------------------------------------------------------
    # Try multiple Overpass servers
    # --------------------------------------------------------

    servers = [

        "https://overpass-api.de/api/interpreter",

        "https://overpass.kumi.systems/api/interpreter",

        "https://overpass.private.coffee/api/interpreter",
    ]

    for server in servers:

        print()
        print(
            f"Trying Overpass server:"
        )

        print(server)

        try:

            response = requests.post(
                server,
                data={
                    "data": query
                },
                headers=headers,
                timeout=240
            )

            print(
                f"HTTP status: "
                f"{response.status_code}"
            )

            response.raise_for_status()

            data = response.json()

            elements = data.get(
                "elements",
                []
            )

            print(
                f"Industrial OSM objects found: "
                f"{len(elements):,}"
            )

            if len(elements) == 0:

                print(
                    "Warning: no industrial "
                    "objects returned."
                )

                continue

            return elements

        except Exception as e:

            print(
                "Server failed:"
            )

            print(
                str(e)
            )

            time.sleep(2)

    raise RuntimeError(
        "Could not download industrial "
        "OpenStreetMap data from any "
        "Overpass server."
    )


# ============================================================
# CONVERT OSM ELEMENTS TO POINTS
# ============================================================

def parse_osm_elements(
    elements
):

    print()
    print(
        "Processing industrial objects..."
    )

    records = []

    for element in elements:

        tags = element.get(
            "tags",
            {}
        )

        # ----------------------------------------------------
        # Coordinates
        # ----------------------------------------------------

        lat = element.get(
            "lat"
        )

        lon = element.get(
            "lon"
        )

        # Ways/relations normally return center
        if lat is None:

            center = element.get(
                "center",
                {}
            )

            lat = center.get(
                "lat"
            )

            lon = center.get(
                "lon"
            )

        if lat is None or lon is None:

            continue

        # ----------------------------------------------------
        # Determine industrial category
        # ----------------------------------------------------

        category = "other"

        if tags.get(
            "landuse"
        ) == "industrial":

            category = "industrial_area"

        elif tags.get(
            "industrial"
        ) == "factory":

            category = "factory"

        elif tags.get(
            "industrial"
        ) == "manufacture":

            category = "manufacturing"

        elif tags.get(
            "industrial"
        ) == "refinery":

            category = "refinery"

        elif tags.get(
            "power"
        ) == "plant":

            category = "power_plant"

        elif tags.get(
            "building"
        ) == "warehouse":

            category = "warehouse"

        elif tags.get(
            "industrial"
        ) == "storage":

            category = "storage"

        elif tags.get(
            "industrial"
        ) == "chemical":

            category = "chemical"

        elif tags.get(
            "industrial"
        ) == "steelmaking":

            category = "steel"

        elif tags.get(
            "industrial"
        ) == "oil":

            category = "oil"

        elif tags.get(
            "industrial"
        ) == "gas":

            category = "gas"

        records.append({

            "osm_id":
                element.get(
                    "id"
                ),

            "osm_type":
                element.get(
                    "type"
                ),

            "latitude":
                float(lat),

            "longitude":
                float(lon),

            "category":
                category,

            "name":
                tags.get(
                    "name",
                    ""
                ),
        })

    if not records:

        return pd.DataFrame(
            columns=[
                "osm_id",
                "osm_type",
                "latitude",
                "longitude",
                "category",
                "name",
            ]
        )

    result = pd.DataFrame(
        records
    )

    result = result.drop_duplicates(
        subset=[
            "osm_type",
            "osm_id"
        ]
    )

    print(
        f"Usable industrial objects: "
        f"{len(result):,}"
    )

    print()
    print(
        "Industrial categories:"
    )

    print(
        result["category"]
        .value_counts()
        .to_string()
    )

    return result


# ============================================================
# CREATE GEODATAFRAMES
# ============================================================

def create_geodataframes(
    grid,
    industrial
):

    grid_gdf = gpd.GeoDataFrame(
        grid.copy(),
        geometry=gpd.points_from_xy(
            grid["longitude"],
            grid["latitude"]
        ),
        crs="EPSG:4326"
    )

    industrial_gdf = gpd.GeoDataFrame(
        industrial.copy(),
        geometry=gpd.points_from_xy(
            industrial["longitude"],
            industrial["latitude"]
        ),
        crs="EPSG:4326"
    )

    # Project to metres
    grid_gdf = grid_gdf.to_crs(
        "EPSG:3857"
    )

    industrial_gdf = industrial_gdf.to_crs(
        "EPSG:3857"
    )

    return (
        grid_gdf,
        industrial_gdf
    )


# ============================================================
# CALCULATE INDUSTRIAL PROXIMITY
# ============================================================

def calculate_industrial_features(
    grid,
    industrial
):

    print()
    print(
        "Calculating industrial proximity..."
    )

    if industrial.empty:

        print(
            "No industrial objects available."
        )

        result = grid.copy()

        result[
            "industrial_objects"
        ] = 0

        result[
            "industrial_area_count"
        ] = 0

        result[
            "factory_count"
        ] = 0

        result[
            "manufacturing_count"
        ] = 0

        result[
            "refinery_count"
        ] = 0

        result[
            "power_plant_count"
        ] = 0

        result[
            "warehouse_count"
        ] = 0

        result[
            "chemical_count"
        ] = 0

        result[
            "industrial_proximity"
        ] = 0

        result[
            "industrial_context_score"
        ] = 0

        result[
            "industrial_fire_candidate"
        ] = 0

        return result

    (
        grid_gdf,
        industrial_gdf
    ) = create_geodataframes(
        grid,
        industrial
    )

    # --------------------------------------------------------
    # Spatial join within radius
    # --------------------------------------------------------

    joined = gpd.sjoin_nearest(
        grid_gdf,
        industrial_gdf[
            [
                "category",
                "name",
                "geometry"
            ]
        ],
        how="left",
        max_distance=
            INDUSTRIAL_RADIUS_METERS,
        distance_col=
            "distance_m"
    )

    # --------------------------------------------------------
    # Distance/proximity
    # --------------------------------------------------------

    joined[
        "distance_m"
    ] = joined[
        "distance_m"
    ].fillna(
        np.inf
    )

    # --------------------------------------------------------
    # Aggregate objects per grid
    # --------------------------------------------------------

    grouped = (
        joined
        .groupby(
            "grid_id"
        )
        .agg(

            industrial_objects=(
                "category",
                lambda x:
                    x.notna().sum()
            ),

            nearest_industrial_distance=(
                "distance_m",
                "min"
            ),
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # Category counts
    # --------------------------------------------------------
    #
    # Count industrial infrastructure types within the
    # configured proximity radius for each FIRMS grid.
    #
    # We intentionally avoid pivot_table here because newer
    # pandas versions can raise:
    # "Grouper for 'category' not 1-dimensional"
    # when spatial-join output contains conflicting columns.
    # --------------------------------------------------------

    categories = [
        "industrial_area",
        "factory",
        "manufacturing",
        "refinery",
        "power_plant",
        "warehouse",
        "storage",
        "chemical",
        "steel",
        "oil",
        "gas",
    ]

    category_counts = (
        joined[
            [
                "grid_id",
                "category",
            ]
        ]
        .dropna(
            subset=["category"]
        )
        .groupby(
            [
                "grid_id",
                "category",
            ],
            observed=True
        )
        .size()
        .unstack(
            fill_value=0
        )
        .reset_index()
    )

    # Make sure every expected category exists
    for category in categories:

        if category not in category_counts.columns:

            category_counts[category] = 0


    # Rename categories into feature names
    rename_map = {

        "industrial_area":
            "industrial_area_count",

        "factory":
            "factory_count",

        "manufacturing":
            "manufacturing_count",

        "refinery":
            "refinery_count",

        "power_plant":
            "power_plant_count",

        "warehouse":
            "warehouse_count",

        "storage":
            "storage_count",

        "chemical":
            "chemical_count",

        "steel":
            "steel_count",

        "oil":
            "oil_count",

        "gas":
            "gas_count",
    }   

    category_counts = (
        category_counts.rename(
            columns=rename_map
        )
    )
    # Rename columns
    rename_map = {

        "industrial_area":
            "industrial_area_count",

        "factory":
            "factory_count",

        "manufacturing":
            "manufacturing_count",

        "refinery":
            "refinery_count",

        "power_plant":
            "power_plant_count",

        "warehouse":
            "warehouse_count",

        "storage":
            "storage_count",

        "chemical":
            "chemical_count",

        "steel":
            "steel_count",

        "oil":
            "oil_count",

        "gas":
            "gas_count",
    }

    category_counts = (
        category_counts.rename(
            columns=rename_map
        )
    )

    # Ensure all category columns exist
    for column in rename_map.values():

        if column not in category_counts.columns:

            category_counts[column] = 0

    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    result = grid.merge(
        grouped,
        on="grid_id",
        how="left"
    )

    result = result.merge(
        category_counts,
        on="grid_id",
        how="left"
    )

    # --------------------------------------------------------
    # Fill missing values
    # --------------------------------------------------------

    numeric_columns = [
        "industrial_objects",
        "nearest_industrial_distance",
    ] + list(
        rename_map.values()
    )

    for column in numeric_columns:

        if column not in result.columns:

            result[column] = 0

    result[
        "industrial_objects"
    ] = result[
        "industrial_objects"
    ].fillna(0)

    result[
        "nearest_industrial_distance"
    ] = result[
        "nearest_industrial_distance"
    ].replace(
        np.inf,
        np.nan
    )

    result[
        "nearest_industrial_distance"
    ] = result[
        "nearest_industrial_distance"
    ].fillna(
        INDUSTRIAL_RADIUS_METERS
    )

    for column in rename_map.values():

        result[column] = (
            result[column]
            .fillna(0)
            .astype(int)
        )

    # --------------------------------------------------------
    # Industrial proximity score
    # --------------------------------------------------------
    #
    # 1.0 = very close
    # 0.0 = at/outside radius
    #
    # This is a contextual score, NOT probability.
    # --------------------------------------------------------

    result[
        "industrial_proximity"
    ] = (
        1
        -
        (
            result[
                "nearest_industrial_distance"
            ]
            /
            INDUSTRIAL_RADIUS_METERS
        )
    )

    result[
        "industrial_proximity"
    ] = (
        result[
            "industrial_proximity"
        ]
        .clip(
            0,
            1
        )
    )

    # --------------------------------------------------------
    # Industrial context score
    # --------------------------------------------------------
    #
    # Different infrastructure types receive different
    # contextual weights.
    #
    # This does NOT claim that these locations are fires.
    # It only increases confidence that a thermal detection
    # occurs in an industrial context.
    # --------------------------------------------------------

    context_score = (

        result[
            "industrial_area_count"
        ] * 1.0

        +

        result[
            "factory_count"
        ] * 1.5

        +

        result[
            "manufacturing_count"
        ] * 1.5

        +

        result[
            "refinery_count"
        ] * 2.0

        +

        result[
            "power_plant_count"
        ] * 1.5

        +

        result[
            "chemical_count"
        ] * 2.0

        +

        result[
            "oil_count"
        ] * 2.0

        +

        result[
            "gas_count"
        ] * 2.0

        +

        result[
            "steel_count"
        ] * 1.5

        +

        result[
            "warehouse_count"
        ] * 0.7

        +

        result[
            "storage_count"
        ] * 0.7
    )

    # Combine object density + proximity
    result[
        "industrial_context_score"
    ] = (

        np.log1p(
            context_score
        )
        *
        (
            0.5
            +
            0.5 *
            result[
                "industrial_proximity"
            ]
        )
    )

    # --------------------------------------------------------
    # Industrial fire candidate
    # --------------------------------------------------------
    #
    # This is ONLY a candidate indicator.
    #
    # It will later be combined with FIRMS thermal
    # intensity/recent activity in the risk model.
    # --------------------------------------------------------

    result[
        "industrial_fire_candidate"
    ] = (

        (
            result[
                "industrial_objects"
            ] > 0
        )
        &
        (
            result[
                "industrial_proximity"
            ] > 0
        )
    ).astype(int)

    return result


# ============================================================
# NORMALIZE INDUSTRIAL SCORE
# ============================================================

def normalize_score(
    result
):

    score = result[
        "industrial_context_score"
    ].values

    if len(score) == 0:

        result[
            "industrial_context_score_norm"
        ] = 0

        return result

    min_value = np.nanmin(
        score
    )

    max_value = np.nanmax(
        score
    )

    if max_value == min_value:

        result[
            "industrial_context_score_norm"
        ] = 0

    else:

        result[
            "industrial_context_score_norm"
        ] = (
            (
                score
                -
                min_value
            )
            /
            (
                max_value
                -
                min_value
            )
        )

    return result


# ============================================================
# SAVE
# ============================================================

def save_output(
    result
):

    print()
    print(
        "Saving industrial feature layer..."
    )

    result = result.replace(
        [
            np.inf,
            -np.inf
        ],
        np.nan
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print(
        f"Saved: {OUTPUT_FILE}"
    )

    print(
        f"Rows: {len(result):,}"
    )

    print(
        f"Columns: {len(result.columns)}"
    )

    return result


# ============================================================
# DISPLAY SUMMARY
# ============================================================

def display_summary(
    result
):

    print()
    print("=" * 70)
    print(
        "INDUSTRIAL CONTEXT SUMMARY"
    )
    print("=" * 70)

    print()

    print(
        "Grid cells with industrial context:"
    )

    print(
        int(
            (
                result[
                    "industrial_objects"
                ] > 0
            ).sum()
        )
    )

    print()

    print(
        "Potential industrial-fire candidate cells:"
    )

    print(
        int(
            result[
                "industrial_fire_candidate"
            ].sum()
        )
    )

    print()

    print(
        "Infrastructure counts:"
    )

    columns = [

        "industrial_area_count",
        "factory_count",
        "manufacturing_count",
        "refinery_count",
        "power_plant_count",
        "warehouse_count",
        "storage_count",
        "chemical_count",
        "steel_count",
        "oil_count",
        "gas_count",
    ]

    summary = (
        result[
            columns
        ]
        .sum()
        .sort_values(
            ascending=False
        )
    )

    print(
        summary.to_string()
    )

    print()
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    grid = load_grid()

    elements = (
        download_industrial_data(
            grid
        )
    )

    industrial = (
        parse_osm_elements(
            elements
        )
    )

    result = (
        calculate_industrial_features(
            grid,
            industrial
        )
    )

    result = normalize_score(
        result
    )

    result = save_output(
        result
    )

    display_summary(
        result
    )

    print()
    print(
        "NEXT STAGE:"
    )

    print(
        "Combine FIRMS thermal activity + "
        "industrial context to generate "
        "industrial fire risk."
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "OpenStreetMap is contextual data only."
    )

    print(
        "NASA FIRMS remains the primary "
        "fire-detection source."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()