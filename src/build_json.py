"""build_json.py - Convert CSV data to JSON for static hosting."""
import os, json, math
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def safe_json(df):
    if df is None or df.empty:
        return []
    df = df.copy()
    df = df.replace([float("inf"), float("-inf")], pd.NA)
    df = df.astype(object).where(pd.notna(df), None)
    return json.loads(df.to_json(orient="records", date_format="iso", default_handler=str))


def normalize_fire_type(value):
    if pd.isna(value):
        return "UNCLASSIFIED"
    v = str(value).strip().upper().replace("-", "_").replace("/", "_").replace(" ", "_")
    aliases = {
        "INDUSTRIAL": "INDUSTRIAL_PERSISTENT", "PERSISTENT": "INDUSTRIAL_PERSISTENT",
        "AGRICULTURAL": "AGRICULTURAL_BURNING", "CROP_BURNING": "AGRICULTURAL_BURNING",
        "FOREST": "FOREST_WILDFIRE", "WILDFIRE": "FOREST_WILDFIRE",
        "FOREST_FIRE": "FOREST_WILDFIRE", "UNKNOWN": "UNCLASSIFIED", "": "UNCLASSIFIED",
    }
    canonical = {"INDUSTRIAL_PERSISTENT", "AGRICULTURAL_BURNING", "FOREST_WILDFIRE", "UNCLASSIFIED"}
    if v in canonical:
        return v
    return aliases.get(v, "UNCLASSIFIED")


