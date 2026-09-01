from pathlib import Path

import numpy as np
import pandas as pd
import folium
from folium import plugins


# ============================================================
# THERMOSCOPE
# ACTIVE FIRE RISK MAP
#
# NASA FIRMS = PRIMARY FIRE SIGNAL
# GRID RISK = SPATIAL RISK
# INFRASTRUCTURE = SUPPORTING CONTEXT
# ============================================================


# ============================================================
# PATHS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "risk_predictions.csv"
)

OUTPUT_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_MAP = (
    OUTPUT_DIR
    / "thermoscope_fire_risk_map.html"
)


# ============================================================
# MAP CONFIGURATION
# ============================================================

MAP_ZOOM = 6

GRID_SIZE = 0.05

VISIBLE_LEVELS = [
    "LOW",
    "MODERATE",
    "HIGH",
    "CRITICAL",
]


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    print("=" * 70)
    print("THERMOSCOPE - ACTIVE FIRE RISK MAP")
    print("=" * 70)

    print()
    print(
        f"Input: {INPUT_FILE}"
    )

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"""
Input file not found:

{INPUT_FILE}

Expected source:
data/processed/risk_predictions.csv
"""
        )

    df = pd.read_csv(
        INPUT_FILE,
        low_memory=False,
    )

    print(
        f"Rows loaded: {len(df):,}"
    )

    return df


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_data(df):

    print()
    print(
        "Preparing spatial fire-risk signals..."
    )

    df = df.copy()

    # --------------------------------------------------------
    # NORMALIZE RISK LEVEL
    # --------------------------------------------------------

    if "risk_level" in df.columns:

        df["risk_level"] = (
            df["risk_level"]
            .fillna("UNKNOWN")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        active = df[
            df["risk_level"].isin(
                VISIBLE_LEVELS
            )
        ].copy()

    else:

        active = df.copy()

        active["risk_level"] = (
            "UNKNOWN"
        )

    # --------------------------------------------------------
    # NUMERIC COLUMNS
    # --------------------------------------------------------

    numeric_columns = [

        "latitude",
        "longitude",

        "risk_score",

        "total_detections",
        "active_days",

        "avg_frp",
        "max_frp",

        "recurrence_ratio",
        "persistent_months",

        "multi_satellite_activity",

        "detections_30d",
        "detections_90d",

        "recent_activity_ratio",
        "frp_intensity_ratio",
        "persistence_ratio",
    ]

    for column in numeric_columns:

        if column not in active.columns:

            active[column] = 0

        active[column] = pd.to_numeric(
            active[column],
            errors="coerce",
        ).fillna(0)

    # --------------------------------------------------------
    # GRID ID
    # --------------------------------------------------------

    if "grid_id" not in active.columns:

        active["grid_id"] = (
            active.index.astype(str)
        )

    else:

        active["grid_id"] = (
            active["grid_id"]
            .astype(str)
            .str.strip()
        )

    # --------------------------------------------------------
    # REMOVE INVALID COORDINATES
    # --------------------------------------------------------

    active = active.dropna(
        subset=[
            "latitude",
            "longitude",
        ]
    )

    active = active[
        active["latitude"].between(
            -90,
            90,
        )
        &
        active["longitude"].between(
            -180,
            180,
        )
    ].copy()

    print(
        f"Active risk cells: {len(active):,}"
    )

    return active


# ============================================================
# RISK COLOR
# ============================================================

def risk_color(level):

    level = str(
        level
    ).strip().upper()

    colors = {
        "CRITICAL": "red",
        "HIGH": "orange",
        "MODERATE": "yellow",
        "LOW": "green",
    }

    return colors.get(
        level,
        "blue",
    )


# ============================================================
# RISK OPACITY
# ============================================================

def risk_fill_opacity(level):

    level = str(
        level
    ).strip().upper()

    opacity = {

        "CRITICAL": 0.72,

        "HIGH": 0.62,

        "MODERATE": 0.48,

        "LOW": 0.32,
    }

    return opacity.get(
        level,
        0.25,
    )


# ============================================================
# GRID BOUNDS
# ============================================================

def get_grid_bounds(
    latitude,
    longitude,
):

    grid_lat = (
        np.floor(
            latitude / GRID_SIZE
        )
        * GRID_SIZE
    )

    grid_lon = (
        np.floor(
            longitude / GRID_SIZE
        )
        * GRID_SIZE
    )

    return [

        [
            grid_lat,
            grid_lon,
        ],

        [
            grid_lat + GRID_SIZE,
            grid_lon + GRID_SIZE,
        ],
    ]


# ============================================================
# INFRASTRUCTURE SUMMARY
# ============================================================

def infrastructure_summary(row):

    infrastructure = []

    infrastructure_columns = [

        (
            "Industrial Area",
            "industrial_area_count",
        ),

        (
            "Factory",
            "factory_count",
        ),

        (
            "Power Plant",
            "power_plant_count",
        ),

        (
            "Warehouse",
            "warehouse_count",
        ),

        (
            "Chemical",
            "chemical_count",
        ),

        (
            "Refinery",
            "refinery_count",
        ),

        (
            "Storage",
            "storage_count",
        ),

        (
            "Steel",
            "steel_count",
        ),

        (
            "Oil",
            "oil_count",
        ),

        (
            "Gas",
            "gas_count",
        ),
    ]

    for name, column in infrastructure_columns:

        value = row.get(
            column,
            0,
        )

        try:

            value = int(
                float(value)
            )

        except Exception:

            value = 0

        if value > 0:

            infrastructure.append(
                f"{name}: {value}"
            )

    if not infrastructure:

        return (
            "Industrial infrastructure "
            "detected nearby."
        )

    return "<br>".join(
        infrastructure
    )


# ============================================================
# POPUP
# ============================================================

def create_popup(row):

    risk = float(
        row.get(
            "risk_score",
            row.get(
                "industrial_fire_risk",
                0,
            ),
        )
    )

    level = str(
        row.get(
            "risk_level",
            "UNKNOWN",
        )
    ).upper()

    grid_id = str(
        row.get(
            "grid_id",
            "N/A",
        )
    )

    # --------------------------------------------------------
    # FIRMS ACTIVITY
    # --------------------------------------------------------

    detections_30d = int(
        float(
            row.get(
                "detections_30d",
                0,
            )
        )
    )

    detections_90d = int(
        float(
            row.get(
                "detections_90d",
                0,
            )
        )
    )

    active_days = int(
        float(
            row.get(
                "active_days",
                0,
            )
        )
    )

    avg_frp = float(
        row.get(
            "avg_frp",
            0,
        )
    )

    max_frp = float(
        row.get(
            "max_frp",
            0,
        )
    )

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    latitude = float(
        row["latitude"]
    )

    longitude = float(
        row["longitude"]
    )

    # --------------------------------------------------------
    # SUPPORTING CONTEXT
    # --------------------------------------------------------

    infrastructure = (
        infrastructure_summary(
            row
        )
    )

    fire_type = str(
        row.get(
            "fire_type",
            "UNCLASSIFIED",
        )
    )

    fire_type_confidence = float(
        row.get(
            "fire_type_confidence",
            0,
        )
    )

    fire_type_reason = str(
        row.get(
            "fire_type_reason",
            "No fire-type classification available.",
        )
    )

    color = risk_color(
        level
    )

    # ========================================================
    # POPUP HTML
    # ========================================================

    popup_html = f"""
    <div style="
        width: 340px;
        font-family: Arial, sans-serif;
        line-height: 1.5;
    ">

        <!-- HEADER -->

        <div style="
            background: {color};
            color: white;
            padding: 11px;
            border-radius: 7px;
            margin-bottom: 10px;
        ">

            <div style="
                font-size: 18px;
                font-weight: bold;
            ">
                🔥 THERMOSCOPE
            </div>

            <div style="
                font-size: 13px;
                margin-top: 2px;
            ">
                Active Fire Risk Signal
            </div>

        </div>


        <!-- RISK -->

        <b>Risk Level:</b>

        <span style="
            color: {color};
            font-weight: bold;
        ">
            {level}
        </span>

        <br>

        <b>Risk Score:</b>
        {risk:.2f}/100

        <br>

        <b>Grid ID:</b>
        {grid_id}


        <hr>


        <!-- NASA FIRMS -->

        <b>🛰 NASA FIRMS THERMAL ACTIVITY</b>

        <br><br>

        Detections — 30 days:
        <b>{detections_30d}</b>

        <br>

        Detections — 90 days:
        <b>{detections_90d}</b>

        <br>

        Active Days:
        <b>{active_days}</b>

        <br>

        Average FRP:
        <b>{avg_frp:.2f}</b>

        <br>

        Maximum FRP:
        <b>{max_frp:.2f}</b>


        <hr>


        <!-- FIRE TYPE -->

        <b>🔥 FIRE SIGNAL CLASSIFICATION</b>

        <br><br>

        Type:
        <b>{fire_type}</b>

        <br>

        Confidence:
        <b>{fire_type_confidence * 100:.1f}%</b>

        <br>

        <small>
        {fire_type_reason}
        </small>


        <hr>


        <!-- INDUSTRIAL CONTEXT -->

        <b>🏭 INDUSTRIAL CONTEXT</b>

        <br><br>

        {infrastructure}


        <hr>


        <!-- LOCATION -->

        <b>📍 LOCATION</b>

        <br><br>

        Latitude:
        {latitude:.5f}

        <br>

        Longitude:
        {longitude:.5f}


        <hr>


        <small>
        <b>Primary Signal:</b>
        NASA FIRMS satellite thermal detection.
        </small>

        <br><br>

        <small>
        <b>Supporting Context:</b>
        Spatially nearby infrastructure.
        </small>

        <br><br>

        <small style="
            color: #555;
        ">
        ⚠ This represents a risk signal based on
        thermal activity and spatial features.
        It is not a confirmation of an active fire.
        </small>

    </div>
    """

    return folium.Popup(
        popup_html,
        max_width=390,
    )


# ============================================================
# CREATE MAP
# ============================================================

def create_map(df):

    print()
    print(
        "Creating GIS map..."
    )

    if len(df) == 0:

        raise RuntimeError(
            "No valid risk cells available."
        )

    # --------------------------------------------------------
    # MAP CENTER
    # --------------------------------------------------------

    center_lat = float(
        df["latitude"].mean()
    )

    center_lon = float(
        df["longitude"].mean()
    )

    fire_map = folium.Map(

        location=[
            center_lat,
            center_lon,
        ],

        zoom_start=MAP_ZOOM,

        tiles="CartoDB positron",

        control_scale=True,
    )


    # ========================================================
    # TITLE
    # ========================================================

    title_html = """
    <div style="
        position: fixed;
        top: 10px;
        left: 50%;
        transform: translateX(-50%);

        z-index: 9999;

        background: white;

        padding: 11px 20px;

        border-radius: 9px;

        box-shadow:
            0 2px 10px
            rgba(0,0,0,0.25);

        font-family: Arial;

        font-size: 18px;

        font-weight: bold;

        white-space: nowrap;
    ">

        🔥 THERMOSCOPE —
        ACTIVE FIRE RISK MAP

    </div>
    """

    fire_map.get_root().html.add_child(
        folium.Element(
            title_html
        )
    )


    # ========================================================
    # RISK LAYERS
    # ========================================================

    layer_groups = {}

    for level in [
        "CRITICAL",
        "HIGH",
        "MODERATE",
        "LOW",
    ]:

        layer_groups[level] = (
            folium.FeatureGroup(
                name=f"{level} Fire Risk Zones",
                show=True,
            )
        )

        layer_groups[level].add_to(
            fire_map
        )


    # ========================================================
    # FIRMS POINTS
    #
    # IMPORTANT:
    # Each point is created from the EXACT SAME row
    # used to create its risk rectangle.
    #
    # Therefore:
    #
    # Rectangle = grid risk zone
    # Point     = FIRMS activity inside that same zone
    #
    # They share:
    # grid_id
    # latitude
    # longitude
    # risk_level
    # risk_score
    # detections
    # ========================================================

    firms_group = folium.FeatureGroup(
        name="NASA FIRMS Thermal Detection Points",
        show=True,
    )

    firms_group.add_to(
        fire_map
    )


    # ========================================================
    # ADD GRID RISK ZONES + FIRMS POINTS
    # ========================================================

    print()
    print(
        "Adding linked risk zones and FIRMS points..."
    )

    for _, row in df.iterrows():

        level = str(
            row.get(
                "risk_level",
                "UNKNOWN",
            )
        ).strip().upper()

        if level not in layer_groups:

            continue

        latitude = float(
            row["latitude"]
        )

        longitude = float(
            row["longitude"]
        )

        risk = float(
            row.get(
                "risk_score",
                row.get(
                    "industrial_fire_risk",
                    0,
                ),
            )
        )

        detections = int(
            float(
                row.get(
                    "detections_30d",
                    0,
                )
            )
        )

        grid_id = str(
            row.get(
                "grid_id",
                "N/A",
            )
        )

        color = risk_color(
            level
        )

        opacity = risk_fill_opacity(
            level
        )

        # ----------------------------------------------------
        # SAME GRID BOUNDS
        # ----------------------------------------------------

        bounds = get_grid_bounds(
            latitude,
            longitude,
        )


        # ====================================================
        # RISK RECTANGLE
        # ====================================================

        rectangle = folium.Rectangle(

            bounds=bounds,

            color=color,

            weight=2,

            fill=True,

            fill_color=color,

            fill_opacity=opacity,

            popup=create_popup(
                row
            ),

            tooltip=(
                f"🔥 {level} | "
                f"Risk: {risk:.1f} | "
                f"Grid: {grid_id} | "
                f"FIRMS: {detections}"
            ),
        )

        rectangle.add_to(
            layer_groups[level]
        )


        # ====================================================
        # FIRMS DETECTION POINT
        #
        # IMPORTANT:
        # This point uses the same row and same coordinates
        # as the rectangle.
        # ====================================================

        if detections > 0:

            if level == "CRITICAL":

                point_radius = 9

            elif level == "HIGH":

                point_radius = 7

            elif level == "MODERATE":

                point_radius = 5

            else:

                point_radius = 4


            point = folium.CircleMarker(

                location=[
                    latitude,
                    longitude,
                ],

                radius=point_radius,

                color="black",

                weight=1,

                fill=True,

                fill_color=color,

                fill_opacity=0.95,

                popup=create_popup(
                    row
                ),

                tooltip=(
                    f"🛰 NASA FIRMS | "
                    f"{level} | "
                    f"Grid: {grid_id} | "
                    f"{detections} detections"
                ),
            )

            point.add_to(
                firms_group
            )


    # ========================================================
    # FIRMS HEATMAP
    # ========================================================

    heat_data = []

    for _, row in df.iterrows():

        latitude = float(
            row["latitude"]
        )

        longitude = float(
            row["longitude"]
        )

        intensity = float(
            row.get(
                "detections_30d",
                0,
            )
        )

        if intensity <= 0:

            continue

        heat_data.append(
            [
                latitude,
                longitude,
                intensity,
            ]
        )


    if heat_data:

        heat_group = (
            folium.FeatureGroup(
                name="FIRMS Thermal Intensity Heatmap",
                show=False,
            )
        )

        plugins.HeatMap(

            heat_data,

            radius=25,

            blur=18,

            min_opacity=0.25,

            max_zoom=10,

        ).add_to(
            heat_group
        )

        heat_group.add_to(
            fire_map
        )


    # ========================================================
    # INFORMATION PANEL
    # ========================================================

    info_html = f"""
    <div style="
        position: fixed;

        top: 80px;
        left: 15px;

        z-index: 9998;

        background: white;

        padding: 10px 13px;

        border-radius: 7px;

        box-shadow:
            0 2px 8px
            rgba(0,0,0,0.22);

        font-family: Arial;

        font-size: 12px;

        line-height: 1.5;
    ">

        <b>THERMOSCOPE SIGNALS</b>

        <br><br>

        🛰 NASA FIRMS =
        Primary Thermal Signal

        <br>

        🏭 Infrastructure =
        Supporting Context

        <br>

        📦 Grid =
        {GRID_SIZE:.2f}° spatial cell

        <br>

        🔗 Risk Zone + FIRMS Point =
        Same Grid Record

    </div>
    """

    fire_map.get_root().html.add_child(
        folium.Element(
            info_html
        )
    )


    # ========================================================
    # LAYER CONTROL
    # ========================================================

    folium.LayerControl(
        collapsed=False
    ).add_to(
        fire_map
    )


    # ========================================================
    # LEGEND
    # ========================================================

    legend_html = """
    <div style="
        position: fixed;

        bottom: 30px;
        left: 30px;

        z-index: 9999;

        background: white;

        padding: 13px;

        border-radius: 8px;

        box-shadow:
            0 2px 8px
            rgba(0,0,0,0.25);

        font-family: Arial;

        font-size: 13px;

        min-width: 170px;
    ">

        <b>
            Fire Risk Level
        </b>

        <br><br>


        <span style="
            display:inline-block;
            width:15px;
            height:15px;
            background:red;
            margin-right:6px;
        "></span>

        CRITICAL

        <br>


        <span style="
            display:inline-block;
            width:15px;
            height:15px;
            background:orange;
            margin-right:6px;
        "></span>

        HIGH

        <br>


        <span style="
            display:inline-block;
            width:15px;
            height:15px;
            background:yellow;
            margin-right:6px;
        "></span>

        MODERATE

        <br>


        <span style="
            display:inline-block;
            width:15px;
            height:15px;
            background:green;
            margin-right:6px;
        "></span>

        LOW


        <hr style="
            margin: 8px 0;
        ">


        <span style="
            display:inline-block;
            width:10px;
            height:10px;
            border-radius:50%;
            background:black;
            margin-right:6px;
        "></span>

        NASA FIRMS Detection

    </div>
    """

    fire_map.get_root().html.add_child(
        folium.Element(
            legend_html
        )
    )


    # ========================================================
    # FULLSCREEN
    # ========================================================

    plugins.Fullscreen(

        position="topleft",

        title="Full Screen",

        title_cancel="Exit Full Screen",

    ).add_to(
        fire_map
    )


    # ========================================================
    # MOUSE POSITION
    # ========================================================

    plugins.MousePosition(

        position="bottomright",

        separator=" | ",

        prefix="Coordinates:",

    ).add_to(
        fire_map
    )


    return fire_map


# ============================================================
# SAVE MAP
# ============================================================

def save_map(fire_map):

    print()
    print(
        "Saving interactive map..."
    )

    fire_map.save(
        OUTPUT_MAP
    )

    print(
        f"Saved: {OUTPUT_MAP}"
    )


# ============================================================
# SUMMARY
# ============================================================

def display_summary(df):

    print()
    print("=" * 70)
    print(
        "ACTIVE FIRE RISK MAP SUMMARY"
    )
    print("=" * 70)

    print()

    print(
        f"Mapped cells: {len(df):,}"
    )

    print()

    print(
        "Risk distribution:"
    )

    if "risk_level" in df.columns:

        print(
            df[
                "risk_level"
            ]
            .value_counts()
            .to_string()
        )

    print()

    print(
        "Top fire-risk zones:"
    )

    columns = [

        "grid_id",

        "risk_score",

        "risk_level",

        "detections_30d",

        "active_days",

        "avg_frp",

        "max_frp",
    ]

    columns = [
        column
        for column in columns
        if column in df.columns
    ]

    if "risk_score" in df.columns:

        print(
            df.sort_values(
                "risk_score",
                ascending=False,
            )[columns]
            .head(10)
            .to_string(
                index=False
            )
        )

    print()

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    df = load_data()

    df = prepare_data(
        df
    )

    display_summary(
        df
    )

    fire_map = create_map(
        df
    )

    save_map(
        fire_map
    )

    print()
    print("=" * 70)
    print(
        "MAP GENERATION COMPLETE"
    )
    print("=" * 70)

    print()

    print(
        "NASA FIRMS = PRIMARY FIRE SIGNAL"
    )

    print(
        "Spatial risk score = RISK ASSESSMENT"
    )

    print(
        "Infrastructure = SUPPORTING CONTEXT"
    )

    print()

    print(
        "Risk zones and FIRMS points are "
        "generated from the same spatial grid records."
    )

    print()

    print(
        "Output:"
    )

    print(
        OUTPUT_MAP
    )

    print()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()