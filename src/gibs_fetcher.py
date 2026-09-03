"""
gibs_fetcher.py — Fetch satellite imagery from NASA GIBS WMS for a specific location.

Uses the WMS GetMap endpoint (no API key needed) to return a cropped
satellite image around any lat/lon coordinate. Retries with older dates
if the most recent imagery is cloud-covered or unavailable.

Usage:
    from src.gibs_fetcher import fetch_gibs_image, fetch_esri_image

    # Fetch yesterday's MODIS true-color image around a fire location
    path = fetch_gibs_image(lat=28.6139, lon=77.2090, span=0.25)

    # Fetch high-res Esri reference imagery (not date-stamped)
    path = fetch_esri_image(lat=28.6139, lon=77.2090, span=0.05)
"""

import os
import io
import datetime
import requests
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, '..', 'data', 'evidence')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _yesterday(offset=1):
    """Return a YYYY-MM-DD string for `offset` days before today."""
    d = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=offset)
    return d.strftime('%Y-%m-%d')


def _build_gibs_url(lat, lon, span, date_str, width=500, height=500):
    """
    Build a NASA GIBS WMS GetMap URL for a cropped region around (lat, lon).

    WMS BBOX format: min_lon,min_lat,max_lon,max_lat (EPSG:4326)
    """
    min_lon = lon - span
    max_lon = lon + span
    min_lat = lat - span
    max_lat = lat + span

    params = {
        'SERVICE': 'WMS',
        'VERSION': '1.1.1',
        'REQUEST': 'GetMap',
        'LAYERS': 'MODIS_Terra_CorrectedReflectance_TrueColor',
        'TIME': date_str,
        'BBOX': f'{min_lon},{min_lat},{max_lon},{max_lat}',
        'SRS': 'EPSG:4326',
        'WIDTH': str(width),
        'HEIGHT': str(height),
        'FORMAT': 'image/jpeg',
    }
    query = '&'.join(f'{k}={v}' for k, v in params.items())
    return f'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?{query}'


def _build_gibs_thermal_url(lat, lon, span, date_str, width=500, height=500):
    """Build a GIBS WMS URL for MODIS thermal anomalies overlay."""
    min_lon = lon - span
    max_lon = lon + span
    min_lat = lat - span
    max_lat = lat + span

    params = {
        'SERVICE': 'WMS',
        'VERSION': '1.1.1',
        'REQUEST': 'GetMap',
        'LAYERS': 'MODIS_Terra_Thermal_Anomalies_375m_All',
        'TIME': date_str,
        'BBOX': f'{min_lon},{min_lat},{max_lon},{max_lat}',
        'SRS': 'EPSG:4326',
        'WIDTH': str(width),
        'HEIGHT': str(height),
        'FORMAT': 'image/png',
        'TRANSPARENT': 'TRUE',
    }
    query = '&'.join(f'{k}={v}' for k, v in params.items())
    return f'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?{query}'


def _is_blank_image(img_bytes, threshold=250):
    """
    Quick heuristic: decode the image and check if it's mostly uniform
    (cloud-covered or ocean = blank). Returns True if >90% of pixels
    are within `threshold` brightness of each other.
    """
    try:
        img = Image.open(io.BytesIO(img_bytes))
        img = img.convert('L')  # grayscale
        pixels = list(img.getdata())
        if len(pixels) < 100:
            return True
        mean_val = sum(pixels) / len(pixels)
        uniform_count = sum(1 for p in pixels if abs(p - mean_val) < 30)
        return (uniform_count / len(pixels)) > 0.90
    except Exception:
        return False


