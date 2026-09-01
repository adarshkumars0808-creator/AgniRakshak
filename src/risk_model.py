import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler


warnings.filterwarnings("ignore")


# ============================================================
# THERMOSCOPE - INDUSTRIAL FIRE RISK MODEL
# ============================================================

INPUT_FILE = Path("data/processed/grid_features.csv")

OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PREDICTION_FILE = OUTPUT_DIR / "risk_predictions.csv"
TOP10_FILE = OUTPUT_DIR / "top10_high_risk.csv"


# ============================================================
# FEATURE GROUPS
# ============================================================

FEATURES = [
    "total_detections",
    "active_days",
    "avg_frp",
    "max_frp",
    "median_frp",
    "frp_std",
    "avg_brightness",
    "max_brightness",
    "avg_confidence",

    "satellite_count",
    "active_months",
    "active_years",
    "years_with_activity",

    "avg_yearly_detections",
    "max_yearly_detections",
    "yearly_detection_std",

    "recurrence_ratio",
    "persistent_months",
    "avg_monthly_detections",
    "max_monthly_detections",

    "satellite_types",
    "snpp_detections",
    "noaa20_detections",
    "noaa21_detections",
    "multi_satellite_activity",

    "detections_30d",
    "active_days_30d",
    "avg_frp_30d",
    "max_frp_30d",

    "detections_90d",
    "active_days_90d",
    "avg_frp_90d",
    "max_frp_90d",

    "seasonal_mean",
    "seasonal_std",
    "seasonality_strength",

    "detections_per_active_day",
    "recent_activity_ratio",
    "frp_intensity_ratio",
    "persistence_ratio",
]


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    print("=" * 70)
    print("THERMOSCOPE - AI FIRE RISK PREDICTION")
    print("=" * 70)

    print(f"Input: {INPUT_FILE}")
    print()

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    print(f"Grid cells loaded: {len(df):,}")
    print(f"Features available: {len(df.columns)}")

    return df


# ============================================================
# PREPARE FEATURES
# ============================================================

def prepare_features(df):

    print()
    print("Preparing ML features...")

    available_features = [
        col for col in FEATURES
        if col in df.columns
    ]

    missing_features = [
        col for col in FEATURES
        if col not in df.columns
    ]

    if missing_features:
        print()
        print("WARNING - Missing features:")
        for col in missing_features:
            print(f"  - {col}")

    X = df[available_features].copy()

    # Replace infinite values
    X = X.replace(
        [np.inf, -np.inf],
        np.nan
    )

    # Fill missing values using median
    X = X.fillna(
        X.median(numeric_only=True)
    )

    X = X.fillna(0)

    print(
        f"ML feature matrix: "
        f"{X.shape[0]:,} rows x {X.shape[1]} features"
    )

    return X, available_features


# ============================================================
# BUILD UNSUPERVISED RISK TARGET
# ============================================================

def build_risk_target(df):

    """
    There is currently no manually labelled industrial-fire
    dataset in the project.

    Therefore, the initial model uses an engineered
    risk index as a pseudo-target.

    This is NOT presented as classification accuracy.

    Later, this can be replaced with verified labels from
    industrial infrastructure / land-cover / satellite data.
    """

    print()
    print("Building risk index...")

    components = {}

    # --------------------------------------------------------
    # Historical recurrence
    # --------------------------------------------------------

    components["recurrence"] = (
        df["recurrence_ratio"]
    )

    # --------------------------------------------------------
    # Persistence
    # --------------------------------------------------------

    components["persistence"] = (
        df["persistence_ratio"]
    )

    # --------------------------------------------------------
    # Recent activity
    # --------------------------------------------------------

    components["recent_activity"] = (
        df["recent_activity_ratio"]
    )

    # --------------------------------------------------------
    # FRP intensity
    # --------------------------------------------------------

    components["frp_intensity"] = (
        df["frp_intensity_ratio"]
    )

    # --------------------------------------------------------
    # Multi satellite agreement
    # --------------------------------------------------------

    satellite_score = (
        df["multi_satellite_activity"]
        / df["satellite_types"].replace(0, 1)
    )

    components["satellite_agreement"] = (
        satellite_score
    )

    # --------------------------------------------------------
    # Detection density
    # --------------------------------------------------------

    detection_score = np.log1p(
        df["total_detections"]
    )

    components["detection_density"] = (
        detection_score
    )

    # --------------------------------------------------------
    # Normalize each component
    # --------------------------------------------------------

    normalized = pd.DataFrame(
        index=df.index
    )

    scaler = MinMaxScaler()

    for name, values in components.items():

        values = (
            pd.Series(values)
            .replace(
                [np.inf, -np.inf],
                np.nan
            )
            .fillna(0)
            .values
            .reshape(-1, 1)
        )

        normalized[name] = scaler.fit_transform(
            values
        ).ravel()

    # --------------------------------------------------------
    # Weighted risk index
    # --------------------------------------------------------

    risk_index = (
        normalized["recurrence"] * 0.22
        + normalized["persistence"] * 0.20
        + normalized["recent_activity"] * 0.18
        + normalized["frp_intensity"] * 0.18
        + normalized["satellite_agreement"] * 0.10
        + normalized["detection_density"] * 0.12
    )

    return risk_index, normalized


