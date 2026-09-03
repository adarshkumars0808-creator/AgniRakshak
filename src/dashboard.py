import os
import sys
import json
import pandas as pd
import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AgniRakshak",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

DATA_DIR = os.path.join(
    PROJECT_DIR,
    "data",
    "processed",
)

HTML_FILE = os.path.join(
    BASE_DIR,
    "dashboard.html",
)

CSS_FILE = os.path.join(
    BASE_DIR,
    "style.css",
)

JS_FILE = os.path.join(
    BASE_DIR,
    "script.js",
)

RISK_FILE = os.path.join(
    DATA_DIR,
    "risk_predictions.csv",
)

DAILY_FILE = os.path.join(
    DATA_DIR,
    "daily_activity.csv",
)

FIRE_TYPE_FILE = os.path.join(
    DATA_DIR,
    "fire_type_predictions.csv",
)

VERIFIED_SITES_FILE = os.path.join(
    DATA_DIR,
    "verified_fire_sites.csv",
)

RISK_ZONES_FILE = os.path.join(
    DATA_DIR,
    "risk_zones.csv",
)

NRT_FILE = os.path.join(
    DATA_DIR,
    "nrt_detections.csv",
)

ALERTS_FILE = os.path.join(
    DATA_DIR,
    "alerts_log.csv",
)


# ============================================================
# LOAD HTML + CSS + JS
# ============================================================

