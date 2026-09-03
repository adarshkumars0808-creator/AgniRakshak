import json
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd


# ============================================================
# THERMOSCOPE — AUTOMATED ALERT ENGINE
#
# Compares latest FIRMS NRT detections against the
# historical risk model (risk_predictions.csv) to detect
# new critical-risk zones and escalating thermal activity.
#
# Alerts are persisted to data/processed/alerts_log.csv
# and surfaced in the dashboard's ALERTS tab.
# ============================================================


DATA_DIR = Path("data/processed")

RISK_FILE = DATA_DIR / "risk_predictions.csv"
NRT_FILE = DATA_DIR / "nrt_detections.csv"
ALERTS_FILE = DATA_DIR / "alerts_log.csv"
FIRE_TYPE_FILE = DATA_DIR / "fire_type_predictions.csv"


# ============================================================
# THRESHOLD CONFIGURATION
# ============================================================

# A grid is "new critical" if it had LOW/MODERATE risk
# historically but now has high FRP NRT detections
FRP_CRITICAL_THRESHOLD = 80
FRP_HIGH_THRESHOLD = 40
FRP_ELEVATED_THRESHOLD = 20

# Minimum NRT detections to trigger an alert in a grid
MIN_NRT_DETECTIONS_FOR_ALERT = 2

# New alert if grid had no NRT detections in the last N hours
NRT_COOLDOWN_HOURS = 12

# Escalation: compare current 24h window vs previous 24h
ESCALATION_MULTIPLIER = 2.0


# ============================================================
# LOAD DATA
# ============================================================

def load_risk_data():
    """Load historical risk predictions."""

    if not RISK_FILE.exists():
        print(f"[WARN] {RISK_FILE} not found")
        return pd.DataFrame()

    df = pd.read_csv(RISK_FILE, low_memory=False)
    df["grid_id"] = df["grid_id"].astype(str).str.strip()
    return df


def load_nrt_data():
    """Load latest NRT detections."""

    if not NRT_FILE.exists():
        print(f"[WARN] {NRT_FILE} not found")
        return pd.DataFrame()

    df = pd.read_csv(NRT_FILE, low_memory=False)
    df["grid_id"] = df["grid_id"].astype(str).str.strip()

    if "acq_date" in df.columns:
        df["acq_date"] = pd.to_datetime(
            df["acq_date"], errors="coerce"
        )

    for col in ["frp", "latitude", "longitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col], errors="coerce"
            )

    return df


def load_fire_type_data():
    """Load fire type classifications."""

    if not FIRE_TYPE_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(FIRE_TYPE_FILE, low_memory=False)
    df["grid_id"] = df["grid_id"].astype(str).str.strip()
    return df


def load_existing_alerts():
    """Load previously generated alerts."""

    if not ALERTS_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(ALERTS_FILE, low_memory=False)
    return df


# ============================================================
# ALERT DETECTION RULES
# ============================================================

