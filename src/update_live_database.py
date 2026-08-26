import pandas as pd

from database import get_connection, initialize_database


# ============================================================
# THERMOSCOPE - UPDATE DATABASE WITH LIVE DATA
# ============================================================


def update_live_database():

    print("=" * 60)
    print("THERMOSCOPE - LIVE DATA → SQLITE DATABASE")
    print("=" * 60)

    # --------------------------------------------------------
    # Make sure database and tables exist
    # --------------------------------------------------------

    initialize_database()

    connection = get_connection()

    try:

        # ====================================================
        # 1. LIVE FIRMS DATA
        # ====================================================

        print("\n[1/3] Updating fire detections...")

        firms_file = "data/delhi_firms_live.csv"

        firms_df = pd.read_csv(firms_file)

        connection.execute(
            "DELETE FROM fire_detections"
        )

        firms_df.to_sql(
            "fire_detections",
            connection,
            if_exists="append",
            index=False
        )

        print(
            f"      Stored {len(firms_df)} fire detections."
        )

        # ====================================================
        # 2. LIVE RISK FEATURES
        # ====================================================

        print("\n[2/3] Updating risk features...")

        features_file = "data/delhi_risk_features_live.csv"

        features_df = pd.read_csv(features_file)

        connection.execute(
            "DELETE FROM risk_features"
        )

        features_df.to_sql(
            "risk_features",
            connection,
            if_exists="append",
            index=False
        )

        print(
            f"      Stored {len(features_df)} risk features."
        )

        # ====================================================
        # 3. LIVE RISK PREDICTIONS
        # ====================================================

        print("\n[3/3] Updating risk predictions...")

        predictions_file = (
            "data/delhi_risk_predictions_live.csv"
        )

        predictions_df = pd.read_csv(
            predictions_file
        )

        connection.execute(
            "DELETE FROM risk_predictions"
        )

        predictions_df.to_sql(
            "risk_predictions",
            connection,
            if_exists="append",
            index=False
        )

        print(
            f"      Stored {len(predictions_df)} risk predictions."
        )

        # ====================================================
        # COMMIT
        # ====================================================

        connection.commit()

        # ====================================================
        # VERIFY DATABASE
        # ====================================================

        print("\n" + "=" * 60)
        print("DATABASE VERIFICATION")
        print("=" * 60)

        tables = [
            "fire_detections",
            "risk_features",
            "risk_predictions"
        ]

        for table in tables:

            count = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            print(
                f"{table}: {count} records"
            )

    except Exception as error:

        connection.rollback()

        print("\nERROR:")
        print(error)

        raise

    finally:

        connection.close()

    print("\n" + "=" * 60)
    print("LIVE DATABASE UPDATE COMPLETE")
    print("=" * 60)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    update_live_database()