from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# THERMOSCOPE / AGNIRAKSHAK
# STAGE 4 — LAND-COVER VERIFICATION + REGIONAL SITE MERGING
# ============================================================
#
# WHY THIS EXISTS
# ------------------------------------------------------------
# Manual spot-checks on Google Maps found that grid cells labeled
# INDUSTRIAL or MINING by the earlier pipeline were frequently
# actually plain cropland or forest. That was checked against the
# real ESA WorldCover 10m land-cover data already computed in
# fire_type_classification.csv, and confirmed:
#
#   INDUSTRIAL-labeled grids actually on built-up/bare land: 7.7%
#   MINING-labeled grids actually on built-up/bare land:     8.1%
#
# ~92% of those two labels were false positives — proximity to an
# OSM industrial-tagged area/point is not enough evidence on its
# own. AGRICULTURAL_BURNING (100% on CROPLAND) and FOREST_FIRE
# (100% on TREE_COVER/SHRUBLAND) were already clean.
#
# This script also re-bins every verified category onto a coarser
# regional grid so the map shows meaningful, distinct locations
# instead of a wall of raw 5km grid cells. Every marker the
# dashboard draws is a REGIONAL AGGREGATE, not a single raw
# detection pixel — that distinction matters when presenting this,
# say so plainly rather than implying pixel-level precision.
#
# WHAT THIS SCRIPT DOES
# ------------------------------------------------------------
# 1. Re-checks every INDUSTRIAL / MINING label against real land
#    cover. Anything not on BUILT_UP or BARE_SPARSE land, or with
#    fewer than MIN_DETECTIONS historical detections, is dropped —
#    fewer, trustworthy sites beats many unverified ones.
# 2. Re-bins each verified category onto a regional grid and
#    aggregates every cell that falls in the same bin into ONE
#    marker (summed detections, max FRP, the best available real
#    site name, a count of how many raw grid cells it represents).
#    Bin size differs by category:
#      INDUSTRIAL / MINING     -> ~8 km  (a single facility can
#                                  span a couple of grid cells)
#      AGRICULTURAL_BURNING /
#      FOREST_FIRE             -> ~40 km (regional hotspot view;
#                                  these are genuinely widespread,
#                                  real, distinct events — this is
#                                  a map-clarity aggregation, not a
#                                  claim that the whole bin burned)
#
# OUTPUT: data/processed/verified_fire_sites.csv
# One row per verified, real, regionally-aggregated site. Rows
# that failed land-cover verification are NOT included.
# ============================================================

DATA_DIR = Path("data/processed")

CLASSIFICATION_FILE = DATA_DIR / "fire_type_classification.csv"
PREDICTIONS_FILE = DATA_DIR / "fire_type_predictions.csv"   # optional, for real site names
RISK_FILE = DATA_DIR / "risk_predictions.csv"                # optional, for risk_score/level
INDUSTRIAL_SITES_FILE = DATA_DIR / "industrial_sites.csv"    # OSM catalog, for name lookup
MINING_SITES_FILE = DATA_DIR / "mining_sites.csv"             # OSM catalog, for name lookup

OUTPUT_FILE = DATA_DIR / "verified_fire_sites.csv"

BUILT_LIKE_LANDCOVER = {"BUILT_UP", "BARE_SPARSE"}
FOREST_LIKE_LANDCOVER = {"TREE_COVER", "SHRUBLAND"}

MIN_DETECTIONS = 3

# How far to search for a NAMED real-world facility to attach to a
# verified INDUSTRIAL/MINING site. This is deliberately wider than
# the regional merge bin (8km) because most OSM industrial/mining
# polygons in this region have no name tag at all (~18% of
# industrial_sites.csv, ~2% of mining_sites.csv actually have one)
# — searching further out finds the nearest KNOWN name rather than
# forcing every site to stay unnamed. The distance is always
# reported alongside the name so it reads as "nearest known
# facility, ~Nkm away", never as a claim that the fire IS that
# exact facility.
NAME_SEARCH_RADIUS_KM = 25.0

