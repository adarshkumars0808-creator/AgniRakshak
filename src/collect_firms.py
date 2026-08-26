import os
from io import StringIO

import pandas as pd
import requests
from dotenv import load_dotenv


# ============================================================
# THERMOSCOPE
# NASA FIRMS MULTI-SATELLITE LIVE DATA
# ============================================================

load_dotenv()

MAP_KEY = os.getenv("FIRMS_MAP_KEY")

if not MAP_KEY:
    print("ERROR: FIRMS_MAP_KEY not found in .env")
    raise SystemExit(1)


# ============================================================
# DELHI NCR BOUNDING BOX
# west, south, east, north
#
# Covers Delhi + major NCR surroundings:
# Gurugram, Faridabad, Noida, Ghaziabad etc.
# ============================================================

NCR_BBOX = "76.5,28.0,77.8,29.3"


# ============================================================
# FIRMS SETTINGS
# ============================================================

# FIRMS Area API supports maximum 5 days per request
DAY_RANGE = 5


# NASA VIIRS Near Real-Time sources
SOURCES = [
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "VIIRS_SNPP_NRT",
]


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_FILE = "data/delhi_firms_live.csv"


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("THERMOSCOPE - NASA FIRMS MULTI-SATELLITE LIVE DATA")
print("=" * 70)

print("\nArea: Delhi NCR")
print("Bounding Box:", NCR_BBOX)
print("Days:", DAY_RANGE)

print("\nSources:")
for source in SOURCES:
    print(" -", source)


# ============================================================
# FETCH DATA
# ============================================================

all_data = []

satellite_counts = {}


for source in SOURCES:

    print("\n" + "-" * 70)
    print("Fetching:", source)
    print("-" * 70)

    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{MAP_KEY}/{source}/{NCR_BBOX}/{DAY_RANGE}"
    )

    try:

        response = requests.get(
            url,
            timeout=60
        )

        print("HTTP Status:", response.status_code)

    except requests.RequestException as e:

        print("WARNING: Connection failed for", source)
        print("Reason:", e)

        satellite_counts[source] = 0
        continue


    # --------------------------------------------------------
    # CHECK HTTP RESPONSE
    # --------------------------------------------------------

    if response.status_code != 200:

        print("WARNING: FIRMS request failed.")
        print(response.text[:500])

        satellite_counts[source] = 0
        continue


    # --------------------------------------------------------
    # CHECK EMPTY RESPONSE
    # --------------------------------------------------------

    if not response.text.strip():

        print("No data returned.")

        satellite_counts[source] = 0
        continue


    # --------------------------------------------------------
    # READ CSV
    # --------------------------------------------------------

    try:

        df = pd.read_csv(
            StringIO(response.text)
        )

    except Exception as e:

        print("WARNING: Could not parse FIRMS CSV.")
        print("Reason:", e)

        satellite_counts[source] = 0
        continue


    # --------------------------------------------------------
    # VALIDATE RESPONSE
    # --------------------------------------------------------

    required_columns = [
        "latitude",
        "longitude",
        "acq_date",
        "acq_time",
        "satellite",
        "frp"
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:

        print(
            "WARNING: Missing columns:",
            missing_columns
        )

        satellite_counts[source] = 0
        continue


    # --------------------------------------------------------
    # CLEAN NUMERIC VALUES
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # REMOVE INVALID COORDINATES
    # --------------------------------------------------------

    df = df.dropna(
        subset=[
            "latitude",
            "longitude"
        ]
    )


    # --------------------------------------------------------
    # ENSURE NCR BOUNDING BOX
    # --------------------------------------------------------

    west, south, east, north = map(
        float,
        NCR_BBOX.split(",")
    )

    df = df[
        (df["longitude"] >= west)
        &
        (df["longitude"] <= east)
        &
        (df["latitude"] >= south)
        &
        (df["latitude"] <= north)
    ]


    # --------------------------------------------------------
    # COUNT
    # --------------------------------------------------------

    count = len(df)

    satellite_counts[source] = count

    print("Observations:", count)


    # --------------------------------------------------------
    # DATE SUMMARY
    # --------------------------------------------------------

    if not df.empty:

        dates = (
            pd.to_datetime(
                df["acq_date"],
                errors="coerce"
            )
            .dropna()
            .dt.date
            .unique()
        )

        print(
            "Detection dates:",
            sorted(dates)
        )


    # --------------------------------------------------------
    # STORE
    # --------------------------------------------------------

    if not df.empty:

        # Store the source used for this request.
        df["firms_source"] = source

        all_data.append(df)


# ============================================================
# COMBINE ALL SATELLITES
# ============================================================

print("\n" + "=" * 70)
print("COMBINING SATELLITE DATA")
print("=" * 70)


if all_data:

    df_live = pd.concat(
        all_data,
        ignore_index=True
    )

else:

    df_live = pd.DataFrame()


# ============================================================
# REMOVE EXACT DUPLICATES
# ============================================================

if not df_live.empty:

    before = len(df_live)

    df_live = df_live.drop_duplicates()

    after = len(df_live)

    print(
        "\nDuplicate observations removed:",
        before - after
    )


# ============================================================
# CLEAN ACQUISITION DATE
# ============================================================

if not df_live.empty:

    df_live["acq_date"] = pd.to_datetime(
        df_live["acq_date"],
        errors="coerce"
    )

    df_live = df_live.dropna(
        subset=["acq_date"]
    )


# ============================================================
# SORT NEWEST FIRST
# ============================================================

if not df_live.empty:

    sort_columns = []

    if "acq_date" in df_live.columns:
        sort_columns.append("acq_date")

    if "acq_time" in df_live.columns:
        sort_columns.append("acq_time")

    if sort_columns:

        df_live = df_live.sort_values(
            sort_columns,
            ascending=False
        )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("LIVE DATA SUMMARY")
print("=" * 70)


for source, count in satellite_counts.items():

    print(
        f"{source}: {count}"
    )


print(
    "\nTOTAL LIVE OBSERVATIONS:",
    len(df_live)
)


# ============================================================
# UNIQUE SATELLITES
# ============================================================

if not df_live.empty:

    print(
        "Unique satellite values:",
        df_live["satellite"].nunique()
    )

    print(
        "Satellite names:",
        df_live["satellite"].dropna().unique()
    )


# ============================================================
# DATE RANGE
# ============================================================

if not df_live.empty:

    print(
        "\nLatest acquisition date:",
        df_live["acq_date"].max().date()
    )

    print(
        "Oldest acquisition date:",
        df_live["acq_date"].min().date()
    )


# ============================================================
# DISPLAY LATEST OBSERVATIONS
# ============================================================

if not df_live.empty:

    display_columns = [
        "latitude",
        "longitude",
        "acq_date",
        "acq_time",
        "satellite",
        "confidence",
        "frp",
    ]

    available_columns = [
        column
        for column in display_columns
        if column in df_live.columns
    ]

    print("\nLatest observations:")

    print(
        df_live[
            available_columns
        ]
        .head(20)
        .to_string(index=False)
    )

else:

    print(
        "\nNo live fire detections returned "
        "for Delhi NCR."
    )


# ============================================================
# SAVE
# ============================================================

os.makedirs(
    os.path.dirname(OUTPUT_FILE),
    exist_ok=True
)

df_live.to_csv(
    OUTPUT_FILE,
    index=False
)


print("\nSaved live data to:")
print(OUTPUT_FILE)

print("\n" + "=" * 70)
print("LIVE FIRMS FETCH COMPLETE")
print("=" * 70)