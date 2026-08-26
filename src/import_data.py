import sqlite3
from pathlib import Path

import pandas as pd

from database import get_connection, initialize_database


# ============================================================
# THERMOSCOPE - IMPORT CSV DATA INTO SQLITE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


FIRMS_FILE = DATA_DIR / "delhi_firms.csv"
FEATURES_FILE = DATA_DIR / "delhi_risk_features.csv"
PREDICTIONS_FILE = DATA_DIR / "delhi_risk_predictions.csv"


def import_fire_detections(connection):
    print("\n[1/3] Importing FIRMS fire detections...")

    df = pd.read_csv(FIRMS_FILE)

    # Replace existing data so repeated imports don't create duplicates.
    connection.execute("DELETE FROM fire_detections")

    df.to_sql(
        "fire_detections",
        connection,
        if_exists="append",
        index=False
    )

    print(f"      Imported {len(df)} fire detections.")


def import_risk_features(connection):
    print("\n[2/3] Importing risk features...")

    df = pd.read_csv(FEATURES_FILE)

    connection.execute("DELETE FROM risk_features")

    df.to_sql(
        "risk_features",
        connection,
        if_exists="append",
        index=False
    )

    print(f"      Imported {len(df)} risk-feature records.")


def import_risk_predictions(connection):
    print("\n[3/3] Importing risk predictions...")

    df = pd.read_csv(PREDICTIONS_FILE)

    connection.execute("DELETE FROM risk_predictions")

    df.to_sql(
        "risk_predictions",
        connection,
        if_exists="append",
        index=False
    )

    print(f"      Imported {len(df)} risk-prediction records.")


def verify_database(connection):
    print("\n" + "=" * 60)
    print("DATABASE VERIFICATION")
    print("=" * 60)

    tables = [
        "fire_detections",
        "risk_features",
        "risk_predictions"
    ]

    for table in tables:

        cursor = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        )

        count = cursor.fetchone()[0]

        print(f"{table}: {count} records")


def main():

    print("=" * 60)
    print("THERMOSCOPE - CSV TO SQLITE IMPORT")
    print("=" * 60)

    # Make sure database/tables exist.
    initialize_database()

    connection = get_connection()

    try:

        import_fire_detections(connection)

        import_risk_features(connection)

        import_risk_predictions(connection)

        connection.commit()

        verify_database(connection)

    except Exception as error:

        connection.rollback()

        print("\nERROR:")
        print(error)

        raise

    finally:

        connection.close()

    print("\n" + "=" * 60)
    print("DATA IMPORT COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()