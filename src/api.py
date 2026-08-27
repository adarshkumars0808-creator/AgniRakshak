from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sqlite3

# ============================================================
# AGNIRAKSHAK - BACKEND API
# SQLite → FastAPI → Dashboard
# ============================================================

app = FastAPI(
    title="AgniRakshak API",
    description="Fire risk prediction backend API",
    version="2.1.0"
)

# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# DATABASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "data" / "thermoscope.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():

    if not DB_FILE.exists():

        raise HTTPException(
            status_code=404,
            detail=f"Thermoscope database not found: {DB_FILE}"
        )

    connection = sqlite3.connect(DB_FILE)

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# SAFE ROW CONVERSION
# ============================================================

def rows_to_dict(rows):

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    return {
        "project": "AgniRakshak",
        "status": "Backend API running",
        "database": "SQLite",
        "database_file": str(DB_FILE),
        "message": "Fire risk prediction API is active"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    connection = None

    try:

        connection = get_db_connection()

        connection.execute(
            "SELECT 1"
        )

        return {
            "status": "healthy",
            "database": "connected",
            "database_file": str(DB_FILE)
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {error}"
        )

    finally:

        if connection:
            connection.close()


# ============================================================
# DATABASE STATS
# ============================================================

@app.get("/api/database/stats")
def get_database_stats():

    connection = get_db_connection()

    try:

        fire_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM fire_detections
            """
        ).fetchone()[0]

        feature_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM risk_features
            """
        ).fetchone()[0]

        prediction_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM risk_predictions
            """
        ).fetchone()[0]

        return {
            "database": "SQLite",
            "fire_detections": fire_count,
            "risk_features": feature_count,
            "risk_predictions": prediction_count
        }

    finally:

        connection.close()


# ============================================================
# ALL RISK PREDICTIONS
# ============================================================

@app.get("/api/risk")
def get_all_risk(mode: str = "sih"):

    mode = mode.lower().strip()

    if mode not in ["sih", "live"]:
        raise HTTPException(
            status_code=400,
            detail="Mode must be either 'sih' or 'live'."
        )

    table_name = (
        "risk_predictions_live"
        if mode == "live"
        else "risk_predictions"
    )

    connection = get_db_connection()

    try:

        cursor = connection.execute(
            f"""
            SELECT *
            FROM {table_name}
            ORDER BY risk_score DESC
            """
        )

        rows = cursor.fetchall()

        return rows_to_dict(rows)

    finally:

        connection.close()

# ============================================================
# TOP HIGH-RISK LOCATIONS
# ============================================================

@app.get("/api/risk/top")
def get_top_risk(limit: int = 10):

    if limit < 1 or limit > 100:

        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100."
        )

    connection = get_db_connection()

    try:

        cursor = connection.execute(
            """
            SELECT *
            FROM risk_predictions
            ORDER BY risk_score DESC
            LIMIT ?
            """,
            (limit,)
        )

        rows = cursor.fetchall()

        return rows_to_dict(rows)

    finally:

        connection.close()


# ============================================================
# RISK SUMMARY
# ============================================================

@app.get("/api/risk/summary")
def get_risk_summary():

    connection = get_db_connection()

    try:

        cursor = connection.execute(
            """
            SELECT

                COUNT(*) AS total_grid_cells,

                SUM(
                    CASE
                        WHEN UPPER(risk_category) = 'HIGH'
                        THEN 1
                        ELSE 0
                    END
                ) AS high_risk,

                SUM(
                    CASE
                        WHEN UPPER(risk_category) = 'MEDIUM'
                        THEN 1
                        ELSE 0
                    END
                ) AS medium_risk,

                SUM(
                    CASE
                        WHEN UPPER(risk_category) = 'LOW'
                        THEN 1
                        ELSE 0
                    END
                ) AS low_risk

            FROM risk_predictions
            """
        )

        row = cursor.fetchone()

        return {
            "total_grid_cells": row["total_grid_cells"] or 0,
            "high_risk": row["high_risk"] or 0,
            "medium_risk": row["medium_risk"] or 0,
            "low_risk": row["low_risk"] or 0
        }

    finally:

        connection.close()


# ============================================================
# LOCATION-SPECIFIC RISK
# ============================================================

@app.get("/api/risk/{grid_id}")
def get_location_risk(grid_id: str):

    connection = get_db_connection()

    try:

        cursor = connection.execute(
            """
            SELECT *
            FROM risk_predictions
            WHERE CAST(grid_id AS TEXT) = ?
            """,
            (grid_id,)
        )

        row = cursor.fetchone()

        if row is None:

            raise HTTPException(
                status_code=404,
                detail=f"Grid location '{grid_id}' not found."
            )

        return dict(row)

    finally:

        connection.close()


# ============================================================
# ALL FIRMS FIRE DETECTIONS
# ============================================================

@app.get("/api/detections")
@app.get("/api/detections")
def get_fire_detections(mode: str = "sih"):

    mode = mode.lower().strip()

    if mode not in ["sih", "live"]:
        raise HTTPException(
            status_code=400,
            detail="Mode must be either 'sih' or 'live'."
        )

    table_name = (
        "fire_detections_live"
        if mode == "live"
        else "fire_detections"
    )

    connection = get_db_connection()

    try:

        cursor = connection.execute(
            f"""
            SELECT *
            FROM {table_name}
            ORDER BY acq_date DESC, acq_time DESC
            """
        )

        rows = cursor.fetchall()

        return rows_to_dict(rows)

    finally:

        connection.close()


# ============================================================
# RECENT FIRE DETECTIONS
# ============================================================

@app.get("/api/detections/recent")
def get_recent_detections(limit: int = 20):

    if limit < 1 or limit > 500:

        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 500."
        )

    connection = get_db_connection()

    try:

        cursor = connection.execute(
            """
            SELECT *
            FROM fire_detections
            ORDER BY acq_date DESC, acq_time DESC
            LIMIT ?
            """,
            (limit,)
        )

        rows = cursor.fetchall()

        return rows_to_dict(rows)

    finally:

        connection.close()


# ============================================================
# RISK FEATURES
# ============================================================

@app.get("/api/features")
def get_risk_features():

    connection = get_db_connection()

    try:

        cursor = connection.execute(
            """
            SELECT *
            FROM risk_features
            ORDER BY activity_score DESC
            """
        )

        rows = cursor.fetchall()

        return rows_to_dict(rows)

    finally:

        connection.close()


# ============================================================
# API DATABASE INFORMATION
# ============================================================

@app.get("/api/database")
def get_database_information():

    connection = get_db_connection()

    try:

        tables = {}

        for table_name in [
            "fire_detections",
            "risk_features",
            "risk_predictions"
        ]:

            cursor = connection.execute(
                f"PRAGMA table_info({table_name})"
            )

            columns = cursor.fetchall()

            tables[table_name] = [
                {
                    "name": column["name"],
                    "type": column["type"]
                }
                for column in columns
            ]

        return {
            "database": str(DB_FILE),
            "tables": tables
        }

    finally:

        connection.close()


# ============================================================
# RUN INFORMATION
# ============================================================

@app.get("/api/status")
def get_api_status():

    connection = get_db_connection()

    try:

        fire_count = connection.execute(
            "SELECT COUNT(*) FROM fire_detections"
        ).fetchone()[0]

        risk_count = connection.execute(
            "SELECT COUNT(*) FROM risk_predictions"
        ).fetchone()[0]

        return {
            "api": "ONLINE",
            "database": "ONLINE",
            "fire_detections": fire_count,
            "risk_predictions": risk_count
        }

    finally:

        connection.close()
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )