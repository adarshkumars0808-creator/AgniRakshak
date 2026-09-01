from pathlib import Path

import pandas as pd
import requests


# ============================================================
# THERMOSCOPE / AGNIRAKSHAK
# INDUSTRIAL FACILITY LOCATIONS (OpenStreetMap / Overpass API)
# ============================================================
#
# IMPORTANT: this script needs internet access and queries the
# public OSM Overpass API. Run it once, from your own machine:
#
#   python src/fetch_industrial_sites.py
#
# It is NOT part of the automated Claude sandbox that wrote this
# code, so it has not been executed there — run it yourself and
# check the printed counts look reasonable before trusting them.
#
# Output: data/processed/industrial_sites.csv
# Used by: classify_fire_type.py (as an optional, stronger
# proximity signal for INDUSTRIAL_PERSISTENT classification)
# ============================================================

OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "industrial_sites.csv"

# Same broad Delhi NCR + Uttar Pradesh bounding box used throughout
# this project (south, west, north, east — Overpass order).
SOUTH, WEST, NORTH, EAST = 23.5, 74.5, 31.5, 85.0

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Tags covering the facility types named in the problem statement:
# oil refineries, petrochemical complexes, thermal power plants,
# steel industries, mining areas, LNG terminals.
OVERPASS_QUERY = f"""
[out:json][timeout:180];
(
  node["landuse"="industrial"]({SOUTH},{WEST},{NORTH},{EAST});
  way["landuse"="industrial"]({SOUTH},{WEST},{NORTH},{EAST});

  node["power"="plant"]({SOUTH},{WEST},{NORTH},{EAST});
  way["power"="plant"]({SOUTH},{WEST},{NORTH},{EAST});

  node["man_made"="works"]({SOUTH},{WEST},{NORTH},{EAST});
  way["man_made"="works"]({SOUTH},{WEST},{NORTH},{EAST});

  node["industrial"="oil"]({SOUTH},{WEST},{NORTH},{EAST});
  way["industrial"="oil"]({SOUTH},{WEST},{NORTH},{EAST});

  node["industrial"="refinery"]({SOUTH},{WEST},{NORTH},{EAST});
  way["industrial"="refinery"]({SOUTH},{WEST},{NORTH},{EAST});

  node["landuse"="quarry"]({SOUTH},{WEST},{NORTH},{EAST});
  way["landuse"="quarry"]({SOUTH},{WEST},{NORTH},{EAST});

  node["man_made"="petroleum_well"]({SOUTH},{WEST},{NORTH},{EAST});

  node["pipeline"="lng"]({SOUTH},{WEST},{NORTH},{EAST});
  way["pipeline"="lng"]({SOUTH},{WEST},{NORTH},{EAST});
);
out center tags;
"""


def fetch():

    print("=" * 70)
    print("THERMOSCOPE - INDUSTRIAL FACILITY FETCH (OpenStreetMap)")
    print("=" * 70)
    print(f"BBox: south={SOUTH}, west={WEST}, north={NORTH}, east={EAST}")
    print("Querying Overpass API (this can take 30-90 seconds)...")

    response = requests.post(
        OVERPASS_URL,
        data={"data": OVERPASS_QUERY},
        timeout=200,
    )

    response.raise_for_status()

    data = response.json()
    elements = data.get("elements", [])

    print(f"Received {len(elements):,} raw elements from OSM.")

    rows = []

    for el in elements:

        if el["type"] == "node":
            lat, lon = el.get("lat"), el.get("lon")
        else:
            center = el.get("center", {})
            lat, lon = center.get("lat"), center.get("lon")

        if lat is None or lon is None:
            continue

        tags = el.get("tags", {})

        facility_type = (
            tags.get("landuse")
            or tags.get("power")
            or tags.get("man_made")
            or tags.get("industrial")
            or tags.get("pipeline")
            or "unknown"
        )

        rows.append(
            {
                "latitude": lat,
                "longitude": lon,
                "name": tags.get("name", ""),
                "facility_type": facility_type,
                "osm_id": el.get("id"),
            }
        )

    if not rows:
        print("WARNING: no industrial facilities returned. Nothing saved.")
        return

    df = pd.DataFrame(rows).drop_duplicates(subset=["latitude", "longitude"])

    df.to_csv(OUTPUT_FILE, index=False)

    print()
    print("Facility type breakdown:")
    print(df["facility_type"].value_counts().to_string())
    print()
    print(f"Saved {len(df):,} facilities to: {OUTPUT_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    fetch()