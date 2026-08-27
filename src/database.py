import sqlite3
from pathlib import Path
import pandas as pd


# ============================================================
# THERMOSCOPE DATABASE
# SQLite connection + schema
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "thermoscope.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# TABLE CREATION
# ============================================================

def create_tables(connection, suffix=""):

    fire_table = f"fire_detections{suffix}"
    feature_table = f"risk_features{suffix}"
    prediction_table = f"risk_predictions{suffix}"

    # --------------------------------------------------------
    # FIRE DETECTIONS
    # --------------------------------------------------------

    connection.execute(f"""
        CREATE TABLE IF NOT EXISTS {fire_table} (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            latitude REAL,
            longitude REAL,

            bright_ti4 REAL,
            scan REAL,
            track REAL,

            acq_date TEXT,
            acq_time TEXT,

            satellite TEXT,
            instrument TEXT,
            confidence TEXT,
            version TEXT,

            bright_ti5 REAL,
            frp REAL,

            daynight TEXT,

            firms_source TEXT
        )
    """)

    # --------------------------------------------------------
    # RISK FEATURES
    # --------------------------------------------------------

    connection.execute(f"""
        CREATE TABLE IF NOT EXISTS {feature_table} (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            grid_id TEXT UNIQUE,

            grid_lat REAL,
            grid_lon REAL,

            detection_count INTEGER,
            active_days INTEGER,

            avg_frp REAL,
            max_frp REAL,
            min_frp REAL,

            satellite_count INTEGER,

            first_detection TEXT,
            last_detection TEXT,

            satellite_source_count INTEGER,
            satellite_agreement REAL,
            satellite_score REAL,

            recurrence_ratio REAL,
            detections_per_active_day REAL,

            frp_intensity REAL,
            recurrence_score REAL,

            repeat_detection_score REAL,
            activity_score REAL,

            activity_category TEXT,

            repeat_score REAL
        )
    """)

    # --------------------------------------------------------
    # RISK PREDICTIONS
    # --------------------------------------------------------

    connection.execute(f"""
        CREATE TABLE IF NOT EXISTS {prediction_table} (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            grid_id TEXT UNIQUE,

            grid_lat REAL,
            grid_lon REAL,

            detection_count INTEGER,
            active_days INTEGER,

            avg_frp REAL,
            max_frp REAL,
            min_frp REAL,

            satellite_count INTEGER,

            first_detection TEXT,
            last_detection TEXT,

            satellite_source_count INTEGER,
            satellite_agreement REAL,
            satellite_score REAL,

            recurrence_ratio REAL,
            detections_per_active_day REAL,

            frp_intensity REAL,
            recurrence_score REAL,

            repeat_detection_score REAL,
            activity_score REAL,

            activity_category TEXT,

            risk_score REAL,
            risk_percentage REAL,

            risk_category TEXT,
            risk_priority INTEGER,

            recurrence_contribution REAL,
            frp_contribution REAL,
            repeat_detection_contribution REAL,

            score_difference REAL,
            score_consistent INTEGER,

            dominant_factor TEXT,

            repeat_score REAL
        )
    """)


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def initialize_database():

    connection = get_connection()

    try:

        # SIH / default tables
        create_tables(
            connection,
            ""
        )

        # LIVE tables
        create_tables(
            connection,
            "_live"
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# GET EXISTING COLUMNS
# ============================================================

def get_columns(
    connection,
    table_name
):

    cursor = connection.execute(
        f"PRAGMA table_info({table_name})"
    )

    return {
        row["name"]
        for row in cursor.fetchall()
    }


# ============================================================
# SQLITE TYPE INFERENCE
# ============================================================

def infer_sqlite_type(series):

    dtype = series.dtype

    if pd.api.types.is_integer_dtype(dtype):

        return "INTEGER"

    if pd.api.types.is_float_dtype(dtype):

        return "REAL"

    if pd.api.types.is_bool_dtype(dtype):

        return "INTEGER"

    return "TEXT"


# ============================================================
# AUTOMATIC COLUMN MIGRATION
# ============================================================

def add_missing_columns(
    connection,
    table_name,
    dataframe
):

    existing_columns = get_columns(
        connection,
        table_name
    )

    added = []

    for column in dataframe.columns:

        # SQLite already has its own auto-increment ID.
        if column == "id":
            continue

        # Column already exists.
        if column in existing_columns:
            continue

        column_type = infer_sqlite_type(
            dataframe[column]
        )

        connection.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN "{column}" {column_type}
            """
        )

        added.append(
            f"{table_name}.{column}"
        )

    return added


# ============================================================
# DATABASE MIGRATION
# ============================================================

def migrate_database():

    connection = get_connection()

    try:

        initialize_database()

    finally:

        connection.close()


# ============================================================
# SHOW DATABASE SCHEMA
# ============================================================

def show_database_schema():

    connection = get_connection()

    try:

        print("\n" + "=" * 60)
        print("DATABASE SCHEMA")
        print("=" * 60)

        tables = [

            "fire_detections",
            "risk_features",
            "risk_predictions",

            "fire_detections_live",
            "risk_features_live",
            "risk_predictions_live"
        ]

        for table in tables:

            print(f"\n{table}:")

            cursor = connection.execute(
                f"PRAGMA table_info({table})"
            )

            columns = cursor.fetchall()

            for column in columns:

                print(
                    f"  - {column['name']}"
                )

    finally:

        connection.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("THERMOSCOPE DATABASE SETUP")
    print("=" * 60)

    print("\nDatabase location:")
    print(DB_PATH)

    initialize_database()

    show_database_schema()

    print(
        "\n" + "=" * 60
    )

    print(
        "DATABASE INITIALIZATION COMPLETE"
    )

    print("=" * 60)