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
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "TradDt",
    "TckrSymb",
    "OpnPric",
    "HghPric",
    "LwPric",
    "ClsPric"
]

missing = [
    col for col in required_columns
    if col not in df.columns
]

if missing:
    print("Missing columns:", missing)
    raise SystemExit(1)

# ============================================================
# CLEAN DATA
# ============================================================

df["TradDt"] = pd.to_datetime(
    df["TradDt"],
    errors="coerce"
)

for col in [
    "OpnPric",
    "HghPric",
    "LwPric",
    "ClsPric"
]:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

df = df.dropna(
    subset=[
        "TradDt",
        "TckrSymb",
        "OpnPric",
        "HghPric",
        "LwPric",
        "ClsPric"
    ]
)

# Keep EQ stocks only
if "SctySrs" in df.columns:
    df = df[
        df["SctySrs"].astype(str).str.strip() == "EQ"
    ].copy()

# ============================================================
# CREATE WEEKLY OHLC
# ============================================================

df = df.sort_values(
    ["TckrSymb", "TradDt"]
)

df["WEEK"] = df["TradDt"].dt.to_period("W-FRI")

weekly = (
    df.groupby(["TckrSymb", "WEEK"])
    .agg(
        Week_Open=("OpnPric", "first"),
        Week_High=("HghPric", "max"),
        Week_Low=("LwPric", "min"),
        Week_Close=("ClsPric", "last"),
        Trading_Days=("TradDt", "count"),
        Last_Date=("TradDt", "max")
    )
    .reset_index()
)

# ============================================================
# REMOVE CURRENT INCOMPLETE WEEK
# ============================================================

latest_date = df["TradDt"].max()
current_week = latest_date.to_period("W-FRI")

weekly = weekly[
    weekly["WEEK"] < current_week
].copy()

print("Completed weekly candles:", len(weekly))

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
    - weekly[
        ["Week_Open", "Week_Close"]
    ].max(axis=1)
)

weekly["Lower_Wick"] = (
    weekly[
        ["Week_Open", "Week_Close"]
    ].min(axis=1)
    - weekly["Week_Low"]
)

weekly = weekly[
    weekly["Range"] > 0
].copy()

# ============================================================
# HAMMER CONDITIONS
# ============================================================

weekly["Hammer"] = (
    (weekly["Body"] <= weekly["Range"] * 0.35)
    &
    (weekly["Lower_Wick"] >= weekly["Body"] * 2)
    &
    (weekly["Upper_Wick"] <= weekly["Body"] * 0.5)
)

# ============================================================
# SHOW HAMMERS
# ============================================================

hammers = weekly[
    weekly["Hammer"]
].copy()

hammers = hammers.sort_values(
    ["WEEK", "TckrSymb"],
    ascending=[False, True]
)

print()
print("==========================================")
print("WEEKLY HAMMER SCANNER")
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
        "TckrSymb",
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
