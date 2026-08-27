import os
import html
import requests

import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium import plugins
from streamlit_folium import st_folium


# ============================================================
# THERMOSCOPE DASHBOARD
# NASA FIRMS / SIH FIRE RISK INTELLIGENCE
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
CSS_FILE = os.path.join(ASSETS_DIR, "style.css")
HTML_FILE = os.path.join(ASSETS_DIR, "dashboard.html")


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="THERMOSCOPE | Fire Risk Intelligence",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# LOAD CSS
# ============================================================

def load_css():

    if os.path.exists(CSS_FILE):

        with open(CSS_FILE, "r", encoding="utf-8") as f:

            st.markdown(
                f"<style>{f.read()}</style>",
                unsafe_allow_html=True,
            )

    else:

        st.warning(
            f"CSS file not found: {CSS_FILE}"
        )


# ============================================================
# LOAD HTML TEMPLATE
# ============================================================

@st.cache_data
def load_html_template():

    if os.path.exists(HTML_FILE):

        with open(HTML_FILE, "r", encoding="utf-8") as f:

            return f.read()

    return ""


load_css()

HTML = load_html_template()


# ============================================================
# TEMPLATE HELPERS
# ============================================================

def render_template(section, **values):

    """
    Render a named HTML section from dashboard.html.
    Values are HTML escaped.
    """

    marker_start = f"<!-- {section}:START -->"
    marker_end = f"<!-- {section}:END -->"

    if marker_start not in HTML or marker_end not in HTML:

        return

    block = (
        HTML
        .split(marker_start, 1)[1]
        .split(marker_end, 1)[0]
    )

    for key, value in values.items():

        block = block.replace(
            "{{" + key + "}}",
            html.escape(str(value)),
        )

    st.markdown(
        block,
        unsafe_allow_html=True,
    )


def render_raw_template(section, **values):

    """
    Render an HTML section while allowing selected
    values to contain HTML.
    """

    marker_start = f"<!-- {section}:START -->"
    marker_end = f"<!-- {section}:END -->"

    if marker_start not in HTML or marker_end not in HTML:

        return

    block = (
        HTML
        .split(marker_start, 1)[1]
        .split(marker_end, 1)[0]
    )

    for key, value in values.items():

        block = block.replace(
            "{{" + key + "}}",
            str(value),
        )

    st.markdown(
        block,
        unsafe_allow_html=True,
    )


# ============================================================
# DATA HELPERS
# ============================================================

def find_column(df, names):

    for name in names:

        if name in df.columns:

            return name

    return None


def popup_value(row, column, default="N/A"):

    value = row.get(
        column,
        default,
    )

    if value is None:

        return default

    try:

        if pd.isna(value):

            return default

    except (TypeError, ValueError):

        pass

    return value


def render_info_card(title, value, text):

    render_raw_template(
        "INFO_CARD",
        TITLE=html.escape(str(title)),
        VALUE=html.escape(str(value)),
        TEXT=html.escape(str(text)),
    )


# ============================================================
# DATA FILE PATHS
# ============================================================

# ============================================================
# DATA FILE PATHS
# ============================================================

def get_data_files(use_live=False):

    if use_live:

        return (
            os.path.join(
                BASE_DIR,
                "..",
                "data",
                "delhi_risk_predictions_live.csv",
            ),
            os.path.join(
                BASE_DIR,
                "..",
                "data",
                "delhi_firms_live.csv",
            ),
        )

    return (
        os.path.join(
            BASE_DIR,
            "..",
            "data",
            "delhi_risk_predictions.csv",
        ),
        os.path.join(
            BASE_DIR,
            "..",
            "data",
            "delhi_firms.csv",
        ),
    )


# ============================================================
# LOAD DATA
# ============================================================

# ============================================================
# LOAD DATA FROM FASTAPI
# ============================================================

