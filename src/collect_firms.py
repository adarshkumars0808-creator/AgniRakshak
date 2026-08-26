import os
import pandas as pd
import requests
from dotenv import load_dotenv

# ============================================================
# THERMOSCOPE - NASA FIRMS LIVE DATA FETCH
# ============================================================

load_dotenv()

MAP_KEY = os.getenv("FIRMS_MAP_KEY")

if not MAP_KEY:
    print("ERROR: FIRMS_MAP_KEY not found in .env")
    raise SystemExit

# ------------------------------------------------------------
# DELHI BOUNDING BOX
# west, south, east, north
# ------------------------------------------------------------

DELHI_BBOX = "76.8,28.4,77.4,28.9"

# ------------------------------------------------------------
# NASA FIRMS API
# ------------------------------------------------------------

SOURCE = "VIIRS_NOAA20_NRT"
DAY_RANGE = 5

URL = (
    f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
    f"{MAP_KEY}/{SOURCE}/{DELHI_BBOX}/{DAY_RANGE}"
)

print("=" * 70)
print("THERMOSCOPE - NASA FIRMS LIVE DATA")
print("=" * 70)

print("\nSource:")
print(SOURCE)

print("\nFetching latest FIRMS data for Delhi...")

# ------------------------------------------------------------
# FETCH DATA
# ------------------------------------------------------------

try:
    response = requests.get(URL, timeout=30)

    print("\nHTTP Status:", response.status_code)

    if response.status_code != 200:
        print("\nERROR: NASA FIRMS API request failed.")
        print(response.text[:500])
        raise SystemExit

except requests.RequestException as e:
    print("\nERROR connecting to NASA FIRMS:")
    print(e)
    raise SystemExit

# ------------------------------------------------------------
# READ CSV
# ------------------------------------------------------------

from io import StringIO

df = pd.read_csv(
    StringIO(response.text)
)

print("\nLive observations received:", len(df))

# ------------------------------------------------------------
# CHECK DATA
# ------------------------------------------------------------

if df.empty:
    print("\nNo fire detections returned for the requested area/day.")
else:

    print("\nColumns received:")
    print(df.columns.tolist())

    print("\nLatest observations:")
    print(
        df[
            [
                "latitude",
                "longitude",
                "acq_date",
                "acq_time",
                "satellite",
                "confidence",
                "frp"
            ]
        ].head(20).to_string(index=False)
    )

# ------------------------------------------------------------
# SAVE LIVE DATA
# ------------------------------------------------------------

OUTPUT_FILE = "data/delhi_firms_live.csv"

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\nSaved live data to:")
print(OUTPUT_FILE)

print("\n" + "=" * 70)
print("LIVE FIRMS FETCH COMPLETE")
print("=" * 70)