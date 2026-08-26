import pandas as pd
import numpy as np

# ============================================================
# THERMOSCOPE - STEP 4
# EXPLAINABLE FIRE RISK SCORING + RISK EXPLANATION
# USING SIH PROVIDED NASA FIRMS DATA
# ============================================================

INPUT_FILE = "data/delhi_risk_features_live.csv"
OUTPUT_FILE = "data/delhi_risk_predictions_live.csv"

print("=" * 70)
print("THERMOSCOPE - EXPLAINABLE FIRE RISK SCORING")
print("USING SIH PROVIDED NASA FIRMS DATA")
print("=" * 70)


# ------------------------------------------------------------
# 1. Load engineered risk features
# ------------------------------------------------------------

try:
    df = pd.read_csv(INPUT_FILE)

except FileNotFoundError:
    raise FileNotFoundError(
        f"\nERROR: Input file not found:\n{INPUT_FILE}\n\n"
        "Please run risk_features.py first."
    )

print("\nLoaded grid cells:", len(df))


# ------------------------------------------------------------
# 2. Check required features
# ------------------------------------------------------------

required_columns = [
    "grid_id",
    "grid_lat",
    "grid_lon",
    "detection_count",
    "active_days",
    "avg_frp",
    "max_frp",
    "recurrence_score",
    "frp_intensity",
    "repeat_detection_score",
    "activity_score"
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:

    print("\nERROR: Missing required columns:")
    print(missing_columns)

    raise ValueError(
        "Required risk features are missing. "
        "Please check risk_features.py output."
    )


# ------------------------------------------------------------
# 3. Clean numeric features
# ------------------------------------------------------------

numeric_columns = [
    "detection_count",
    "active_days",
    "avg_frp",
    "max_frp",
    "recurrence_score",
    "frp_intensity",
    "repeat_detection_score",
    "activity_score"
]

for column in numeric_columns:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# Replace invalid / missing values

df[numeric_columns] = (
    df[numeric_columns]
    .replace([np.inf, -np.inf], np.nan)
    .fillna(0)
)


# ------------------------------------------------------------
# 4. Validate score ranges
# ------------------------------------------------------------

score_columns = [
    "recurrence_score",
    "frp_intensity",
    "repeat_detection_score",
    "activity_score"
]

for column in score_columns:

    df[column] = (
        df[column]
        .clip(0, 1)
    )


# ------------------------------------------------------------
# 5. Explainable risk components
# ------------------------------------------------------------
#
# Thermoscope risk model:
#
#   Recurrence / Persistence = 45%
#   FRP Intensity            = 35%
#   Repeat Detection         = 20%
#
# Each contribution is calculated separately so that the
# final risk score can be explained to the user.
#
# Satellite agreement is NOT included because the current
# SIH-provided dataset contains one satellite source.
# ------------------------------------------------------------

df["recurrence_contribution"] = (
    0.45 * df["recurrence_score"]
)

df["frp_contribution"] = (
    0.35 * df["frp_intensity"]
)

df["repeat_detection_contribution"] = (
    0.20 * df["repeat_detection_score"]
)


# ------------------------------------------------------------
# 6. Calculate explainable risk score
# ------------------------------------------------------------

df["risk_score"] = (
    df["recurrence_contribution"]
    + df["frp_contribution"]
    + df["repeat_detection_contribution"]
)


# Keep score between 0 and 1

df["risk_score"] = (
    df["risk_score"]
    .clip(0, 1)
)


# ------------------------------------------------------------
# 7. Consistency check against Step 3 activity_score
# ------------------------------------------------------------
#
# Step 3 already creates activity_score using the same
# weighted components.
#
# We check whether Step 4 reproduces that score.
# This is a validation check, NOT a model accuracy claim.
# ------------------------------------------------------------

df["score_difference"] = (
    df["risk_score"] - df["activity_score"]
).abs()


# Floating-point tolerance

CONSISTENCY_TOLERANCE = 0.000001

df["score_consistent"] = (
    df["score_difference"]
    <= CONSISTENCY_TOLERANCE
)


inconsistent_count = (
    (~df["score_consistent"])
    .sum()
)


# ------------------------------------------------------------
# 8. Convert risk score to percentage
# ------------------------------------------------------------

df["risk_percentage"] = (
    df["risk_score"] * 100
).round(2)


# ------------------------------------------------------------
# 9. Risk classification
# ------------------------------------------------------------
#
# Score >= 0.75  → HIGH
# Score >= 0.45  → MEDIUM
# Score <  0.45  → LOW
#
# These are Thermoscope classification thresholds.
# ------------------------------------------------------------

def classify_risk(score):

    if score >= 0.75:
        return "HIGH"

    elif score >= 0.45:
        return "MEDIUM"

    else:
        return "LOW"


df["risk_category"] = (
    df["risk_score"]
    .apply(classify_risk)
)


# ------------------------------------------------------------
# 10. Risk priority
# ------------------------------------------------------------
#
# Highest risk score gets priority 1.
# Equal scores receive the same priority.
# ------------------------------------------------------------

df["risk_priority"] = (
    df["risk_score"]
    .rank(
        ascending=False,
        method="dense"
    )
    .astype(int)
)


# ------------------------------------------------------------
# 11. Determine dominant risk factor
# ------------------------------------------------------------
#
# The largest weighted contribution is used to explain
# the primary factor influencing the risk score.
# ------------------------------------------------------------

def get_dominant_factor(row):

    contributions = {
        "Recurrence / Persistence": row["recurrence_contribution"],
        "FRP Intensity": row["frp_contribution"],
        "Repeat Detection": row["repeat_detection_contribution"]
    }

    return max(
        contributions,
        key=contributions.get
    )


df["dominant_factor"] = (
    df.apply(
        get_dominant_factor,
        axis=1
    )
)


# ------------------------------------------------------------
# 12. Generate human-readable risk explanation
# ------------------------------------------------------------

def generate_explanation(row):

    category = row["risk_category"]

    recurrence = row["recurrence_score"]
    frp = row["frp_intensity"]
    repeat = row["repeat_detection_score"]

    dominant = row["dominant_factor"]

    if category == "HIGH":

        explanation = (
            f"HIGH risk driven primarily by {dominant}. "
            f"Recurrence score: {recurrence:.2f}, "
            f"FRP intensity: {frp:.2f}, "
            f"repeat detection score: {repeat:.2f}."
        )

    elif category == "MEDIUM":

        explanation = (
            f"MEDIUM risk with {dominant} as the strongest "
            f"contributing factor. "
            f"Recurrence score: {recurrence:.2f}, "
            f"FRP intensity: {frp:.2f}, "
            f"repeat detection score: {repeat:.2f}."
        )

    else:

        explanation = (
            f"LOW risk based on the current observed fire "
            f"activity. "
            f"Recurrence score: {recurrence:.2f}, "
            f"FRP intensity: {frp:.2f}, "
            f"repeat detection score: {repeat:.2f}."
        )

    return explanation


df["risk_explanation"] = (
    df.apply(
        generate_explanation,
        axis=1
    )
)


# ------------------------------------------------------------
# 13. Sort highest risk first
# ------------------------------------------------------------

df = (
    df.sort_values(
        by="risk_score",
        ascending=False
    )
    .reset_index(drop=True)
)


# ------------------------------------------------------------
# 14. Save risk predictions
# ------------------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ------------------------------------------------------------
# 15. Display risk results
# ------------------------------------------------------------

print("\n" + "-" * 70)
print("RISK RESULTS")
print("-" * 70)

result_columns = [
    "grid_id",
    "risk_score",
    "risk_percentage",
    "risk_category",
    "risk_priority",
    "dominant_factor"
]

print(
    df[result_columns]
    .to_string(index=False)
)


# ------------------------------------------------------------
# 16. Display contribution details
# ------------------------------------------------------------

print("\n" + "-" * 70)
print("RISK CONTRIBUTIONS")
print("-" * 70)

contribution_columns = [
    "grid_id",
    "recurrence_contribution",
    "frp_contribution",
    "repeat_detection_contribution"
]

print(
    df[contribution_columns]
    .to_string(index=False)
)


# ------------------------------------------------------------
# 17. Risk category summary
# ------------------------------------------------------------

print("\nRisk categories:")

print(
    df["risk_category"]
    .value_counts()
)


# ------------------------------------------------------------
# 18. Consistency validation
# ------------------------------------------------------------

print("\n" + "-" * 70)
print("MODEL CONSISTENCY CHECK")
print("-" * 70)

print(
    "Rows checked:",
    len(df)
)

print(
    "Consistent rows:",
    int(df["score_consistent"].sum())
)

print(
    "Inconsistent rows:",
    int(inconsistent_count)
)

if inconsistent_count == 0:

    print(
        "STATUS: PASS - Step 4 risk score matches "
        "Step 3 activity score."
    )

else:

    print(
        "STATUS: WARNING - Some rows differ from "
        "Step 3 activity score."
    )


# ------------------------------------------------------------
# 19. Highest-risk grid
# ------------------------------------------------------------

if len(df) > 0:

    print("\n" + "-" * 70)
    print("HIGHEST-RISK GRID")
    print("-" * 70)

    highest_risk = df.iloc[0]

    print(
        "Grid ID:",
        highest_risk["grid_id"]
    )

    print(
        "Risk Score:",
        round(
            highest_risk["risk_score"],
            4
        )
    )

    print(
        "Risk Percentage:",
        highest_risk["risk_percentage"],
        "%"
    )

    print(
        "Risk Category:",
        highest_risk["risk_category"]
    )

    print(
        "Dominant Factor:",
        highest_risk["dominant_factor"]
    )

    print(
        "Explanation:",
        highest_risk["risk_explanation"]
    )

else:

    print(
        "\nWARNING: No grid cells available."
    )


# ------------------------------------------------------------
# 20. Output information
# ------------------------------------------------------------

print("\nSaved to:")
print(OUTPUT_FILE)

print("\n" + "=" * 70)
print("STEP 4 COMPLETE")
print("EXPLAINABLE RISK OUTPUT GENERATED")
print("=" * 70)