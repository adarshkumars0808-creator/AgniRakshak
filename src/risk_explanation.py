import os
import pandas as pd


# ============================================================
# THERMOSCOPE - EXPLAINABLE FIRE RISK ENGINE
# STEP 6
# USING SIH PROVIDED NASA FIRMS DATA
# SUPPORTS SIH + LIVE PROCESSED DATA
# ============================================================


SIH_PREDICTION_FILE = "data/delhi_risk_predictions.csv"
LIVE_PREDICTION_FILE = "data/delhi_risk_predictions_live.csv"


# ============================================================
# 1. LOAD PREDICTIONS
# ============================================================

def load_predictions(mode="auto"):
    """
    Load Thermoscope risk predictions.

    mode:
        auto -> live file if available, otherwise SIH
        live -> live predictions only
        sih  -> SIH predictions only
    """

    if mode == "live":

        if not os.path.exists(LIVE_PREDICTION_FILE):
            raise FileNotFoundError(
                f"Live prediction file not found: "
                f"{LIVE_PREDICTION_FILE}"
            )

        return pd.read_csv(LIVE_PREDICTION_FILE)

    if mode == "sih":

        if not os.path.exists(SIH_PREDICTION_FILE):
            raise FileNotFoundError(
                f"SIH prediction file not found: "
                f"{SIH_PREDICTION_FILE}"
            )

        return pd.read_csv(SIH_PREDICTION_FILE)

    # --------------------------------------------------------
    # AUTO MODE
    # --------------------------------------------------------

    if os.path.exists(LIVE_PREDICTION_FILE):

        print(
            "Explainability mode: LIVE PROCESSED DATA"
        )

        return pd.read_csv(LIVE_PREDICTION_FILE)

    if os.path.exists(SIH_PREDICTION_FILE):

        print(
            "Explainability mode: SIH DATASET"
        )

        return pd.read_csv(SIH_PREDICTION_FILE)

    raise FileNotFoundError(
        "No Thermoscope prediction file found."
    )


# ============================================================
# 2. SAFE VALUE HELPERS
# ============================================================

def safe_float(value, default=0.0):

    try:

        if pd.isna(value):
            return default

        return float(value)

    except (ValueError, TypeError):

        return default


def safe_int(value, default=0):

    try:

        if pd.isna(value):
            return default

        return int(float(value))

    except (ValueError, TypeError):

        return default


# ============================================================
# 3. RISK LEVEL
# ============================================================

def get_risk_level(score):

    score = safe_float(score)

    if score >= 0.75:
        return "HIGH"

    elif score >= 0.45:
        return "MEDIUM"

    return "LOW"


# ============================================================
# 4. EXPLAIN RECURRENCE
# ============================================================

def explain_recurrence(row):

    active_days = safe_int(
        row.get("active_days", 0)
    )

    detection_count = safe_int(
        row.get("detection_count", 0)
    )

    recurrence_score = safe_float(
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
            f"The grid recorded {detection_count} fire "
            "detections, indicating repeated activity."
        )

    elif detection_count == 1:

        reasons.append(
            "One fire detection was recorded in this grid."
        )

    if not reasons:

        reasons.append(
            "No significant recurrence information "
            "is available for this grid."
        )

    return reasons, recurrence_score


# ============================================================
# 5. EXPLAIN FRP
# ============================================================

def explain_frp(row):

    avg_frp = safe_float(
        row.get("avg_frp", 0)
    )

    max_frp = safe_float(
        row.get("max_frp", 0)
    )

    frp_intensity = safe_float(
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
            "FRP intensity is relatively high compared "
            "with the strongest grid in the current dataset."
        )

    elif frp_intensity >= 0.45:

        reasons.append(
            "FRP intensity indicates moderate fire intensity "
            "relative to the current dataset."
        )

    else:

        reasons.append(
            "FRP intensity is comparatively lower than "
            "the strongest grid."
        )

    return reasons, frp_intensity


