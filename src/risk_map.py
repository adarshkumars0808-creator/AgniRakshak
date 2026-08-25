import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


# ============================================================
# THERMOSCOPE - DELHI NCR FIRE RISK MAP
# ============================================================

print("=" * 65)
print("THERMOSCOPE - DELHI NCR FIRE RISK MAP")
print("=" * 65)


# ============================================================
# FILE PATHS
# ============================================================

PREDICTION_FILE = "data/delhi_risk_predictions.csv"
FIRMS_FILE = "data/delhi_master.csv"
OUTPUT_FILE = "data/delhi_fire_risk_map.png"


# ============================================================
# 1. LOAD DATA
# ============================================================

pred = pd.read_csv(PREDICTION_FILE)
firms = pd.read_csv(FIRMS_FILE)

print("\nLoaded prediction cells:", len(pred))
print("Loaded FIRMS observations:", len(firms))


# ============================================================
# 2. FIND RISK COLUMN
# ============================================================

risk_column = None

for column in [
    "predicted_risk",
    "risk_category",
    "activity_category"
]:
    if column in pred.columns:
        risk_column = column
        break


if risk_column is None:
    raise ValueError(
        "No risk column found. Expected one of: "
        "predicted_risk, risk_category, activity_category"
    )


print("Using risk column:", risk_column)


pred[risk_column] = (
    pred[risk_column]
    .astype(str)
    .str.upper()
    .str.strip()
)


# ============================================================
# 3. GET GRID COORDINATES
# ============================================================

if (
    "grid_lat" in pred.columns
    and "grid_lon" in pred.columns
):

    pred["latitude"] = pd.to_numeric(
        pred["grid_lat"],
        errors="coerce"
    )

    pred["longitude"] = pd.to_numeric(
        pred["grid_lon"],
        errors="coerce"
    )

    print("Using grid coordinates from prediction data.")


else:

    firms["latitude"] = pd.to_numeric(
        firms["latitude"],
        errors="coerce"
    )

    firms["longitude"] = pd.to_numeric(
        firms["longitude"],
        errors="coerce"
    )

    firms = firms.dropna(
        subset=[
            "latitude",
            "longitude"
        ]
    ).copy()


    firms["grid_id"] = (
        firms["latitude"].round(2).astype(str)
        + "_"
        + firms["longitude"].round(2).astype(str)
    )


    coordinates = (
        firms.groupby("grid_id")
        .agg(
            latitude=("latitude", "mean"),
            longitude=("longitude", "mean")
        )
        .reset_index()
    )


    pred = pred.merge(
        coordinates,
        on="grid_id",
        how="left"
    )


    print("Coordinates calculated from FIRMS data.")


# ============================================================
# 4. CHECK COORDINATES
# ============================================================

df = pred.dropna(
    subset=[
        "latitude",
        "longitude"
    ]
).copy()


matched = len(df)

print(
    "\nCoordinates matched:",
    matched,
    "/",
    len(pred)
)


if df.empty:
    raise ValueError(
        "No valid coordinates found for risk cells."
    )


# ============================================================
# 5. PREPARE RISK SCORE
# ============================================================

if "risk_score" in df.columns:

    df["display_score"] = pd.to_numeric(
        df["risk_score"],
        errors="coerce"
    )

elif "activity_score" in df.columns:

    df["display_score"] = pd.to_numeric(
        df["activity_score"],
        errors="coerce"
    )

else:

    df["display_score"] = np.nan


# ============================================================
# 6. FORMAT RISK SCORE
# ============================================================

def format_risk_score(value):

    if pd.isna(value):
        return None

    value = float(value)

    if value > 1:
        return f"{value:.1f}%"

    return f"{value * 100:.1f}%"


# ============================================================
# 7. CALCULATE BUBBLE SIZE
# ============================================================

def calculate_bubble_size(data):

    if "activity_score" in data.columns:

        values = pd.to_numeric(
            data["activity_score"],
            errors="coerce"
        )

    elif "risk_score" in data.columns:

        values = pd.to_numeric(
            data["risk_score"],
            errors="coerce"
        )

    else:

        return np.full(
            len(data),
            400
        )


    values = values.fillna(0)


    values = np.where(
        values > 1,
        values / 100,
        values
    )


    values = np.clip(
        values,
        0,
        1
    )


    return (
        300
        + values * 900
    )


df["bubble_size"] = calculate_bubble_size(df)


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
        df[risk_column] == risk
    ]


    if subset.empty:
        continue


    ax.scatter(
        subset["longitude"],
        subset["latitude"],
        s=subset["bubble_size"],
        color=RISK_COLORS[risk],
        alpha=0.65,
        edgecolors="black",
        linewidths=1.2,
        zorder=3
    )


# ============================================================
# 11. SORT DATA
# ============================================================

df = df.sort_values(
    by=[
        "longitude",
        "latitude"
    ]
).reset_index(drop=True)


# ============================================================
# 12. ADD CLEAN LABELS
# ============================================================

for _, row in df.iterrows():

    latitude = float(
        row["latitude"]
    )

    longitude = float(
        row["longitude"]
    )


    score_text = format_risk_score(
        row["display_score"]
    )


    grid_id = row.get(
        "grid_id",
        f"{latitude:.2f}_{longitude:.2f}"
    )


    if score_text is None:

        label = str(grid_id)

    else:

        label = (
            f"{grid_id}\n"
            f"Risk: {score_text}"
        )


    # --------------------------------------------------------
    # Label positioning
    # --------------------------------------------------------

    if (
        abs(latitude - 28.74) < 0.01
        and abs(longitude - 76.92) < 0.005
    ):

        offset = (
            -85,
            20
        )

        horizontal_alignment = "right"


    elif (
        abs(latitude - 28.74) < 0.01
        and abs(longitude - 76.93) < 0.005
    ):

        offset = (
            18,
            20
        )

        horizontal_alignment = "left"


    else:

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
# 13. TITLE
# ============================================================

ax.set_title(
    "THERMOSCOPE - Delhi NCR Fire Risk Map",
    fontsize=20,
    fontweight="bold",
    pad=18
)


# ============================================================
# 14. AXIS LABELS
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
# 15. GRID
# ============================================================

ax.grid(
    True,
    linestyle="--",
    linewidth=0.8,
    alpha=0.25,
    zorder=0
)


# ============================================================
# 16. MAP MARGINS
# ============================================================

ax.margins(
    x=0.08,
    y=0.12
)


# ============================================================
# 17. RISK COUNTS
# ============================================================

risk_counts = df[
    risk_column
].value_counts()


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
# 18. CLEAN LEGEND
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
# 19. SUMMARY BOX
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
    df[risk_column].value_counts()
)

print("\nMap saved to:")
print(OUTPUT_FILE)

print("\n" + "=" * 65)
print("RISK MAP COMPLETE")
print("=" * 65)


# ============================================================
# 22. SHOW MAP
# ============================================================

plt.show()

plt.close()