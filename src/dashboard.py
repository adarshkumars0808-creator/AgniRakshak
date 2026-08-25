import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium


# ============================================================
# THERMOSCOPE
# DELHI NCR FIRE RISK INTELLIGENCE DASHBOARD
# ============================================================

st.set_page_config(
    page_title="Thermoscope",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

.main {
    background-color: #0e1117;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

.title {
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 0px;
}

.subtitle {
    font-size: 18px;
    color: #9aa4b2;
    margin-bottom: 25px;
}

.metric-card {
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #30363d;
    background-color: #161b22;
    text-align: center;
}

.metric-title {
    font-size: 14px;
    color: #9aa4b2;
}

.metric-value {
    font-size: 30px;
    font-weight: 700;
}

.high {
    color: #ff4b4b;
}

.medium {
    color: #ffa500;
}

.low {
    color: #00c853;
}

.info-box {
    padding: 15px;
    border-radius: 10px;
    background-color: #161b22;
    border: 1px solid #30363d;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="title">🔥 THERMOSCOPE</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Delhi NCR Fire Risk Intelligence & Satellite Monitoring System'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# LOAD DATA
# ============================================================

try:

    risk_df = pd.read_csv(
        "data/delhi_risk_predictions.csv"
    )

    firms_df = pd.read_csv(
    "data/delhi_firms_sih.csv"
)

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


# Risk column
risk_column = find_column(
    risk_df,
    [
        "risk_category",
        "predicted_risk",
        "risk",
        "activity_category"
    ]
)


# FIRMS coordinates
firms_lat = find_column(
    firms_df,
    [
        "latitude",
        "lat",
        "Latitude"
    ]
)

firms_lon = find_column(
    firms_df,
    [
        "longitude",
        "lon",
        "Longitude"
    ]
)


# Risk coordinates
risk_lat = find_column(
    risk_df,
    [
        "grid_lat",
        "latitude",
        "lat",
        "Latitude"
    ]
)

risk_lon = find_column(
    risk_df,
    [
        "grid_lon",
        "longitude",
        "lon",
        "Longitude"
    ]
)


if risk_column is None:

    st.error(
        "Risk column not found in prediction data."
    )

    st.stop()


# ============================================================
# NORMALIZE RISK VALUES
# ============================================================

risk_df[risk_column] = (
    risk_df[risk_column]
    .astype(str)
    .str.upper()
    .str.strip()
)


# ============================================================
# RISK COUNTS
# ============================================================

total_fires = len(firms_df)

total_cells = len(risk_df)

high_risk = len(
    risk_df[
        risk_df[risk_column] == "HIGH"
    ]
)

medium_risk = len(
    risk_df[
        risk_df[risk_column] == "MEDIUM"
    ]
)

low_risk = len(
    risk_df[
        risk_df[risk_column] == "LOW"
    ]
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Controls")

    st.markdown("---")

    selected_risk = st.multiselect(
        "Risk Levels",
        [
            "HIGH",
            "MEDIUM",
            "LOW"
        ],
        default=[
            "HIGH",
            "MEDIUM",
            "LOW"
        ]
    )

    st.markdown("---")

    st.subheader("🛰️ Data Source")

    st.write(
        "NASA FIRMS"
    )

    st.write(
        "VIIRS satellite observations"
    )

    st.markdown("---")

    st.subheader("📍 Region")

    st.write(
        "Delhi NCR"
    )

    st.write(
        "Approx. bounding region"
    )


# ============================================================
# FILTER DATA
# ============================================================

filtered_risk = risk_df[
    risk_df[risk_column].isin(selected_risk)
]


# ============================================================
# TOP METRICS
# ============================================================

c1, c2, c3, c4, c5 = st.columns(5)


with c1:

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">🔥 FIRMS DETECTIONS</div>
            <div class="metric-value">{total_fires}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


with c2:

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">🗺️ GRID CELLS</div>
            <div class="metric-value">{total_cells}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


with c3:

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">🔴 HIGH RISK</div>
            <div class="metric-value high">{high_risk}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


with c4:

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">🟠 MEDIUM RISK</div>
            <div class="metric-value medium">{medium_risk}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


with c5:

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">🟢 LOW RISK</div>
            <div class="metric-value low">{low_risk}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


st.markdown("<br>", unsafe_allow_html=True)


# ============================================================
# MAP HEADER
# ============================================================

st.header("🗺️ Delhi NCR Fire Risk Map")

st.caption(
    "Risk zones are generated from satellite-derived fire activity features."
)


# ============================================================
# CREATE MAP
# ============================================================

m = folium.Map(
    location=[
        28.6139,
        77.2090
    ],
    zoom_start=11,
    min_zoom=9,
    max_zoom=16,
    tiles="OpenStreetMap"
)


# ============================================================
# MAP LEGEND
# ============================================================

legend_html = """
<div style="
position: fixed;
bottom: 30px;
left: 30px;
z-index: 9999;
background-color: white;
padding: 12px;
border-radius: 8px;
border: 1px solid #999;
font-size: 13px;
">

<b>🔥 Risk Legend</b><br><br>

<span style="color:red;">●</span>
HIGH RISK<br>

<span style="color:orange;">●</span>
MEDIUM RISK<br>

<span style="color:green;">●</span>
LOW RISK<br>

<span style="color:black;">●</span>
FIRMS Detection

</div>
"""


m.get_root().html.add_child(
    folium.Element(legend_html)
)


# ============================================================
# RISK MARKERS
# ============================================================

if risk_lat and risk_lon:

    for _, row in filtered_risk.iterrows():

        try:

            lat = float(row[risk_lat])
            lon = float(row[risk_lon])

        except:

            continue


        risk = row[risk_column]


        if risk == "HIGH":

            color = "red"

        elif risk == "MEDIUM":

            color = "orange"

        else:

            color = "green"


        # Extra feature information

        activity = row.get(
            "activity_score",
            "N/A"
        )

        detections = row.get(
            "detection_count",
            "N/A"
        )

        active_days = row.get(
            "active_days",
            "N/A"
        )

        avg_frp = row.get(
            "avg_frp",
            "N/A"
        )

        max_frp = row.get(
            "max_frp",
            "N/A"
        )


        popup_html = f"""
        <div style="width:250px">

        <h4>🔥 Thermoscope Risk Zone</h4>

        <b>Risk:</b>
        {risk}

        <br><br>

        <b>Detection Count:</b>
        {detections}

        <br>

        <b>Active Days:</b>
        {active_days}

        <br>

        <b>Average FRP:</b>
        {avg_frp}

        <br>

        <b>Maximum FRP:</b>
        {max_frp}

        <br>

        <b>Activity Score:</b>
        {activity}

        <br><br>

        <b>Coordinates:</b><br>
        {lat:.5f}, {lon:.5f}

        </div>
        """


        folium.CircleMarker(

            location=[
                lat,
                lon
            ],

            radius=14,

            color=color,

            fill=True,

            fill_color=color,

            fill_opacity=0.55,

            weight=2,

            popup=folium.Popup(
                popup_html,
                max_width=300
            )

        ).add_to(m)


# ============================================================
# FIRMS DETECTION MARKERS
# ============================================================

if firms_lat and firms_lon:

    for _, row in firms_df.iterrows():

        try:

            lat = float(
                row[firms_lat]
            )

            lon = float(
                row[firms_lon]
            )

        except:

            continue


        frp = row.get(
            "frp",
            "N/A"
        )

        date = row.get(
            "acq_date",
            "N/A"
        )

        time = row.get(
            "acq_time",
            "N/A"
        )

        satellite = row.get(
            "satellite",
            "N/A"
        )


        popup_html = f"""
        <div style="width:220px">

        <h4>🛰️ FIRMS Detection</h4>

        <b>Date:</b>
        {date}

        <br>

        <b>Time:</b>
        {time}

        <br>

        <b>Satellite:</b>
        {satellite}

        <br>

        <b>FRP:</b>
        {frp}

        <br><br>

        <b>Location:</b><br>
        {lat:.5f}, {lon:.5f}

        </div>
        """


        folium.CircleMarker(

            location=[
                lat,
                lon
            ],

            radius=4,

            color="black",

            fill=True,

            fill_color="black",

            fill_opacity=0.8,

            popup=folium.Popup(
                popup_html,
                max_width=280
            )

        ).add_to(m)


# ============================================================
# DISPLAY MAP
# ============================================================

st_folium(
    m,
    width=None,
    height=650,
    returned_objects=[]
)


# ============================================================
# ANALYTICS SECTION
# ============================================================

st.divider()

st.header("📊 Fire Risk Analytics")


left, right = st.columns(2)


# ------------------------------------------------------------
# RISK DISTRIBUTION
# ------------------------------------------------------------

with left:

    st.subheader(
        "Risk Distribution"
    )

    risk_counts = (
        filtered_risk[risk_column]
        .value_counts()
    )

    st.bar_chart(
        risk_counts
    )


# ------------------------------------------------------------
# HOTSPOT TABLE
# ------------------------------------------------------------

with right:

    st.subheader(
        "🔥 Highest Activity Zones"
    )

    display_columns = []

    for column in [
    "grid_id",
    "detection_count",
    "active_days",
    "avg_frp",
    "max_frp",
    "activity_score",
    "risk_category"
]:

        if column in filtered_risk.columns:

            display_columns.append(
                column
            )


    hotspot_df = filtered_risk[
        display_columns
    ].copy()


    if "activity_score" in hotspot_df.columns:

        hotspot_df = hotspot_df.sort_values(
            "activity_score",
            ascending=False
        )


    st.dataframe(
        hotspot_df.head(10),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# SATELLITE INFORMATION
# ============================================================

st.divider()

st.header("🛰️ Satellite Observation Information")


info1, info2, info3 = st.columns(3)


with info1:

    st.markdown(
        """
        ### VIIRS

        **Visible Infrared Imaging Radiometer Suite**

        Used for high-resolution satellite
        fire and thermal anomaly detection.
        """
    )


with info2:

    st.markdown(
        """
        ### FIRMS

        **Fire Information for Resource Management System**

        Provides near-real-time satellite
        fire observations.
        """
    )


with info3:

    st.markdown(
        """
        ### Thermoscope

        Combines satellite detections,
        spatial activity and machine-learning
        based risk classification.
        """
    )


# ============================================================
# FIRMS DATA
# ============================================================

st.divider()

st.header("🔥 FIRMS Detection Data")

st.dataframe(
    firms_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# RISK DATA
# ============================================================

st.header("🎯 Risk Prediction Data")

st.dataframe(
    filtered_risk,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "THERMOSCOPE • Satellite-Based Fire Risk Intelligence • Delhi NCR"
)