# ============================================================
# TRAIN ML MODEL
# ============================================================

def train_model(X, target):

    print()
    print("Training Random Forest model...")

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=14,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1
    )

    model.fit(
        X,
        target
    )

    print("Model training complete.")

    return model


# ============================================================
# GENERATE PREDICTIONS
# ============================================================

def generate_predictions(
    df,
    X,
    model
):

    print()
    print("Generating risk predictions...")

    predicted = model.predict(X)

    # Normalize to 0-100
    scaler = MinMaxScaler(
        feature_range=(0, 100)
    )

    risk_score = scaler.fit_transform(
        predicted.reshape(-1, 1)
    ).ravel()

    result = df[
        [
            "grid_id",
            "latitude",
            "longitude",
            "total_detections",
            "active_days",
            "avg_frp",
            "max_frp",
            "recurrence_ratio",
            "persistent_months",
            "multi_satellite_activity",
            "detections_30d",
            "detections_90d",
            "recent_activity_ratio",
            "frp_intensity_ratio",
            "persistence_ratio",
        ]
    ].copy()

    result["risk_score"] = risk_score

    # --------------------------------------------------------
    # Risk categories
    # --------------------------------------------------------

    result["risk_level"] = pd.cut(
        result["risk_score"],
        bins=[
            -np.inf,
            25,
            50,
            75,
            np.inf
        ],
        labels=[
            "LOW",
            "MODERATE",
            "HIGH",
            "CRITICAL"
        ]
    )

    # Rank
    result["risk_rank"] = (
        result["risk_score"]
        .rank(
            ascending=False,
            method="first"
        )
        .astype(int)
    )

    result = result.sort_values(
        "risk_score",
        ascending=False
    )

    return result


# ============================================================
# SAVE MODEL OUTPUTS
# ============================================================

def save_outputs(result):

    print()
    print("Saving prediction outputs...")

    result.to_csv(
        PREDICTION_FILE,
        index=False
    )

    top10 = result.head(10).copy()

    top10.to_csv(
        TOP10_FILE,
        index=False
    )

    print(
        f"Saved: {PREDICTION_FILE}"
    )

    print(
        f"Saved: {TOP10_FILE}"
    )

    return top10


# ============================================================
# DISPLAY TOP 10
# ============================================================

def display_top10(top10):

    print()
    print("=" * 70)
    print("TOP 10 HIGH-RISK THERMAL ZONES")
    print("=" * 70)

    display_columns = [
        "risk_rank",
        "grid_id",
        "latitude",
        "longitude",
        "risk_score",
        "risk_level",
        "total_detections",
        "active_days",
        "avg_frp",
        "persistent_months",
        "multi_satellite_activity",
    ]

    print(
        top10[
            display_columns
        ].to_string(
            index=False
        )
    )

    print()
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    df = load_data()

    X, feature_names = prepare_features(
        df
    )

    target, components = build_risk_target(
        df
    )

    model = train_model(
        X,
        target
    )

    result = generate_predictions(
        df,
        X,
        model
    )

    top10 = save_outputs(
        result
    )

    display_top10(
        top10
    )

    print()
    print(
        f"ML features used: {len(feature_names)}"
    )

    print(
        "Risk methodology: recurrence + persistence + "
        "recent activity + FRP + satellite agreement + "
        "historical detection density"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "This is a risk-ranking model, not a verified "
        "industrial-fire classifier."
    )

    print(
        "Verified industrial labels and land-cover/"
        "industrial-infrastructure features can be added "
        "in the next stage."
    )


if __name__ == "__main__":
    main()