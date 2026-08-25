import streamlit as st
import pandas as pd
import folium
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

    /* ---------- GLOBAL ---------- */

    .stApp {
        background:
            radial-gradient(circle at 85% 5%, rgba(255, 90, 30, 0.08), transparent 25%),
            #0b0f15;
        color: #f5f7fa;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* ---------- SIDEBAR ---------- */

    [data-testid="stSidebar"] {
        background: #0d121a;
        border-right: 1px solid #252c36;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #f5f7fa;
    }

    /* ---------- HERO ---------- */

    .hero {
        padding: 10px 0 20px 0;
    }

    .hero-title {
        font-size: 48px;
        font-weight: 850;
        letter-spacing: -1px;
        margin-bottom: 4px;
    }

    .hero-subtitle {
        color: #9aa4b2;
        font-size: 17px;
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

    /* ---------- SECTION ---------- */

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

    /* ---------- CARDS ---------- */

    div[data-testid="stMetric"] {
        background: linear-gradient(
            145deg,
            #151b24,
            #10151d
        );
        border: 1px solid #29313d;
        border-radius: 15px;
        padding: 18px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.18);
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

    /* ---------- INFO CARDS ---------- */

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

    /* ---------- DIVIDER ---------- */

    hr {
        border-color: #252c36 !important;
        margin-top: 30px !important;
        margin-bottom: 30px !important;
    }

    /* ---------- TABLE ---------- */

    [data-testid="stDataFrame"] {
        border: 1px solid #29313d;
        border-radius: 12px;
        overflow: hidden;
    }

    /* ---------- MAP ---------- */

    .map-caption {
        color: #7f8997;
        font-size: 12px;
        margin-top: 7px;
    }

    /* ---------- FOOTER ---------- */

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


# ============================================================
# DETECT IMPORTANT COLUMNS
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
            risk_df["activity_score"],
            bins=[-float("inf"), 0.33, 0.66, float("inf")],
            labels=["LOW", "MEDIUM", "HIGH"],
        )

    elif avg_frp_column is not None:

        risk_df["risk_category"] = pd.cut(
            risk_df[avg_frp_column],
            bins=[-float("inf"), 2, 4, float("inf")],
            labels=["LOW", "MEDIUM", "HIGH"],
        )

    elif detection_column is not None:

        risk_df["risk_category"] = pd.cut(
            risk_df[detection_column],
            bins=[-float("inf"), 1, 2, float("inf")],
            labels=["LOW", "MEDIUM", "HIGH"],
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
        for x in ["HIGH", "MEDIUM", "LOW"]
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

        Approx. bounding region
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
        """
        <div class="hero">
            <div class="hero-title">🔥 THERMOSCOPE</div>
            <div class="hero-subtitle">
                Delhi NCR Fire Risk Intelligence & Satellite Monitoring System
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with header_right:

    st.markdown(
        """
        <div style="text-align:right; padding-top:10px;">
            <span class="live-badge">
                🟢 LIVE MONITORING
            </span>
        </div>
        """,
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

high_count = int(
    (risk_df[risk_column] == "HIGH").sum()
)

medium_count = int(
    (risk_df[risk_column] == "MEDIUM").sum()
)

low_count = int(
    (risk_df[risk_column] == "LOW").sum()
)


m1, m2, m3, m4, m5 = st.columns(5)


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


# ============================================================
# FIRE RISK MAP
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">🗺️ Delhi NCR Fire Risk Map</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-subtitle">'
    'Satellite-derived fire activity and predicted spatial risk zones'
    '</div>',
    unsafe_allow_html=True,
)


# Delhi center
map_center = [
    28.6139,
    77.2090,
]


fire_map = folium.Map(
    location=map_center,
    zoom_start=10,
    tiles="CartoDB dark_matter",
    control_scale=True,
)


# Risk colors
risk_colors = {
    "HIGH": "#ff3b30",
    "MEDIUM": "#ff9500",
    "LOW": "#30d158",
}


# Add risk grid markers
if (
    lat_column is not None
    and lon_column is not None
    and not filtered_risk.empty
):

    for _, row in filtered_risk.iterrows():

        try:

            lat = float(row[lat_column])
            lon = float(row[lon_column])

        except Exception:
            continue

        risk_value = str(
            row[risk_column]
        ).upper()

        color = risk_colors.get(
            risk_value,
            "#38bdf8",
        )

        popup_text = f"""
        <b>Risk Level:</b> {risk_value}<br>
        <b>Grid:</b> {row.get("grid_id", "N/A")}<br>
        <b>Detections:</b> {row.get("detection_count", "N/A")}<br>
        <b>Avg FRP:</b> {row.get("avg_frp", "N/A")}<br>
        <b>Max FRP:</b> {row.get("max_frp", "N/A")}
        """

        folium.CircleMarker(
            location=[lat, lon],
            radius=10,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.65,
            weight=2,
            popup=folium.Popup(
                popup_text,
                max_width=300,
            ),
            tooltip=f"{risk_value} RISK",
        ).add_to(fire_map)


st_folium(
    fire_map,
    width=None,
    height=560,
    returned_objects=[],
)

st.markdown(
    '<div class="map-caption">'
    '🔴 High Risk &nbsp;&nbsp; '
    '🟠 Medium Risk &nbsp;&nbsp; '
    '🟢 Low Risk &nbsp;&nbsp; '
    'Click a zone for satellite-derived details.'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# RISK ANALYTICS
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">📊 Fire Risk Analytics</div>',
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


# ---------- RISK DISTRIBUTION ----------

with analytics_left:

    risk_counts = (
        filtered_risk[risk_column]
        .value_counts()
        .reindex(
            ["HIGH", "MEDIUM", "LOW"],
            fill_value=0,
        )
    )

    st.bar_chart(
        risk_counts,
        height=330,
    )


# ---------- HIGHEST ACTIVITY ZONES ----------

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
    '<div class="section-title">🛰️ Satellite Observation Information</div>',
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

    st.markdown(
        """
        <div class="info-card">

        <div class="info-card-title">
        DATA SOURCE
        </div>

        <div class="info-card-value">
        NASA FIRMS
        </div>

        <div class="info-card-text">
        Fire Information for Resource Management System
        provides satellite-based thermal anomaly observations.
        </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


with info2:

    st.markdown(
        """
        <div class="info-card">

        <div class="info-card-title">
        SATELLITE SENSOR
        </div>

        <div class="info-card-value">
        VIIRS
        </div>

        <div class="info-card-text">
        Visible Infrared Imaging Radiometer Suite enables
        detection of active thermal anomalies.
        </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


with info3:

    st.markdown(
        """
        <div class="info-card">

        <div class="info-card-title">
        INTELLIGENCE PIPELINE
        </div>

        <div class="info-card-value">
        Detection → Risk
        </div>

        <div class="info-card-text">
        Satellite observations are aggregated spatially and
        converted into explainable fire-risk predictions.
        </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# FIRMS DETECTION DATA
# ============================================================

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">🔥 FIRMS Detection Data</div>',
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
    '<div class="section-title">🎯 Risk Prediction Data</div>',
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