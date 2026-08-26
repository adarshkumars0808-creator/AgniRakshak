import pandas as pd


# ============================================================
# THERMOSCOPE - EXPLAINABLE FIRE RISK ENGINE
# STEP 5
# USING SIH PROVIDED NASA FIRMS DATA
# ============================================================

PREDICTION_FILE = "data/delhi_risk_predictions.csv"


# ============================================================
# 1. LOAD PREDICTIONS
# ============================================================

def load_predictions():
    """Load Thermoscope risk prediction data."""

    return pd.read_csv(PREDICTION_FILE)


# ============================================================
# 2. RISK LEVEL
# ============================================================

def get_risk_level(score):
    """Convert risk score into LOW / MEDIUM / HIGH."""

    score = float(score)

    if score >= 0.75:
        return "HIGH"

    elif score >= 0.45:
        return "MEDIUM"

    else:
        return "LOW"


# ============================================================
# 3. EXPLAIN RECURRENCE
# ============================================================

def explain_recurrence(row):

    active_days = int(
        row.get("active_days", 0)
    )

    detection_count = int(
        row.get("detection_count", 0)
    )

    recurrence_score = float(
        row.get("recurrence_score", 0)
    )

    reasons = []

    if active_days >= 2:

        reasons.append(
            f"Fire activity was detected across "
            f"{active_days} different days."
        )

    elif active_days == 1:

        reasons.append(
            "Fire activity was detected on one observation day."
        )

    if detection_count >= 2:

        reasons.append(
            f"The grid recorded {detection_count} fire detections, "
            "indicating repeated activity."
        )

    elif detection_count == 1:

        reasons.append(
            "One fire detection was recorded in this grid."
        )

    return reasons, recurrence_score


# ============================================================
# 4. EXPLAIN FRP
# ============================================================

def explain_frp(row):

    avg_frp = float(
        row.get("avg_frp", 0)
    )

    max_frp = float(
        row.get("max_frp", 0)
    )

    frp_intensity = float(
        row.get("frp_intensity", 0)
    )

    reasons = []

    if max_frp > 0:

        reasons.append(
            f"Maximum Fire Radiative Power (FRP) was "
            f"{max_frp:.2f}, with an average FRP of "
            f"{avg_frp:.2f}."
        )

    if frp_intensity >= 0.75:

        reasons.append(
            "The observed FRP is relatively high compared "
            "with the strongest grid in the current dataset."
        )

    elif frp_intensity >= 0.45:

        reasons.append(
            "The observed FRP indicates moderate fire intensity "
            "relative to the current dataset."
        )

    else:

        reasons.append(
            "The observed FRP is relatively lower compared "
            "with the strongest grid in the current dataset."
        )

    return reasons, frp_intensity


# ============================================================
# 5. EXPLAIN SATELLITE EVIDENCE
# ============================================================

def explain_satellite(row):

    satellite_agreement = int(
        row.get("satellite_agreement", 0)
    )

    satellite_score = float(
        row.get("satellite_score", 0)
    )

    satellite_source_count = int(
        row.get("satellite_source_count", 1)
    )

    reasons = []

    if satellite_agreement >= 1:

        reasons.append(
            f"Fire activity was supported by "
            f"{satellite_source_count} satellite/source identifiers."
        )

    else:

        reasons.append(
            "Only one satellite/source identifier is available "
            "in the current SIH dataset, so independent satellite "
            "agreement cannot be established."
        )

    return reasons, satellite_score


# ============================================================
# 6. EXPLAIN DETECTION STRENGTH
# ============================================================

def explain_detection(row):

    detection_count = int(
        row.get("detection_count", 0)
    )

    detection_score = float(
        row.get("detection_score", 0)
    )

    reasons = []

    if detection_score >= 0.75:

        reasons.append(
            "Detection frequency is high relative to the "
            "other grids in the current dataset."
        )

    elif detection_score >= 0.45:

        reasons.append(
            "Detection frequency is moderate relative to "
            "the other grids."
        )

    else:

        reasons.append(
            "Detection frequency is comparatively lower "
            "than the strongest grid."
        )

    return reasons, detection_score


# ============================================================
# 7. MAIN GRID EXPLANATION
# ============================================================