@st.cache_data
def load_data(use_live=False):

    API_BASE_URL = "http://127.0.0.1:8000"

    mode = "live" if use_live else "sih"

    try:

        # ====================================================
        # RISK PREDICTIONS
        # ====================================================

        risk_response = requests.get(
            f"{API_BASE_URL}/api/risk",
            params={
                "mode": mode
            },
            timeout=10,
        )

        risk_response.raise_for_status()

        risk_df = pd.DataFrame(
            risk_response.json()
        )

        # ====================================================
        # FIRMS DETECTIONS
        # ====================================================

        firms_response = requests.get(
            f"{API_BASE_URL}/api/detections",
            params={
                "mode": mode
            },
            timeout=10,
        )

        firms_response.raise_for_status()

        firms_df = pd.DataFrame(
            firms_response.json()
        )

        # ====================================================
        # VALIDATE RISK DATA
        # ====================================================

        if risk_df.empty:

            raise ValueError(
                "Risk API returned no data."
            )

        # ====================================================
        # VALIDATE FIRMS DATA
        # ====================================================

        if firms_df.empty:

            raise ValueError(
                "FIRMS API returned no data."
            )

        return (
            risk_df,
            firms_df
        )

    # ========================================================
    # API CONNECTION ERROR
    # ========================================================

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "Unable to connect to Thermoscope FastAPI.\n\n"
            "Start the API first using:\n"
            "uvicorn src.api:app --reload --port 8000"
        )

    # ========================================================
    # API TIMEOUT
    # ========================================================

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "FastAPI request timed out.\n\n"
            "Please check that FastAPI is running."
        )

    # ========================================================
    # REQUEST ERROR
    # ========================================================

    except requests.exceptions.RequestException as error:

        raise RuntimeError(
            f"Thermoscope API request failed:\n{error}"
        )

    # ========================================================
    # DATA ERROR
    # ========================================================

    except ValueError as error:

        raise RuntimeError(
            f"Thermoscope data error:\n{error}"
        )

        # ----------------------------------------------------
        # Get FIRMS detection data from FastAPI
        # ----------------------------------------------------

        firms_response = requests.get(
    f"{API_BASE_URL}/api/detections",
    params={"mode": mode},
    timeout=10
)
        firms_response.raise_for_status()

        firms_df = pd.DataFrame(
            firms_response.json()
        )

        # ----------------------------------------------------
        # Validate responses
        # ----------------------------------------------------

        if risk_df.empty:

            raise ValueError(
                "Risk API returned no data."
            )

        if firms_df.empty:

            raise ValueError(
                "FIRMS API returned no data."
            )

        return risk_df, firms_df

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "Unable to connect to AgniRakshak API. "
            "Please start FastAPI on port 8000."
        )

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "API request timed out. "
            "Please check that FastAPI is running."
        )

    except requests.exceptions.RequestException as error:

        raise RuntimeError(
            f"API request failed: {error}"
        )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## ⚙️ Controls")

    st.divider()

    st.markdown("### 📡 Data Mode")

    live_risk_file, live_firms_file = get_data_files(
        use_live=True
    )

    live_available = (
        os.path.exists(live_risk_file)
        and os.path.exists(live_firms_file)
    )

    data_mode = st.radio(
        "Select data mode",
        [
            "SIH Dataset",
            "Live Processed Data",
        ],
        index=0,
    )

    if (
        data_mode == "Live Processed Data"
        and not live_available
    ):

        st.warning(
            "Live processed files are not available. "
            "Switching to the SIH dataset."
        )

        data_mode = "SIH Dataset"

    use_live = (
        data_mode == "Live Processed Data"
    )

    render_raw_template(
        "STATUS_CARD",
        ICON="🟢" if use_live else "🔵",
        TEXT=(
            "Live processed CSV files detected."
            if use_live
            else
            "Using the SIH-provided NASA FIRMS dataset."
        ),
    )

    if st.button(
        "🔄 Refresh Data",
        use_container_width=True,
    ):

        st.cache_data.clear()

        st.rerun()

    st.divider()


# ============================================================
# LOAD DATA
# ============================================================

try:

    risk_df, firms_df = load_data(
        use_live=use_live
    )

except Exception as e:

    if use_live:

        try:

            use_live = False

            risk_df, firms_df = load_data(
                use_live=False
            )

            st.sidebar.warning(
                "Live data could not be loaded. "
                "SIH dataset is being used."
            )

        except Exception as fallback_error:

            st.error(
                f"Unable to load Thermoscope data: "
                f"{fallback_error}"
            )

            st.stop()

    else:

        st.error(
            f"Unable to load Thermoscope data: {e}"
        )

        st.stop()


# ============================================================
# RISK COLUMNS
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
# FALLBACK RISK CLASSIFICATION
# ============================================================

