import pandas as pd

MAP_KEY = "e7ee29a40aabd3717c2bbecc11d68876"

# Delhi NCR approximate bounding box
west = 76.80
south = 28.35
east = 77.50
north = 28.90

url = (
    f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
    f"{MAP_KEY}/VIIRS_NOAA20_NRT/"
    f"{west},{south},{east},{north}/5"
)

print("Downloading FIRMS data...")

df = pd.read_csv(url)

print("\nDownload successful!")
print("Total observations:", len(df))

print("\nColumns:")
print(df.columns.tolist())

print("\nFirst 5 rows:")
print(df.head())

# Save data
df.to_csv("data/delhi_firms.csv", index=False)

print("\nSaved as data/delhi_firms.csv")