import pandas as pd


# ============================================================
# THERMOSCOPE - RISK SUMMARY ENGINE
# ============================================================

PREDICTION_FILE = "data/delhi_risk_predictions.csv"


def load_predictions():
    """Load Thermoscope risk prediction data."""
    return pd.read_csv(PREDICTION_FILE)


def generate_summary():
    """Generate overall fire-risk summary."""

    df = load_predictions()

    total_grids = len(df)

    high_count = (df["risk_score"] >= 0.75).sum()
    medium_count = (
        (df["risk_score"] >= 0.50) &
        (df["risk_score"] < 0.75)
    ).sum()
    low_count = (df["risk_score"] < 0.50).sum()

    average_risk = df["risk_score"].mean()

    highest_risk_row = df.loc[df["risk_score"].idxmax()]

    return {
        "total_grids": total_grids,
        "high_risk": high_count,
        "medium_risk": medium_count,
        "low_risk": low_count,
        "average_risk": average_risk,
        "highest_risk_grid": highest_risk_row.get(
            "grid_id", "Unknown"
        ),
        "highest_risk_score": highest_risk_row["risk_score"],
    }


def print_summary():
    """Print risk summary in a readable format."""

    summary = generate_summary()

    print("=" * 65)
    print("THERMOSCOPE - OVERALL FIRE RISK SUMMARY")
    print("=" * 65)

    print(f"\nTotal grids analysed : {summary['total_grids']}")
    print(f"High-risk grids      : {summary['high_risk']}")
    print(f"Medium-risk grids    : {summary['medium_risk']}")
    print(f"Low-risk grids       : {summary['low_risk']}")

    print(
        f"\nAverage risk score   : "
        f"{summary['average_risk']:.4f}"
    )

    print(
        f"Highest-risk grid    : "
        f"{summary['highest_risk_grid']}"
    )

    print(
        f"Highest risk score   : "
        f"{summary['highest_risk_score']:.4f}"
    )

    print("\n" + "=" * 65)


if __name__ == "__main__":
    print_summary()