if risk_column is None:

    if "risk_score" in risk_df.columns:

        score = pd.to_numeric(
            risk_df["risk_score"],
            errors="coerce",
        )

        risk_df["risk_category"] = pd.cut(
            score,
            bins=[
                -float("inf"),
                0.45,
                0.75,
                float("inf"),
            ],
            labels=[
                "LOW",
                "MEDIUM",
                "HIGH",
            ],
        )

    elif "activity_score" in risk_df.columns:

        score = pd.to_numeric(
            risk_df["activity_score"],
            errors="coerce",
        )

        risk_df["risk_category"] = pd.cut(
            score,
            bins=[
                -float("inf"),
                0.45,
                0.75,
                float("inf"),
            ],
            labels=[
                "LOW",
                "MEDIUM",
                "HIGH",
            ],
        )

    elif avg_frp_column is not None:

        frp = pd.to_numeric(
            risk_df[avg_frp_column],
            errors="coerce",
        )

        risk_df["risk_category"] = pd.cut(
            frp,
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

        detections = pd.to_numeric(
            risk_df[detection_column],
            errors="coerce",
        )

        risk_df["risk_category"] = pd.cut(
            detections,
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
# SIDEBAR FILTERS
# ============================================================

with st.sidebar:

    st.divider()

    st.markdown("### 🎯 Risk Filter")

    present = set(
        risk_df[
            risk_column
        ]
        .dropna()
        .unique()
    )

    available_risks = [
        x
        for x in [
            "HIGH",
            "MEDIUM",
            "LOW",
        ]
        if x in present
    ]

    if not available_risks:

        available_risks = [
            "HIGH",
            "MEDIUM",
            "LOW",
        ]

    selected_risks = st.multiselect(
        "Select risk levels",
        options=available_risks,
        default=available_risks,
    )

    st.divider()

    st.markdown("### 🛰️ Data Source")

    st.markdown(
        "**NASA FIRMS**\n\n"
        "VIIRS satellite observations"
    )

    st.divider()

    st.markdown("### 📍 Monitoring Region")

    st.markdown(
        "**Delhi NCR**\n\n"
        "Approx. Delhi NCR monitoring extent"
    )

    st.divider()

    st.markdown("### 🧠 Intelligence Layer")

    st.caption(
        "Satellite activity → "
        "Spatial aggregation → "
        "Risk scoring → "
        "Prediction"
    )


# ============================================================
# FILTERED RISK DATA
# ============================================================

if selected_risks:

    filtered_risk = (
        risk_df[
            risk_df[risk_column]
            .isin(selected_risks)
        ]
        .copy()
    )

else:

    filtered_risk = (
        risk_df
        .iloc[0:0]
        .copy()
    )


# ============================================================
# HEADER
# ============================================================

header_left, header_right = st.columns(
    [5, 1],
    vertical_alignment="center",
)

with header_left:

    render_template(
        "HERO",
        TITLE="🔥 THERMOSCOPE",
        SUBTITLE=(
            "Delhi NCR Fire Risk Intelligence "
            "& Satellite Monitoring System"
        ),
    )

with header_right:

    render_template(
        "BADGE",
        BADGE_CLASS=(
            "live-badge"
            if use_live
            else "dataset-badge"
        ),
        BADGE_TEXT=(
            "🟢 LIVE PROCESSED DATA"
            if use_live
            else
            "🛰️ NASA FIRMS • VIIRS DATA"
        ),
    )


# ============================================================
# SYSTEM OVERVIEW
# ============================================================

render_template(
    "SECTION_LABEL",
    TEXT="SYSTEM OVERVIEW",
)

total_firms = len(firms_df)

total_grids = len(risk_df)


# ============================================================
# SYSTEM STATUS
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)

render_template(
    "SECTION_TITLE",
    TEXT="🟢 System Status",
)

status1, status2, status3, status4 = st.columns(4)

with status1:

    st.metric(
        "🔥 FIRMS DETECTIONS",
        len(firms_df),
    )

with status2:

    st.metric(
        "🗺️ RISK GRID CELLS",
        len(risk_df),
    )

with status3:

    st.metric(
        "🛰️ SATELLITE",
        "VIIRS",
    )

with status4:

    st.metric(
        "⚡ BACKEND",
        "ONLINE",
    )




# ============================================================
# LAST DETECTION
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

            latest_detection = (
                dates.max()
                .strftime("%d %b %Y")
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

        latest_detection = (
            dates.max()
            .strftime("%d %b %Y")
        )


# ============================================================
# RISK COUNTS
# ============================================================

high_count = int(
    (
        risk_df[risk_column]
        == "HIGH"
    ).sum()
)

medium_count = int(
    (
        risk_df[risk_column]
        == "MEDIUM"
    ).sum()
)

low_count = int(
    (
        risk_df[risk_column]
        == "LOW"
    ).sum()
)


# ============================================================
# OVERVIEW METRICS
# ============================================================

# ============================================================
# RISK METRICS
# ============================================================

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric(
        "🔴 HIGH RISK",
        f"{high_count:,}",
    )

with m2:
    st.metric(
        "🟠 MEDIUM RISK",
        f"{medium_count:,}",
    )

with m3:
    st.metric(
        "🟢 LOW RISK",
        f"{low_count:,}",
    )

with m4:
    st.metric(
        "📅 LAST DETECTION",
        latest_detection or "N/A",
    )


# ============================================================
# MAP SECTION
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)

render_template(
    "SECTION_TITLE",
    TEXT="🗺️ Delhi NCR Thermal Fire Risk Map",
)

render_template(
    "SECTION_SUBTITLE",
    TEXT=(
        "NASA FIRMS thermal activity with "
        "FRP-weighted spatial intensity and "
        "Thermoscope risk classification"
    ),
)


# ============================================================
# MAP
# ============================================================

map_center = [
    28.6139,
    77.2090,
]

fire_map = folium.Map(
    location=map_center,
    zoom_start=9,
    tiles=None,
    control_scale=True,
)


# ============================================================
# SATELLITE BASE MAP
# ============================================================

folium.TileLayer(
    tiles=(
        "https://server.arcgisonline.com/"
        "ArcGIS/rest/services/World_Imagery/"
        "MapServer/tile/{z}/{y}/{x}"
    ),
    attr="Esri World Imagery",
    name="🛰️ Satellite Base",
    overlay=False,
    control=True,
    show=True,
).add_to(fire_map)


# ============================================================
# STREET MAP
# ============================================================

folium.TileLayer(
    tiles=(
        "https://{s}.tile.openstreetmap.org/"
        "{z}/{x}/{y}.png"
    ),
    attr="© OpenStreetMap contributors",
    name="🗺️ Street Map",
    overlay=False,
    control=True,
    show=False,
).add_to(fire_map)


# ============================================================
# RISK COLORS
# ============================================================

risk_colors = {
    "HIGH": "#ff3030",
    "MEDIUM": "#ff9500",
    "LOW": "#20c96b",
}


# ============================================================
# FIRMS COLUMNS
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
# THERMAL DATA
# ============================================================

thermal_data = []

thermal_df = pd.DataFrame()


if (
    firms_lat_column
    and firms_lon_column
):

    thermal_df = firms_df.copy()

    thermal_df[
        firms_lat_column
    ] = pd.to_numeric(
        thermal_df[
            firms_lat_column
        ],
        errors="coerce",
    )

    thermal_df[
        firms_lon_column
    ] = pd.to_numeric(
        thermal_df[
            firms_lon_column
        ],
        errors="coerce",
    )

    if firms_frp_column:

        thermal_df[
            "_thermal_frp"
        ] = pd.to_numeric(
            thermal_df[
                firms_frp_column
            ],
            errors="coerce",
        )

    else:

        thermal_df[
            "_thermal_frp"
        ] = 1.0

    thermal_df[
        "_thermal_frp"
    ] = (
        thermal_df[
            "_thermal_frp"
        ]
        .fillna(0)
        .clip(lower=0)
    )

    thermal_df = thermal_df[
        thermal_df[
            firms_lat_column
        ].between(27.0, 30.5)
        &
        thermal_df[
            firms_lon_column
        ].between(75.0, 79.5)
    ].dropna(
        subset=[
            firms_lat_column,
            firms_lon_column,
        ]
    )


    if not thermal_df.empty:

        max_frp = (
            thermal_df[
                "_thermal_frp"
            ].max()
        )

        thermal_df[
            "_thermal_weight"
        ] = (
            thermal_df[
                "_thermal_frp"
            ] / max_frp
            if max_frp > 0
            else 0.5
        )

        thermal_df[
            "_thermal_weight"
        ] = thermal_df[
            "_thermal_weight"
        ].clip(
            0.08,
            1.0,
        )


        for _, row in thermal_df.iterrows():

            try:

                fire_lat = float(
                    row[
                        firms_lat_column
                    ]
                )

                fire_lon = float(
                    row[
                        firms_lon_column
                    ]
                )

                fire_weight = float(
                    row[
                        "_thermal_weight"
                    ]
                )

            except (
                TypeError,
                ValueError,
            ):

                continue


            if (
                np.isfinite(fire_lat)
                and np.isfinite(fire_lon)
                and np.isfinite(fire_weight)
            ):

                thermal_data.append(
                    [
                        fire_lat,
                        fire_lon,
                        fire_weight,
                    ]
                )


# ============================================================
# THERMAL HEATMAP
# ============================================================

thermal_layer = folium.FeatureGroup(
    name="🔥 FIRMS Thermal Activity",
    overlay=True,
    control=True,
    show=True,
)


if thermal_data:

    plugins.HeatMap(
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
    ).add_to(
        thermal_layer
    )


    plugins.HeatMap(
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
    ).add_to(
        thermal_layer
    )


thermal_layer.add_to(
    fire_map
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


for point in thermal_data:

    folium.CircleMarker(
        location=[
            point[0],
            point[1],
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


for _, row in filtered_risk.iterrows():

    if not lat_column or not lon_column:
        continue

    try:

        lat = float(row[lat_column])
        lon = float(row[lon_column])

    except (TypeError, ValueError):

        continue

    if not (
        np.isfinite(lat)
        and np.isfinite(lon)
    ):

        continue

    map_bounds.append([lat, lon])

    risk_value = (
        str(
            row[risk_column]
        )
        .upper()
        .strip()
    )

    risk_color = risk_colors.get(
        risk_value,
        "#38bdf8",
    )


    # ========================================================
    # EXPLAINABILITY
    # ========================================================

    dominant_factor = str(
        popup_value(
            row,
            "dominant_factor",
            "Multiple fire indicators",
        )
    )

    explanation = {

        "HIGH":
            "Multiple fire-activity indicators suggest elevated "
            "thermal risk in this spatial cell.",

        "MEDIUM":
            "Observed fire activity shows moderate thermal risk "
            "based on the available spatial indicators.",

        "LOW":
            "Observed fire activity currently indicates relatively "
            "low thermal risk in this spatial cell.",

    }.get(
        risk_value,
        "Risk classification based on available Thermoscope indicators.",
    )


    # ========================================================
    # COMPACT POPUP
    # ========================================================

    popup_text = f"""
    <div class="map-popup" style="
        width: 100%;
        max-width: 340px;
        max-height: 360px;
        overflow-y: auto;
        overflow-x: hidden;
        box-sizing: border-box;
        padding: 4px 7px 6px 4px;
        font-family: Arial, sans-serif;
        font-size: 12px;
        line-height: 1.35;
    ">

        <!-- HEADER -->

        <div class="popup-header" style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        ">

            <div class="popup-title" style="
                font-size: 13px;
                font-weight: 700;
                white-space: nowrap;
            ">
                🔥 THERMOSCOPE
            </div>

            <div
                class="popup-risk"
                style="
                    color:{risk_color};
                    font-size:12px;
                    font-weight:800;
                    white-space:nowrap;
                "
            >
                🎯 {html.escape(risk_value)} RISK
            </div>

        </div>


        <!-- LOCATION -->

        <div class="popup-meta" style="
            background: #f5f5f5;
            border-radius: 7px;
            padding: 6px 8px;
            margin-bottom: 7px;
            color: #333;
        ">

            <b>Grid:</b>
            {html.escape(
                str(
                    popup_value(
                        row,
                        "grid_id",
                    )
                )
            )}

            <br>

            <b>Location:</b>
            {lat:.5f}, {lon:.5f}

        </div>


        <!-- RISK SCORE -->

        <div class="popup-score" style="
            text-align:center;
            border-radius:8px;
            padding:7px;
            margin-bottom:8px;
            background:#fafafa;
            border:1px solid #e5e5e5;
        ">

            <div style="
                font-size:9px;
                font-weight:700;
                letter-spacing:0.7px;
                color:#777;
            ">
                RISK ASSESSMENT
            </div>

            <div style="
                color:{risk_color};
                font-size:22px;
                font-weight:800;
                margin:1px 0;
            ">
                {html.escape(
                    str(
                        popup_value(
                            row,
                            "risk_score",
                        )
                    )
                )}
            </div>

            <div style="
                font-size:10px;
                color:#555;
            ">
                Risk Percentage:
                <b>
                    {html.escape(
                        str(
                            popup_value(
                                row,
                                "risk_percentage",
                            )
                        )
                    )}%
                </b>
            </div>

        </div>


        <!-- WHY THIS RISK -->

        <div style="
            font-size:11px;
            font-weight:800;
            margin:7px 0 4px 0;
            color:#222;
        ">
            🔎 WHY THIS RISK?
        </div>

        <div style="
            border-left:3px solid {risk_color};
            background:#fafafa;
            border-radius:5px;
            padding:6px 8px;
            margin-bottom:7px;
            color:#444;
            font-size:10px;
        ">

            <b>Dominant Factor:</b>
            {html.escape(dominant_factor)}

            <br>

            {html.escape(explanation)}

        </div>


        <!-- OBSERVED FIRE ACTIVITY -->

        <div style="
            font-size:11px;
            font-weight:800;
            margin:7px 0 4px 0;
            color:#222;
        ">
            🔥 OBSERVED FIRE ACTIVITY
        </div>

        <table style="
            width:100%;
            border-collapse:collapse;
            font-size:10px;
            margin-bottom:7px;
        ">

            <tr>
                <td style="padding:3px 4px;">
                    FIRMS Detections
                </td>

                <td style="
                    padding:3px 4px;
                    text-align:right;
                    font-weight:700;
                ">
                    {html.escape(
                        str(
                            popup_value(
                                row,
                                "detection_count",
                            )
                        )
                    )}
                </td>
            </tr>

            <tr>
                <td style="padding:3px 4px;">
                    Active Days
                </td>

                <td style="
                    padding:3px 4px;
                    text-align:right;
                    font-weight:700;
                ">
                    {html.escape(
                        str(
                            popup_value(
                                row,
                                "active_days",
                            )
                        )
                    )}
                </td>
            </tr>

            <tr>
                <td style="padding:3px 4px;">
                    Average FRP
                </td>

                <td style="
                    padding:3px 4px;
                    text-align:right;
                    font-weight:700;
                ">
                    {html.escape(
                        str(
                            popup_value(
                                row,
                                "avg_frp",
                            )
                        )
                    )}
                </td>
            </tr>

            <tr>
                <td style="padding:3px 4px;">
                    Maximum FRP
                </td>

                <td style="
                    padding:3px 4px;
                    text-align:right;
                    font-weight:700;
                ">
                    {html.escape(
                        str(
                            popup_value(
                                row,
                                "max_frp",
                            )
                        )
                    )}
                </td>
            </tr>

        </table>


        <!-- INTELLIGENCE SIGNALS -->

        <div style="
            font-size:11px;
            font-weight:800;
            margin:7px 0 4px 0;
            color:#222;
        ">
            🧠 INTELLIGENCE SIGNALS
        </div>

        <table style="
            width:100%;
            border-collapse:collapse;
            font-size:10px;
            margin-bottom:7px;
        ">

            <tr>
                <td style="padding:3px 4px;">
                    ↻ Recurrence Score
                </td>

                <td style="
                    padding:3px 4px;
                    text-align:right;
                    font-weight:700;
                ">
                    {html.escape(
                        str(
                            popup_value(
                                row,
                                "recurrence_score",
                            )
                        )
                    )}
                </td>
            </tr>

            <tr>
                <td style="padding:3px 4px;">
                    🛰️ Satellite Score
                </td>

                <td style="
                    padding:3px 4px;
                    text-align:right;
                    font-weight:700;
                ">
                    {html.escape(
                        str(
                            popup_value(
                                row,
                                "satellite_score",
                            )
                        )
                    )}
                </td>
            </tr>

            <tr>
                <td style="padding:3px 4px;">
                    🌡️ FRP Intensity
                </td>

                <td style="
                    padding:3px 4px;
                    text-align:right;
                    font-weight:700;
                ">
                    {html.escape(
                        str(
                            popup_value(
                                row,
                                "frp_intensity",
                            )
                        )
                    )}
                </td>
            </tr>

            <tr>
                <td style="padding:3px 4px;">
                    🔁 Repeat Detection
                </td>

                <td style="
                    padding:3px 4px;
                    text-align:right;
                    font-weight:700;
                ">
                    {html.escape(
                        str(
                            popup_value(
                                row,
                                "repeat_detection_score",
                            )
                        )
                    )}
                </td>
            </tr>

            <tr>
                <td style="padding:3px 4px;">
                    📊 Activity Score
                </td>

                <td style="
                    padding:3px 4px;
                    text-align:right;
                    font-weight:700;
                ">
                    {html.escape(
                        str(
                            popup_value(
                                row,
                                "activity_score",
                            )
                        )
                    )}
                </td>
            </tr>

        </table>


        <!-- RISK CONTRIBUTIONS -->

        <div style="
            font-size:11px;
            font-weight:800;
            margin:7px 0 4px 0;
            color:#222;
        ">
            📊 RISK CONTRIBUTIONS
        </div>

        <table style="
            width:100%;
            border-collapse:collapse;
            font-size:10px;
            margin-bottom:7px;
        ">

            <tr>
                <td style="padding:3px 4px;">
                    ↻ Recurrence
                </td>

                <td style="
                    padding:3px 4px;
                    text-align:right;
                    font-weight:700;
                ">
                    {html.escape(
                        str(
                            popup_value(
                                row,
                                "recurrence_contribution",
                            )
                        )
                    )}
                </td>
            </tr>

            <tr>
                <td style="padding:3px 4px;">
                    🌡️ FRP
                </td>

                <td style="
                    padding:3px 4px;
                    text-align:right;
                    font-weight:700;
                ">
                    {html.escape(
                        str(
                            popup_value(
                                row,
                                "frp_contribution",
                            )
                        )
                    )}
                </td>
            </tr>

            <tr>
                <td style="padding:3px 4px;">
                    🔁 Repeat Detection
                </td>

                <td style="
                    padding:3px 4px;
                    text-align:right;
                    font-weight:700;
                ">
                    {html.escape(
                        str(
                            popup_value(
                                row,
                                "repeat_detection_contribution",
                            )
                        )
                    )}
                </td>
            </tr>

        </table>


        <!-- FINAL ASSESSMENT -->

        <div style="
            border:1px solid {risk_color};
            border-radius:7px;
            padding:7px;
            text-align:center;
            margin-top:7px;
            background:#fafafa;
        ">

            <div style="
                font-size:9px;
                color:#777;
                font-weight:700;
                letter-spacing:0.5px;
            ">
                THERMOSCOPE ASSESSMENT
            </div>

            <strong style="
                color:{risk_color};
                font-size:12px;
            ">
                {html.escape(risk_value)} FIRE RISK
            </strong>

        </div>

    </div>
    """


    # ========================================================
    # RISK GRID
    # ========================================================

    grid_size = 0.01
    half_grid = grid_size / 2

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
            max_width=360,
            max_height=430,
        ),
        tooltip=(
            f"🎯 {risk_value} RISK — "
            "Click for details"
        ),
    ).add_to(risk_layer)


    # ========================================================
    # RISK MARKER
    # ========================================================

    folium.CircleMarker(
        location=[
            lat,
            lon,
        ],
        radius=6,
        color=risk_color,
        fill=True,
        fill_color=risk_color,
        fill_opacity=0.95,
        weight=2,
        popup=folium.Popup(
            popup_text,
            max_width=360,
            max_height=430,
        ),
        tooltip=(
            f"🎯 {risk_value} RISK — "
            "Click for details"
        ),
    ).add_to(risk_layer)


risk_layer.add_to(
    fire_map
)


# ============================================================
# MAP OVERLAY HTML
# ============================================================

def get_template_block(section):

    start = f"<!-- {section}:START -->"
    end = f"<!-- {section}:END -->"

    if (
        start not in HTML
        or end not in HTML
    ):

        return ""

    return (
        HTML
        .split(start, 1)[1]
        .split(end, 1)[0]
        .strip()
    )


map_title_html = get_template_block(
    "MAP_TITLE"
)

legend_html = get_template_block(
    "MAP_LEGEND"
)


if map_title_html:

    fire_map.get_root().html.add_child(
        folium.Element(
            map_title_html
        )
    )


if legend_html:

    fire_map.get_root().html.add_child(
        folium.Element(
            legend_html
        )
    )


# ============================================================
# MAP LAYER CONTROL
# ============================================================

folium.LayerControl(
    position="topright",
    collapsed=False,
).add_to(
    fire_map
)


# ============================================================
# MAP AUTO ZOOM
# ============================================================

if map_bounds:

    fire_map.fit_bounds(
        map_bounds,
        padding=(45, 45),
    )

elif thermal_data:

    fire_map.fit_bounds(
        [
            [
                point[0],
                point[1],
            ]
            for point in thermal_data
        ],
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


render_template(
    "MAP_CAPTION",
    TEXT=(
        "🟢 Low Thermal Activity → "
        "🟡 Moderate → "
        "🟠 Elevated → "
        "🔴 High Thermal Activity | "
        "🎯 Risk markers show Thermoscope spatial classification."
    ),
)


# ============================================================
# RISK INTELLIGENCE SUMMARY
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)

render_template(
    "SECTION_TITLE",
    TEXT="🧠 Risk Intelligence Summary",
)

render_template(
    "SECTION_SUBTITLE",
    TEXT=(
        "Key indicators contributing to the "
        "current fire-risk assessment"
    ),
)


intel1, intel2, intel3, intel4 = st.columns(4)

active_cells = len(
    filtered_risk
)


# ============================================================
# TOTAL DETECTIONS
# ============================================================

if detection_column:

    total_detections = int(
        pd.to_numeric(
            filtered_risk[
                detection_column
            ],
            errors="coerce",
        )
        .fillna(0)
        .sum()
    )

else:

    total_detections = 0


# ============================================================
# AVG FRP
# ============================================================

if avg_frp_column:

    avg_frp = pd.to_numeric(
        filtered_risk[
            avg_frp_column
        ],
        errors="coerce",
    ).mean()

    avg_frp_text = (
        f"{avg_frp:.2f}"
        if pd.notna(avg_frp)
        else "N/A"
    )

else:

    avg_frp_text = "N/A"


# ============================================================
# DOMINANT RISK
# ============================================================

dominant_risk = (

    filtered_risk[
        risk_column
    ]
    .value_counts()
    .idxmax()

    if not filtered_risk.empty

    else "N/A"
)


with intel1:

    render_info_card(
        "ACTIVE RISK CELLS",
        active_cells,
        "Spatial grid cells currently included "
        "in the selected risk view.",
    )


with intel2:

    render_info_card(
        "FIRE DETECTIONS",
        total_detections,
        "FIRMS detections contributing to "
        "the selected risk cells.",
    )


with intel3:

    render_info_card(
        "AVG FRP",
        avg_frp_text,
        "Average Fire Radiative Power "
        "across selected cells.",
    )


with intel4:

    render_info_card(
        "DOMINANT RISK",
        dominant_risk,
        "Most frequent risk category "
        "in the current selection.",
    )


# ============================================================
# TEMPORAL FIRE ACTIVITY
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)

render_template(
    "SECTION_TITLE",
    TEXT="🔥 Temporal Fire Activity",
)

render_template(
    "SECTION_SUBTITLE",
    TEXT=(
        "Fire detection activity over time "
        "from NASA FIRMS observations"
    ),
)


temporal_df = firms_df.copy()

date_source = find_column(
    temporal_df,
    [
        "acq_date",
        "date",
    ],
)


if date_source:

    temporal_df[
        "_thermoscope_date"
    ] = pd.to_datetime(
        temporal_df[
            date_source
        ],
        errors="coerce",
    )

    temporal_df = temporal_df[
        temporal_df[
            "_thermoscope_date"
        ].notna()
    ].copy()

else:

    temporal_df = pd.DataFrame()


if not temporal_df.empty:

    daily_activity = (
        temporal_df
        .groupby(
            "_thermoscope_date"
        )
        .size()
        .rename("detections")
    )


    st.line_chart(
        daily_activity,
        height=320,
    )


    peak_date = (
        daily_activity
        .idxmax()
    )

    peak_count = int(
        daily_activity.max()
    )

    observation_days = int(
        daily_activity.count()
    )


    temporal_left, temporal_right = (
        st.columns(2)
    )


    with temporal_left:

        render_info_card(
            "PEAK FIRE ACTIVITY",
            f"{peak_count} detections",
            (
                "Highest number of FIRMS detections "
                f"recorded on "
                f"{peak_date.strftime('%d %b %Y')}."
            ),
        )


    with temporal_right:

        render_info_card(
            "OBSERVATION PERIOD",
            f"{observation_days} active days",
            (
                "Number of dates containing at least "
                "one FIRMS fire detection."
            ),
        )


else:

    st.info(
        "Temporal FIRMS observation data is unavailable."
    )


# ============================================================
# FIRE RISK ANALYTICS
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)

