from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# THERMOSCOPE / AGNIRAKSHAK
# STAGE 4.5 — REGIONAL RISK ZONE AGGREGATION
# ============================================================
#
# WHY THIS EXISTS
# ------------------------------------------------------------
# risk_predictions.csv has one row per raw 5km analysis grid cell
# — 26,891 of them. Plotting every one of those as an individual
# marker looks like an unprocessed data dump, not an analysis
# product. This script re-bins them onto a coarser ~30km regional
# grid so the map shows a manageable number of distinct, labeled
# risk zones instead.
#
# The full-resolution 26,891-cell risk_predictions.csv is NOT
# replaced or deleted — the dashboard's heatmap layer still uses
# it directly for a smooth risk-density surface. This script only
# produces the DISCRETE, CLICKABLE marker layer that sits on top
# of that heatmap.
#
# Each output zone reports:
#   - the highest risk_score in that region (drives the marker's
#     color/urgency — a regional zone is only as safe as its worst
#     cell)
#   - the average risk_score across the region (context)
#   - summed historical detections
#   - how many raw 5km grid cells were merged into it
#
# OUTPUT: data/processed/risk_zones.csv
# ============================================================

DATA_DIR = Path("data/processed")

RISK_FILE = DATA_DIR / "risk_predictions.csv"
OUTPUT_FILE = DATA_DIR / "risk_zones.csv"

BIN_SIZE_KM = 30


def main():

    print("=" * 70)
    print("THERMOSCOPE / AGNIRAKSHAK - REGIONAL RISK ZONE AGGREGATION")
    print("=" * 70)

    if not RISK_FILE.exists():
        raise FileNotFoundError(
            f"Missing file: {RISK_FILE}\nRun risk_model.py first."
        )

    df = pd.read_csv(RISK_FILE, low_memory=False)
    print(f"Loaded {len(df):,} raw risk grid cells from {RISK_FILE.name}")

    bin_deg = BIN_SIZE_KM / 111.0

    df["bin_lat"] = (np.floor(df["latitude"] / bin_deg) * bin_deg).round(4)
    df["bin_lon"] = (np.floor(df["longitude"] / bin_deg) * bin_deg).round(4)

    print(f"Re-binning onto a ~{BIN_SIZE_KM} km regional grid...")

    rows = []

    for (_, _), group in df.groupby(["bin_lat", "bin_lon"]):

        group = group.sort_values("risk_score", ascending=False)
        rep = group.iloc[0]  # the single worst cell anchors this zone

        rows.append({
            "zone_id": rep["grid_id"],
            "grid_ids_merged": ";".join(group["grid_id"].astype(str)),
            "n_grids_merged": len(group),
            "latitude": rep["latitude"],
            "longitude": rep["longitude"],
            "risk_score": rep["risk_score"],
            "risk_level": rep["risk_level"],
            "avg_risk_score": round(group["risk_score"].mean(), 1),
            "total_detections": int(group["total_detections"].sum()),
            "avg_frp": round(group["avg_frp"].mean(), 2) if "avg_frp" in group.columns else np.nan,
            "max_frp": group["max_frp"].max() if "max_frp" in group.columns else np.nan,
            "region_radius_km": BIN_SIZE_KM,
        })

    result = pd.DataFrame(rows).sort_values("risk_score", ascending=False)

    result.to_csv(OUTPUT_FILE, index=False)

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)
    print(f"Raw grid cells:      {len(df):,}")
    print(f"Regional risk zones: {len(result):,}")
    print()
    print("Risk level breakdown (by each zone's worst cell):")
    print(result["risk_level"].value_counts().to_string())
    print()
    print(f"Saved to: {OUTPUT_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()