# ============================================================
# 6. EXPLAIN SATELLITE EVIDENCE
# ============================================================

def explain_satellite(row):

    satellite_agreement = safe_int(
        row.get("satellite_agreement", 0)
    )

    satellite_score = safe_float(
        row.get("satellite_score", 0)
    )

    satellite_source_count = safe_int(
        row.get("satellite_source_count", 1),
        default=1
    )

    reasons = []

    if satellite_agreement >= 1:

        reasons.append(
            f"Fire activity was supported by "
            f"{satellite_source_count} satellite/source "
            "identifiers."
        )

    elif satellite_source_count > 1:

        reasons.append(
            f"Multiple satellite/source identifiers "
            f"are present ({satellite_source_count})."
        )

    else:

        reasons.append(
            "The current dataset does not provide enough "
            "independent satellite evidence to establish "
            "multi-satellite agreement."
        )

    return reasons, satellite_score


# ============================================================
# 7. EXPLAIN DETECTION STRENGTH
# ============================================================

def explain_detection(row):

    detection_count = safe_int(
        row.get("detection_count", 0)
    )

    detection_score = safe_float(
        row.get("detection_score", 0)
    )

    reasons = []

    if detection_score >= 0.75:

        reasons.append(
            "Detection frequency is high relative to "
            "other grids in the current dataset."
        )

    elif detection_score >= 0.45:

        reasons.append(
            "Detection frequency is moderate relative "
            "to other grids."
        )

    else:

        reasons.append(
            "Detection frequency is comparatively lower "
            "than the strongest grid."
        )

    if detection_count > 0:

        reasons.append(
            f"Total detections in this grid: "
            f"{detection_count}."
        )

    return reasons, detection_score


# ============================================================
# 8. EXPLAIN GRID
# ============================================================

def explain_grid(row):
    """
    Generate a human-readable explanation for one grid cell.
    """

    risk_score = safe_float(
        row.get("risk_score", 0)
    )

    risk_percentage = safe_float(
        row.get(
            "risk_percentage",
            risk_score * 100
        )
    )

    risk_level = get_risk_level(
        risk_score
    )

    # --------------------------------------------------------
    # Evidence
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
    # Combine reasons
    # --------------------------------------------------------

    reasons = []

    reasons.extend(recurrence_reasons)
    reasons.extend(frp_reasons)
    reasons.extend(satellite_reasons)
    reasons.extend(detection_reasons)

    # --------------------------------------------------------
    # Overall interpretation
    # --------------------------------------------------------

    if risk_level == "HIGH":

        summary = (
            f"HIGH RISK ({risk_percentage:.2f}%): "
            "The grid shows comparatively strong fire-activity "
            "indicators based on the available Thermoscope "
            "features."
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
            "The available indicators show comparatively "
            "lower fire activity."
        )

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
# 9. EXPLAIN ALL GRIDS
# ============================================================

def explain_all(mode="auto"):

    df = load_predictions(
        mode=mode
    )

    explanations = []

    for _, row in df.iterrows():

        explanations.append(
            explain_grid(row)
        )

    return explanations


# ============================================================
# 10. PRINT EXPLANATIONS
# ============================================================

def print_explanations(mode="auto"):

    explanations = explain_all(
        mode=mode
    )

    print("=" * 70)

    print(
        "THERMOSCOPE - EXPLAINABLE FIRE RISK ANALYSIS"
    )

    print(
        "USING SIH PROVIDED NASA FIRMS DATA"
    )

    print("=" * 70)

    print(
        f"\nTotal grids analysed: "
        f"{len(explanations)}"
    )

    for item in explanations:

        print("\n" + "-" * 70)

        print(
            f"Grid: {item['grid_id']}"
        )

        print(
            f"Risk Level: {item['risk_level']}"
        )

        print(
            f"Risk Score: {item['risk_score']:.4f}"
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
# 11. ENTRY POINT
# ============================================================

if __name__ == "__main__":

    print_explanations(
        mode="auto"
    )