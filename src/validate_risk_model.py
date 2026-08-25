import pandas as pd
import numpy as np

# ============================================================
# THERMOSCOPE - RISK MODEL VALIDATION
# ============================================================

INPUT_FILE = "data/delhi_risk_predictions.csv"

print("=" * 70)
print("THERMOSCOPE - RISK MODEL VALIDATION")
print("=" * 70)

# ------------------------------------------------------------
# 1. Load predictions
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print("\nRows:", len(df))

# ------------------------------------------------------------
# 2. Required columns
# ------------------------------------------------------------

required_columns = [
    "grid_id",
    "risk_score",
    "risk_percentage",
    "risk_category",
    "risk_priority"
]

missing = [
    col for col in required_columns
    if col not in df.columns
]

if missing:
    print("\nFAIL - Missing columns:")
    print(missing)
    raise ValueError("Validation failed.")

print("Required columns: PASS")

# ------------------------------------------------------------
# 3. Risk score range
# ------------------------------------------------------------

score_valid = (
    df["risk_score"].between(0, 1).all()
)

print(
    "Risk score range:",
    "PASS" if score_valid else "FAIL"
)

# ------------------------------------------------------------
# 4. Risk percentage range
# ------------------------------------------------------------

percentage_valid = (
    df["risk_percentage"].between(0, 100).all()
)

print(
    "Risk percentage range:",
    "PASS" if percentage_valid else "FAIL"
)

# ------------------------------------------------------------
# 5. Check score-percentage consistency
# ------------------------------------------------------------

expected_percentage = (
    df["risk_score"] * 100
).round(2)

percentage_consistent = np.allclose(
    df["risk_percentage"],
    expected_percentage,
    atol=0.01
)

print(
    "Score/percentage consistency:",
    "PASS" if percentage_consistent else "FAIL"
)

# ------------------------------------------------------------
# 6. Check risk categories
# ------------------------------------------------------------

def expected_category(score):

    if score >= 0.75:
        return "HIGH"

    elif score >= 0.45:
        return "MEDIUM"

    else:
        return "LOW"


expected_categories = (
    df["risk_score"]
    .apply(expected_category)
)

category_valid = (
    df["risk_category"] == expected_categories
).all()

print(
    "Risk classification:",
    "PASS" if category_valid else "FAIL"
)

# ------------------------------------------------------------
# 7. Duplicate grid IDs
# ------------------------------------------------------------

duplicate_grids = df["grid_id"].duplicated().sum()

print(
    "Duplicate grid IDs:",
    "PASS" if duplicate_grids == 0 else "FAIL"
)

# ------------------------------------------------------------
# 8. Missing values
# ------------------------------------------------------------

missing_values = df[
    required_columns
].isna().sum().sum()

print(
    "Missing required values:",
    "PASS" if missing_values == 0 else "FAIL"
)

# ------------------------------------------------------------
# 9. Check sorting
# ------------------------------------------------------------

sorted_correctly = (
    df["risk_score"].is_monotonic_decreasing
)

print(
    "Highest-risk first sorting:",
    "PASS" if sorted_correctly else "FAIL"
)

# ------------------------------------------------------------
# 10. Risk distribution
# ------------------------------------------------------------

print("\nRisk distribution:")
print(
    df["risk_category"]
    .value_counts()
)

# ------------------------------------------------------------
# 11. Summary
# ------------------------------------------------------------

checks = [
    score_valid,
    percentage_valid,
    percentage_consistent,
    category_valid,
    duplicate_grids == 0,
    missing_values == 0,
    sorted_correctly
]

print("\n" + "-" * 70)

if all(checks):
    print("OVERALL VALIDATION: PASS")
else:
    print("OVERALL VALIDATION: REVIEW REQUIRED")

print("-" * 70)

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

print("\n" + "=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)