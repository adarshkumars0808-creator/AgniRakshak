# ============================================================
# THERMOSCOPE - COMPLETE RISK ANALYSIS RUNNER
# ============================================================

from risk_summary import generate_summary
from top_risk_areas import get_top_risk_areas
from risk_explanation import explain_all
from risk_alerts import generate_all_alerts


def run_analysis():
    """Run the complete Thermoscope risk analysis."""

    print("=" * 70)
    print("THERMOSCOPE - COMPLETE FIRE RISK ANALYSIS")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. Overall summary
    # --------------------------------------------------------

    summary = generate_summary()

    print("\n[1] OVERALL RISK SUMMARY")
    print("-" * 70)

    print(f"Total grids       : {summary['total_grids']}")
    print(f"High-risk grids   : {summary['high_risk']}")
    print(f"Medium-risk grids : {summary['medium_risk']}")
    print(f"Low-risk grids    : {summary['low_risk']}")
    print(f"Average risk      : {summary['average_risk']:.4f}")

    print(
        f"Highest-risk grid : "
        f"{summary['highest_risk_grid']}"
    )

    print(
        f"Highest-risk score: "
        f"{summary['highest_risk_score']:.4f}"
    )

    # --------------------------------------------------------
    # 2. Top risk areas
    # --------------------------------------------------------

    print("\n[2] TOP RISK AREAS")
    print("-" * 70)

    top_areas = get_top_risk_areas(5)

    for rank, (_, row) in enumerate(
        top_areas.iterrows(),
        start=1
    ):
        print(
            f"{rank}. "
            f"{row['grid_id']} | "
            f"Score: {row['risk_score']:.4f} | "
            f"Level: {row['risk_level']}"
        )

    # --------------------------------------------------------
    # 3. Explainable risk analysis
    # --------------------------------------------------------

    print("\n[3] EXPLAINABLE RISK ANALYSIS")
    print("-" * 70)

    explanations = explain_all()

    for item in explanations:

        print(
            f"\nGrid: {item['grid_id']} | "
            f"{item['risk_level']} | "
            f"Score: {item['risk_score']:.4f}"
        )

        print(f"Summary: {item['summary']}")

        for reason in item["reasons"]:
            print(f"  - {reason}")

    # --------------------------------------------------------
    # 4. Risk alerts
    # --------------------------------------------------------

    print("\n[4] FIRE RISK ALERTS")
    print("-" * 70)

    alerts = generate_all_alerts()

    if alerts:
        for alert in alerts:
            print(
                f"{alert['grid_id']} | "
                f"{alert['risk_level']} | "
                f"{alert['priority']} | "
                f"{alert['message']}"
            )
    else:
        print("No alerts generated.")

    # --------------------------------------------------------
    # Complete
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("THERMOSCOPE ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_analysis()