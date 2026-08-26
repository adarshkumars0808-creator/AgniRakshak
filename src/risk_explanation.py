import pandas as pd


# ============================================================
# THERMOSCOPE - EXPLAINABLE FIRE RISK ENGINE
# ============================================================

PREDICTION_FILE = "data/delhi_risk_predictions.csv"


def load_predictions():
    """Load Thermoscope risk prediction data."""
    return pd.read_csv(PREDICTION_FILE)


def explain_grid(row):
    """
    Generate a human-readable explanation
    for one grid cell.
    """

    detection_count = row.get("detection_count", 0)
    active_days = row.get("active_days", 0)
    avg_frp = row.get("avg_frp", 0)
    max_frp = row.get("max_frp", 0)
    satellite_agreement = row.get("satellite_agreement", 0)
    risk_score = row.get("risk_score", 0)

    # --------------------------------------------------------
    # Convert risk score into risk level
    # --------------------------------------------------------

    if risk_score >= 0.75:
        risk_level = "HIGH"
    elif risk_score >= 0.45:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    reasons = []

    # --------------------------------------------------------
    # Detection recurrence
    # --------------------------------------------------------

    if detection_count >= 3:
        reasons.append(
            f"Repeated fire detections were observed "
            f"({detection_count} detections)."
        )

    elif detection_count == 2:
        reasons.append(
            "The grid shows repeated fire activity with 2 detections."
        )

    elif detection_count == 1:
        reasons.append(
            "A fire detection was observed in this grid."
        )

    # --------------------------------------------------------
    # Active days
    # --------------------------------------------------------

    if active_days >= 3:
        reasons.append(
            f"Fire activity occurred across "
            f"{active_days} different days."
        )

    elif active_days == 2:
        reasons.append(
            "Fire activity was observed on multiple days."
        )

    # --------------------------------------------------------
    # FRP
    # --------------------------------------------------------

    if max_frp >= 10:
        reasons.append(
            f"High maximum Fire Radiative Power was recorded "
            f"({max_frp:.2f})."
        )

    elif max_frp >= 5:
        reasons.append(
            f"Moderate fire intensity was recorded "
            f"(max FRP {max_frp:.2f})."
        )

    elif max_frp > 0:
        reasons.append(
            f"Detected fire activity has measurable FRP "
            f"({max_frp:.2f})."
        )

    # --------------------------------------------------------
    # Satellite agreement
    # --------------------------------------------------------

    if satellite_agreement >= 1:
        reasons.append(
            "Satellite observations support the detected fire activity."
        )

    # --------------------------------------------------------
    # Risk interpretation
    # --------------------------------------------------------

    if risk_level == "HIGH":

        summary = (
            "HIGH RISK: Multiple fire-related indicators "
            "suggest elevated fire risk."
        )

    elif risk_level == "MEDIUM":

        summary = (
            "MEDIUM RISK: The grid shows measurable fire "
            "activity and requires attention."
        )

    else:

        summary = (
            "LOW RISK: Current indicators suggest "
            "relatively lower fire risk."
        )

    return {
        "grid_id": row.get("grid_id", "Unknown"),
        "risk_level": risk_level,
        "risk_score": risk_score,
        "summary": summary,
        "reasons": reasons,
    }


def explain_all():
    """Generate explanations for all prediction grids."""

    df = load_predictions()

    explanations = []

    for _, row in df.iterrows():

        explanations.append(
            explain_grid(row)
        )

    return explanations


def print_explanations():
    """Print explanations in a readable terminal format."""

    explanations = explain_all()

    print("=" * 65)
    print("THERMOSCOPE - EXPLAINABLE FIRE RISK ANALYSIS")
    print("=" * 65)

    for item in explanations:

        print("\n" + "-" * 65)

        print(f"Grid: {item['grid_id']}")
        print(f"Risk Level: {item['risk_level']}")
        print(f"Risk Score: {item['risk_score']}")

        print("\nExplanation:")
        print(item["summary"])

        print("\nContributing Factors:")

        if item["reasons"]:

            for reason in item["reasons"]:
                print(f"  • {reason}")

        else:

            print("  • No significant indicators available.")

    print("\n" + "=" * 65)


if __name__ == "__main__":
    print_explanations()