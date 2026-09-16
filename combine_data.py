import pandas as pd
import glob
import os

# Find all daily cash CSV files
files = glob.glob("cash_data/cash_*.csv")

print("Files found:", len(files))

if not files:
    raise Exception("No cash CSV files found.")

# Read all files
dataframes = []

for file in sorted(files):
    print("Reading:", file)

    df = pd.read_csv(file)
    dataframes.append(df)

# Combine everything
combined = pd.concat(dataframes, ignore_index=True)

# Remove duplicate rows if any
combined = combined.drop_duplicates()

# Sort by date and symbol
combined = combined.sort_values(
    by=["DATE1", "SYMBOL"]
)

# Save consolidated file
output_file = "Cash_Historical.csv"

combined.to_csv(
    output_file,
    index=False
)

print("=" * 60)
print("Combined rows:", len(combined))
print("Output file:", output_file)
print("Files combined:", len(files))
print("=" * 60)
