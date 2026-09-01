import os
import time
from pathlib import Path
from datetime import date, timedelta
from io import StringIO

import pandas as pd
import requests
from dotenv import load_dotenv


# ============================================================
# THERMOSCOPE
# NASA FIRMS HISTORICAL DATA FETCHER
# ============================================================

load_dotenv()

MAP_KEY = os.getenv("FIRMS_MAP_KEY")

if not MAP_KEY:
    raise RuntimeError(
        "FIRMS_MAP_KEY not found in .env"
    )


# ============================================================
# TARGET REGION
# ============================================================
#
# Broad bounding box covering:
# Delhi NCR + Uttar Pradesh
#
# west, south, east, north
#
# Exact spatial filtering will happen later during processing.
# ============================================================

WEST = 74.5
SOUTH = 23.5
EAST = 85.0
NORTH = 31.5

BBOX = f"{WEST},{SOUTH},{EAST},{NORTH}"


# ============================================================
# DATA PERIOD
# ============================================================

START_DATE = date(2020, 1, 1)

# Automatically fetch until today's date.
END_DATE = date.today()


# ============================================================
# FIRMS SATELLITE SOURCES
# ============================================================
#
# S-NPP:
#   Available throughout our target period.
#
# NOAA-20:
#   Available throughout our target period.
#
# NOAA-21:
#   Available from January 17, 2024.
#
# IMPORTANT:
# NOAA-21 uses VIIRS_NOAA21_NRT.
# ============================================================

SOURCES = [
    "VIIRS_SNPP_SP",
    "VIIRS_NOAA20_SP",
    "VIIRS_NOAA21_NRT",
]


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# NASA FIRMS AREA API
# ============================================================

BASE_URL = (
    "https://firms.modaps.eosdis.nasa.gov"
    "/api/area/csv"
)


# ============================================================
# REQUEST SETTINGS
# ============================================================

MAX_RETRIES = 3
RETRY_DELAY = 5
REQUEST_TIMEOUT = 120
CHUNK_DAYS = 5
REQUEST_DELAY = 1


# ============================================================
# DATE CHUNK GENERATOR
# ============================================================

def daterange_chunks(start_date, end_date, days=5):
    """
    Generate non-overlapping date chunks.

    FIRMS Area API supports a maximum of 5 days
    per request.
    """

    current = start_date

    while current <= end_date:

        chunk_end = min(
            current + timedelta(days=days - 1),
            end_date
        )

        yield current, chunk_end

        current = chunk_end + timedelta(days=1)


# ============================================================
# FETCH ONE FIRMS CHUNK
# ============================================================

def fetch_chunk(source, start_date, end_date):
    """
    Download one historical FIRMS data chunk.
    """

    day_range = (
        end_date - start_date
    ).days + 1

    url = (
        f"{BASE_URL}/"
        f"{MAP_KEY}/"
        f"{source}/"
        f"{BBOX}/"
        f"{day_range}/"
        f"{start_date.isoformat()}"
    )

    print()
    print(
        f"[DOWNLOAD] {source} | "
        f"{start_date} -> {end_date}"
    )

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            response = requests.get(
                url,
                timeout=REQUEST_TIMEOUT
            )

            # ------------------------------------------------
            # Helpful error output
            # ------------------------------------------------

            if response.status_code != 200:

                print(
                    f"  HTTP {response.status_code}"
                )

                print(
                    f"  Response: "
                    f"{response.text[:300]}"
                )

                response.raise_for_status()

            # ------------------------------------------------
            # Empty response
            # ------------------------------------------------

            if not response.text.strip():

                print(
                    "  Empty response"
                )

                return pd.DataFrame()

            # ------------------------------------------------
            # Convert CSV response to DataFrame
            # ------------------------------------------------

            df = pd.read_csv(
                StringIO(response.text)
            )

            # ------------------------------------------------
            # Add satellite source
            # ------------------------------------------------

            if not df.empty:

                df["source"] = source

            print(
                f"  Received "
                f"{len(df):,} detections"
            )

            return df

        except Exception as exc:

            print(
                f"  Attempt "
                f"{attempt}/{MAX_RETRIES} failed: "
                f"{exc}"
            )

            if attempt < MAX_RETRIES:

                print(
                    f"  Retrying in "
                    f"{RETRY_DELAY} seconds..."
                )

                time.sleep(RETRY_DELAY)

    print(
        "  FAILED - moving to next chunk"
    )

    return pd.DataFrame()


# ============================================================
# SAVE CHUNK
# ============================================================

