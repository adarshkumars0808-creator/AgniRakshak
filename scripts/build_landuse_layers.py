from pathlib import Path
import time
import requests
import pandas as pd


# ============================================================
# THERMOSCOPE
# STEP 1 — AGRICULTURAL + FOREST GIS LAYERS
#
# Source:
# OpenStreetMap / Overpass API
#
# IMPORTANT:
# These are CONTEXTUAL LAND-USE coordinates.
# They are NOT fire detections.
# NASA FIRMS remains the primary fire source.
# ============================================================


OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


AGRICULTURAL_FILE = (
    OUTPUT_DIR / "agricultural_sites.csv"
)

FOREST_FILE = (
    OUTPUT_DIR / "forest_sites.csv"
)


# ============================================================
# STUDY AREA
# ============================================================

# Covers the existing Thermoscope FIRMS study region.

SOUTH = 23.5
WEST = 74.5
NORTH = 31.5
EAST = 85.0


# ============================================================
# OVERPASS
# ============================================================

OVERPASS_URL = (
    "https://overpass-api.de/api/interpreter"
)


# ============================================================
# QUERY HELPER
# ============================================================

def query_overpass(query, description):

    print()
    print("=" * 70)
    print(f"DOWNLOADING {description}")
    print("=" * 70)

    # Multiple public Overpass instances.
    # If one rejects/throttles the request, try another.
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]

    headers = {
        "User-Agent": (
            "Thermoscope-SIH2026/1.0 "
            "(GIS land-use preparation)"
        ),
        "Accept": "application/json",
    }

    last_error = None

    for endpoint in endpoints:

        print()
        print(f"Server: {endpoint}")

        for attempt in range(1, 3):

            try:

                print(
                    f"Attempt {attempt}/2..."
                )

                response = requests.post(
                    endpoint,
                    data={
                        "data": query
                    },
                    headers=headers,
                    timeout=300,
                )

                response.raise_for_status()

                data = response.json()

                elements = data.get(
                    "elements",
                    []
                )

                print(
                    f"Received "
                    f"{len(elements):,} "
                    f"OSM elements."
                )

                return data

            except Exception as e:

                last_error = e

                print(
                    f"Request failed: {e}"
                )

                if attempt < 2:

                    print(
                        "Waiting 5 seconds..."
                    )

                    time.sleep(5)

        print(
            "Trying next Overpass server..."
        )

    raise RuntimeError(
        f"Could not download {description}. "
        f"Last error: {last_error}"
    )


# ============================================================
# CONVERT OSM ELEMENTS TO POINTS
# ============================================================

def elements_to_points(
    data,
    category,
):

    rows = []

    elements = data.get(
        "elements",
        []
    )

    for element in elements:

        tags = element.get(
            "tags",
            {}
        )

        # ----------------------------------------------------
        # Node
        # ----------------------------------------------------

        if element.get("type") == "node":

            lat = element.get("lat")
            lon = element.get("lon")

        # ----------------------------------------------------
        # Way / relation
        #
        # We use OSM-provided center when available.
        # This is a representative coordinate for the
        # land-use object, NOT a fire coordinate.
        # ----------------------------------------------------

        else:

            center = element.get(
                "center",
                {}
            )

            lat = center.get("lat")
            lon = center.get("lon")

        if lat is None or lon is None:

            continue

        landuse = (
            tags.get("landuse")
            or tags.get("natural")
            or tags.get("crop")
            or ""
        )

        name = (
            tags.get("name")
            or tags.get("name:en")
            or ""
        )

        rows.append(
            {
                "latitude": lat,
                "longitude": lon,
                "site_name": name,
                "site_type": landuse,
                "category": category,
                "source": "OpenStreetMap",
                "osm_id": element.get("id"),
                "osm_type": element.get("type"),
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# AGRICULTURE
# ============================================================

def build_agricultural():

    # --------------------------------------------------------
    # farmland = agricultural crop land
    # orchard  = agricultural permanent crops
    # vineyard = agricultural crop land
    #
    # meadow is intentionally excluded initially because
    # it can represent non-crop grassland.
    # --------------------------------------------------------

    query = f"""
    [out:json][timeout:180];

    (
      way["landuse"="farmland"]
        ({SOUTH},{WEST},{NORTH},{EAST});

      way["landuse"="orchard"]
        ({SOUTH},{WEST},{NORTH},{EAST});

      way["landuse"="vineyard"]
        ({SOUTH},{WEST},{NORTH},{EAST});
    );

    out center tags;
    """

    data = query_overpass(
        query,
        "AGRICULTURAL LAND"
    )

    df = elements_to_points(
        data,
        "AGRICULTURAL"
    )

    if df.empty:

        print(
            "WARNING: No agricultural "
            "land-use objects returned."
        )

    else:

        # Remove duplicate coordinates.

        df = df.drop_duplicates(
            subset=[
                "latitude",
                "longitude"
            ]
        )

    df.to_csv(
        AGRICULTURAL_FILE,
        index=False
    )

    print()
    print(
        f"Agricultural records saved: "
        f"{len(df):,}"
    )

    print(
        f"File: {AGRICULTURAL_FILE}"
    )

    return df


# ============================================================
# FOREST
# ============================================================

def build_forest():

    # --------------------------------------------------------
    # natural=wood
    # landuse=forest
    #
    # These represent mapped woodland/forest areas.
    # --------------------------------------------------------

    query = f"""
    [out:json][timeout:180];

    (
      way["natural"="wood"]
        ({SOUTH},{WEST},{NORTH},{EAST});

      way["landuse"="forest"]
        ({SOUTH},{WEST},{NORTH},{EAST});
    );

    out center tags;
    """

    data = query_overpass(
        query,
        "FOREST / WOODLAND"
    )

    df = elements_to_points(
        data,
        "FOREST"
    )

    if df.empty:

        print(
            "WARNING: No forest "
            "land-use objects returned."
        )

    else:

        df = df.drop_duplicates(
            subset=[
                "latitude",
                "longitude"
            ]
        )

    df.to_csv(
        FOREST_FILE,
        index=False
    )

    print()
    print(
        f"Forest records saved: "
        f"{len(df):,}"
    )

    print(
        f"File: {FOREST_FILE}"
    )

    return df


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    agricultural,
    forest,
):

    print()
    print("=" * 70)
    print("LAND-USE LAYER GENERATION COMPLETE")
    print("=" * 70)

    print(
        f"Agricultural points : "
        f"{len(agricultural):,}"
    )

    print(
        f"Forest points       : "
        f"{len(forest):,}"
    )

    print()
    print("OUTPUT FILES")
    print("-" * 70)

    print(
        agricultural.to_csv(
            index=False
        )[:0]
        or
        AGRICULTURAL_FILE
    )

    print(
        forest.to_csv(
            index=False
        )[:0]
        or
        FOREST_FILE
    )

    print()
    print("IMPORTANT:")
    print(
        "These coordinates represent mapped "
        "land-use objects."
    )

    print(
        "They are contextual GIS evidence, "
        "not FIRMS fire detections."
    )

    print(
        "NASA FIRMS remains the primary "
        "fire-detection source."
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("THERMOSCOPE — GIS LAND-USE PREPARATION")
    print("=" * 70)

    agricultural = build_agricultural()

    # Small delay between Overpass requests.
    time.sleep(3)

    forest = build_forest()

    print_summary(
        agricultural,
        forest
    )


if __name__ == "__main__":
    main()