# Regional aggregation bin size per verified category, in km.
# ~111 km per degree of latitude is used to convert to degrees.
BIN_SIZE_KM = {
    "INDUSTRIAL": 8,
    "MINING": 8,
    "AGRICULTURAL_BURNING": 40,
    "FOREST_FIRE": 40,
}


# ------------------------------------------------------------
# LOAD
# ------------------------------------------------------------

def load_inputs():

    if not CLASSIFICATION_FILE.exists():
        raise FileNotFoundError(
            f"Missing file: {CLASSIFICATION_FILE}\n"
            "This script needs the land-cover-enriched classification "
            "file (the one with a landcover_class column)."
        )

    df = pd.read_csv(CLASSIFICATION_FILE, low_memory=False)
    print(f"Loaded {len(df):,} grid cells from {CLASSIFICATION_FILE.name}")

    if PREDICTIONS_FILE.exists():
        pred = pd.read_csv(PREDICTIONS_FILE, low_memory=False)
        keep = [
            c for c in [
                "grid_id", "coordinate_source",
                "display_latitude", "display_longitude",
                "display_site_name", "display_site_type",
            ]
            if c in pred.columns
        ]
        df = df.merge(pred[keep], on="grid_id", how="left")
        print(f"Merged real-site names/coordinates from {PREDICTIONS_FILE.name}")
    else:
        print(
            f"NOTE: {PREDICTIONS_FILE.name} not found — sites will show "
            "grid coordinates only, no matched real-world name."
        )
        for col in ["display_latitude", "display_longitude", "display_site_name", "display_site_type"]:
            df[col] = np.nan

    if RISK_FILE.exists():
        risk = pd.read_csv(RISK_FILE, low_memory=False)[["grid_id", "risk_score", "risk_level"]]
        df = df.merge(risk, on="grid_id", how="left")
    else:
        df["risk_score"] = np.nan
        df["risk_level"] = ""

    return df


# ------------------------------------------------------------
# LAND-COVER VERIFICATION
# ------------------------------------------------------------

def verify_fire_type(row):

    ft = str(row.get("fire_type", "")).upper()
    lc = str(row.get("landcover_class", "")).upper()
    detections = row.get("total_detections", 0) or 0

    if ft == "INDUSTRIAL":
        if lc in BUILT_LIKE_LANDCOVER and detections >= MIN_DETECTIONS:
            return "INDUSTRIAL", (
                f"On {lc.replace('_',' ').title()} land cover (ESA WorldCover 10m) "
                f"with {int(detections)} historical detections — consistent with a "
                f"real industrial fire source."
            )
        return "UNVERIFIED", (
            f"Originally labeled INDUSTRIAL, but the actual land cover here is "
            f"{lc.replace('_',' ').title()}, not built-up/bare land — likely a "
            f"false positive from proximity to an industrial area rather than "
            f"an industrial fire itself."
        )

    if ft == "MINING":
        if lc in BUILT_LIKE_LANDCOVER and detections >= MIN_DETECTIONS:
            return "MINING", (
                f"On {lc.replace('_',' ').title()} land cover with "
                f"{int(detections)} historical detections — consistent with "
                f"open-pit mining/processing activity."
            )
        return "UNVERIFIED", (
            f"Originally labeled MINING, but the actual land cover here is "
            f"{lc.replace('_',' ').title()}, not bare/built land — likely a "
            f"false positive."
        )

    if ft == "AGRICULTURAL_BURNING":
        if lc == "CROPLAND":
            return "AGRICULTURAL_BURNING", "On cropland — consistent with crop-residue burning."
        return "UNVERIFIED", f"Labeled agricultural burning but land cover is {lc.title()}, not cropland."

    if ft == "FOREST_FIRE":
        if lc in FOREST_LIKE_LANDCOVER:
            return "FOREST_FIRE", f"On {lc.replace('_',' ').title()} — consistent with a forest/wildland fire."
        return "UNVERIFIED", f"Labeled forest fire but land cover is {lc.title()}, not tree cover/shrubland."

    return "UNVERIFIED", "Not confidently classified with current signals."


