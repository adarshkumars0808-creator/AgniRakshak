import pandas as pd
import matplotlib.pyplot as plt

print("=" * 60)
print("THERMOSCOPE - DELHI FIRE RISK MAP")
print("=" * 60)

# Load prediction data
pred = pd.read_csv("data/delhi_risk_predictions.csv")

print("\nLoaded prediction cells:", len(pred))

# --------------------------------------------------
# Use grid coordinates directly from predictions
# --------------------------------------------------

df = pred.copy()

df["latitude"] = pd.to_numeric(
    df["grid_lat"],
    errors="coerce"
)

df["longitude"] = pd.to_numeric(
    df["grid_lon"],
    errors="coerce"
)

print(
    "\nCoordinates matched:",
    df["latitude"].notna().sum(),
    "/",
    len(df)
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

    subset = df[df["risk_category"] == risk]

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



# --------------------------------------------------
# Summary
# --------------------------------------------------

print("\nRisk distribution:")
print(df["risk_category"].value_counts())

print("\nMap saved to:")
print(output)

print("\n" + "=" * 60)
print("STEP 4B COMPLETE")
print("=" * 60)