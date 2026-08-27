import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


# ============================================================
# THERMOSCOPE - STEP 5
# DELHI NCR FIRE RISK MAP
# ============================================================

print("=" * 65)
print("THERMOSCOPE - DELHI NCR FIRE RISK MAP")
print("USING SIH PROVIDED NASA FIRMS DATA")
print("=" * 65)


# ============================================================
# FILE PATHS
# ============================================================

PREDICTION_FILE = "data/delhi_risk_predictions_live.csv"
OUTPUT_FILE = "data/delhi_fire_risk_map.png"


# ============================================================
# 1. LOAD RISK PREDICTIONS
# ============================================================

pred = pd.read_csv(PREDICTION_FILE)

print("\nLoaded prediction cells:", len(pred))


# ============================================================
# 2. CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "grid_id",
    "grid_lat",
    "grid_lon",
    "risk_score",
    "risk_percentage",
    "risk_category"
]

missing_columns = [
    column
    for column in required_columns
    if column not in pred.columns
]

if missing_columns:

    print("\nERROR: Missing columns:")
    print(missing_columns)

    raise ValueError(
        "Required risk map columns are missing."
    )


# ============================================================
# 3. PREPARE RISK CATEGORY
# ============================================================

pred["risk_category"] = (
    pred["risk_category"]
    .astype(str)
    .str.upper()
    .str.strip()
)


# ============================================================
# 4. GET GRID COORDINATES
# ============================================================

pred["latitude"] = pd.to_numeric(
    pred["grid_lat"],
    errors="coerce"
)

pred["longitude"] = pd.to_numeric(
    pred["grid_lon"],
    errors="coerce"
)


print(
    "Using grid coordinates from risk predictions."
)


# ============================================================
# 5. CHECK VALID COORDINATES
# ============================================================

df = pred.dropna(
    subset=[
        "latitude",
        "longitude"
    ]
).copy()


print(
    "\nCoordinates matched:",
    len(df),
    "/",
    len(pred)
)


if df.empty:

    raise ValueError(
        "No valid coordinates found for risk cells."
    )


# ============================================================
# 6. PREPARE RISK SCORE
# ============================================================

df["display_score"] = pd.to_numeric(
    df["risk_score"],
    errors="coerce"
)


df["risk_percentage"] = pd.to_numeric(
    df["risk_percentage"],
    errors="coerce"
)


# ============================================================
# 7. CALCULATE BUBBLE SIZE
# ============================================================

score_values = (
    df["display_score"]
    .fillna(0)
    .clip(0, 1)
)


df["bubble_size"] = (
    350
    + score_values * 1000
)


# ============================================================
# 8. RISK COLORS
# ============================================================

RISK_COLORS = {
    "LOW": "green",
    "MEDIUM": "orange",
    "HIGH": "red"
}


# ============================================================
# 9. CREATE FIGURE
# ============================================================

fig, ax = plt.subplots(
    figsize=(13, 8)
)


# ============================================================
# 10. PLOT RISK LEVELS
# ============================================================

for risk in [
    "LOW",
    "MEDIUM",
    "HIGH"
]:

    subset = df[
        df["risk_category"] == risk
    ]


    if subset.empty:
        continue


    ax.scatter(
        subset["longitude"],
        subset["latitude"],
        s=subset["bubble_size"],
        color=RISK_COLORS[risk],
        alpha=0.70,
        edgecolors="black",
        linewidths=1.2,
        zorder=3
    )


# ============================================================
# 11. ADD RISK LABELS
# ============================================================

for _, row in df.iterrows():

    latitude = float(
        row["latitude"]
    )

    longitude = float(
        row["longitude"]
    )

    grid_id = str(
        row["grid_id"]
    )

    risk_category = str(
        row["risk_category"]
    )

    risk_percentage = row[
        "risk_percentage"
    ]


    if pd.notna(risk_percentage):

        score_text = (
            f"{float(risk_percentage):.1f}%"
        )

    else:

        score_text = "N/A"


    label = (
        f"{grid_id}\n"
        f"{risk_category}\n"
        f"Risk: {score_text}"
    )


    # --------------------------------------------------------
    # Label positioning
    # --------------------------------------------------------

    offset = (
        15,
        12
    )

    horizontal_alignment = "left"


    ax.annotate(
        label,
        xy=(
            longitude,
            latitude
        ),
        xytext=offset,
        textcoords="offset points",
        fontsize=9,
        fontweight="bold",
        ha=horizontal_alignment,
        va="bottom",
        bbox=dict(
            boxstyle="round,pad=0.35",
            facecolor="white",
            edgecolor="gray",
            linewidth=1,
            alpha=0.95
        ),
        arrowprops=dict(
            arrowstyle="-",
            color="gray",
            linewidth=0.8,
            alpha=0.7
        ),
        zorder=5
    )