def fetch_gibs_image(lat, lon, span=0.25, size=500, out_file=None, max_retries=3):
    """
    Fetch a NASA GIBS MODIS Terra True Color satellite image for a location.

    Args:
        lat:        Latitude of the center point
        lon:        Longitude of the center point
        span:       Half-width of the bounding box in degrees (0.25 ≈ 28km)
        size:       Output image size in pixels (square)
        out_file:   Output file path (auto-generated if None)
        max_retries: How many days back to try if imagery is blank/cloudy

    Returns:
        dict with keys:
            'path':     Path to saved image file
            'date':     Acquisition date (YYYY-MM-DD)
            'url':      The GIBS URL that was fetched
            'age_hours': Approximate age in hours from now
            'source':   'NASA_GIBS_MODIS'
            'blank':    True if image appears cloud-covered/blank
        None on complete failure.
    """
    if out_file is None:
        out_file = os.path.join(
            OUTPUT_DIR,
            f'gibs_{lat:.4f}_{lon:.4f}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        )

    for attempt in range(1, max_retries + 1):
        date_str = _yesterday(offset=attempt)
        url = _build_gibs_url(lat, lon, span, date_str, size, size)
        age_hours = attempt * 24

        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                print(f'[GIBS] Attempt {attempt}: HTTP {resp.status_code} for {date_str}')
                continue

            img_bytes = resp.content
            if len(img_bytes) < 500:
                print(f'[GIBS] Attempt {attempt}: Response too small ({len(img_bytes)} bytes) for {date_str}')
                continue

            blank = _is_blank_image(img_bytes)
            if blank and attempt < max_retries:
                print(f'[GIBS] Attempt {attempt}: Image appears blank/cloudy for {date_str}, trying older date...')
                continue

            # Save the image
            with open(out_file, 'wb') as f:
                f.write(img_bytes)

            return {
                'path': out_file,
                'date': date_str,
                'url': url,
                'age_hours': age_hours,
                'source': 'NASA_GIBS_MODIS',
                'blank': blank,
            }

        except requests.exceptions.Timeout:
            print(f'[GIBS] Attempt {attempt}: Timeout for {date_str}')
        except requests.exceptions.RequestException as e:
            print(f'[GIBS] Attempt {attempt}: Request error: {e}')
        except Exception as e:
            print(f'[GIBS] Attempt {attempt}: Unexpected error: {e}')

    # All retries failed — return None
    print(f'[GIBS] All {max_retries} attempts failed for ({lat}, {lon})')
    return None


def fetch_gibs_thermal_overlay(lat, lon, span=0.25, size=500, date_str=None):
    """
    Fetch a GIBS MODIS thermal anomalies overlay image (transparent PNG).
    Red/orange dots = detected thermal hotspots.
    """
    if date_str is None:
        date_str = _yesterday(offset=1)

    url = _build_gibs_thermal_url(lat, lon, span, date_str, size, size)
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200 and len(resp.content) > 500:
            out_file = os.path.join(
                OUTPUT_DIR,
                f'gibs_thermal_{lat:.4f}_{lon:.4f}_{date_str}.png'
            )
            with open(out_file, 'wb') as f:
                f.write(resp.content)
            return {'path': out_file, 'date': date_str, 'url': url}
    except Exception as e:
        print(f'[GIBS] Thermal overlay failed: {e}')
    return None


def fetch_esri_image(lat, lon, span=0.05, width=800, height=800, out_file=None):
    """
    Fetch high-res Esri World Imagery for a location (NOT date-stamped).
    Use as fallback when GIBS is unavailable or higher resolution is needed.

    Note: Esri imagery may be years old — it does not indicate current conditions.
    """
    min_lon = lon - span
    max_lon = lon + span
    min_lat = lat - span
    max_lat = lat + span

    url = (
        f'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export'
        f'?bbox={min_lon},{min_lat},{max_lon},{max_lat}'
        f'&bboxSR=4326&imageSR=4326'
        f'&size={width},{height}'
        f'&format=png32&f=image'
    )

    if out_file is None:
        out_file = os.path.join(
            OUTPUT_DIR,
            f'esri_{lat:.4f}_{lon:.4f}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        )

    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200 and len(resp.content) > 500:
            with open(out_file, 'wb') as f:
                f.write(resp.content)
            return {
                'path': out_file,
                'url': url,
                'source': 'Esri_World_Imagery',
                'note': 'Reference imagery — may not reflect current conditions',
            }
    except Exception as e:
        print(f'[Esri] Fetch failed: {e}')
    return None


# ============================================================
# CLI — quick test
# ============================================================
if __name__ == '__main__':
    import sys
    lat = float(sys.argv[1]) if len(sys.argv) > 1 else 28.6139
    lon = float(sys.argv[2]) if len(sys.argv) > 2 else 77.2090

    print(f'Fetching GIBS image for ({lat}, {lon})...')
    result = fetch_gibs_image(lat, lon)
    if result:
        print(f'  Saved: {result["path"]}')
        print(f'  Date:  {result["date"]} (~{result["age_hours"]}h ago)')
        print(f'  Blank: {result["blank"]}')
    else:
        print('  Failed — trying Esri fallback...')
        result = fetch_esri_image(lat, lon)
        if result:
            print(f'  Saved: {result["path"]}')
            print(f'  Note:  {result["note"]}')
