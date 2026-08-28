import pandas as pd
import folium


# ============================================================
# THERMOSCOPE - STEP 6
# INTERACTIVE GIS RISK GRID MAP
# USING SIH PROVIDED NASA FIRMS DATA
# ============================================================

INPUT_FILE = "data/delhi_risk_predictions_live.csv"
OUTPUT_FILE = "data/delhi_risk_interactive.html"

GRID_SIZE = 0.01


print("=" * 70)
print("THERMOSCOPE - INTERACTIVE DELHI NCR RISK GRID")
print("USING SIH PROVIDED NASA FIRMS DATA")
print("=" * 70)


# ============================================================
# 1. LOAD RISK PREDICTIONS
# ============================================================

try:

    df = pd.read_csv(INPUT_FILE)

except FileNotFoundError:

    raise FileNotFoundError(
        f"\nERROR: File not found:\n{INPUT_FILE}\n\n"
        "Please run risk_model.py first."
    )


print("\nLoaded prediction cells:", len(df))


# ============================================================
# 2. CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "grid_id",
    "grid_lat",
    "grid_lon",
    "risk_score",
    "risk_percentage",
    "risk_category",
    "detection_count",
    "active_days",
    "avg_frp",
    "max_frp",
    "recurrence_score",
    "frp_intensity",
    "repeat_detection_score",
    "dominant_factor",
    "risk_explanation"
]


missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]


if missing_columns:

    print("\nERROR: Missing columns:")
    print(missing_columns)

    raise ValueError(
        "Required risk information is missing. "
        "Please check risk_model.py output."
    )


# ============================================================
# 3. CLEAN NUMERIC COLUMNS
# ============================================================

numeric_columns = [
    "grid_lat",
    "grid_lon",
    "risk_score",
    "risk_percentage",
    "detection_count",
    "active_days",
    "avg_frp",
    "max_frp",
    "recurrence_score",
    "frp_intensity",
    "repeat_detection_score"
]


for column in numeric_columns:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# ============================================================
# 4. CLEAN RISK CATEGORY
# ============================================================

df["risk_category"] = (
    df["risk_category"]
    .astype(str)
    .str.upper()
    .str.strip()
)


# ============================================================
# 5. REMOVE INVALID COORDINATES
# ============================================================

df = df.dropna(
    subset=[
        "grid_lat",
        "grid_lon",
        "risk_score"
    ]
).copy()


print("Valid risk cells:", len(df))


if df.empty:

    raise ValueError(
        "No valid risk cells available."
    )


# ============================================================
# 6. RISK COLORS
# ============================================================

RISK_COLORS = {
    "LOW": "green",
    "MEDIUM": "orange",
    "HIGH": "red"
}


# ============================================================
# 7. MAP CENTER
# ============================================================

map_center = [
    df["grid_lat"].mean(),
    df["grid_lon"].mean()
]


risk_map = folium.Map(
    location=map_center,
    zoom_start=9,
    tiles="OpenStreetMap",
    control_scale=True
)


# ============================================================
# 8. CREATE RISK LAYERS
# ============================================================

risk_layers = {}


for risk in [
    "LOW",
    "MEDIUM",
    "HIGH"
]:

    risk_layers[risk] = folium.FeatureGroup(
        name=f"{risk} Risk Grid",
        show=True
    )

    risk_layers[risk].add_to(
        risk_map
    )


# ============================================================
# 9. ADD RISK GRID CELLS
# ============================================================

