import pandas as pd
import folium
from folium.plugins import MarkerCluster

# ============================================================
# THERMOSCOPE - INTERACTIVE GIS RISK MAP
# ============================================================

INPUT_FILE = "data/delhi_risk_predictions_live.csv"
OUTPUT_FILE = "data/delhi_risk_interactive.html"

print("=" * 70)
print("THERMOSCOPE - INTERACTIVE DELHI NCR RISK MAP")
print("=" * 70)

# ------------------------------------------------------------
# 1. LOAD RISK PREDICTIONS
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print("\nLoaded prediction cells:", len(df))

# ------------------------------------------------------------
# 2. CLEAN COORDINATES
# ------------------------------------------------------------

df["latitude"] = pd.to_numeric(
    df["grid_lat"],
    errors="coerce"
)

df["longitude"] = pd.to_numeric(
    df["grid_lon"],
    errors="coerce"
)

df["risk_score"] = pd.to_numeric(
    df["risk_score"],
    errors="coerce"
)

df["risk_percentage"] = pd.to_numeric(
    df["risk_percentage"],
    errors="coerce"
)

df = df.dropna(
    subset=[
        "latitude",
        "longitude"
    ]
).copy()

print("Valid risk cells:", len(df))

# ------------------------------------------------------------
# 3. NORMALIZE RISK CATEGORY
# ------------------------------------------------------------

df["risk_category"] = (
    df["risk_category"]
    .astype(str)
    .str.upper()
    .str.strip()
)

# ------------------------------------------------------------
# 4. RISK COLORS
# ------------------------------------------------------------

RISK_COLORS = {
    "LOW": "green",
    "MEDIUM": "orange",
    "HIGH": "red"
}

# ------------------------------------------------------------
# 5. MAP CENTER
# ------------------------------------------------------------

map_center = [
    df["latitude"].mean(),
    df["longitude"].mean()
]

risk_map = folium.Map(
    location=map_center,
    zoom_start=10,
    tiles="OpenStreetMap"
)

# ------------------------------------------------------------
# 6. CREATE RISK LAYERS
# ------------------------------------------------------------

risk_layers = {}

for risk in ["LOW", "MEDIUM", "HIGH"]:

    risk_layers[risk] = folium.FeatureGroup(
        name=f"{risk} Risk"
    )

    risk_layers[risk].add_to(risk_map)

# ------------------------------------------------------------
# 7. ADD RISK CELLS
# ------------------------------------------------------------

for _, row in df.iterrows():

    risk = row["risk_category"]

    color = RISK_COLORS.get(
        risk,
        "blue"
    )

    # Bubble size based on risk score
    score = row["risk_score"]

    if pd.isna(score):
        radius = 8
    else:
        score = float(score)

        if score > 1:
            score = score / 100

        score = max(
            0,
            min(score, 1)
        )

        radius = 7 + (score * 10)

    grid_id = row.get(
        "grid_id",
        "N/A"
    )

    risk_percentage = row.get(
        "risk_percentage",
        "N/A"
    )

    activity_score = row.get(
        "activity_score",
        "N/A"
    )

    detection_count = row.get(
        "detection_count",
        "N/A"
    )

    active_days = row.get(
        "active_days",
        "N/A"
    )

    popup_html = f"""
    <div style="width:260px">

        <h4 style="margin-bottom:10px;">
            🔥 THERMOSCOPE Risk Cell
        </h4>

        <b>Grid ID:</b> {grid_id}<br><br>

        <b>Risk Level:</b>
        <span style="
            color:{color};
            font-weight:bold;
        ">
            {risk}
        </span>
        <br><br>

        <b>Risk Percentage:</b>
        {risk_percentage}<br>

        <b>Risk Score:</b>
        {score:.3f}<br>

        <b>Activity Score:</b>
        {activity_score}<br>

        <b>FIRMS Detections:</b>
        {detection_count}<br>

        <b>Active Days:</b>
        {active_days}<br><br>

        <b>Latitude:</b>
        {row["latitude"]:.5f}<br>

        <b>Longitude:</b>
        {row["longitude"]:.5f}

    </div>
    """

    folium.CircleMarker(
        location=[
            row["latitude"],
            row["longitude"]
        ],
        radius=radius,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.65,
        weight=2,
        popup=folium.Popup(
            popup_html,
            max_width=300
        ),
        tooltip=(
            f"{grid_id} | "
            f"{risk} RISK"
        )
    ).add_to(
        risk_layers.get(
            risk,
            risk_layers["LOW"]
        )
    )

# ------------------------------------------------------------
# 8. ADD LEGEND / LAYER CONTROL
# ------------------------------------------------------------

folium.LayerControl(
    collapsed=False
).add_to(risk_map)

# ------------------------------------------------------------
# 9. SAVE MAP
# ------------------------------------------------------------

risk_map.save(
    OUTPUT_FILE
)

# ------------------------------------------------------------
# 10. SUMMARY
# ------------------------------------------------------------

print("\nRisk distribution:")

print(
    df["risk_category"]
    .value_counts()
)

print("\nInteractive risk map saved to:")
print(OUTPUT_FILE)

print("\n" + "=" * 70)
print("INTERACTIVE RISK MAP COMPLETE")
print("=" * 70)