def save_chunk(
    df,
    source,
    start_date,
    end_date
):
    """
    Save downloaded FIRMS data as CSV.
    """

    if df.empty:

        print(
            "  No detections - "
            "nothing to save"
        )

        return False

    filename = (
        f"{source}_"
        f"{start_date:%Y%m%d}_"
        f"{end_date:%Y%m%d}.csv"
    )

    path = RAW_DIR / filename

    df.to_csv(
        path,
        index=False
    )

    print(
        f"  Saved: {path}"
    )

    return True


# ============================================================
# GET SOURCE START DATE
# ============================================================

def get_source_start_date(source):
    """
    Return the earliest date that should be requested
    for each satellite source.
    """

    if source == "VIIRS_NOAA21_NRT":

        # NOAA-21 data starts from January 17, 2024.
        return date(2024, 1, 17)

    return START_DATE


# ============================================================
# PROCESS ONE SATELLITE
# ============================================================

def process_source(source):
    """
    Download all required historical chunks
    for one satellite source.
    """

    source_start = get_source_start_date(source)

    print()
    print("=" * 70)
    print(f"SOURCE: {source}")
    print(
        f"Period: "
        f"{source_start} -> {END_DATE}"
    )
    print("=" * 70)

    downloaded_files = 0
    skipped_files = 0
    failed_chunks = 0

    for chunk_start, chunk_end in daterange_chunks(
        source_start,
        END_DATE,
        days=CHUNK_DAYS
    ):

        # ----------------------------------------------------
        # Expected filename
        # ----------------------------------------------------

        expected_file = (
            RAW_DIR
            / f"{source}_"
              f"{chunk_start:%Y%m%d}_"
              f"{chunk_end:%Y%m%d}.csv"
        )

        # ----------------------------------------------------
        # Resume support
        # ----------------------------------------------------

        if expected_file.exists():

            print(
                f"[SKIP] Already exists: "
                f"{expected_file.name}"
            )

            skipped_files += 1

            continue

        # ----------------------------------------------------
        # Download
        # ----------------------------------------------------

        df = fetch_chunk(
            source,
            chunk_start,
            chunk_end
        )

        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        if not df.empty:

            saved = save_chunk(
                df,
                source,
                chunk_start,
                chunk_end
            )

            if saved:
                downloaded_files += 1

        else:

            failed_chunks += 1

        # ----------------------------------------------------
        # Small delay between requests
        # ----------------------------------------------------

        time.sleep(REQUEST_DELAY)

    print()
    print(
        f"{source} COMPLETE"
    )

    print(
        f"  New files    : {downloaded_files}"
    )

    print(
        f"  Skipped files: {skipped_files}"
    )

    print(
        f"  Failed/empty : {failed_chunks}"
    )

    return downloaded_files


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "THERMOSCOPE - NASA FIRMS "
        "HISTORICAL DATA DOWNLOAD"
    )
    print("=" * 70)

    print(
        f"Region BBOX : {BBOX}"
    )

    print(
        f"Overall Period: "
        f"{START_DATE} -> {END_DATE}"
    )

    print(
        "Target Area  : Delhi NCR + Uttar Pradesh"
    )

    print()
    print(
        "Satellites:"
    )

    print(
        "  - VIIRS S-NPP"
    )

    print(
        "  - VIIRS NOAA-20"
    )

    print(
        "  - VIIRS NOAA-21 NRT "
        "(from 2024-01-17)"
    )

    print()

    total_files = 0

    # ========================================================
    # PROCESS ALL SOURCES
    # ========================================================

    for source in SOURCES:

        try:

            total_files += process_source(
                source
            )

        except KeyboardInterrupt:

            print()
            print(
                "DOWNLOAD INTERRUPTED BY USER"
            )

            print(
                "Already downloaded files "
                "will be preserved."
            )

            return

        except Exception as exc:

            print()
            print(
                f"[ERROR] {source}: {exc}"
            )

            print(
                "Moving to next satellite..."
            )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print(
        "DOWNLOAD PROCESS COMPLETE"
    )
    print("=" * 70)

    print(
        f"New files downloaded: "
        f"{total_files}"
    )

    print(
        f"Raw data directory: "
        f"{RAW_DIR.resolve()}"
    )

    print()
    print(
        "Next step:"
    )

    print(
        "RAW FIRMS DATA"
        " -> CLEAN / MERGE"
        " -> SPATIAL GRID"
        " -> FEATURES"
        " -> ML RISK MODEL"
        " -> TOP 10 HIGH-RISK"
    )

    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()