for _, row in df.iterrows():

    risk = row["risk_category"]

    color = RISK_COLORS.get(
        risk,
        "blue"
    )


    # --------------------------------------------------------
    # Grid boundaries
    # --------------------------------------------------------

    grid_lat = float(
        row["grid_lat"]
    )

    grid_lon = float(
        row["grid_lon"]
    )

    south = grid_lat
    north = grid_lat + GRID_SIZE

    west = grid_lon
    east = grid_lon + GRID_SIZE


    # --------------------------------------------------------
    # Risk score
    # --------------------------------------------------------

    score = float(
        row["risk_score"]
    )

    score = max(
        0,
        min(score, 1)
    )


    risk_percentage = float(
        row["risk_percentage"]
    )


    # --------------------------------------------------------
    # Grid fill opacity
    # --------------------------------------------------------

    fill_opacity = (
        0.20
        +
        (score * 0.45)
    )


    # ========================================================
    # 10. POPUP CONTENT
    # ========================================================

    popup_html = f"""
    <div style="
        width:330px;
        font-family:Arial,sans-serif;
        line-height:1.5;
    ">

        <div style="
            background:{color};
            color:white;
            padding:10px;
            border-radius:7px;
            margin-bottom:10px;
            text-align:center;
        ">

            <div style="
                font-size:18px;
                font-weight:bold;
            ">
                🔥 THERMOSCOPE
            </div>

            <div style="
                font-size:14px;
                margin-top:3px;
            ">
                {risk} RISK ZONE
            </div>

        </div>


        <table style="
            width:100%;
            border-collapse:collapse;
            font-size:13px;
        ">

            <tr>
                <td><b>Grid ID</b></td>
                <td>{row["grid_id"]}</td>
            </tr>

            <tr>
                <td><b>Risk Score</b></td>
                <td>{score:.3f}</td>
            </tr>

            <tr>
                <td><b>Risk Level</b></td>
                <td>
                    <b style="color:{color};">
                        {risk}
                    </b>
                </td>
            </tr>

            <tr>
                <td><b>Risk Percentage</b></td>
                <td>{risk_percentage:.2f}%</td>
            </tr>

            <tr>
                <td><b>FIRMS Detections</b></td>
                <td>{int(row["detection_count"])}</td>
            </tr>

            <tr>
                <td><b>Active Days</b></td>
                <td>{int(row["active_days"])}</td>
            </tr>

            <tr>
                <td><b>Average FRP</b></td>
                <td>{row["avg_frp"]:.3f}</td>
            </tr>

            <tr>
                <td><b>Maximum FRP</b></td>
                <td>{row["max_frp"]:.3f}</td>
            </tr>

            <tr>
                <td><b>Recurrence Score</b></td>
                <td>{row["recurrence_score"]:.3f}</td>
            </tr>

            <tr>
                <td><b>FRP Intensity</b></td>
                <td>{row["frp_intensity"]:.3f}</td>
            </tr>

            <tr>
                <td><b>Repeat Detection</b></td>
                <td>{row["repeat_detection_score"]:.3f}</td>
            </tr>

        </table>


        <hr>


        <div style="
            background:#f4f4f4;
            padding:8px;
            border-radius:6px;
        ">

            <b>Dominant Risk Factor:</b><br>

            {row["dominant_factor"]}

        </div>


        <div style="
            background:#f4f4f4;
            padding:8px;
            border-radius:6px;
            margin-top:7px;
        ">

            <b>Risk Explanation:</b><br>

            {row["risk_explanation"]}

        </div>


        <hr>


        <div style="font-size:12px;color:#555;">

            <b>Grid Coordinates</b><br>

            Latitude:
            {grid_lat:.5f}<br>

            Longitude:
            {grid_lon:.5f}

        </div>

    </div>
    """


    # ========================================================
    # 11. GRID RECTANGLE
    # ========================================================

    folium.Rectangle(

        bounds=[
            [south, west],
            [north, east]
        ],

        color=color,

        weight=2,

        fill=True,

        fill_color=color,

        fill_opacity=fill_opacity,

        popup=folium.Popup(
            popup_html,
            max_width=380
        ),

        tooltip=(
            f"🔥 {risk} | "
            f"Risk: {risk_percentage:.1f}% | "
            f"Grid: {row['grid_id']}"
        )

    ).add_to(
        risk_layers.get(
            risk,
            risk_layers["LOW"]
        )
    )


    # ========================================================
    # 12. CENTER MARKER
    # ========================================================

    folium.CircleMarker(

        location=[
            grid_lat + GRID_SIZE / 2,
            grid_lon + GRID_SIZE / 2
        ],

        radius=4 + (score * 7),

        color=color,

        fill=True,

        fill_color=color,

        fill_opacity=0.85,

        weight=1,

        tooltip=(
            f"{risk} Risk - "
            f"{risk_percentage:.1f}%"
        )

    ).add_to(
        risk_layers.get(
            risk,
            risk_layers["LOW"]
        )
    )


# ============================================================
# 13. LAYER CONTROL
# ============================================================

folium.LayerControl(
    collapsed=False
).add_to(
    risk_map
)


# ============================================================
# 14. MAP TITLE
# ============================================================

title_html = """
<div style="
    position: fixed;
    top: 15px;
    left: 50%;
    transform: translateX(-50%);
    z-index:9999;

    background:white;

    padding:10px 20px;

    border-radius:8px;

    box-shadow:
        0 2px 8px rgba(0,0,0,0.25);

    font-family:Arial,sans-serif;

    font-size:18px;

    font-weight:bold;

    color:#222;
">

🔥 THERMOSCOPE — Delhi NCR Fire Risk Grid

</div>
"""


risk_map.get_root().html.add_child(
    folium.Element(title_html)
)


# ============================================================
# 15. SAVE MAP
# ============================================================

risk_map.save(
    OUTPUT_FILE
)


# ============================================================
# 16. TERMINAL SUMMARY
# ============================================================

print("\n" + "-" * 70)
print("RISK DISTRIBUTION")
print("-" * 70)

print(
    df["risk_category"]
    .value_counts()
)


print("\n" + "-" * 70)
print("HIGHEST RISK CELL")
print("-" * 70)


highest_risk = (
    df.sort_values(
        by="risk_score",
        ascending=False
    )
    .iloc[0]
)


print(
    "Grid:",
    highest_risk["grid_id"]
)

print(
    "Risk:",
    highest_risk["risk_category"]
)

print(
    "Risk Score:",
    f"{highest_risk['risk_score']:.3f}"
)

print(
    "Risk Percentage:",
    f"{highest_risk['risk_percentage']:.2f}%"
)

print(
    "Dominant Factor:",
    highest_risk["dominant_factor"]
)


print("\nInteractive risk grid saved to:")

print(
    OUTPUT_FILE
)


print("\n" + "=" * 70)
print("STEP 6 - INTERACTIVE GIS RISK GRID COMPLETE")
print("=" * 70)