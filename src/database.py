import sqlite3
from pathlib import Path
import pandas as pd

# ============================================================
# THERMOSCOPE DATABASE
# SQLite database connection + automatic schema migration
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "thermoscope.db"

PREDICTIONS_FILE = DATA_DIR / "delhi_risk_predictions_live.csv"
FEATURES_FILE = DATA_DIR / "delhi_risk_features_live.csv"
FIRMS_FILE = DATA_DIR / "delhi_firms_live.csv"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# INITIAL DATABASE TABLES
# ============================================================

def initialize_database():

    connection = get_connection()
    cursor = connection.cursor()

    # ========================================================
    # FIRE DETECTIONS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fire_detections (

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

    # ========================================================
    # RISK FEATURES
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_features (

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

            activity_category TEXT
        )
    """)

    # ========================================================
    # RISK PREDICTIONS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_predictions (

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

            dominant_factor TEXT
        )
    """)

    connection.commit()
    connection.close()


# ============================================================
# GET EXISTING COLUMNS
# ============================================================

def get_columns(connection, table_name):

    cursor = connection.execute(
        f"PRAGMA table_info({table_name})"
    )

    return {
        row["name"]
        for row in cursor.fetchall()
    }


# ============================================================
# AUTOMATIC COLUMN MIGRATION
# ============================================================

def add_missing_columns(connection, table_name, dataframe):

    existing_columns = get_columns(
        connection,
        table_name
    )

    added = []

    for column in dataframe.columns:

        # Ignore SQLite primary key.
        if column == "id":
            continue

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
# INFER SQLITE TYPE
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
# AUTOMATIC DATABASE MIGRATION
# ============================================================

def migrate_database():

    connection = get_connection()

    all_added_columns = []

    # ========================================================
    # LIVE FIRMS FILE
    # ========================================================

    if FIRMS_FILE.exists():

        try:

            firms_df = pd.read_csv(
                FIRMS_FILE,
                nrows=5
            )

            added = add_missing_columns(
                connection,
                "fire_detections",
                firms_df
            )

            all_added_columns.extend(added)

        except Exception as error:

            print(
                "Warning: Could not inspect live FIRMS file:"
            )

            print(error)

    # ========================================================
    # LIVE FEATURES FILE
    # ========================================================

    if FEATURES_FILE.exists():

        try:

            features_df = pd.read_csv(
                FEATURES_FILE,
                nrows=5
            )

            added = add_missing_columns(
                connection,
                "risk_features",
                features_df
            )

            all_added_columns.extend(added)

        except Exception as error:

            print(
                "Warning: Could not inspect live features file:"
            )

            print(error)

    # ========================================================
    # LIVE PREDICTIONS FILE
    # ========================================================

    if PREDICTIONS_FILE.exists():

        try:

            predictions_df = pd.read_csv(
                PREDICTIONS_FILE,
                nrows=5
            )

            added = add_missing_columns(
                connection,
                "risk_predictions",
                predictions_df
            )

            all_added_columns.extend(added)

        except Exception as error:

            print(
                "Warning: Could not inspect live predictions file:"
            )

            print(error)

    connection.commit()
    connection.close()

    # ========================================================
    # DISPLAY MIGRATIONS
    # ========================================================

    if all_added_columns:

        print("\nDatabase migration:")

        for column in all_added_columns:

            print(
                f"Added column: {column}"
            )

    else:

        print(
            "\nDatabase migration: "
            "No new columns required."
        )


# ============================================================
# SHOW DATABASE SCHEMA
# ============================================================

def show_database_schema():

    connection = get_connection()

    print("\n" + "=" * 60)
    print("DATABASE SCHEMA")
    print("=" * 60)

    tables = [
        "fire_detections",
        "risk_features",
        "risk_predictions"
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

    # --------------------------------------------------------
    # Create tables
    # --------------------------------------------------------

    initialize_database()

    # --------------------------------------------------------
    # Automatically compare current live CSV schema
    # with SQLite schema and add anything missing.
    # --------------------------------------------------------

    migrate_database()

    # --------------------------------------------------------
    # Show final schema
    # --------------------------------------------------------

    show_database_schema()

    print("\n" + "=" * 60)
    print("DATABASE INITIALIZATION / MIGRATION COMPLETE")
    print("=" * 60)

    print("\nDatabase:")
    print(DB_PATH)

    print("\nReady for live database update.")