def build():
    print("=" * 60)
    print("BUILD JSON - Converting CSVs to JSON for static hosting")
    print("=" * 60)
    ts = datetime.now(timezone.utc).isoformat()

    risk_file = DATA_DIR / "risk_predictions.csv"
    if risk_file.exists():
        risk_df = pd.read_csv(risk_file, low_memory=False)
        risk_df["grid_id"] = risk_df["grid_id"].astype(str).str.strip()
        risk_df["risk_level"] = risk_df["risk_level"].fillna("LOW").astype(str).str.strip().str.upper()

        # Merge fire-type classification + display coordinates from
        # fire_type_predictions.csv (produced by classify_fire_type.py)
        # BEFORE any fire_type column is created, so the merge does not
        # collide (which would produce fire_type_x/fire_type_y).
        # Without this, every grid would come out as UNCLASSIFIED.
        ft_file = DATA_DIR / "fire_type_predictions.csv"
        FT_MERGE_COLS = [
            "fire_type", "fire_type_confidence", "fire_type_reason",
            "display_latitude", "display_longitude", "display_site_name",
            "display_site_type", "coordinate_source", "display_coordinate_distance_km",
        ]
        if ft_file.exists():
            try:
                ft_df = pd.read_csv(ft_file, usecols=["grid_id"] + FT_MERGE_COLS, low_memory=False)
                ft_df["grid_id"] = ft_df["grid_id"].astype(str).str.strip()
                ft_df = ft_df.drop_duplicates(subset=["grid_id"], keep="last")
                matched = int(ft_df["fire_type"].notna().sum())
                risk_df = risk_df.merge(ft_df, on="grid_id", how="left")
                print(f"  Merged fire-type data for {matched:,} grids")
            except Exception as exc:
                print(f"  [WARN] Could not merge fire_type_predictions.csv: {exc}")

        if "fire_type" in risk_df.columns:
            risk_df["fire_type"] = risk_df["fire_type"].apply(normalize_fire_type)
        else:
            risk_df["fire_type"] = "UNCLASSIFIED"
        num_cols = ["latitude", "longitude", "total_detections", "active_days", "avg_frp", "max_frp",
                     "recurrence_ratio", "persistent_months", "detections_30d", "detections_90d",
                     "risk_score", "fire_type_confidence"]
        for c in num_cols:
            if c in risk_df.columns:
                risk_df[c] = pd.to_numeric(risk_df[c], errors="coerce")
        risk_df = risk_df.dropna(subset=["grid_id", "latitude", "longitude"]).drop_duplicates(subset=["grid_id"], keep="last")

        for c in ["coordinate_source", "display_site_name", "display_site_type"]:
            if c in risk_df.columns:
                risk_df[c] = risk_df[c].fillna("").astype(str)
        for c in ["display_latitude", "display_longitude"]:
            if c in risk_df.columns:
                risk_df[c] = pd.to_numeric(risk_df[c], errors="coerce")
        if "fire_type_reason" not in risk_df.columns:
            risk_df["fire_type_reason"] = ""
        risk_df["fire_type_reason"] = risk_df["fire_type_reason"].fillna("").astype(str)
        if "fire_type_confidence" not in risk_df.columns:
            risk_df["fire_type_confidence"] = 0.0
        risk_df["fire_type_confidence"] = pd.to_numeric(risk_df["fire_type_confidence"], errors="coerce").fillna(0.0)
        mask = (risk_df["fire_type_confidence"] >= 0) & (risk_df["fire_type_confidence"] <= 1)
        risk_df.loc[mask, "fire_type_confidence"] *= 100
        risk_df["fire_type_confidence"] = risk_df["fire_type_confidence"].clip(0, 100).round(1)
        risk_df["map_recent_activity"] = ((risk_df["detections_30d"].fillna(0) > 0) | (risk_df["detections_90d"].fillna(0) > 0))
        historical_count = len(risk_df)
        recent_count = int(risk_df["map_recent_activity"].sum())
        grid_json = safe_json(risk_df)
        print(f"  grid_data.json: {len(grid_json)} rows")
    else:
        grid_json = []
        historical_count = 0
        recent_count = 0
        print("  WARNING: risk_predictions.csv not found")

    daily_file = DATA_DIR / "daily_activity.csv"
    daily_json = safe_json(pd.read_csv(daily_file, low_memory=False)) if daily_file.exists() else []
    if daily_file.exists() and daily_json:
        print(f"  daily_data.json: {len(daily_json)} rows")

    sites_file = DATA_DIR / "verified_fire_sites.csv"
    sites_json = safe_json(pd.read_csv(sites_file, low_memory=False)) if sites_file.exists() else []
    if sites_file.exists():
        print(f"  fire_sites.json: {len(sites_json)} rows")

    zones_file = DATA_DIR / "risk_zones.csv"
    if zones_file.exists():
        zones_df = pd.read_csv(zones_file, low_memory=False)
        if "risk_level" in zones_df.columns:
            zones_df["risk_level"] = zones_df["risk_level"].fillna("").astype(str).str.upper()
        zones_json = safe_json(zones_df)
        print(f"  risk_zones.json: {len(zones_json)} rows")
    else:
        zones_json = []

    nrt_file = DATA_DIR / "nrt_detections.csv"
    if nrt_file.exists():
        nrt_df = pd.read_csv(nrt_file, low_memory=False)
        if "acq_date" in nrt_df.columns:
            nrt_df["acq_date"] = pd.to_datetime(nrt_df["acq_date"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
        for c in ["latitude", "longitude", "frp", "confidence"]:
            if c in nrt_df.columns:
                nrt_df[c] = pd.to_numeric(nrt_df[c], errors="coerce")
        nrt_json = safe_json(nrt_df)
        print(f"  nrt_data.json: {len(nrt_json)} rows")
    else:
        nrt_json = []

    alerts_file = DATA_DIR / "alerts_log.csv"
    if alerts_file.exists():
        alerts_df = pd.read_csv(alerts_file, low_memory=False)
        if "timestamp" in alerts_df.columns:
            alerts_df["timestamp"] = pd.to_datetime(alerts_df["timestamp"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
        alerts_json = safe_json(alerts_df)
        active_count = int((alerts_df["status"] == "ACTIVE").sum()) if "status" in alerts_df.columns else 0
        print(f"  alerts_data.json: {len(alerts_json)} rows")
    else:
        alerts_json = []
        active_count = 0

    nrt_ts_file = DATA_DIR / "nrt_latest_timestamp.txt"
    nrt_timestamp = nrt_ts_file.read_text().strip() if nrt_ts_file.exists() else ""

    (DATA_DIR / "grid_data.json").write_text(json.dumps(grid_json, default=str))
    (DATA_DIR / "daily_data.json").write_text(json.dumps(daily_json, default=str))
    (DATA_DIR / "fire_sites.json").write_text(json.dumps(sites_json, default=str))
    (DATA_DIR / "risk_zones.json").write_text(json.dumps(zones_json, default=str))
    (DATA_DIR / "nrt_data.json").write_text(json.dumps(nrt_json, default=str))
    (DATA_DIR / "alerts_data.json").write_text(json.dumps(alerts_json, default=str))

    fire_type_counts = {}
    for row in grid_json:
        ft = row.get("fire_type", "UNCLASSIFIED")
        fire_type_counts[ft] = fire_type_counts.get(ft, 0) + 1

    meta = {
        "generated_at": ts,
        "historical_grid_count": historical_count,
        "recent_grid_count": recent_count,
        "nrt_detections_count": len(nrt_json),
        "nrt_timestamp": nrt_timestamp,
        "active_alert_count": active_count,
        "fire_type_counts": fire_type_counts,
    }
    (DATA_DIR / "metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"BUILD COMPLETE: {historical_count:,} grids, {len(nrt_json):,} NRT, {active_count} alerts")


if __name__ == "__main__":
    build()