def detect_critical_new_zones(
    risk_df, nrt_df, fire_type_df
):
    """
    Detect grids that were historically low-risk but
    now show high FRP NRT activity.
    """

    alerts = []

    # Aggregate NRT detections per grid
    nrt_agg = (
        nrt_df.groupby("grid_id")
        .agg(
            nrt_count=("frp", "size"),
            nrt_max_frp=("frp", "max"),
            nrt_avg_frp=("frp", "mean"),
            latest_acq=("acq_date", "max"),
            sensors=("sensor", lambda x: ", ".join(
                sorted(set(x.dropna()))
            )),
        )
        .reset_index()
    )

    # Only consider grids with enough NRT activity
    nrt_agg = nrt_agg[
        nrt_agg["nrt_count"] >= MIN_NRT_DETECTIONS_FOR_ALERT
    ]

    if nrt_agg.empty:
        return alerts

    # Merge with historical risk
    merged = nrt_agg.merge(
        risk_df[[
            "grid_id", "risk_score", "risk_level",
            "latitude", "longitude",
            "total_detections", "avg_frp",
            "max_frp", "recurrence_ratio",
        ]],
        on="grid_id",
        how="left",
        suffixes=("_nrt", "_hist"),
    )

    # Add fire type info if available
    if not fire_type_df.empty:
        ft_cols = ["grid_id", "fire_type", "fire_type_reason"]
        ft_cols = [
            c for c in ft_cols
            if c in fire_type_df.columns
        ]
        if "grid_id" in ft_cols:
            merged = merged.merge(
                fire_type_df[ft_cols],
                on="grid_id",
                how="left",
            )

    now = datetime.now(timezone.utc)

    for _, row in merged.iterrows():
        grid_id = row["grid_id"]
        nrt_frp = row.get("nrt_max_frp", 0)
        hist_risk = row.get("risk_score", 0)
        hist_risk_level = str(
            row.get("risk_level", "LOW")
        ).upper()

        alert_type = None
        severity = None
        description = None

        # -----------------------------------------------
        # RULE 1: Low historical risk + high NRT FRP
        # → New critical zone
        # -----------------------------------------------
        if (
            hist_risk < 50
            and nrt_frp >= FRP_CRITICAL_THRESHOLD
        ):
            alert_type = "NEW_CRITICAL_ZONE"
            severity = "critical"
            description = (
                f"Grid {grid_id} had {hist_risk_level} "
                f"risk (score {hist_risk:.0f}) but NRT "
                f"detections show FRP up to "
                f"{nrt_frp:.0f} MW."
            )

        # -----------------------------------------------
        # RULE 2: Escalating activity
        # Current NRT FRP significantly exceeds
        # historical average
        # -----------------------------------------------
        elif (
            nrt_frp >= FRP_HIGH_THRESHOLD
            and row.get("nrt_avg_frp", 0)
            > row.get("avg_frp_hist", 1)
            * ESCALATION_MULTIPLIER
        ):
            alert_type = "ESCALATING_ACTIVITY"
            severity = "high"
            avg_hist = row.get("avg_frp_hist", 1)
            description = (
                f"Grid {grid_id}: NRT FRP "
                f"({nrt_frp:.0f} MW) exceeds "
                f"historical avg "
                f"({avg_hist:.0f} MW) by "
                f"{ESCALATION_MULTIPLIER}x."
            )

        # -----------------------------------------------
        # RULE 3: Already high-risk + sustained NRT
        # → Persistent high-risk alert
        # -----------------------------------------------
        elif (
            hist_risk >= 75
            and row.get("nrt_count", 0) >= 5
        ):
            alert_type = "PERSISTENT_HIGH_RISK"
            severity = "critical"
            description = (
                f"Grid {grid_id}: CRITICAL risk "
                f"(score {hist_risk:.0f}) with "
                f"{int(row['nrt_count'])} NRT "
                f"detections."
            )

        # -----------------------------------------------
        # RULE 4: Elevated NRT activity
        # -----------------------------------------------
        elif nrt_frp >= FRP_ELEVATED_THRESHOLD:
            alert_type = "ELEVATED_ACTIVITY"
            severity = "medium"
            description = (
                f"Grid {grid_id}: Elevated NRT "
                f"activity (FRP {nrt_frp:.0f} MW, "
                f"{int(row['nrt_count'])} detections)."
            )

        if alert_type:
            lat = row.get("latitude_nrt") or row.get(
                "latitude", 0
            )
            lon = row.get("longitude_nrt") or row.get(
                "longitude", 0
            )

            alerts.append({
                "alert_id": (
                    f"{grid_id}_{alert_type}_"
                    f"{now.strftime('%Y%m%d_%H')}"
                ),
                "timestamp": now.isoformat(),
                "grid_id": grid_id,
                "latitude": float(lat),
                "longitude": float(lon),
                "alert_type": alert_type,
                "severity": severity,
                "description": description,
                "nrt_detections": int(
                    row.get("nrt_count", 0)
                ),
                "nrt_max_frp": float(nrt_frp),
                "historical_risk_score": float(
                    hist_risk
                ),
                "historical_risk_level": hist_risk_level,
                "sensors": row.get("sensors", ""),
                "fire_type": row.get(
                    "fire_type", "UNCLASSIFIED"
                ),
                "status": "ACTIVE",
            })

    return alerts


# ============================================================
# DEDUPLICATE AGAINST EXISTING ALERTS
# ============================================================

