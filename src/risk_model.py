import pandas as pd
import numpy as np

# ============================================================
# THERMOSCOPE - STEP 4
# EXPLAINABLE FIRE RISK SCORING
# ============================================================

INPUT_FILE = "data/delhi_risk_features.csv"
OUTPUT_FILE = "data/delhi_risk_predictions.csv"

print("=" * 70)
print("THERMOSCOPE - FIRE RISK SCORING MODEL")
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
    "satellite_agreement",
    "avg_frp",
    "max_frp",
    "recurrence_score",
    "satellite_score",
    "frp_intensity",
    "activity_score"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    print("\nERROR: Missing columns:")
    print(missing_columns)
    raise ValueError("Required risk features are missing.")

# ------------------------------------------------------------
# 3. Clean numeric features
# ------------------------------------------------------------

numeric_columns = [
    "detection_count",
    "active_days",
    "satellite_agreement",
    "avg_frp",
    "max_frp",
    "recurrence_score",
    "satellite_score",
    "frp_intensity",
    "activity_score"
]

for column in numeric_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )

df[numeric_columns] = df[numeric_columns].fillna(0)

# ------------------------------------------------------------
# 4. Normalize detection activity
# ------------------------------------------------------------

max_detection = df["detection_count"].max()

if max_detection > 0:
    df["detection_score"] = (
        df["detection_count"] / max_detection
    )
else:
    df["detection_score"] = 0

# ------------------------------------------------------------
# 5. Normalize FRP activity
# ------------------------------------------------------------

max_avg_frp = df["avg_frp"].max()

if max_avg_frp > 0:
    df["avg_frp_score"] = (
        df["avg_frp"] / max_avg_frp
    )
else:
    df["avg_frp_score"] = 0

# ------------------------------------------------------------
# 6. Combined risk score
# ------------------------------------------------------------
#
# Current explainable weighting:
#
# Recurrence       = 30%
# Satellite        = 25%
# FRP intensity    = 25%
# Detection        = 20%
#
# Score range: 0 - 1
# ------------------------------------------------------------

df["risk_score"] = (
    0.30 * df["recurrence_score"]
    +
    0.25 * df["satellite_score"]
    +
    0.25 * df["frp_intensity"]
    +
    0.20 * df["detection_score"]
)

# Keep score within 0-1
df["risk_score"] = (
    df["risk_score"]
    .clip(0, 1)
)

# ------------------------------------------------------------
# 7. Convert to percentage
# ------------------------------------------------------------

df["risk_percentage"] = (
    df["risk_score"] * 100
).round(2)

# ------------------------------------------------------------
# 8. Risk classification
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
# 9. Risk priority
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
# 10. Sort highest risk first
# ------------------------------------------------------------

df = df.sort_values(
    by="risk_score",
    ascending=False
).reset_index(drop=True)

# ------------------------------------------------------------
# 11. Save results
# ------------------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False
)

# ------------------------------------------------------------
# 12. Display results
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