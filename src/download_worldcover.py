import os
import requests


# ============================================================
# ESA WORLDCOVER 2021 v200 DOWNLOADER
#
# Project area:
#   Longitude: 74.5E -> 85.0E
#   Latitude : 23.5N -> 31.5N
#
# WorldCover tiles are 3 x 3 degree tiles.
# ============================================================


OUT_DIR = "data/worldcover"

BASE_URL = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com/"
    "v200/2021/map/"
)


# ------------------------------------------------------------
# Relevant 3-degree tiles for Thermoscope bbox
#
# Tile names use LOWER-LEFT corner.
# ------------------------------------------------------------

TILES = [

    # 23.5N -> 26.5N
    "N21E072",
    "N21E075",
    "N21E078",
    "N21E081",
    "N21E084",

    # 26.5N -> 29.5N
    "N24E072",
    "N24E075",
    "N24E078",
    "N24E081",
    "N24E084",

    # 29.5N -> 32.5N
    "N27E072",
    "N27E075",
    "N27E078",
    "N27E081",
    "N27E084",
]


# ------------------------------------------------------------
# CREATE OUTPUT DIRECTORY
# ------------------------------------------------------------

os.makedirs(
    OUT_DIR,
    exist_ok=True
)


# ------------------------------------------------------------
# DOWNLOAD TILE
# ------------------------------------------------------------

def download_tile(tile):

    filename = (
        "ESA_WorldCover_10m_2021_v200_"
        f"{tile}_Map.tif"
    )

    url = BASE_URL + filename

    output_path = os.path.join(
        OUT_DIR,
        filename
    )

    # --------------------------------------------------------
    # Already downloaded
    # --------------------------------------------------------

    if os.path.exists(output_path):

        size_mb = (
            os.path.getsize(output_path)
            / (1024 * 1024)
        )

        print(
            f"[SKIP] {tile} "
            f"({size_mb:.1f} MB already exists)"
        )

        return True


    print()
    print(
        f"[DOWNLOAD] {tile}"
    )

    print(
        f"URL: {url}"
    )


    try:

        response = requests.get(
            url,
            stream=True,
            timeout=180
        )

        response.raise_for_status()


        total_bytes = 0


        with open(
            output_path,
            "wb"
        ) as f:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if not chunk:
                    continue

                f.write(chunk)

                total_bytes += len(chunk)


        size_mb = (
            total_bytes
            / (1024 * 1024)
        )


        print(
            f"[SAVE] {filename} "
            f"({size_mb:.1f} MB)"
        )

        return True


    except Exception as error:

        print(
            f"[ERROR] {tile}: {error}"
        )


        if os.path.exists(output_path):

            os.remove(
                output_path
            )


        return False


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    print("=" * 60)
    print("ESA WORLDCOVER 2021 v200 DOWNLOAD")
    print("=" * 60)

    print(
        f"Tiles required: {len(TILES)}"
    )

    print(
        "Area: Delhi NCR + Uttar Pradesh + surrounding bbox"
    )

    print()


    success = 0
    failed = 0


    for index, tile in enumerate(
        TILES,
        start=1
    ):

        print(
            f"[{index}/{len(TILES)}]"
        )


        if download_tile(tile):

            success += 1

        else:

            failed += 1


    print()
    print("=" * 60)

    print(
        f"WORLDCOVER DOWNLOAD COMPLETE"
    )

    print(
        f"Successful: {success}"
    )

    print(
        f"Failed:     {failed}"
    )

    print(
        f"Output:     {OUT_DIR}"
    )

    print("=" * 60)


if __name__ == "__main__":

    main()