# ------------------------------------------------------------
# NEAREST NAMED FACILITY LOOKUP
# ------------------------------------------------------------

def load_named_catalog(path):
    """
    Load an OSM site catalog and keep only rows that actually have
    a name (or, failing that, an operator) on record. Most rows in
    these catalogs do NOT have one — that's a real limitation of
    the underlying OSM data for this region, not a bug.
    """

    if not path.exists():
        print(f"NOTE: {path.name} not found — skipping name lookup for it.")
        return pd.DataFrame(columns=["latitude", "longitude", "display_name"])

    catalog = pd.read_csv(path, low_memory=False)

    if "name" not in catalog.columns:
        catalog["name"] = np.nan
    if "operator" not in catalog.columns:
        catalog["operator"] = np.nan

    catalog["display_name"] = catalog["name"].fillna(catalog["operator"])
    catalog = catalog.dropna(subset=["display_name", "latitude", "longitude"])

    print(
        f"  {path.name}: {len(catalog):,} facilities have a real name/operator on record"
    )

    return catalog[["latitude", "longitude", "display_name"]].reset_index(drop=True)


def attach_nearest_named_facility(df, catalog, radius_km):
    """
    For each row in df, find the nearest facility in `catalog` that
    has a real name, and attach it if within radius_km. Leaves
    site_name empty (not fabricated) when nothing named is that
    close — the honest answer, not a guess.
    """

    if df.empty:
        return df

    df = df.copy()

    if catalog.empty:
        df["site_name"] = df.get("site_name", "")
        df["named_facility_distance_km"] = np.nan
        return df

    cat_lat = catalog["latitude"].to_numpy()
    cat_lon = catalog["longitude"].to_numpy()
    cat_name = catalog["display_name"].to_numpy()

    names = []
    dists = []

    for lat, lon, existing_name in zip(
        df["latitude"], df["longitude"], df.get("site_name", [""] * len(df))
    ):

        # Already has a name from fire_type_predictions.csv's own
        # matching — keep it, still report distance as 0/unknown.
        if isinstance(existing_name, str) and existing_name.strip():
            names.append(existing_name)
            dists.append(0.0)
            continue

        d = haversine_km(lat, lon, cat_lat, cat_lon)
        idx = int(np.argmin(d))

        if d[idx] <= radius_km:
            names.append(str(cat_name[idx]))
            dists.append(round(float(d[idx]), 1))
        else:
            names.append("")
            dists.append(np.nan)

    df["site_name"] = names
    df["named_facility_distance_km"] = dists

    return df


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


# ------------------------------------------------------------
# REGIONAL BIN MERGE (fast, vectorized — safe for large N)
# ------------------------------------------------------------