render_template(
    "SECTION_TITLE",
    TEXT="📊 Fire Risk Analytics",
)

render_template(
    "SECTION_SUBTITLE",
    TEXT=(
        "Distribution of predicted risk levels "
        "across monitored grid cells"
    ),
)


analytics_left, analytics_right = (
    st.columns([1.25, 1])
)


with analytics_left:

    risk_counts = (
        filtered_risk[
            risk_column
        ]
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


with analytics_right:

    st.markdown(
        "### 🔥 Highest Activity Zones"
    )

    activity_df = (
        filtered_risk.copy()
    )


    sort_column = (
        avg_frp_column
        or detection_column
    )


    if (
        sort_column
        and not activity_df.empty
    ):

        activity_df[
            sort_column
        ] = pd.to_numeric(
            activity_df[
                sort_column
            ],
            errors="coerce",
        )

        activity_df = (
            activity_df
            .sort_values(
                sort_column,
                ascending=False,
            )
        )


    display_columns = [
        col
        for col in [
            "grid_id",
            risk_column,
            "risk_score",
            "risk_percentage",
            "dominant_factor",
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

render_template(
    "SECTION_TITLE",
    TEXT="🛰️ Satellite Observation Information",
)

render_template(
    "SECTION_SUBTITLE",
    TEXT=(
        "Understanding the satellite data "
        "powering Thermoscope"
    ),
)


info1, info2, info3 = st.columns(3)


with info1:

    render_info_card(
        "DATA SOURCE",
        "NASA FIRMS",
        (
            "Fire Information for Resource "
            "Management System provides satellite-based "
            "thermal anomaly observations."
        ),
    )


with info2:

    render_info_card(
        "SATELLITE SENSOR",
        "VIIRS",
        (
            "Visible Infrared Imaging Radiometer Suite "
            "enables detection of active thermal anomalies."
        ),
    )


with info3:

    render_info_card(
        "INTELLIGENCE PIPELINE",
        "Detection → Risk",
        (
            "Satellite observations are aggregated "
            "spatially and converted into explainable "
            "fire-risk predictions."
        ),
    )


# ============================================================
# FIRMS DATA TABLE
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)

render_template(
    "SECTION_TITLE",
    TEXT="🔥 FIRMS Detection Data",
)

render_template(
    "SECTION_SUBTITLE",
    TEXT=(
        "Raw satellite fire detections used by "
        "the Thermoscope intelligence layer"
    ),
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

render_template(
    "SECTION_TITLE",
    TEXT="🎯 Risk Prediction Data",
)

render_template(
    "SECTION_SUBTITLE",
    TEXT=(
        "Spatially aggregated fire activity "
        "and explainable risk prediction information"
    ),
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

render_template(
    "FOOTER",
    TEXT=(
        "THERMOSCOPE • Satellite-Based Fire Risk "
        "Intelligence • Delhi NCR"
    ),
    SOURCE=(
        "Powered by NASA FIRMS / VIIRS satellite observations"
    ),
)