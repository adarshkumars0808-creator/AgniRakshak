import pandas as pd
import numpy as np

# ============================================================
# THERMOSCOPE - STEP 4
# EXPLAINABLE FIRE RISK SCORING
# USING SIH PROVIDED NASA FIRMS DATA
# ============================================================

INPUT_FILE = "data/delhi_risk_features.csv"
OUTPUT_FILE = "data/delhi_risk_predictions.csv"

print("=" * 70)
print("THERMOSCOPE - FIRE RISK SCORING MODEL")
print("USING SIH PROVIDED NASA FIRMS DATA")
print("=" * 70)

# ------------------------------------------------------------
# 1. Load engineered risk features
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

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
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    print("\nERROR: Missing columns:")
    print(missing_columns)

    raise ValueError(
        "Required risk features are missing."
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

df[numeric_columns] = (
    df[numeric_columns]
    .fillna(0)
)

# ------------------------------------------------------------
# 4. Validate feature ranges
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
# 5. Explainable risk score
# ------------------------------------------------------------
#
# The feature-engineering stage already calculates
# an explainable activity score using:
#
#   Recurrence / persistence = 45%
#   FRP intensity             = 35%
#   Repeat detections         = 20%
#
# The current SIH-provided dataset contains only
# one satellite source.
#
# Therefore satellite agreement is NOT artificially
# included in the risk score.
#
# We use the validated activity_score as the base
# risk score to keep Step 3B and Step 4 consistent.
# ------------------------------------------------------------

df["risk_score"] = (
    0.45 * df["recurrence_score"]
    +
    0.35 * df["frp_intensity"]
    +
    0.20 * df["repeat_detection_score"]
)

# Keep score between 0 and 1

df["risk_score"] = (
    df["risk_score"]
    .clip(0, 1)
)

# ------------------------------------------------------------
# 6. Convert risk score to percentage
# ------------------------------------------------------------

df["risk_percentage"] = (
    df["risk_score"] * 100
).round(2)

# ------------------------------------------------------------
# 7. Risk classification
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
# 8. Risk priority
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
# 9. Sort highest risk first
# ------------------------------------------------------------

df = (
    df.sort_values(
        by="risk_score",
        ascending=False
    )
    .reset_index(drop=True)
)

# ------------------------------------------------------------
# 10. Save results
# ------------------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False
)

# ------------------------------------------------------------
# 11. Display results
# ------------------------------------------------------------

print("\n" + "-" * 70)
print("RISK RESULTS")
print("-" * 70)

print(
    df[
        [
            "grid_id",
            "risk_score",
            "risk_percentage",
            "risk_category",
            "risk_priority"
        ]
    ]
    .to_string(index=False)
)

print("\nRisk categories:")

print(
    df["risk_category"]
    .value_counts()
)

print("\nHighest-risk grid:")

print(
    df.iloc[0][
        [
            "grid_id",
            "risk_score",
            "risk_percentage",
            "risk_category"
        ]
    ]
)

print("\nSaved to:")

print(OUTPUT_FILE)

print("\n" + "=" * 70)
print("STEP 4 COMPLETE")
print("=" * 70)