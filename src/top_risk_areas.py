import pandas as pd


# ============================================================
# THERMOSCOPE - TOP RISK AREAS
# ============================================================

PREDICTION_FILE = "data/delhi_risk_predictions.csv"


def load_predictions():
    """Load Thermoscope risk prediction data."""
    return pd.read_csv(PREDICTION_FILE)


def get_risk_level(score):
    """Convert risk score into Thermoscope risk category."""

    if score >= 0.75:
        return "HIGH"
    elif score >= 0.50:
        return "MEDIUM"
    else:
        return "LOW"


def get_top_risk_areas(top_n=5):
    """Return the highest-risk grid areas."""

    df = load_predictions()

    df["risk_level"] = df["risk_score"].apply(get_risk_level)

    top_areas = (
        df.sort_values("risk_score", ascending=False)
        .head(top_n)
    )

    return top_areas[
        ["grid_id", "risk_score", "risk_level"]
    ]


def print_top_risk_areas():
    """Print highest-risk grids."""

    top_areas = get_top_risk_areas()

    print("=" * 65)
    print("THERMOSCOPE - TOP RISK AREAS")
    print("=" * 65)

    for rank, (_, row) in enumerate(top_areas.iterrows(), start=1):

        print(f"\nRank {rank}")
        print(f"Grid ID    : {row['grid_id']}")
        print(f"Risk Score : {row['risk_score']:.4f}")
        print(f"Risk Level : {row['risk_level']}")

    print("\n" + "=" * 65)


if __name__ == "__main__":
    print_top_risk_areas()