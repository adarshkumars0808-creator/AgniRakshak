import pandas as pd

# Load FIRMS data
file_path = "data/delhi_firms.csv"

df = pd.read_csv(file_path)

print("=" * 60)
print("THERMOSCOPE - DELHI FIRMS DATA ANALYSIS")
print("=" * 60)

# --------------------------------------------------
# 1. BASIC INFORMATION
# --------------------------------------------------

print("\n1. BASIC INFORMATION")
print("-" * 40)

print("Total thermal detections:", len(df))
print("Number of columns:", len(df.columns))

print("\nColumns:")
print(df.columns.tolist())


# --------------------------------------------------
# 2. DATE-WISE DETECTIONS
# --------------------------------------------------

print("\n2. DATE-WISE DETECTIONS")
print("-" * 40)

df["acq_date"] = pd.to_datetime(df["acq_date"])

date_counts = df["acq_date"].dt.date.value_counts().sort_index()

for date, count in date_counts.items():
    print(f"{date} : {count} detections")


# --------------------------------------------------
# 3. DAY VS NIGHT
# --------------------------------------------------

print("\n3. DAY VS NIGHT")
print("-" * 40)

print(df["daynight"].value_counts())


# --------------------------------------------------
# 4. FRP ANALYSIS
# --------------------------------------------------

print("\n4. FRP ANALYSIS")
print("-" * 40)

print("Average FRP:", round(df["frp"].mean(), 2))
print("Maximum FRP:", round(df["frp"].max(), 2))
print("Minimum FRP:", round(df["frp"].min(), 2))

print("\nTop 5 highest FRP detections:")

top_frp = df.nlargest(5, "frp")[
    ["latitude", "longitude", "acq_date", "acq_time", "frp"]
]

print(top_frp.to_string(index=False))


# --------------------------------------------------
# 5. TEMPERATURE ANALYSIS
# --------------------------------------------------

print("\n5. TEMPERATURE ANALYSIS")
print("-" * 40)

print("Average Brightness Temperature:",
      round(df["bright_ti4"].mean(), 2))

print("Maximum Brightness Temperature:",
      round(df["bright_ti4"].max(), 2))

print("Minimum Brightness Temperature:",
      round(df["bright_ti4"].min(), 2))


# --------------------------------------------------
# 6. CONFIDENCE ANALYSIS
# --------------------------------------------------

print("\n6. CONFIDENCE ANALYSIS")
print("-" * 40)

print(df["confidence"].value_counts())


# --------------------------------------------------
# 7. GEOGRAPHIC RANGE
# --------------------------------------------------

print("\n7. GEOGRAPHIC RANGE")
print("-" * 40)

print("Latitude range:",
      round(df["latitude"].min(), 5),
      "to",
      round(df["latitude"].max(), 5))

print("Longitude range:",
      round(df["longitude"].min(), 5),
      "to",
      round(df["longitude"].max(), 5))


# --------------------------------------------------
# 8. MISSING VALUES
# --------------------------------------------------

print("\n8. MISSING VALUES")
print("-" * 40)

missing = df.isnull().sum()

print(missing[missing > 0])


# --------------------------------------------------
# 9. SUMMARY
# --------------------------------------------------

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)