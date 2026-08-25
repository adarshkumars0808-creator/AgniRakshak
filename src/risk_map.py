import pandas as pd
import matplotlib.pyplot as plt

print("=" * 60)
print("THERMOSCOPE - DELHI FIRE RISK MAP")
print("=" * 60)

# Load prediction data
pred = pd.read_csv("data/delhi_risk_predictions.csv")

# Load original FIRMS data
firms = pd.read_csv("data/delhi_master.csv")

print("\nLoaded prediction cells:", len(pred))
print("Loaded FIRMS observations:", len(firms))

# --------------------------------------------------
# Get coordinates for each grid cell
# --------------------------------------------------

firms["grid_id"] = (
    firms["latitude"].round(2).astype(str)
    + "_"
    + firms["longitude"].round(2).astype(str)
)

# Average coordinates for each grid
coordinates = (
    firms.groupby("grid_id")
    .agg(
        latitude=("latitude", "mean"),
        longitude=("longitude", "mean")
    )
    .reset_index()
)

# --------------------------------------------------
# Merge coordinates with predictions
# --------------------------------------------------

df = pred.merge(
    coordinates,
    on="grid_id",
    how="left"
)

print("\nCoordinates matched:",
      df["latitude"].notna().sum(),
      "/",
      len(df))

# --------------------------------------------------
# Create risk map
# --------------------------------------------------

plt.figure(figsize=(10, 8))

for risk in ["LOW", "MEDIUM", "HIGH"]:

    subset = df[df["predicted_risk"] == risk]

    if len(subset) == 0:
        continue

    plt.scatter(
        subset["longitude"],
        subset["latitude"],
        s=subset["activity_score"] * 800 + 100,
        label=risk,
        alpha=0.7
    )

# --------------------------------------------------
# Add grid labels
# --------------------------------------------------

for _, row in df.iterrows():

    if pd.notna(row["latitude"]) and pd.notna(row["longitude"]):

        plt.annotate(
            row["grid_id"],
            (row["longitude"], row["latitude"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8
        )

plt.xlabel("Longitude")
plt.ylabel("Latitude")

plt.title("THERMOSCOPE - Delhi Fire Risk Map")

plt.legend()
plt.grid(True, alpha=0.3)

# --------------------------------------------------
# Save map
# --------------------------------------------------

output = "data/delhi_fire_risk_map.png"

plt.savefig(
    output,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

# --------------------------------------------------
# Summary
# --------------------------------------------------

print("\nRisk distribution:")
print(df["predicted_risk"].value_counts())

print("\nMap saved to:")
print(output)

print("\n" + "=" * 60)
print("STEP 4B COMPLETE")
print("=" * 60)