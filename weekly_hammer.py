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
print("Columns:", df.columns.tolist())

# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

df.columns = df.columns.str.strip()

# ============================================================
# CLEAN DATA
# ============================================================

df["DATE1"] = pd.to_datetime(
    df["DATE1"],
    errors="coerce"
)

for col in [
    "OPEN_PRICE",
    "HIGH_PRICE",
    "LOW_PRICE",
    "CLOSE_PRICE"
]:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

df = df.dropna(
    subset=[
        "DATE1",
        "SYMBOL",
        "OPEN_PRICE",
        "HIGH_PRICE",
        "LOW_PRICE",
        "CLOSE_PRICE"
    ]
)

# ============================================================
# KEEP EQUITY STOCKS ONLY
# ============================================================

df = df[
    df["SERIES"].astype(str).str.strip() == "EQ"
].copy()

# ============================================================
# REMOVE ETF / INDEX-LIKE SYMBOLS
# ============================================================

exclude_keywords = [
    "ETF",
    "BEES",
    "LIQUID",
    "SILVER",
    "GOLD",
    "MOM",
    "SENSEX",
    "NIFTY",
    "MID150",
    "MIDSMALL",
    "INFRABEES",
    "PHARMABEES"
]

pattern = "|".join(exclude_keywords)

df = df[
    ~df["SYMBOL"]
    .astype(str)
    .str.upper()
    .str.contains(pattern, na=False)
].copy()

# ============================================================
# CREATE WEEKLY OHLC
# ============================================================

df = df.sort_values(
    ["SYMBOL", "DATE1"]
)

df["WEEK"] = df["DATE1"].dt.to_period("W-FRI")

weekly = (
    df.groupby(["SYMBOL", "WEEK"])
    .agg(
        Week_Open=("OPEN_PRICE", "first"),
        Week_High=("HIGH_PRICE", "max"),
        Week_Low=("LOW_PRICE", "min"),
        Week_Close=("CLOSE_PRICE", "last"),
        Trading_Days=("DATE1", "count"),
        Last_Date=("DATE1", "max")
    )
    .reset_index()
)

# ============================================================
# REMOVE CURRENT INCOMPLETE WEEK
# ============================================================

latest_date = df["DATE1"].max()

current_week = latest_date.to_period("W-FRI")

weekly = weekly[
    weekly["WEEK"] < current_week
].copy()

print(
    "Completed weekly candles:",
    len(weekly)
)

# ============================================================
# REQUIRE FULL 5-DAY WEEK
# ============================================================

weekly = weekly[
    weekly["Trading_Days"] == 5
].copy()

print(
    "5-day weekly candles:",
    len(weekly)
)

# ============================================================
# HAMMER CALCULATION
# ============================================================

weekly["Body"] = (
    weekly["Week_Close"]
    - weekly["Week_Open"]
).abs()

weekly["Range"] = (
    weekly["Week_High"]
    - weekly["Week_Low"]
)

weekly["Upper_Wick"] = (
    weekly["Week_High"]
    -
    weekly[
        ["Week_Open", "Week_Close"]
    ].max(axis=1)
)

weekly["Lower_Wick"] = (
    weekly[
        ["Week_Open", "Week_Close"]
    ].min(axis=1)
    -
    weekly["Week_Low"]
)

# ============================================================
# REMOVE ZERO-RANGE CANDLES
# ============================================================

weekly = weekly[
    weekly["Range"] > 0
].copy()

# ============================================================
# CLOSE POSITION INSIDE WEEKLY RANGE
# ============================================================

weekly["Close_Position"] = (
    (weekly["Week_Close"] - weekly["Week_Low"])
    /
    weekly["Range"]
)

# ============================================================
# STRICT WEEKLY HAMMER CONDITIONS
# ============================================================

weekly["Hammer"] = (
    # Small body
    (weekly["Body"] <= weekly["Range"] * 0.30)

    &

    # Long lower wick
    (weekly["Lower_Wick"] >= weekly["Body"] * 2.5)

    &

    # Very small upper wick
    (weekly["Upper_Wick"] <= weekly["Body"] * 0.30)

    &

    # Close in upper 30% of weekly range
    (weekly["Close_Position"] >= 0.70)
)

# ============================================================
# GET HAMMERS
# ============================================================

hammers = weekly[
    weekly["Hammer"]
].copy()

hammers = hammers.sort_values(
    ["WEEK", "SYMBOL"],
    ascending=[False, True]
)

# ============================================================
# DISPLAY RESULTS
# ============================================================

print()
print("==========================================")
print("STRICT WEEKLY HAMMER SCANNER")
print("==========================================")

print(
    "Hammer candles found:",
    len(hammers)
)

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
        "Close_Position",
        "Trading_Days"
    ]

    print(
        hammers[display_columns]
        .to_string(index=False)
    )

print()
print("Weekly hammer scan completed.")