def merge_by_region(df, bin_km):
    """
    Aggregate every row that falls in the same coarse
    lat/lon bin into a single representative marker. The
    representative point (name, exact coordinate, land cover) is
    taken from whichever raw cell in that bin has the most
    detections — detections themselves are summed across the
    whole bin.
    """

    if df.empty:
        return df

    bin_deg = bin_km / 111.0

    d = df.copy()
    d["bin_lat"] = (np.floor(d["latitude"] / bin_deg) * bin_deg).round(4)
    d["bin_lon"] = (np.floor(d["longitude"] / bin_deg) * bin_deg).round(4)

    rows = []

    for (_, _), group in d.groupby(["bin_lat", "bin_lon"]):

        group = group.sort_values("total_detections", ascending=False)
        rep = group.iloc[0]

        names = [
            n for n in group["display_site_name"].dropna().astype(str)
            if n.strip()
        ]

        rows.append({
            "grid_id": rep["grid_id"],
            "grid_ids_merged": ";".join(group["grid_id"].astype(str)),
            "n_grids_merged": len(group),
            "fire_type": rep["fire_type_verified"],
            "site_name": names[0] if names else "",
            "verification_reason": rep["verification_reason"],
            "latitude": rep["latitude"],
            "longitude": rep["longitude"],
            "total_detections": int(group["total_detections"].sum()),
            "avg_frp": rep.get("avg_frp", np.nan),
            "max_frp": group["max_frp"].max() if "max_frp" in group.columns else np.nan,
            "landcover_class": rep["landcover_class"],
            "risk_score": group["risk_score"].max() if "risk_score" in group.columns else np.nan,
            "risk_level": rep.get("risk_level", ""),
            "region_radius_km": bin_km,
        })

    return pd.DataFrame(rows)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    print("=" * 70)
    print("THERMOSCOPE / AGNIRAKSHAK - LAND-COVER VERIFICATION + REGIONAL MERGE")
    print("=" * 70)

    df = load_inputs()

    # Resolve the coordinate to plot: prefer a real matched site's
    # coordinate, fall back to the raw grid centroid.
    df["latitude"] = df["display_latitude"].fillna(df["latitude"])
    df["longitude"] = df["display_longitude"].fillna(df["longitude"])

    print()
    print("Verifying fire_type against real land cover (ESA WorldCover 10m)...")

    verified = df.apply(verify_fire_type, axis=1, result_type="expand")
    verified.columns = ["fire_type_verified", "verification_reason"]
    df = pd.concat([df, verified], axis=1)

    before_counts = df["fire_type"].value_counts()
    after_counts = df["fire_type_verified"].value_counts()

    print()
    print("BEFORE verification:")
    print(before_counts.to_string())
    print()
    print("AFTER verification (UNVERIFIED rows excluded from output):")
    print(after_counts.to_string())

    verified_df = df[df["fire_type_verified"] != "UNVERIFIED"].copy()

    print()
    print("Re-binning each category onto its regional aggregation grid...")

    print()
    print("Loading real-world facility name catalogs...")
    industrial_catalog = load_named_catalog(INDUSTRIAL_SITES_FILE)
    mining_catalog = load_named_catalog(MINING_SITES_FILE)

    merged_parts = []

    for fire_type, bin_km in BIN_SIZE_KM.items():

        subset = verified_df[verified_df["fire_type_verified"] == fire_type]

        if subset.empty:
            continue

        merged = merge_by_region(subset, bin_km)

        print(
            f"  {fire_type}: {len(subset):,} verified grid cells "
            f"-> {len(merged):,} regional sites (~{bin_km} km bins)"
        )

        if fire_type == "INDUSTRIAL":
            merged = attach_nearest_named_facility(
                merged, industrial_catalog, NAME_SEARCH_RADIUS_KM
            )
            named = (merged["site_name"].astype(str).str.strip() != "").sum()
            print(
                f"    -> {named}/{len(merged)} got a real facility name "
                f"(within {NAME_SEARCH_RADIUS_KM:.0f}km)"
            )

        elif fire_type == "MINING":
            merged = attach_nearest_named_facility(
                merged, mining_catalog, NAME_SEARCH_RADIUS_KM
            )
            named = (merged["site_name"].astype(str).str.strip() != "").sum()
            print(
                f"    -> {named}/{len(merged)} got a real facility name "
                f"(within {NAME_SEARCH_RADIUS_KM:.0f}km) — mining sites are "
                f"sparsely named in OSM for this region, so this ceiling is "
                f"expected to be lower than industrial."
            )

        merged_parts.append(merged)

    if not merged_parts:
        raise RuntimeError("No verified fire-type rows survived land-cover checking.")

    result = pd.concat(merged_parts, ignore_index=True, sort=False)
    result = result.sort_values("total_detections", ascending=False)

    result.to_csv(OUTPUT_FILE, index=False)

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)
    print(f"Final verified, regionally-aggregated sites: {len(result):,}")
    print(result["fire_type"].value_counts().to_string())
    print()

    for ft in ["INDUSTRIAL", "MINING"]:
        sub = result[result["fire_type"] == ft]
        if len(sub):
            named = (sub["site_name"].astype(str).str.strip() != "").sum()
            print(f"{ft} name coverage: {named}/{len(sub)} ({named/len(sub)*100:.0f}%)")

    print()
    print(f"Saved to: {OUTPUT_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()