def load_dashboard():

    if not os.path.exists(HTML_FILE):
        raise FileNotFoundError(
            f"Missing dashboard HTML file:\n{HTML_FILE}"
        )

    if not os.path.exists(CSS_FILE):
        raise FileNotFoundError(
            f"Missing dashboard CSS file:\n{CSS_FILE}"
        )

    if not os.path.exists(JS_FILE):
        raise FileNotFoundError(
            f"Missing dashboard JavaScript file:\n{JS_FILE}"
        )

    with open(
        HTML_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        page_html = f.read()

    with open(
        CSS_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        css = f.read()

    with open(
        JS_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        js = f.read()

    page_html = page_html.replace(
        '<link rel="stylesheet" href="style.css">',
        "",
    )

    page_html = page_html.replace(
        "<link rel='stylesheet' href='style.css'>",
        "",
    )

    page_html = page_html.replace(
        "</head>",
        f"<style>{css}</style></head>",
        1,
    )

    page_html = page_html.replace(
        '<script src="script.js"></script>',
        f"<script>{js}</script>",
        1,
    )

    page_html = page_html.replace(
        "<script src='script.js'></script>",
        f"<script>{js}</script>",
        1,
    )

    return page_html


# ============================================================
# SAFE JSON SERIALIZATION
# ============================================================

def dataframe_to_json(df):

    if df is None or df.empty:
        return "[]"

    df = df.copy()

    df = df.replace(
        [float("inf"), float("-inf")],
        pd.NA,
    )

    try:
        return df.to_json(
            orient="records",
            date_format="iso",
            date_unit="ms",
            force_ascii=False,
            default_handler=str,
        )

    except Exception:

        df = df.astype(object)

        df = df.where(
            pd.notna(df),
            None,
        )

        records = df.to_dict(
            orient="records"
        )

        return json.dumps(
            records,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
            default=str,
        )


# ============================================================
# FIRE TYPE NORMALIZATION
# ============================================================

def normalize_fire_type(value):

    if pd.isna(value):
        return "UNCLASSIFIED"

    value = str(value).strip().upper()

    value = (
        value
        .replace("-", "_")
        .replace("/", "_")
        .replace(" ", "_")
    )

    aliases = {

        "INDUSTRIAL":
            "INDUSTRIAL_PERSISTENT",

        "PERSISTENT":
            "INDUSTRIAL_PERSISTENT",

        "INDUSTRIAL_PERSISTENT_SOURCE":
            "INDUSTRIAL_PERSISTENT",

        "INDUSTRIAL_SOURCE":
            "INDUSTRIAL_PERSISTENT",

        "AGRICULTURAL":
            "AGRICULTURAL_BURNING",

        "CROP_BURNING":
            "AGRICULTURAL_BURNING",

        "CROP_FIRE":
            "AGRICULTURAL_BURNING",

        "FOREST":
            "FOREST_WILDFIRE",

        "WILDFIRE":
            "FOREST_WILDFIRE",

        "FOREST_FIRE":
            "FOREST_WILDFIRE",

        "WILDLAND_FIRE":
            "FOREST_WILDFIRE",

        "UNKNOWN":
            "UNCLASSIFIED",

        "NONE":
            "UNCLASSIFIED",

        "NULL":
            "UNCLASSIFIED",

        "":
            "UNCLASSIFIED",
    }

    # Already-canonical values (e.g. "INDUSTRIAL_PERSISTENT" as
    # produced directly by classify_fire_type.py) must pass through
    # unchanged — they are not in the alias table above, which only
    # maps SHORTER/alternate spellings onto the canonical names.
    canonical_types = {
        "INDUSTRIAL_PERSISTENT",
        "AGRICULTURAL_BURNING",
        "FOREST_WILDFIRE",
        "UNCLASSIFIED",
    }

    if value in canonical_types:
        return value

    return aliases.get(
        value,
        "UNCLASSIFIED",
    )


# ============================================================
# AUTO-UPDATE — runs on every page load if data is stale
# ============================================================
# Refresh button runs: auto_update.py then fetch_nrt.py
import subprocess

qp = st.query_params
if qp.get("refresh", "") == "1":
    st.cache_data.clear()
    try:
        subprocess.run([sys.executable, os.path.join(BASE_DIR, "src", "auto_update.py")],
                       capture_output=True, text=True, timeout=300, cwd=str(BASE_DIR))
        subprocess.run([sys.executable, os.path.join(BASE_DIR, "src", "fetch_nrt.py")],
                       capture_output=True, text=True, timeout=120, cwd=str(BASE_DIR))
    except Exception:
        pass
    st.query_params.clear()
    st.rerun()


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_data():

    if not os.path.exists(RISK_FILE):
        raise FileNotFoundError(
            f"Missing risk prediction file:\n{RISK_FILE}"
        )

    if not os.path.exists(DAILY_FILE):
        raise FileNotFoundError(
            f"Missing daily activity file:\n{DAILY_FILE}"
        )

    try:
        risk_df = pd.read_csv(
            RISK_FILE,
            low_memory=False,
        )
    except Exception as e:
        raise RuntimeError(
            f"Could not read risk_predictions.csv:\n{e}"
        )

    try:
        daily_df = pd.read_csv(
            DAILY_FILE,
            low_memory=False,
        )
    except Exception as e:
        raise RuntimeError(
            f"Could not read daily_activity.csv:\n{e}"
        )

    return risk_df, daily_df


# ============================================================
# LOAD MAIN DATA
# ============================================================

try:

    risk_df, daily_df = load_data()

except Exception as e:

    st.error(
        "AgniRakshak data load failed."
    )

    st.code(str(e))

    st.stop()


# ============================================================
# NORMALIZE GRID ID
# ============================================================

if "grid_id" in risk_df.columns:

    risk_df["grid_id"] = (
        risk_df["grid_id"]
        .astype(str)
        .str.strip()
    )


# ============================================================
# NUMERIC COLUMNS
# ============================================================

numeric_columns = [

    "latitude",
    "longitude",

    "total_detections",
    "active_days",

    "avg_frp",
    "max_frp",

    "recurrence_ratio",
    "persistent_months",

    "multi_satellite_activity",

    "detections_30d",
    "detections_90d",

    "recent_activity_ratio",
    "frp_intensity_ratio",
    "persistence_ratio",

    "risk_score",
    "risk_rank",
]


for col in numeric_columns:

    if col in risk_df.columns:

        risk_df[col] = pd.to_numeric(
            risk_df[col],
            errors="coerce",
        )


# ============================================================
# NORMALIZE RISK LEVEL
# ============================================================

if "risk_level" in risk_df.columns:

    risk_df["risk_level"] = (
        risk_df["risk_level"]
        .fillna("LOW")
        .astype(str)
        .str.strip()
        .str.upper()
        .replace(
            {
                "CRITICAL RISK": "CRITICAL",
                "HIGH RISK": "HIGH",
                "MEDIUM": "MODERATE",
                "MEDIUM RISK": "MODERATE",
                "MODERATE RISK": "MODERATE",
                "LOW RISK": "LOW",
            }
        )
    )


# ============================================================
# FIRE TYPE DATA
# ============================================================

fire_type_loaded = False

if os.path.exists(FIRE_TYPE_FILE):

    try:

        fire_df = pd.read_csv(
            FIRE_TYPE_FILE,
            low_memory=False,
        )

        if "grid_id" in fire_df.columns:

            fire_df["grid_id"] = (
                fire_df["grid_id"]
                .astype(str)
                .str.strip()
            )

        fire_type_cols = [
            "grid_id",
            "fire_type",
            "fire_type_confidence",
            "fire_type_reason",
            "coordinate_source",
            "display_latitude",
            "display_longitude",
            "display_site_name",
            "display_site_type",
        ]

        available_cols = [
            c
            for c in fire_type_cols
            if c in fire_df.columns
        ]

        if "grid_id" in available_cols:

            fire_df = fire_df[
                available_cols
            ].copy()

            fire_df = fire_df.dropna(
                subset=["grid_id"]
            )

            fire_df = fire_df.drop_duplicates(
                subset=["grid_id"],
                keep="last",
            )

            for col in [
                "fire_type",
                "fire_type_confidence",
                "fire_type_reason",
                "coordinate_source",
                "display_latitude",
                "display_longitude",
                "display_site_name",
                "display_site_type",
            ]:

                if col in risk_df.columns:
                    risk_df = risk_df.drop(
                        columns=[col]
                    )

            rows_before = len(risk_df)

            risk_df = risk_df.merge(
                fire_df,
                on="grid_id",
                how="left",
                validate="one_to_one",
            )

            if len(risk_df) != rows_before:

                st.warning(
                    "Fire-type merge changed grid row count."
                )

            fire_type_loaded = (
                "fire_type" in risk_df.columns
            )

    except Exception as e:

        st.warning(
            "Fire-type classification could not be merged."
        )

        st.caption(str(e))


# ============================================================
# FIRE TYPE DEFAULTS
# ============================================================

if not fire_type_loaded:

    risk_df["fire_type"] = "UNCLASSIFIED"

    risk_df["fire_type_confidence"] = 0.0

    risk_df["fire_type_reason"] = (
        "Fire-type classification has not been run yet."
    )

else:

    risk_df["fire_type"] = (
        risk_df["fire_type"]
        .apply(normalize_fire_type)
    )

    if "fire_type_confidence" not in risk_df.columns:
        risk_df["fire_type_confidence"] = 0.0

    risk_df["fire_type_confidence"] = pd.to_numeric(
        risk_df["fire_type_confidence"],
        errors="coerce",
    ).fillna(0.0)

    confidence_mask = (
        risk_df["fire_type_confidence"] >= 0
    ) & (
        risk_df["fire_type_confidence"] <= 1
    )

    risk_df.loc[
        confidence_mask,
        "fire_type_confidence",
    ] *= 100

    risk_df["fire_type_confidence"] = (
        risk_df["fire_type_confidence"]
        .clip(0, 100)
        .round(1)
    )

    if "fire_type_reason" not in risk_df.columns:

        risk_df["fire_type_reason"] = (
            "No classification reason available."
        )

    risk_df["fire_type_reason"] = (
        risk_df["fire_type_reason"]
        .fillna(
            "No classification reason available."
        )
        .astype(str)
    )


# ============================================================
# GIS SITE DISPLAY DEFAULTS
# ============================================================
# coordinate_source / display_* come from classify_fire_type.py
# when it matched a grid cell to a real OSM industrial/
# agricultural/forest site. If fire-type classification wasn't
# loaded, or a given row didn't match a real site, these stay
# empty and the dashboard falls back to the raw grid centroid.

for col in [
    "coordinate_source",
    "display_site_name",
    "display_site_type",
]:
    if col not in risk_df.columns:
        risk_df[col] = ""
    risk_df[col] = risk_df[col].fillna("").astype(str)

for col in ["display_latitude", "display_longitude"]:
    if col not in risk_df.columns:
        risk_df[col] = None
    risk_df[col] = pd.to_numeric(risk_df[col], errors="coerce")


# ============================================================
# DAILY DATA
# ============================================================

if "date" in daily_df.columns:

    daily_df["date"] = pd.to_datetime(
        daily_df["date"],
        errors="coerce",
    )

    daily_df = daily_df.dropna(
        subset=["date"]
    )

    daily_df["date"] = (
        daily_df["date"]
        .dt.strftime("%Y-%m-%d")
    )


if "detections" in daily_df.columns:

    daily_df["detections"] = pd.to_numeric(
        daily_df["detections"],
        errors="coerce",
    ).fillna(0)


if "avg_frp" in daily_df.columns:

    daily_df["avg_frp"] = pd.to_numeric(
        daily_df["avg_frp"],
        errors="coerce",
    ).fillna(0)


daily_df = daily_df.replace(
    [float("inf"), float("-inf")],
    pd.NA,
)


# ============================================================
# REQUIRED RISK COLUMNS
# ============================================================

required_risk_columns = [

    "grid_id",
    "latitude",
    "longitude",

    "total_detections",
    "active_days",

    "avg_frp",
    "max_frp",

    "recurrence_ratio",
    "persistent_months",

    "detections_30d",
    "detections_90d",

    "risk_score",
    "risk_level",

]


missing_risk = [
    c
    for c in required_risk_columns
    if c not in risk_df.columns
]


if missing_risk:

    st.error(
        "Missing columns in risk_predictions.csv:"
    )

    st.code(
        ", ".join(missing_risk)
    )

    st.stop()


# ============================================================
# CLEAN GRID DATA
# ============================================================

risk_df = risk_df.dropna(
    subset=[
        "grid_id",
        "latitude",
        "longitude",
    ]
)


risk_df["grid_id"] = (
    risk_df["grid_id"]
    .astype(str)
    .str.strip()
)


risk_df = risk_df.drop_duplicates(
    subset=["grid_id"],
    keep="last",
)


# ============================================================
# FINAL NUMERIC SAFETY
# ============================================================

for col in numeric_columns:

    if col in risk_df.columns:

        risk_df[col] = pd.to_numeric(
            risk_df[col],
            errors="coerce",
        )


# ============================================================
# MAP ACTIVITY FLAG
# ============================================================
#
# IMPORTANT:
#
# total_detections represents historical FIRMS activity.
# It must NOT be used to call a cell "currently active".
#
# Map precision is based on recent activity.
#
# detections_30d > 0
#         OR
# detections_90d > 0
#
# The JS will primarily use detections_30d.
#
# ============================================================

risk_df["map_recent_activity"] = (
    (
        risk_df["detections_30d"].fillna(0)
        > 0
    )
    |
    (
        risk_df["detections_90d"].fillna(0)
        > 0
    )
)


# ============================================================
# DEBUG COUNTS
# ============================================================

historical_grid_count = len(risk_df)

recent_grid_count = int(
    risk_df["map_recent_activity"].sum()
)


st.session_state[
    "thermoscope_grid_count"
] = historical_grid_count

st.session_state[
    "thermoscope_recent_grid_count"
] = recent_grid_count

st.session_state[
    "thermoscope_fire_type_loaded"
] = fire_type_loaded


# ============================================================
# FIRE TYPE COUNTS
# ============================================================

fire_type_counts = (
    risk_df["fire_type"]
    .value_counts()
    .to_dict()
)


st.session_state[
    "thermoscope_fire_type_counts"
] = fire_type_counts


# ============================================================
# LOAD VERIFIED, MERGED FIRE SITES
# ============================================================
# This comes from verify_and_merge_sites.py — it re-checks every
# INDUSTRIAL/MINING label against real ESA WorldCover land cover
# (proximity to an industrial area alone was found to be wrong
# ~92% of the time) and merges grid cells within 8km of each
# other into single site markers. Only verified sites are in this
# file; nothing unverified is shown on the fire-type map layer.

if os.path.exists(VERIFIED_SITES_FILE):

    fire_sites_df = pd.read_csv(
        VERIFIED_SITES_FILE,
        low_memory=False,
    )

    for col in ["site_name", "verification_reason", "landcover_class", "risk_level"]:
        if col in fire_sites_df.columns:
            fire_sites_df[col] = fire_sites_df[col].fillna("").astype(str)

    for col in ["latitude", "longitude", "total_detections", "avg_frp", "max_frp", "risk_score", "named_facility_distance_km"]:
        if col in fire_sites_df.columns:
            fire_sites_df[col] = pd.to_numeric(fire_sites_df[col], errors="coerce")

else:

    fire_sites_df = pd.DataFrame()

    st.caption(
        "ℹ️ data/processed/verified_fire_sites.csv not found — run "
        "verify_and_merge_sites.py to enable the verified fire-type "
        "map layer. Showing risk data only."
    )


# ============================================================
# LOAD REGIONAL RISK ZONES
# ============================================================
# This comes from merge_risk_zones.py — it re-bins the raw
# 26,891 risk_predictions.csv grid cells onto a ~30km regional
# grid so the map's discrete Risk Grid Markers layer shows a
# manageable number of distinct zones. The heatmap layer still
# uses the full-resolution risk_df below for a smooth surface.

if os.path.exists(RISK_ZONES_FILE):

    risk_zones_df = pd.read_csv(
        RISK_ZONES_FILE,
        low_memory=False,
    )

    if "risk_level" in risk_zones_df.columns:
        risk_zones_df["risk_level"] = (
            risk_zones_df["risk_level"].fillna("").astype(str).str.upper()
        )

    for col in ["latitude", "longitude", "risk_score", "avg_risk_score", "total_detections", "avg_frp", "max_frp"]:
        if col in risk_zones_df.columns:
            risk_zones_df[col] = pd.to_numeric(risk_zones_df[col], errors="coerce")

else:

    risk_zones_df = pd.DataFrame()

    st.caption(
        "ℹ️ data/processed/risk_zones.csv not found — run "
        "merge_risk_zones.py to enable the regional risk map layer. "
        "Falling back to the full raw grid (26,891 cells)."
    )


# ============================================================
# PREPARE JSON
# ============================================================

grid_json = dataframe_to_json(
    risk_df
)

daily_json = dataframe_to_json(
    daily_df
)

fire_sites_json = dataframe_to_json(
    fire_sites_df
)

risk_zones_json = dataframe_to_json(
    risk_zones_df
)


# ============================================================
# LOAD NRT DATA
# ============================================================
# Near-real-time FIRMS detections from fetch_nrt.py.
# This file may not exist until the first NRT fetch runs.

if os.path.exists(NRT_FILE):

    try:

        nrt_df = pd.read_csv(
            NRT_FILE,
            low_memory=False,
        )

        if "acq_date" in nrt_df.columns:
            nrt_df["acq_date"] = pd.to_datetime(
                nrt_df["acq_date"],
                errors="coerce",
            )
            nrt_df["acq_date"] = (
                nrt_df["acq_date"]
                .dt.strftime("%Y-%m-%d %H:%M")
            )

        for col in ["latitude", "longitude", "frp", "confidence"]:
            if col in nrt_df.columns:
                nrt_df[col] = pd.to_numeric(
                    nrt_df[col], errors="coerce"
                )

    except Exception as e:

        st.warning(
            f"Could not load NRT detections: {e}"
        )
        nrt_df = pd.DataFrame()

else:

    nrt_df = pd.DataFrame()

nrt_json = dataframe_to_json(nrt_df)


# ============================================================
# LOAD ALERTS DATA
# ============================================================
# Alerts generated by alert_engine.py.

if os.path.exists(ALERTS_FILE):

    try:

        alerts_df = pd.read_csv(
            ALERTS_FILE,
            low_memory=False,
        )

        if "timestamp" in alerts_df.columns:
            alerts_df["timestamp"] = pd.to_datetime(
                alerts_df["timestamp"],
                errors="coerce",
            )
            alerts_df["timestamp"] = (
                alerts_df["timestamp"]
                .dt.strftime("%Y-%m-%d %H:%M")
            )

        for col in ["latitude", "longitude", "nrt_max_frp", "historical_risk_score"]:
            if col in alerts_df.columns:
                alerts_df[col] = pd.to_numeric(
                    alerts_df[col], errors="coerce"
                )

    except Exception as e:

        st.warning(
            f"Could not load alerts log: {e}"
        )
        alerts_df = pd.DataFrame()

else:

    alerts_df = pd.DataFrame()

alerts_json = dataframe_to_json(alerts_df)

active_alert_count = 0
if not alerts_df.empty and "status" in alerts_df.columns:
    active_alert_count = int(
        (alerts_df["status"] == "ACTIVE").sum()
    )


# ============================================================
# LOAD DASHBOARD
# ============================================================

try:

    dashboard_html = load_dashboard()

except Exception as e:

    st.error(
        "AgniRakshak dashboard files could not be loaded."
    )

    st.code(str(e))

    st.stop()


# ============================================================
# INJECT DATA
# ============================================================

nrt_timestamp = ""
if os.path.exists(os.path.join(DATA_DIR, "nrt_latest_timestamp.txt")):
    try:
        nrt_timestamp = open(
            os.path.join(DATA_DIR, "nrt_latest_timestamp.txt")
        ).read().strip()
    except Exception:
        nrt_timestamp = ""

nrt_detections_count = len(nrt_df) if not nrt_df.empty else 0

# Load forecast data
FORECAST_FILE = os.path.join(DATA_DIR, "fire_forecast.json")
try:
    with open(FORECAST_FILE, encoding="utf-8") as f:
        forecast_data = json.load(f)
    forecast_json = json.dumps(forecast_data)
except Exception:
    forecast_data = {}
    forecast_json = "{}"


data_script = f"""
<script>
window.THERMOSCOPE_DATA = {{
    gridData: {grid_json},
    dailyData: {daily_json},
    fireSiteData: {fire_sites_json},
    riskZoneData: {risk_zones_json},
    nrtData: {nrt_json},
    alertsData: {alerts_json},
    historicalGridCount: {historical_grid_count},
    recentGridCount: {recent_grid_count},
    nrtDetectionsCount: {nrt_detections_count},
    nrtTimestamp: "{nrt_timestamp}",
    activeAlertCount: {active_alert_count}
}};
</script>
"""


if "</head>" in dashboard_html:

    # Inject forecast data as a separate script BEFORE the main data script
    # to avoid issues with large JSON inside the main data blob
    forecast_script = '<script>window._FC_DATA = ' + forecast_json + ';</script>\n'
    dashboard_html = dashboard_html.replace(
        "</head>",
        forecast_script + data_script + "</head>",
        1,
    )

else:

    dashboard_html = (
        data_script
        + dashboard_html
    )


# ============================================================
# HIDE STREAMLIT CHROME — seamless single frame
# ============================================================

st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer[data-testid="stFooter"] {visibility: hidden;}
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
            max-width: 100% !important;
        }
        [data-testid="stAppViewContainer"] {
            background-color: #080c14 !important;
        }
        .stDeployButton {display: none;}
        div[data-testid="stToolbar"] {display: none;}
        div[data-testid="stStatusWidget"] {display: none;}
        section[data-testid="stSidebar"] {display: none;}
    </style>
    <script>
    // Kill ONLY the outer Streamlit scrollbar, not the inner iframe content
    (function() {
      function killOuterScroll() {
        // Target ONLY Streamlit wrapper elements — NOT body/html, NOT iframe contents
        var targets = [
          document.querySelector('[data-testid="stApp"]'),
          document.querySelector('.main .block-container'),
          document.querySelector('section.main'),
          document.querySelector('[data-testid="stAppViewContainer"]')
        ];
        targets.forEach(function(el) {
          if (!el) return;
          el.style.overflow = 'hidden';
          el.style.height = '100vh';
          el.style.maxHeight = '100vh';
        });
        // Targeted scrollbar kill — only Streamlit containers, NOT * wildcard
        var css = document.getElementById('kill-outer-scroll');
        if (!css) {
          css = document.createElement('style');
          css.id = 'kill-outer-scroll';
          css.textContent = '
            [data-testid="stApp"]::-webkit-scrollbar, 
            [data-testid="stApp"] > div::-webkit-scrollbar,
            .main .block-container::-webkit-scrollbar,
            section.main::-webkit-scrollbar,
            [data-testid="stAppViewContainer"]::-webkit-scrollbar {
              display: none !important; 
              width: 0 !important; 
              height: 0 !important;
            }
            [data-testid="stApp"], 
            [data-testid="stApp"] > div,
            .main .block-container,
            section.main,
            [data-testid="stAppViewContainer"] {
              scrollbar-width: none !important;
              -ms-overflow-style: none !important;
            }
          ';
          document.head.appendChild(css);
        }
      }
      killOuterScroll();
      setTimeout(killOuterScroll, 500);
      setTimeout(killOuterScroll, 1500);
      setTimeout(killOuterScroll, 3000);
      var observer = new MutationObserver(function() {
        var app = document.querySelector('[data-testid="stApp"]');
        if (app && app.scrollHeight > app.clientHeight + 50) {
          killOuterScroll();
        }
      });
      observer.observe(document.body, { childList: true, subtree: true });
    })();
    </script>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# BUILD CREDITS (moved from top captions to footer)
# ============================================================

credits_lines = []
credits_lines.append(
    f"🔥 AgniRakshak — "
    f"{historical_grid_count:,} historical FIRMS grid cells · "
    f"{recent_grid_count:,} recent activity cells"
)

if not fire_sites_df.empty:
    site_counts = fire_sites_df["fire_type"].value_counts().to_dict()
    credits_lines.append(
        f"✓ {len(fire_sites_df):,} land-cover-verified, regionally-aggregated "
        f"fire-type sites (" + ", ".join(f"{v:,} {k}" for k, v in site_counts.items()) + ")"
    )

if not risk_zones_df.empty:
    credits_lines.append(
        f"✓ {len(risk_zones_df):,} regional risk zones "
        f"(aggregated from {historical_grid_count:,} raw grid cells)"
    )

credits_html = "<br>".join(credits_lines)
dashboard_html = dashboard_html.replace("{{CREDITS}}", credits_html)



# ============================================================
# RENDER
# ============================================================

st.components.v1.html(
    dashboard_html,
    height=900,
    scrolling=True,
)