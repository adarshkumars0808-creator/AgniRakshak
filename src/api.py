from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pathlib import Path

# ============================================================
# AGNIRAKSHAK - BACKEND API
# ============================================================

app = FastAPI(
    title="AgniRakshak API",
    description="Fire risk prediction backend API",
    version="1.0.0"
)

# ------------------------------------------------------------
# CORS
# ------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# DATA PATH
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "delhi_risk_predictions.csv"


# ------------------------------------------------------------
# Helper function
# ------------------------------------------------------------

def load_data():

    if not DATA_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Risk prediction dataset not found."
        )

    return pd.read_csv(DATA_FILE)


# ------------------------------------------------------------
# HOME
# ------------------------------------------------------------

@app.get("/")
def home():

    return {
        "project": "AgniRakshak",
        "status": "Backend API running",
        "message": "Fire risk prediction API is active"
    }


# ------------------------------------------------------------
# HEALTH CHECK
# ------------------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


# ------------------------------------------------------------
# ALL RISK DATA
# ------------------------------------------------------------

@app.get("/api/risk")
def get_all_risk():

    df = load_data()

    return df.to_dict(orient="records")


# ------------------------------------------------------------
# TOP HIGH-RISK LOCATIONS
# ------------------------------------------------------------

@app.get("/api/risk/top")
def get_top_risk(limit: int = 10):

    df = load_data()

    df = df.sort_values(
        by="risk_score",
        ascending=False
    )

    result = df.head(limit)

    return result.to_dict(orient="records")


# ------------------------------------------------------------
# RISK SUMMARY
# ------------------------------------------------------------

@app.get("/api/risk/summary")
def get_risk_summary():

    df = load_data()

    return {
        "total_grid_cells": int(len(df)),
        "high_risk": int(
            (df["risk_category"] == "HIGH").sum()
        ),
        "medium_risk": int(
            (df["risk_category"] == "MEDIUM").sum()
        ),
        "low_risk": int(
            (df["risk_category"] == "LOW").sum()
        )
    }


# ------------------------------------------------------------
# LOCATION-SPECIFIC RISK
# ------------------------------------------------------------

@app.get("/api/risk/{grid_id}")
def get_location_risk(grid_id: str):

    df = load_data()

    result = df[
        df["grid_id"].astype(str) == grid_id
    ]

    if result.empty:

        raise HTTPException(
            status_code=404,
            detail="Grid location not found."
        )

    return result.iloc[0].to_dict()