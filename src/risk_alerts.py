import pandas as pd


# ============================================================
# THERMOSCOPE - FIRE RISK ALERT ENGINE
# ============================================================

PREDICTION_FILE = "data/delhi_risk_predictions.csv"


def load_predictions():
    """Load Thermoscope risk prediction data."""
    return pd.read_csv(PREDICTION_FILE)


def generate_alert(row):
    """
    Generate an operational alert for one grid cell.
    """

    grid_id = row.get("grid_id", "Unknown")
    risk_score = float(row.get("risk_score", 0))

    detection_count = int(row.get("detection_count", 0))
    active_days = int(row.get("active_days", 0))
    max_frp = float(row.get("max_frp", 0))
    satellite_agreement = int(row.get("satellite_agreement", 0))

    # --------------------------------------------------------
    # Risk classification
    # --------------------------------------------------------

    if risk_score >= 0.75:
        risk_level = "HIGH"
        priority = "CRITICAL"
        message = "Immediate attention recommended."

    elif risk_score >= 0.45:
        risk_level = "MEDIUM"
        priority = "WARNING"
        message = "Area should be monitored closely."

    else:
        risk_level = "LOW"
        priority = "NORMAL"
        message = "No immediate action required."

    # --------------------------------------------------------
    # Alert reasons
    # --------------------------------------------------------

    reasons = []

    if detection_count >= 2:
        reasons.append(
            f"Repeated fire detections ({detection_count})."
        )
    elif detection_count == 1:
        reasons.append(
            "Fire detection observed in this grid."
        )

    if active_days >= 2:
        reasons.append(
            f"Fire activity observed across {active_days} days."
        )

    if max_frp >= 5:
        reasons.append(
            f"Elevated fire intensity (max FRP {max_frp:.2f})."
        )
    elif max_frp > 0:
        reasons.append(
            f"Measurable fire intensity (max FRP {max_frp:.2f})."
        )

    if satellite_agreement >= 1:
        reasons.append(
            "Satellite observations support the detection."
        )

    return {
        "grid_id": grid_id,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "priority": priority,
        "message": message,
        "reasons": reasons,
    }


def generate_all_alerts():
    """Generate alerts for every prediction grid."""

    df = load_predictions()

    alerts = []

    for _, row in df.iterrows():
        alerts.append(generate_alert(row))

    return alerts


def print_alerts():
    """Display Thermoscope alerts in the terminal."""

    alerts = generate_all_alerts()

    print("=" * 70)
    print("THERMOSCOPE - FIRE RISK ALERTS")
    print("=" * 70)

    for alert in alerts:

        print("\n" + "-" * 70)

        print(f"Grid       : {alert['grid_id']}")
        print(f"Risk Level : {alert['risk_level']}")
        print(f"Risk Score : {alert['risk_score']:.4f}")
        print(f"Priority   : {alert['priority']}")
        print(f"Status     : {alert['message']}")

        print("\nAlert Factors:")

        if alert["reasons"]:
            for reason in alert["reasons"]:
                print(f"  • {reason}")
        else:
            print("  • No significant indicators detected.")

    print("\n" + "=" * 70)
def get_high_priority_alerts():
    """
    Return only HIGH-risk alerts.

    Useful for dashboards, maps, APIs,
    and future notification systems.
    """

    alerts = generate_all_alerts()

    high_priority = []

    for alert in alerts:
        if alert["risk_level"] == "HIGH":
            high_priority.append(alert)

    return high_priority

if __name__ == "__main__":
    print_alerts()

    print("\n")
    print("=" * 70)
    print("HIGH PRIORITY ALERTS")
    print("=" * 70)

    high_alerts = get_high_priority_alerts()

    if high_alerts:
        for alert in high_alerts:
            print(
                f"Grid: {alert['grid_id']} | "
                f"Score: {alert['risk_score']:.4f} | "
                f"Priority: {alert['priority']}"
            )
    else:
        print("No HIGH-risk grids detected.")