def deduplicate_alerts(new_alerts, existing_df):
    """
    Remove alerts that already exist for the same
    grid_id + alert_type within the cooldown window.
    """

    if existing_df.empty:
        return new_alerts

    recent_cutoff = pd.Timestamp.now("UTC").tz_localize(None) - pd.Timedelta(
        hours=NRT_COOLDOWN_HOURS
    )

    recent = existing_df.copy()
    if "timestamp" in recent.columns:
        recent["timestamp"] = pd.to_datetime(
            recent["timestamp"], errors="coerce"
        )
        recent = recent[
            recent["timestamp"] >= recent_cutoff
        ]

    existing_keys = set()
    for _, row in recent.iterrows():
        key = (
            row.get("grid_id", ""),
            row.get("alert_type", ""),
        )
        existing_keys.add(key)

    deduped = []
    for alert in new_alerts:
        key = (alert["grid_id"], alert["alert_type"])
        if key not in existing_keys:
            deduped.append(alert)
            existing_keys.add(key)

    removed = len(new_alerts) - len(deduped)
    if removed > 0:
        print(
            f"Dedup: removed {removed} alerts "
            f"within {NRT_COOLDOWN_HOURS}h cooldown"
        )

    return deduped


# ============================================================
# PERSIST ALERTS
# ============================================================

def save_alerts(new_alerts, existing_df):
    """Append new alerts to the log file."""

    if not new_alerts:
        return

    new_df = pd.DataFrame(new_alerts)

    if existing_df.empty:
        combined = new_df
    else:
        combined = pd.concat(
            [existing_df, new_df],
            ignore_index=True,
        )

    # Keep last 30 days only
    if "timestamp" in combined.columns:
        combined["timestamp"] = pd.to_datetime(
            combined["timestamp"], errors="coerce"
        )
        cutoff = pd.Timestamp.now("UTC").tz_localize(None) - pd.Timedelta(
            days=30
        )
        combined = combined[
            combined["timestamp"] >= cutoff
        ]

    combined.to_csv(ALERTS_FILE, index=False)
    print(f"Saved {len(new_alerts)} new alerts")
    print(f"Total alerts in log: {len(combined)}")


# ============================================================
# MAIN
# ============================================================

def run_alert_engine():
    """
    Full alert engine run:
    1. Load risk model + NRT data
    2. Detect new alerts
    3. Deduplicate
    4. Save
    """

    print()
    print("=" * 60)
    print("THERMOSCOPE — ALERT ENGINE")
    print(
        f"Run time: "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    print("=" * 60)

    # Load data
    risk_df = load_risk_data()
    nrt_df = load_nrt_data()
    fire_type_df = load_fire_type_data()
    existing_df = load_existing_alerts()

    if risk_df.empty:
        print("[WARN] No risk data — skipping alerts")
        return []

    if nrt_df.empty:
        print("[WARN] No NRT data — skipping alerts")
        return []

    print(
        f"Risk grids: {len(risk_df):,}"
    )
    print(
        f"NRT detections: {len(nrt_df):,}"
    )
    print(
        f"Existing alerts: {len(existing_df):,}"
    )

    # Detect
    new_alerts = detect_critical_new_zones(
        risk_df, nrt_df, fire_type_df
    )

    print(f"\nNew alerts detected: {len(new_alerts)}")

    # Deduplicate
    deduped = deduplicate_alerts(
        new_alerts, existing_df
    )

    # Save
    save_alerts(deduped, existing_df)

    # Summary
    if deduped:
        print()
        print("-" * 60)
        print("NEW ALERTS:")
        print("-" * 60)
        for a in deduped[:20]:
            print(
                f"  [{a['severity'].upper():>8}] "
                f"{a['alert_type']:<28} "
                f"grid={a['grid_id']}"
            )

    print()
    print("=" * 60)

    return deduped


# ============================================================
# GET LATEST ALERTS FOR DASHBOARD
# ============================================================

def get_active_alerts():
    """
    Return active alerts formatted for the dashboard.
    Called by dashboard.py to inject into the HTML.
    """

    df = load_existing_alerts()

    if df.empty:
        return []

    if "status" in df.columns:
        df = df[df["status"] == "ACTIVE"]

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(
            df["timestamp"], errors="coerce"
        )
        df = df.sort_values(
            "timestamp", ascending=False
        )

    # Limit to last 100 alerts
    df = df.head(100)

    # Convert to list of dicts for JSON injection
    records = df.to_dict(orient="records")

    # Clean NaN values
    for rec in records:
        for k, v in rec.items():
            if pd.isna(v):
                rec[k] = None

    return records


if __name__ == "__main__":
    run_alert_engine()
