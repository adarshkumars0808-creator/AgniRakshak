import streamlit as st
import pandas as pd
import numpy as np
import folium

from folium import plugins
from streamlit_folium import st_folium


# ============================================================
# THERMOSCOPE
# DELHI NCR FIRE RISK INTELLIGENCE DASHBOARD
# ============================================================

st.set_page_config(
    page_title="THERMOSCOPE | Fire Risk Intelligence",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
<style>

.stApp {
    background:
        radial-gradient(
            circle at 85% 5%,
            rgba(255, 90, 30, 0.08),
            transparent 25%
        ),
        #0b0f15;
    color: #f5f7fa;
}

.block-container {
    max-width: 1500px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}


/* ============================================================
    SIDEBAR
   ============================================================ */

[data-testid="stSidebar"] {
    background: #0d121a;
    border-right: 1px solid #252c36;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #f5f7fa;
}


/* ============================================================
    HERO
   ============================================================ */

.hero {
    background: linear-gradient(
        145deg,
        #151b24,
        #10151d
    );

    border: 1px solid #29313d;
    border-radius: 18px;
    padding: 24px 28px;

    box-shadow:
        0 10px 30px rgba(0, 0, 0, 0.22);
}

.hero-title {
    font-size: 48px;
    font-weight: 850;
    letter-spacing: -1px;
    margin-bottom: 6px;
    color: #f5f7fa;
}

.hero-subtitle {
    color: #9aa4b2;
    font-size: 17px;
    line-height: 1.5;
    margin-top: 4px;
}

.live-badge {
    display: inline-block;
    padding: 7px 15px;
    border-radius: 30px;
    border: 1px solid rgba(0, 220, 120, 0.30);
    background: rgba(0, 180, 100, 0.08);
    color: #35e68a;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
}


/* ============================================================
    SECTION
   ============================================================ */

.section-label {
    color: #737f8e;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-top: 10px;
    margin-bottom: 10px;
}

.section-title {
    font-size: 28px;
    font-weight: 800;
    margin-bottom: 4px;
}

.section-subtitle {
    color: #8d98a7;
    font-size: 14px;
    margin-bottom: 18px;
}


/* ============================================================
    METRIC CARDS
   ============================================================ */

div[data-testid="stMetric"] {
    background: linear-gradient(
        145deg,
        #151b24,
        #10151d
    );

    border: 1px solid #29313d;
    border-radius: 15px;
    padding: 18px;

    box-shadow:
        0 8px 25px rgba(0, 0, 0, 0.18);
}

div[data-testid="stMetricLabel"] {
    color: #8f9aaa !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    text-transform: uppercase;
}

div[data-testid="stMetricValue"] {
    color: #f4f7fb !important;
    font-weight: 800 !important;
}


/* ============================================================
    INFO CARDS
   ============================================================ */

.info-card {
    background: #111720;
    border: 1px solid #29313d;
    border-radius: 15px;
    padding: 20px;
    height: 100%;
}

.info-card-title {
    color: #8d98a7;
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}

.info-card-value {
    color: #f4f7fb;
    font-size: 22px;
    font-weight: 750;
}

.info-card-text {
    color: #8d98a7;
    font-size: 13px;
    margin-top: 6px;
    line-height: 1.5;
}


/* ============================================================
    DIVIDER
   ============================================================ */

hr {
    border-color: #252c36 !important;
    margin-top: 30px !important;
    margin-bottom: 30px !important;
}


/* ============================================================
    TABLE
   ============================================================ */

[data-testid="stDataFrame"] {
    border: 1px solid #29313d;
    border-radius: 12px;
    overflow: hidden;
}


/* ============================================================
    MAP
   ============================================================ */

.map-caption {
    color: #7f8997;
    font-size: 12px;
    margin-top: 7px;
}


/* ============================================================
    FOOTER
   ============================================================ */

.footer {
    text-align: center;
    color: #687382;
    font-size: 12px;
    padding: 25px 0 5px 0;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_data():

    risk_df = pd.read_csv(
        "data/delhi_risk_predictions.csv"
    )

    firms_df = pd.read_csv(
        "data/delhi_firms_sih.csv"
    )

    return risk_df, firms_df


try:

    risk_df, firms_df = load_data()

except Exception as e:

    st.error(
        f"Unable to load Thermoscope data: {e}"
    )

    st.stop()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def find_column(df, names):

    for name in names:

        if name in df.columns:
            return name

    return None


def render_info_card(title, value, text):

    card_html = (
        '<div class="info-card">'
        f'<div class="info-card-title">{title}</div>'
        f'<div class="info-card-value">{value}</div>'
        f'<div class="info-card-text">{text}</div>'
        '</div>'
    )

    st.markdown(
        card_html,
        unsafe_allow_html=True,
    )


# ============================================================
# DETECT IMPORTANT RISK COLUMNS
# ============================================================

risk_column = find_column(
    risk_df,
    [
        "risk_category",
        "predicted_risk",
        "risk",
        "activity_category",
        "risk_level",
    ],
)


lat_column = find_column(
    risk_df,
    [
        "grid_lat",
        "latitude",
        "lat",
        "Latitude",
    ],
)


lon_column = find_column(
    risk_df,
    [
        "grid_lon",
        "longitude",
        "lon",
        "Longitude",
    ],
)


detection_column = find_column(
    risk_df,
    [
        "detection_count",
        "detections",
        "fire_count",
    ],
)


avg_frp_column = find_column(
    risk_df,
    [
        "avg_frp",
        "mean_frp",
    ],
)


max_frp_column = find_column(
    risk_df,
    [
        "max_frp",
        "maximum_frp",
    ],
)


# ============================================================
# CREATE RISK CATEGORY IF NOT PRESENT
# ============================================================

if risk_column is None:

    if "activity_score" in risk_df.columns:

        risk_df["risk_category"] = pd.cut(
            pd.to_numeric(
                risk_df["activity_score"],
                errors="coerce",
            ),
            bins=[
                -float("inf"),
                0.33,
                0.66,
                float("inf"),
            ],
            labels=[
                "LOW",
                "MEDIUM",
                "HIGH",
            ],
        )

    elif avg_frp_column is not None:

        risk_df["risk_category"] = pd.cut(
            pd.to_numeric(
                risk_df[avg_frp_column],
                errors="coerce",
            ),
            bins=[
                -float("inf"),
                2,
                4,
                float("inf"),
            ],
            labels=[
                "LOW",
                "MEDIUM",
                "HIGH",
            ],
        )

    elif detection_column is not None:

        risk_df["risk_category"] = pd.cut(
            pd.to_numeric(
                risk_df[detection_column],
                errors="coerce",
            ),
            bins=[
                -float("inf"),
                1,
                2,
                float("inf"),
            ],
            labels=[
                "LOW",
                "MEDIUM",
                "HIGH",
            ],
        )

    else:

        risk_df["risk_category"] = "LOW"

    risk_column = "risk_category"


risk_df[risk_column] = (
    risk_df[risk_column]
    .astype(str)
    .str.upper()
    .str.strip()
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "## ⚙️ Controls"
    )

    st.divider()

    st.markdown(
        "### 🎯 Risk Filter"
    )

    available_risks = [
        x
        for x in [
            "HIGH",
            "MEDIUM",
            "LOW",
        ]
        if x in risk_df[risk_column].unique()
    ]

    selected_risks = st.multiselect(
        "Select risk levels",
        options=available_risks,
        default=available_risks,
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown(
        "### 🛰️ Data Source"
    )

    st.markdown(
        """
**NASA FIRMS**

VIIRS satellite observations
"""
    )

    st.divider()

    st.markdown(
        "### 📍 Monitoring Region"
    )

    st.markdown(
        """
**Delhi NCR**

Approx. Delhi NCR monitoring extent
"""
    )

    st.divider()

    st.markdown(
        "### 🧠 Intelligence Layer"
    )

    st.caption(
        "Satellite activity → Spatial aggregation → "
        "Risk scoring → Prediction"
    )


# ============================================================
# FILTER DATA
# ============================================================

if selected_risks:

    filtered_risk = risk_df[
        risk_df[risk_column].isin(selected_risks)
    ].copy()

else:

    filtered_risk = risk_df.copy()


# ============================================================
# HEADER
# ============================================================

header_left, header_right = st.columns(
    [5, 1],
    vertical_alignment="center",
)


with header_left:

    st.markdown(
        '<div class="hero">'
        '<div class="hero-title">🔥 THERMOSCOPE</div>'
        '<div class="hero-subtitle">'
        'Delhi NCR Fire Risk Intelligence & Satellite Monitoring System'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


with header_right:

    st.markdown(
        '<div style="'
        'display:flex;'
        'justify-content:flex-end;'
        'align-items:center;'
        'height:100%;'
        'padding-top:12px;'
        '">'
        '<div class="live-badge">'
        '🛰️ SATELLITE MONITORING'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# SYSTEM OVERVIEW
# ============================================================

st.markdown(
    '<div class="section-label">SYSTEM OVERVIEW</div>',
    unsafe_allow_html=True,
)


total_firms = len(firms_df)
total_grids = len(risk_df)


# ============================================================
# LATEST DETECTION DATE
# ============================================================

latest_detection = None


for date_col in [
    "acq_date",
    "date",
]:

    if date_col in firms_df.columns:

        dates = pd.to_datetime(
            firms_df[date_col],
            errors="coerce",
        )

        if dates.notna().any():

            latest_detection = dates.max().strftime(
                "%d %b %Y"
            )

            break


if (
    latest_detection is None
    and "last_detection" in risk_df.columns
):

    dates = pd.to_datetime(
        risk_df["last_detection"],
        errors="coerce",
    )

    if dates.notna().any():

        latest_detection = dates.max().strftime(
            "%d %b %Y"
        )


# ============================================================
# RISK COUNTS
# ============================================================

high_count = int(
    (
        risk_df[risk_column] == "HIGH"
    ).sum()
)


medium_count = int(
    (
        risk_df[risk_column] == "MEDIUM"
    ).sum()
)


low_count = int(
    (
        risk_df[risk_column] == "LOW"
    ).sum()
)


# ============================================================
# OVERVIEW METRICS
# ============================================================

m1, m2, m3, m4, m5, m6 = st.columns(6)


with m1:

    st.metric(
        "🔥 FIRMS DETECTIONS",
        total_firms,
    )


with m2:

    st.metric(
        "🗺️ GRID CELLS",
        total_grids,
    )


with m3:

    st.metric(
        "🔴 HIGH RISK",
        high_count,
    )


with m4:

    st.metric(
        "🟠 MEDIUM RISK",
        medium_count,
    )


with m5:

    st.metric(
        "🟢 LOW RISK",
        low_count,
    )


with m6:

    st.metric(
        "📅 LAST DETECTION",
        latest_detection
        if latest_detection
        else "N/A",
    )


# ============================================================
# THERMOSCOPE THERMAL FIRE RISK MAP
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="section-title">
        🗺️ Delhi NCR Thermal Fire Risk Map
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="section-subtitle">
        NASA FIRMS thermal activity with FRP-weighted spatial
        intensity and Thermoscope risk classification
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# MAP CENTER
# ============================================================

map_center = [28.6139, 77.2090]


# ============================================================
# CREATE MAP
# ============================================================

fire_map = folium.Map(
    location=map_center,
    zoom_start=9,
    tiles=None,
    control_scale=True,
)


# ============================================================
# BASE MAP 1 — SATELLITE
# ============================================================

folium.TileLayer(
    tiles=(
        "https://server.arcgisonline.com/ArcGIS/rest/services/"
        "World_Imagery/MapServer/tile/{z}/{y}/{x}"
    ),
    attr="Esri World Imagery",
    name="🛰️ Satellite Base",
    overlay=False,
    control=True,
    show=True,
).add_to(
    fire_map
)


# ============================================================
# BASE MAP 2 — STREET
# ============================================================

folium.TileLayer(
    tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr="© OpenStreetMap contributors",
    name="🗺️ Street Map",
    overlay=False,
    control=True,
    show=False,
).add_to(
    fire_map
)


# ============================================================
# RISK COLORS
# ============================================================

risk_colors = {
    "HIGH": "#ff3030",
    "MEDIUM": "#ff9500",
    "LOW": "#20c96b",
}


# ============================================================
# FIRMS COORDINATE COLUMNS
# ============================================================

firms_lat_column = find_column(
    firms_df,
    [
        "latitude",
        "lat",
        "Latitude",
        "LATITUDE",
    ],
)

firms_lon_column = find_column(
    firms_df,
    [
        "longitude",
        "lon",
        "Longitude",
        "LONGITUDE",
    ],
)

firms_frp_column = find_column(
    firms_df,
    [
        "frp",
        "FRP",
        "fire_radiative_power",
        "Fire Radiative Power",
    ],
)


# ============================================================
# CREATE THERMAL DATA
# ============================================================

thermal_data = []

thermal_df = pd.DataFrame()


if (
    firms_lat_column is not None
    and firms_lon_column is not None
):

    thermal_df = firms_df.copy()


    # --------------------------------------------------------
    # VALIDATE COORDINATES
    # --------------------------------------------------------

    thermal_df[firms_lat_column] = pd.to_numeric(
        thermal_df[firms_lat_column],
        errors="coerce",
    )

    thermal_df[firms_lon_column] = pd.to_numeric(
        thermal_df[firms_lon_column],
        errors="coerce",
    )


    # --------------------------------------------------------
    # FRP
    # --------------------------------------------------------

    if firms_frp_column is not None:

        thermal_df["_thermal_frp"] = pd.to_numeric(
            thermal_df[firms_frp_column],
            errors="coerce",
        )

    else:

        thermal_df["_thermal_frp"] = 1.0


    thermal_df["_thermal_frp"] = (
        thermal_df["_thermal_frp"]
        .fillna(0)
        .clip(lower=0)
    )


    # --------------------------------------------------------
    # DELHI NCR / SURROUNDING MONITORING EXTENT
    # --------------------------------------------------------

    thermal_df = thermal_df[
        thermal_df[firms_lat_column].between(
            27.0,
            30.5,
        )
        &
        thermal_df[firms_lon_column].between(
            75.0,
            79.5,
        )
    ].copy()


    # --------------------------------------------------------
    # REMOVE INVALID COORDINATES
    # --------------------------------------------------------

    thermal_df = thermal_df[
        thermal_df[firms_lat_column].notna()
        &
        thermal_df[firms_lon_column].notna()
    ].copy()


    # --------------------------------------------------------
    # NORMALIZE FRP
    # --------------------------------------------------------

    if not thermal_df.empty:

        max_frp = thermal_df["_thermal_frp"].max()


        if max_frp > 0:

            thermal_df["_thermal_weight"] = (
                thermal_df["_thermal_frp"]
                / max_frp
            )

        else:

            thermal_df["_thermal_weight"] = 0.5


        thermal_df["_thermal_weight"] = (
            thermal_df["_thermal_weight"]
            .clip(
                lower=0.08,
                upper=1.0,
            )
        )


        # ----------------------------------------------------
        # BUILD HEATMAP DATA
        # ----------------------------------------------------

        for _, row in thermal_df.iterrows():

            try:

                fire_lat = float(
                    row[firms_lat_column]
                )

                fire_lon = float(
                    row[firms_lon_column]
                )

                fire_weight = float(
                    row["_thermal_weight"]
                )

            except (
                TypeError,
                ValueError,
            ):

                continue


            if not (
                np.isfinite(fire_lat)
                and np.isfinite(fire_lon)
                and np.isfinite(fire_weight)
            ):

                continue


            thermal_data.append(
                [
                    fire_lat,
                    fire_lon,
                    fire_weight,
                ]
            )


# ============================================================
# THERMAL ACTIVITY OVERLAY
#
# This is an overlay above the selected base map.
# ============================================================

thermal_layer = folium.FeatureGroup(
    name="🔥 FIRMS Thermal Activity",
    overlay=True,
    control=True,
    show=True,
)


# ============================================================
# BROAD THERMAL FIELD
# ============================================================

if thermal_data:

    broad_thermal = plugins.HeatMap(
        thermal_data,
        radius=70,
        blur=55,
        min_opacity=0.10,
        max_zoom=12,
        gradient={
            0.00: "#063b1d",
            0.10: "#0b6b32",
            0.20: "#16a34a",
            0.32: "#65c466",
            0.45: "#b7e51d",
            0.58: "#ffe600",
            0.70: "#ffae00",
            0.82: "#ff6500",
            0.92: "#ff2b00",
            1.00: "#c90000",
        },
    )

    broad_thermal.add_to(
        thermal_layer
    )


# ============================================================
# CORE THERMAL HOTSPOTS
# ============================================================

if thermal_data:

    core_thermal = plugins.HeatMap(
        thermal_data,
        radius=32,
        blur=24,
        min_opacity=0.25,
        max_zoom=15,
        gradient={
            0.00: "#16803a",
            0.20: "#39b54a",
            0.40: "#d6e900",
            0.58: "#ffd000",
            0.72: "#ff8c00",
            0.86: "#ff3b00",
            1.00: "#b80000",
        },
    )

    core_thermal.add_to(
        thermal_layer
    )


# ============================================================
# FIRMS DETECTION POINTS
# ============================================================

detection_group = folium.FeatureGroup(
    name="🔥 FIRMS Detection Points",
    overlay=True,
    control=True,
    show=True,
)


if thermal_data:

    for point in thermal_data:

        fire_lat = point[0]
        fire_lon = point[1]

        folium.CircleMarker(
            location=[
                fire_lat,
                fire_lon,
            ],

            radius=3,

            color="#ffd166",

            fill=True,

            fill_color="#ff5a00",

            fill_opacity=0.90,

            weight=1,

            tooltip="NASA FIRMS thermal detection",

        ).add_to(
            detection_group
        )


# ============================================================
# ADD THERMAL LAYER
# ============================================================

thermal_layer.add_to(
    fire_map
)


# ============================================================
# ADD FIRMS DETECTION LAYER
# ============================================================

detection_group.add_to(
    fire_map
)


# ============================================================
# RISK CLASSIFICATION LAYER
# ============================================================

risk_layer = folium.FeatureGroup(
    name="🎯 Risk Classification",
    overlay=True,
    control=True,
    show=True,
)


map_bounds = []


if (
    lat_column is not None
    and lon_column is not None
    and not filtered_risk.empty
):

    for _, row in filtered_risk.iterrows():

        try:

            lat = float(
                row[lat_column]
            )

            lon = float(
                row[lon_column]
            )

        except (
            TypeError,
            ValueError,
        ):

            continue


        if pd.isna(lat) or pd.isna(lon):

            continue


        map_bounds.append(
            [
                lat,
                lon,
            ]
        )


        # ----------------------------------------------------
        # RISK VALUE
        # ----------------------------------------------------

        risk_value = str(
            row[risk_column]
        ).upper().strip()


        risk_color = risk_colors.get(
            risk_value,
            "#38bdf8",
        )


        # ----------------------------------------------------
        # POPUP
        # ----------------------------------------------------

        popup_text = f"""
        <div style="
            width:300px;
            font-family:Arial,sans-serif;
            color:#222;
        ">

            <h3 style="margin-bottom:10px;">
                🔥 THERMOSCOPE RISK CELL
            </h3>

            <b>Risk Level:</b>
            <span style="
                color:{risk_color};
                font-weight:bold;
            ">
                {risk_value}
            </span>

            <br><br>

            <b>Grid:</b>
            {row.get("grid_id", "N/A")}

            <br>

            <b>Latitude:</b>
            {lat:.5f}

            <br>

            <b>Longitude:</b>
            {lon:.5f}

            <hr>

            <b>Risk Score:</b>
            {row.get("risk_score", "N/A")}

            <br>

            <b>Risk Percentage:</b>
            {row.get("risk_percentage", "N/A")}%

            <br><br>

            <b>Detection Count:</b>
            {row.get("detection_count", "N/A")}

            <br>

            <b>Active Days:</b>
            {row.get("active_days", "N/A")}

            <br>

            <b>Average FRP:</b>
            {row.get("avg_frp", "N/A")}

            <br>

            <b>Maximum FRP:</b>
            {row.get("max_frp", "N/A")}

            <hr>

            <b>Recurrence Score:</b>
            {row.get("recurrence_score", "N/A")}

            <br>

            <b>Satellite Score:</b>
            {row.get("satellite_score", "N/A")}

            <br>

            <b>FRP Intensity:</b>
            {row.get("frp_intensity", "N/A")}

            <br>

            <b>Activity Score:</b>
            {row.get("activity_score", "N/A")}

        </div>
        """


        # ----------------------------------------------------
        # RISK GRID CELL
        # ----------------------------------------------------

        GRID_SIZE = 0.01
        half_grid = GRID_SIZE / 2


        folium.Rectangle(
            bounds=[
                [
                    lat - half_grid,
                    lon - half_grid,
                ],
                [
                    lat + half_grid,
                    lon + half_grid,
                ],
            ],

            color=risk_color,

            fill=True,

            fill_color=risk_color,

            fill_opacity=0.06,

            weight=1.2,

            opacity=0.75,

            popup=folium.Popup(
                popup_text,
                max_width=350,
            ),

            tooltip=(
                f"🎯 {risk_value} RISK"
                "<br>"
                "Click for details"
            ),

        ).add_to(
            risk_layer
        )


        # ----------------------------------------------------
        # RISK MARKER
        # ----------------------------------------------------

        folium.CircleMarker(
            location=[
                lat,
                lon,
            ],

            radius=5,

            color=risk_color,

            fill=True,

            fill_color=risk_color,

            fill_opacity=0.95,

            weight=2,

            popup=folium.Popup(
                popup_text,
                max_width=350,
            ),

            tooltip=f"{risk_value} RISK",

        ).add_to(
            risk_layer
        )


# ============================================================
# ADD RISK LAYER
# ============================================================

risk_layer.add_to(
    fire_map
)


# ============================================================
# MAP TITLE
# ============================================================

title_html = """
<div style="
    position:absolute;
    top:18px;
    left:50%;
    transform:translateX(-50%);
    z-index:1000;

    background:rgba(8,12,18,0.94);

    border:1px solid #465365;
    border-radius:14px;

    padding:11px 24px;

    color:#f5f7fa;

    font-family:Arial,sans-serif;

    font-size:18px;
    font-weight:800;

    white-space:nowrap;

    box-shadow:
        0 6px 25px rgba(0,0,0,0.45);
">
🔥 THERMOSCOPE • DELHI NCR THERMAL RISK
</div>
"""


fire_map.get_root().html.add_child(
    folium.Element(
        title_html
    )
)


# ============================================================
# CUSTOM LEGEND
# ============================================================

legend_html = """
<div style="
    position:absolute;
    bottom:28px;
    right:20px;
    z-index:1000;

    width:310px;

    background:rgba(8,12,18,0.94);

    border:1px solid #465365;
    border-radius:14px;

    padding:17px 19px;

    color:#f5f7fa;

    font-family:Arial,sans-serif;

    box-shadow:
        0 6px 25px rgba(0,0,0,0.45);
">


<div style="
    font-size:17px;
    font-weight:800;
    margin-bottom:12px;
">
🔥 THERMAL INTENSITY
</div>


<div style="
    height:16px;
    border-radius:10px;

    background:
        linear-gradient(
            to right,
            #063b1d,
            #16a34a,
            #b7e51d,
            #ffe600,
            #ffae00,
            #ff6500,
            #ff2b00,
            #c90000
        );
"></div>


<div style="
    display:flex;
    justify-content:space-between;

    margin-top:5px;

    color:#aab4c1;
    font-size:11px;
">

<span>LOW FRP</span>
<span>HIGH FRP</span>

</div>


<div style="
    border-top:1px solid #29313d;
    margin:15px 0;
"></div>


<div style="
    font-size:17px;
    font-weight:800;
    margin-bottom:10px;
">
🎯 RISK CLASSIFICATION
</div>


<div style="margin:7px 0;">
<span style="
    display:inline-block;
    width:12px;
    height:12px;
    background:#ff3030;
    border-radius:50%;
    margin-right:8px;
"></span>
HIGH RISK
</div>


<div style="margin:7px 0;">
<span style="
    display:inline-block;
    width:12px;
    height:12px;
    background:#ff9500;
    border-radius:50%;
    margin-right:8px;
"></span>
MEDIUM RISK
</div>


<div style="margin:7px 0;">
<span style="
    display:inline-block;
    width:12px;
    height:12px;
    background:#20c96b;
    border-radius:50%;
    margin-right:8px;
"></span>
LOW RISK
</div>


<div style="
    border-top:1px solid #29313d;
    margin:15px 0;
"></div>


<div style="
    color:#aab4c1;
    font-size:11px;
    line-height:1.5;
">

Thermal visualization is derived from
NASA FIRMS Fire Radiative Power (FRP).

<br><br>

Green → Yellow → Orange → Red represents
increasing observed thermal activity.

</div>

</div>
"""


fire_map.get_root().html.add_child(
    folium.Element(
        legend_html
    )
)


# ============================================================
# LAYER CONTROL
# ============================================================

folium.LayerControl(
    position="topright",
    collapsed=False,
).add_to(
    fire_map
)


# ============================================================
# AUTO ZOOM
# ============================================================

if map_bounds:

    fire_map.fit_bounds(
        map_bounds,
        padding=(45, 45),
    )

elif thermal_data:

    thermal_bounds = [
        [point[0], point[1]]
        for point in thermal_data
    ]

    fire_map.fit_bounds(
        thermal_bounds,
        padding=(45, 45),
    )


# ============================================================
# DISPLAY MAP
# ============================================================

st_folium(
    fire_map,
    width=None,
    height=650,
    returned_objects=[],
)


# ============================================================
# MAP CAPTION
# ============================================================

st.markdown(
    """
    <div class="map-caption">
        🟢 Low Thermal Activity
        &nbsp;&nbsp;→&nbsp;&nbsp;
        🟡 Moderate
        &nbsp;&nbsp;→&nbsp;&nbsp;
        🟠 Elevated
        &nbsp;&nbsp;→&nbsp;&nbsp;
        🔴 High Thermal Activity
        &nbsp;&nbsp;|&nbsp;&nbsp;
        🎯 Risk markers show Thermoscope spatial classification.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# RISK INTELLIGENCE SUMMARY
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="section-title">'
    '🧠 Risk Intelligence Summary'
    '</div>',
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="section-subtitle">'
    'Key indicators contributing to the current fire-risk assessment'
    '</div>',
    unsafe_allow_html=True,
)


intel1, intel2, intel3, intel4 = st.columns(4)


# ============================================================
# INTELLIGENCE VALUES
# ============================================================

active_cells = len(
    filtered_risk
)


if detection_column is not None:

    total_detections = int(
        pd.to_numeric(
            filtered_risk[detection_column],
            errors="coerce",
        )
        .fillna(0)
        .sum()
    )

else:

    total_detections = 0


if avg_frp_column is not None:

    avg_frp = pd.to_numeric(
        filtered_risk[avg_frp_column],
        errors="coerce",
    ).mean()


    avg_frp_text = (
        f"{avg_frp:.2f}"
        if pd.notna(avg_frp)
        else "N/A"
    )

else:

    avg_frp_text = "N/A"


if not filtered_risk.empty:

    dominant_risk = (
        filtered_risk[risk_column]
        .value_counts()
        .idxmax()
    )

else:

    dominant_risk = "N/A"


with intel1:

    render_info_card(
        "ACTIVE RISK CELLS",
        active_cells,
        "Spatial grid cells currently included in the selected risk view.",
    )


with intel2:

    render_info_card(
        "FIRE DETECTIONS",
        total_detections,
        "FIRMS detections contributing to the selected risk cells.",
    )


with intel3:

    render_info_card(
        "AVG FRP",
        avg_frp_text,
        "Average Fire Radiative Power across selected cells.",
    )


with intel4:

    render_info_card(
        "DOMINANT RISK",
        dominant_risk,
        "Most frequent risk category in the current selection.",
    )


# ============================================================
# TEMPORAL FIRE ACTIVITY ANALYSIS
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="section-title">'
    '🔥 Temporal Fire Activity'
    '</div>',
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="section-subtitle">'
    'Fire detection activity over time from NASA FIRMS observations'
    '</div>',
    unsafe_allow_html=True,
)


temporal_df = firms_df.copy()


# ============================================================
# PREPARE TEMPORAL DATA
# ============================================================

if "acq_date" in temporal_df.columns:

    temporal_df["acq_date"] = pd.to_datetime(
        temporal_df["acq_date"],
        errors="coerce",
    )

    temporal_df = temporal_df[
        temporal_df["acq_date"].notna()
    ].copy()

else:

    temporal_df = pd.DataFrame()


# ============================================================
# TEMPORAL ANALYSIS
# ============================================================

if not temporal_df.empty:

    daily_activity = (
        temporal_df
        .groupby("acq_date")
        .size()
        .rename("detections")
    )


    st.line_chart(
        daily_activity,
        height=320,
    )


    peak_date = daily_activity.idxmax()


    peak_count = int(
        daily_activity.max()
    )


    observation_days = int(
        daily_activity.count()
    )


    temporal_left, temporal_right = st.columns(2)


    with temporal_left:

        render_info_card(
            "PEAK FIRE ACTIVITY",
            f"{peak_count} detections",
            (
                "Highest number of FIRMS detections recorded on "
                f"{peak_date.strftime('%d %b %Y')}."
            ),
        )


    with temporal_right:

        render_info_card(
            "OBSERVATION PERIOD",
            f"{observation_days} active days",
            "Number of dates containing at least one FIRMS fire detection.",
        )


else:

    st.info(
        "Temporal FIRMS observation data is unavailable."
    )


# ============================================================
# RISK ANALYTICS
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="section-title">'
    '📊 Fire Risk Analytics'
    '</div>',
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="section-subtitle">'
    'Distribution of predicted risk levels across monitored grid cells'
    '</div>',
    unsafe_allow_html=True,
)


analytics_left, analytics_right = st.columns(
    [1.25, 1]
)


# ============================================================
# RISK DISTRIBUTION
# ============================================================

with analytics_left:

    risk_counts = (
        filtered_risk[risk_column]
        .value_counts()
        .reindex(
            [
                "HIGH",
                "MEDIUM",
                "LOW",
            ],
            fill_value=0,
        )
    )


    st.bar_chart(
        risk_counts,
        height=330,
    )


# ============================================================
# HIGHEST ACTIVITY ZONES
# ============================================================

with analytics_right:

    st.markdown(
        "### 🔥 Highest Activity Zones"
    )


    activity_df = filtered_risk.copy()


    sort_column = None


    if avg_frp_column is not None:

        sort_column = avg_frp_column

    elif detection_column is not None:

        sort_column = detection_column


    if sort_column is not None:

        activity_df[sort_column] = pd.to_numeric(
            activity_df[sort_column],
            errors="coerce",
        )

        activity_df = activity_df.sort_values(
            sort_column,
            ascending=False,
        )


    display_columns = [
        col
        for col in [
            "grid_id",
            risk_column,
            "detection_count",
            "active_days",
            "avg_frp",
            "max_frp",
        ]
        if col in activity_df.columns
    ]


    if display_columns:

        st.dataframe(
            activity_df[
                display_columns
            ].head(8),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Activity information unavailable."
        )


# ============================================================
# SATELLITE INFORMATION
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="section-title">'
    '🛰️ Satellite Observation Information'
    '</div>',
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="section-subtitle">'
    'Understanding the satellite data powering Thermoscope'
    '</div>',
    unsafe_allow_html=True,
)


info1, info2, info3 = st.columns(3)


with info1:

    render_info_card(
        "DATA SOURCE",
        "NASA FIRMS",
        (
            "Fire Information for Resource Management System "
            "provides satellite-based thermal anomaly observations."
        ),
    )


with info2:

    render_info_card(
        "SATELLITE SENSOR",
        "VIIRS",
        (
            "Visible Infrared Imaging Radiometer Suite enables "
            "detection of active thermal anomalies."
        ),
    )


with info3:

    render_info_card(
        "INTELLIGENCE PIPELINE",
        "Detection → Risk",
        (
            "Satellite observations are aggregated spatially "
            "and converted into explainable fire-risk predictions."
        ),
    )


# ============================================================
# FIRMS DETECTION DATA
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="section-title">'
    '🔥 FIRMS Detection Data'
    '</div>',
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="section-subtitle">'
    'Raw satellite fire detections used by the Thermoscope intelligence layer'
    '</div>',
    unsafe_allow_html=True,
)


st.dataframe(
    firms_df,
    use_container_width=True,
    height=350,
    hide_index=True,
)


# ============================================================
# RISK PREDICTION DATA
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="section-title">'
    '🎯 Risk Prediction Data'
    '</div>',
    unsafe_allow_html=True,
)


st.markdown(
    '<div class="section-subtitle">'
    'Spatially aggregated fire activity and predicted risk information'
    '</div>',
    unsafe_allow_html=True,
)


st.dataframe(
    filtered_risk,
    use_container_width=True,
    height=380,
    hide_index=True,
)


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
<div class="footer">

    THERMOSCOPE • Satellite-Based Fire Risk Intelligence • Delhi NCR

    <br>

    Powered by NASA FIRMS / VIIRS satellite observations

</div>
""",
    unsafe_allow_html=True,
)