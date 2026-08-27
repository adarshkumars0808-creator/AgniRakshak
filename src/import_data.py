from pathlib import Path

import pandas as pd

from database import (
    get_connection,
    initialize_database,
    add_missing_columns,
)


# ============================================================
# THERMOSCOPE - CSV TO SQLITE IMPORT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


# ============================================================
# SIH DATA
# ============================================================

SIH_FILES = {

    "fire_detections":
        DATA_DIR / "delhi_firms.csv",

    "risk_features":
        DATA_DIR / "delhi_risk_features.csv",

    "risk_predictions":
        DATA_DIR / "delhi_risk_predictions.csv",
}


# ============================================================
# LIVE DATA
# ============================================================

LIVE_FILES = {

    "fire_detections_live":
        DATA_DIR / "delhi_firms_live.csv",

    "risk_features_live":
        DATA_DIR / "delhi_risk_features_live.csv",

    "risk_predictions_live":
        DATA_DIR / "delhi_risk_predictions_live.csv",
}


# ============================================================
# IMPORT ONE FILE
# ============================================================

def import_file(
    connection,
    table_name,
    file_path
):

    print(
        f"\n      Table: {table_name}"
    )

    # --------------------------------------------------------
    # CHECK FILE
    # --------------------------------------------------------

    if not file_path.exists():

        print(
            f"      WARNING: File not found: "
            f"{file_path.name}"
        )

        return 0

    # --------------------------------------------------------
    # READ CSV
    # --------------------------------------------------------

    df = pd.read_csv(
        file_path
    )

    # --------------------------------------------------------
    # AUTOMATIC COLUMN MIGRATION
    # --------------------------------------------------------
    # If CSV contains a new column that is not yet present
    # in SQLite, automatically add it to the table.

    added_columns = add_missing_columns(
        connection,
        table_name,
        df
    )

    if added_columns:

        print(
            "      Added database columns:"
        )

        for column in added_columns:

            print(
                f"        + {column}"
            )

    # --------------------------------------------------------
    # REMOVE PREVIOUS DATA
    # --------------------------------------------------------

    connection.execute(
        f"DELETE FROM {table_name}"
    )

    # --------------------------------------------------------
    # IMPORT DATA
    # --------------------------------------------------------

    df.to_sql(
        table_name,
        connection,
        if_exists="append",
        index=False
    )

    print(
        f"      Imported {len(df)} records."
    )

    return len(df)


# ============================================================
# IMPORT SIH DATA
# ============================================================

def import_sih_data(
    connection
):

    print(
        "\n" + "=" * 60
    )

    print(
        "IMPORTING SIH DATA"
    )

    print(
        "=" * 60
    )

    totals = {}

    for table, file_path in SIH_FILES.items():

        totals[table] = import_file(
            connection,
            table,
            file_path
        )

    return totals


# ============================================================
# IMPORT LIVE DATA
# ============================================================

def import_live_data(
    connection
):

    print(
        "\n" + "=" * 60
    )

    print(
        "IMPORTING LIVE PROCESSED DATA"
    )

    print(
        "=" * 60
    )

    totals = {}

    for table, file_path in LIVE_FILES.items():

        totals[table] = import_file(
            connection,
            table,
            file_path
        )

    return totals


# ============================================================
# DATABASE VERIFICATION
# ============================================================

def verify_database(
    connection
):

    print(
        "\n" + "=" * 60
    )

    print(
        "DATABASE VERIFICATION"
    )

    print(
        "=" * 60
    )

    tables = [

        "fire_detections",
        "risk_features",
        "risk_predictions",

        "fire_detections_live",
        "risk_features_live",
        "risk_predictions_live"
    ]

    for table in tables:

        count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(
            f"{table}: {count} records"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)

    print(
        "THERMOSCOPE - DATA IMPORT"
    )

    print("=" * 60)

    # --------------------------------------------------------
    # MAKE SURE DATABASE EXISTS
    # --------------------------------------------------------

    initialize_database()

    connection = get_connection()

    try:

        # ----------------------------------------------------
        # SIH DATA
        # ----------------------------------------------------

        import_sih_data(
            connection
        )

        # ----------------------------------------------------
        # LIVE DATA
        # ----------------------------------------------------

        import_live_data(
            connection
        )

        # ----------------------------------------------------
        # COMMIT
        # ----------------------------------------------------

        connection.commit()

        # ----------------------------------------------------
        # VERIFY
        # ----------------------------------------------------

        verify_database(
            connection
        )

    except Exception as error:

        connection.rollback()

        print(
            "\nERROR:"
        )

        print(
            error
        )

        raise

    finally:

        connection.close()

    print(
        "\n" + "=" * 60
    )

    print(
        "DATA IMPORT COMPLETE"
    )

    print(
        "=" * 60
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()