# ============================================================
# 12. TITLE
# ============================================================

ax.set_title(
    "THERMOSCOPE - Delhi NCR Fire Risk Map",
    fontsize=20,
    fontweight="bold",
    pad=18
)


# ============================================================
# 13. AXIS LABELS
# ============================================================

ax.set_xlabel(
    "Longitude",
    fontsize=12
)

ax.set_ylabel(
    "Latitude",
    fontsize=12
)


# ============================================================
# 14. MAP GRID
# ============================================================

ax.grid(
    True,
    linestyle="--",
    linewidth=0.8,
    alpha=0.25,
    zorder=0
)


# ============================================================
# 15. MAP MARGINS
# ============================================================

ax.margins(
    x=0.08,
    y=0.12
)


# ============================================================
# 16. RISK COUNTS
# ============================================================

risk_counts = (
    df["risk_category"]
    .value_counts()
)


high_count = int(
    risk_counts.get(
        "HIGH",
        0
    )
)


medium_count = int(
    risk_counts.get(
        "MEDIUM",
        0
    )
)


low_count = int(
    risk_counts.get(
        "LOW",
        0
    )
)


# ============================================================
# 17. LEGEND
# ============================================================

legend_handles = [

    Line2D(
        [0],
        [0],
        marker="o",
        linestyle="None",
        markerfacecolor="green",
        markeredgecolor="black",
        markeredgewidth=0.8,
        markersize=9,
        alpha=0.8,
        label=f"LOW ({low_count})"
    ),

    Line2D(
        [0],
        [0],
        marker="o",
        linestyle="None",
        markerfacecolor="orange",
        markeredgecolor="black",
        markeredgewidth=0.8,
        markersize=9,
        alpha=0.8,
        label=f"MEDIUM ({medium_count})"
    ),

    Line2D(
        [0],
        [0],
        marker="o",
        linestyle="None",
        markerfacecolor="red",
        markeredgecolor="black",
        markeredgewidth=0.8,
        markersize=9,
        alpha=0.8,
        label=f"HIGH ({high_count})"
    )
]


ax.legend(
    handles=legend_handles,
    title="Risk Level",
    loc="lower right",
    frameon=True,
    fancybox=True,
    framealpha=0.9,
    fontsize=10,
    title_fontsize=11,
    borderpad=0.8,
    labelspacing=0.6
)


# ============================================================
# 18. SUMMARY BOX
# ============================================================

summary_text = (
    f"GRID CELLS: {len(df)}\n"
    f"HIGH RISK: {high_count}\n"
    f"MEDIUM RISK: {medium_count}\n"
    f"LOW RISK: {low_count}"
)


ax.text(
    0.015,
    0.975,
    summary_text,
    transform=ax.transAxes,
    fontsize=10,
    fontweight="bold",
    verticalalignment="top",
    horizontalalignment="left",
    bbox=dict(
        boxstyle="round,pad=0.5",
        facecolor="white",
        edgecolor="black",
        linewidth=1,
        alpha=0.95
    ),
    zorder=6
)


# ============================================================
# 19. MAP LIMITS
# ============================================================

# Automatically fit map around available grid cells

lat_min = df["latitude"].min()
lat_max = df["latitude"].max()

lon_min = df["longitude"].min()
lon_max = df["longitude"].max()


lat_padding = max(
    (lat_max - lat_min) * 0.15,
    0.02
)

lon_padding = max(
    (lon_max - lon_min) * 0.15,
    0.02
)


ax.set_xlim(
    lon_min - lon_padding,
    lon_max + lon_padding
)


ax.set_ylim(
    lat_min - lat_padding,
    lat_max + lat_padding
)


# ============================================================
# 20. SAVE MAP
# ============================================================

plt.tight_layout()


plt.savefig(
    OUTPUT_FILE,
    dpi=300,
    bbox_inches="tight"
)


# ============================================================
# 21. TERMINAL SUMMARY
# ============================================================

print("\nRisk distribution:")
print(
    df["risk_category"]
    .value_counts()
)


print("\nHighest-risk grid:")

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
    "Risk percentage:",
    f"{highest_risk['risk_percentage']:.2f}%"
)


print("\nMap saved to:")
print(OUTPUT_FILE)


print("\n" + "=" * 65)
print("STEP 5 - RISK MAP COMPLETE")
print("=" * 65)


# ============================================================
# 22. SHOW MAP
# ============================================================

plt.show()

plt.close()