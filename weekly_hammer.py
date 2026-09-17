import pandas as pd
import os

# ============================================================
# SETTINGS
# ============================================================

INPUT_FILE = "Cash_Historical.csv"

# ============================================================
# LOAD CASH DATA
# ============================================================

if not os.path.exists(INPUT_FILE):
    print(f"File not found: {INPUT_FILE}")
    raise SystemExit(1)

df = pd.read_csv(INPUT_FILE)

print("Cash data loaded.")
print("Rows:", len(df))

# ============================================================
# CLEAN DATA
# ============================================================

df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")

for col in ["OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(
    subset=[
        "DATE",
        "SYMBOL",
        "OPEN_PRICE",
        "HIGH_PRICE",
        "LOW_PRICE",
        "CLOSE_PRICE"
    ]
)

# Keep EQ stocks only
if "SERIES" in df.columns:
    df = df[df["SERIES"] == "EQ"].copy()

# ============================================================
# CREATE WEEKLY OHLC
# ============================================================

df = df.sort_values(["SYMBOL", "DATE"])

df["WEEK"] = df["DATE"].dt.to_period("W-FRI")

weekly = (
    df.groupby(["SYMBOL", "WEEK"])
    .agg(
        Week_Open=("OPEN_PRICE", "first"),
        Week_High=("HIGH_PRICE", "max"),
        Week_Low=("LOW_PRICE", "min"),
        Week_Close=("CLOSE_PRICE", "last"),
        Trading_Days=("DATE", "count"),
        Last_Date=("DATE", "max")
    )
    .reset_index()
)

# ============================================================
# REMOVE CURRENT INCOMPLETE WEEK
# ============================================================

latest_date = df["DATE"].max()
current_week = latest_date.to_period("W-FRI")

weekly = weekly[
    weekly["WEEK"] < current_week
].copy()

print("Completed weekly candles:", len(weekly))

# ============================================================
# HAMMER CALCULATION
# ============================================================

weekly["Body"] = (
    weekly["Week_Close"] - weekly["Week_Open"]
).abs()

weekly["Range"] = (
    weekly["Week_High"] - weekly["Week_Low"]
)

weekly["Upper_Wick"] = (
    weekly["Week_High"]
    - weekly[["Week_Open", "Week_Close"]].max(axis=1)
)

weekly["Lower_Wick"] = (
    weekly[["Week_Open", "Week_Close"]].min(axis=1)
    - weekly["Week_Low"]
)

# Avoid division problems
weekly = weekly[weekly["Range"] > 0].copy()

# ============================================================
# HAMMER CONDITIONS
# ============================================================

weekly["Hammer"] = (
    # Small body
    (weekly["Body"] <= weekly["Range"] * 0.35)

    &

    # Long lower wick
    (weekly["Lower_Wick"] >= weekly["Body"] * 2)

    &

    # Small upper wick
    (weekly["Upper_Wick"] <= weekly["Body"] * 0.5)
)

# ============================================================
# SHOW HAMMERS
# ============================================================

hammers = weekly[weekly["Hammer"]].copy()

hammers = hammers.sort_values(
    ["WEEK", "SYMBOL"],
    ascending=[False, True]
)

print()
print("==========================================")
print("WEEKLY HAMMER SCANNER")
print("==========================================")
print("Hammer candles found:", len(hammers))
print()

if hammers.empty:
    print("No weekly hammer patterns found.")

else:
    display_columns = [
        "SYMBOL",
        "WEEK",
        "Week_Open",
        "Week_High",
        "Week_Low",
        "Week_Close",
        "Body",
        "Upper_Wick",
        "Lower_Wick",
        "Trading_Days"
    ]

    print(
        hammers[display_columns]
        .to_string(index=False)
    )

print()
print("Weekly hammer scan completed.")