def explain_grid(row):
    """
    Generate a human-readable explanation for one grid cell.
    """

    risk_score = float(
        row.get("risk_score", 0)
    )

    risk_percentage = float(
        row.get(
            "risk_percentage",
            risk_score * 100
        )
    )

    risk_level = get_risk_level(
        risk_score
    )

    # --------------------------------------------------------
    # Individual evidence
    # --------------------------------------------------------

    recurrence_reasons, recurrence_score = (
        explain_recurrence(row)
    )

    frp_reasons, frp_intensity = (
        explain_frp(row)
    )

    satellite_reasons, satellite_score = (
        explain_satellite(row)
    )

    detection_reasons, detection_score = (
        explain_detection(row)
    )

    # --------------------------------------------------------
    # Combine explanations
    # --------------------------------------------------------

    reasons = []

    reasons.extend(
        recurrence_reasons
    )

    reasons.extend(
        frp_reasons
    )

    reasons.extend(
        satellite_reasons
    )

    reasons.extend(
        detection_reasons
    )

    # --------------------------------------------------------
    # Overall interpretation
    # --------------------------------------------------------

    if risk_level == "HIGH":

        summary = (
            f"HIGH RISK ({risk_percentage:.2f}%): "
            "The grid has comparatively strong fire-activity "
            "indicators based on recurrence, FRP intensity and "
            "detection frequency."
        )

    elif risk_level == "MEDIUM":

        summary = (
            f"MEDIUM RISK ({risk_percentage:.2f}%): "
            "The grid shows measurable fire activity and "
            "should be monitored."
        )

    else:

        summary = (
            f"LOW RISK ({risk_percentage:.2f}%): "
            "The current indicators show comparatively "
            "lower fire activity."
        )

    # --------------------------------------------------------
    # Return structured explanation
    # --------------------------------------------------------

    return {

        "grid_id": row.get(
            "grid_id",
            "Unknown"
        ),

        "risk_level": risk_level,

        "risk_score": round(
            risk_score,
            4
        ),

        "risk_percentage": round(
            risk_percentage,
            2
        ),

        "recurrence_score": round(
            recurrence_score,
            4
        ),

        "frp_intensity": round(
            frp_intensity,
            4
        ),

        "satellite_score": round(
            satellite_score,
            4
        ),

        "detection_score": round(
            detection_score,
            4
        ),

        "summary": summary,

        "reasons": reasons
    }


# ============================================================
# 8. EXPLAIN ALL GRIDS
# ============================================================

def explain_all():

    df = load_predictions()

    explanations = []

    for _, row in df.iterrows():

        explanations.append(
            explain_grid(row)
        )

    return explanations


# ============================================================
# 9. PRINT EXPLANATIONS
# ============================================================

def print_explanations():

    explanations = explain_all()

    print("=" * 70)
    print(
        "THERMOSCOPE - EXPLAINABLE FIRE RISK ANALYSIS"
    )
    print(
        "USING SIH PROVIDED NASA FIRMS DATA"
    )
    print("=" * 70)

    for item in explanations:

        print("\n" + "-" * 70)

        print(
            f"Grid: {item['grid_id']}"
        )

        print(
            f"Risk Level: {item['risk_level']}"
        )

        print(
            f"Risk Score: {item['risk_score']}"
        )

        print(
            f"Risk Percentage: "
            f"{item['risk_percentage']:.2f}%"
        )

        print("\nScore Components:")

        print(
            f"  Recurrence: "
            f"{item['recurrence_score']:.3f}"
        )

        print(
            f"  FRP Intensity: "
            f"{item['frp_intensity']:.3f}"
        )

        print(
            f"  Satellite Evidence: "
            f"{item['satellite_score']:.3f}"
        )

        print(
            f"  Detection Activity: "
            f"{item['detection_score']:.3f}"
        )

        print("\nOverall Explanation:")

        print(
            f"  {item['summary']}"
        )

        print("\nContributing Factors:")

        if item["reasons"]:

            for reason in item["reasons"]:

                print(
                    f"  • {reason}"
                )

        else:

            print(
                "  • No significant indicators available."
            )

    print("\n" + "=" * 70)
    print(
        "EXPLAINABLE RISK ANALYSIS COMPLETE"
    )
    print("=" * 70)


# ============================================================
# 10. RUN
# ============================================================

if __name__ == "__main__":

    print_explanations()