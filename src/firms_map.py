import pandas as pd
import folium
from folium.plugins import MarkerCluster

# ============================================================
# THERMOSCOPE - STEP 4A
# SIH FIRMS INTERACTIVE HOTSPOT MAP
# ============================================================

INPUT_FILE = "data/delhi_firms_sih.csv"
OUTPUT_FILE = "data/delhi_firms_interactive.html"

print("=" * 70)
print("THERMOSCOPE - SIH FIRMS INTERACTIVE MAP")
print("=" * 70)

# ------------------------------------------------------------
# 1. Load SIH-provided FIRMS dataset
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print("\nLoaded SIH FIRMS observations:", len(df))

# ------------------------------------------------------------
# 2. Clean coordinates
# ------------------------------------------------------------

df["latitude"] = pd.to_numeric(
    df["latitude"],
    errors="coerce"
)

df["longitude"] = pd.to_numeric(
    df["longitude"],
    errors="coerce"
)

df["frp"] = pd.to_numeric(
    df["frp"],
    errors="coerce"
)

df = df.dropna(
    subset=["latitude", "longitude"]
)

print("Valid coordinate observations:", len(df))

# ------------------------------------------------------------
# 3. Create Delhi map
# ------------------------------------------------------------

map_center = [
    df["latitude"].mean(),
    df["longitude"].mean()
]

fire_map = folium.Map(
    location=map_center,
    zoom_start=10,
    tiles="OpenStreetMap"
)

# ------------------------------------------------------------
# 4. Marker cluster
# ------------------------------------------------------------

marker_cluster = MarkerCluster(
    name="FIRMS Fire Detections"
)

marker_cluster.add_to(fire_map)

# ------------------------------------------------------------
# 5. Add FIRMS observations
# ------------------------------------------------------------

for _, row in df.iterrows():

    popup_html = f"""
    <b>THERMOSCOPE - FIRMS Detection</b><br><br>

    <b>Date:</b> {row.get("acq_date", "N/A")}<br>
    <b>Time:</b> {row.get("acq_time", "N/A")}<br>
    <b>Satellite:</b> {row.get("satellite", "N/A")}<br>
    <b>FRP:</b> {row.get("frp", "N/A")}<br>
    <b>Confidence:</b> {row.get("confidence", "N/A")}<br>
    <b>Day/Night:</b> {row.get("daynight", "N/A")}<br>
    <b>Latitude:</b> {row["latitude"]:.5f}<br>
    <b>Longitude:</b> {row["longitude"]:.5f}
    """

    folium.CircleMarker(
        location=[
            row["latitude"],
            row["longitude"]
        ],
        radius=5,
        popup=folium.Popup(
            popup_html,
            max_width=300
        ),
        tooltip="FIRMS Fire Detection",
        fill=True,
        fill_opacity=0.7
    ).add_to(marker_cluster)

# ------------------------------------------------------------
# 6. Add layer control
# ------------------------------------------------------------

folium.LayerControl().add_to(fire_map)

# ------------------------------------------------------------
# 7. Save interactive map
# ------------------------------------------------------------

fire_map.save(OUTPUT_FILE)

print("\nInteractive map saved to:")
print(OUTPUT_FILE)

print("\n" + "=" * 70)
print("STEP 4A COMPLETE")
print("=" * 70)