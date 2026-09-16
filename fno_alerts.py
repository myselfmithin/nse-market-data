import pandas as pd
import requests
import os
import glob
import json


# ============================================================
# SETTINGS
# ============================================================

BOT_TOKEN = os.getenv("FNO_TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("FNO_TELEGRAM_CHAT_ID")

MIN_OI_VOLUME_RATIO = 5
MIN_VOLUME = 10000
MAX_ALERTS = 20

HISTORY_FILE = "fno_alert_history.json"


# ============================================================
# CHECK TELEGRAM SETTINGS
# ============================================================

if not BOT_TOKEN or not CHAT_ID:
    raise Exception(
        "FNO Telegram secrets are missing."
    )


# ============================================================
# LOAD ALERT HISTORY
# ============================================================

if os.path.exists(HISTORY_FILE):

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            alert_history = json.load(file)

    except Exception:

        alert_history = {}

else:

    alert_history = {}


# ============================================================
# FIND TWO LATEST F&O FILES
# ============================================================

files = sorted(
    glob.glob(
        "fno_data/fno_*.csv"
    ),
    reverse=True
)


if len(files) < 2:

    raise Exception(
        "Need at least 2 F&O daily files."
    )


latest_file = files[0]
previous_file = files[1]


print("=" * 60)
print("F&O TELEGRAM SCANNER")
print("=" * 60)

print("Latest file:")
print(latest_file)

print("Previous file:")
print(previous_file)


# ============================================================
# LOAD DATA
# ============================================================

latest = pd.read_csv(
    latest_file
)

previous = pd.read_csv(
    previous_file
)


print(
    "\nLatest rows:",
    len(latest)
)

print(
    "Previous rows:",
    len(previous)
)


# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

latest.columns = latest.columns.str.strip()
previous.columns = previous.columns.str.strip()


# ============================================================
# STOCK OPTIONS ONLY
# STO = STOCK DERIVATIVES
# ============================================================

latest = latest[
    (latest["FinInstrmTp"] == "STO") &
    (latest["OptnTp"].isin(["CE", "PE"]))
].copy()


previous = previous[
    (previous["FinInstrmTp"] == "STO") &
    (previous["OptnTp"].isin(["CE", "PE"]))
].copy()


print(
    "\nStock option rows:"
)

print(
    "Latest:",
    len(latest)
)

print(
    "Previous:",
    len(previous)
)


# ============================================================
# NUMERIC COLUMNS
# ============================================================

numeric_columns = [

    "StrkPric",
    "ClsPric",
    "UndrlygPric",
    "OpnIntrst",
    "ChngInOpnIntrst",
    "TtlTradgVol"

]


for column in numeric_columns:

    latest[column] = pd.to_numeric(
        latest[column],
        errors="coerce"
    )

    previous[column] = pd.to_numeric(
        previous[column],
        errors="coerce"
    )


# ============================================================
# CLEAN EXPIRY
# ============================================================

latest["XpryDt"] = pd.to_datetime(
    latest["XpryDt"],
    errors="coerce"
)

previous["XpryDt"] = pd.to_datetime(
    previous["XpryDt"],
    errors="coerce"
)


# ============================================================
# REMOVE INVALID DATA
# ============================================================

required_columns = [

    "TckrSymb",
    "XpryDt",
    "StrkPric",
    "OptnTp",
    "ClsPric",
    "UndrlygPric",
    "OpnIntrst",
    "ChngInOpnIntrst",
    "TtlTradgVol"

]


latest = latest.dropna(
    subset=required_columns
)

previous = previous.dropna(
    subset=required_columns
)


# ============================================================
# FIND NEAREST EXPIRY FOR EACH STOCK
# ============================================================

latest_expiry = (

    latest
    .groupby("TckrSymb")["XpryDt"]
    .min()
    .reset_index()

)

latest_expiry = latest_expiry.rename(
    columns={
        "XpryDt": "SelectedExpiry"
    }
)


latest = latest.merge(
    latest_expiry,
    on="TckrSymb",
    how="inner"
)


latest = latest[
    latest["XpryDt"]
    ==
    latest["SelectedExpiry"]
].copy()


# ============================================================
# PREVIOUS DAY SAME CONTRACT
# ============================================================

previous_key = [

    "TckrSymb",
    "XpryDt",
    "StrkPric",
    "OptnTp"

]


previous_compare = previous[
    previous_key +
    [
        "ClsPric",
        "UndrlygPric",
        "OpnIntrst",
        "ChngInOpnIntrst",
        "TtlTradgVol"
    ]
].copy()


previous_compare = previous_compare.rename(

    columns={

        "ClsPric":
            "Prev_OptionPrice",

        "UndrlygPric":
            "Prev_UnderlyingPrice",

        "OpnIntrst":
            "Prev_OI",

        "ChngInOpnIntrst":
            "Prev_COI",

        "TtlTradgVol":
            "Prev_Volume"

    }

)


# ============================================================
# MERGE TWO DAYS
# ============================================================

merged = latest.merge(

    previous_compare,

    on=previous_key,

    how="inner"

)


print(
    "\nContracts available for comparison:",
    len(merged)
)


# ============================================================
# OI / VOLUME
# ============================================================

merged = merged[
    merged["TtlTradgVol"] > 0
].copy()


merged["OI_Volume_Ratio"] = (

    merged["OpnIntrst"]
    /
    merged["TtlTradgVol"]

)


# ============================================================
# USER'S CONDITIONS
# ============================================================

signal = merged[
    (merged["OI_Volume_Ratio"] > MIN_OI_VOLUME_RATIO)
    &
    (merged["TtlTradgVol"] >= MIN_VOLUME)
    &
    (merged["ChngInOpnIntrst"] > 0)
    &
    (merged["ChngInOpnIntrst"] > merged["Prev_COI"])
].copy()
      
# ============================================================
# PRICE CHANGE
# ============================================================

signal["PriceChangePct"] = (

    (
        signal["UndrlygPric"]
        -
        signal["Prev_UnderlyingPrice"]
    )

    /

    signal["Prev_UnderlyingPrice"]

) * 100


# ============================================================
# SORT SIGNALS
# ============================================================

signal = signal.sort_values(

    by=[
        "OI_Volume_Ratio",
        "PriceChangePct"
    ],

    ascending=False

)


signal = signal.head(
    MAX_ALERTS
)


print(
    "\nPotential signals:",
    len(signal)
)


# ============================================================
# NUMBER FORMATTING
# ============================================================

def format_price(value):

    try:

        return f"₹{value:,.2f}"

    except:

        return "-"


def format_lakh(value):

    try:

        return f"{value / 100000:.2f}L"

    except:

        return "-"
def format_contracts(value):
    try:
        return f"{value:,.0f}"
    except:
        return "-"

# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    response = requests.post(

        url,

        data={
            "chat_id": CHAT_ID,
            "text": message
        },

        timeout=30

    )

    response.raise_for_status()


# ============================================================
# SEND NEW ALERTS
# ============================================================

alerts_sent = 0

latest_trade_date = pd.to_datetime(
    latest["TradDt"].iloc[0]
).strftime("%Y-%m-%d")


for _, row in signal.iterrows():

    symbol = str(
        row["TckrSymb"]
    )

    option_type = str(
        row["OptnTp"]
    )

    expiry = row["XpryDt"].strftime(
        "%d-%b-%Y"
    )

    strike = format_price(
        row["StrkPric"]
    )

    # Unique contract identifier
    alert_key = (

        latest_trade_date
        + "_"
        + symbol
        + "_"
        + expiry
        + "_"
        + str(row["StrkPric"])
        + "_"
        + option_type

    )


    # ========================================================
    # DUPLICATE CHECK
    # ========================================================

    if alert_key in alert_history:

        print(
            "Already alerted:",
            symbol,
            option_type,
            strike
        )

        continue


    option_price = format_price(
        row["ClsPric"]
    )

    previous_option_price = format_price(
        row["Prev_OptionPrice"]
    )

    underlying = format_price(
        row["UndrlygPric"]
    )

    previous_underlying = format_price(
        row["Prev_UnderlyingPrice"]
    )

    oi = format_lakh(
        row["OpnIntrst"]
    )

    coi = format_lakh(
        row["ChngInOpnIntrst"]
    )

    previous_coi = format_lakh(
        row["Prev_COI"]
    )

    volume = format_contracts(row["TtlTradgVol"])

    ratio = row["OI_Volume_Ratio"]

    price_change = row["PriceChangePct"]


    message = f"""
🟢 F&O LONG BUILDUP PROXY

📌 {symbol}
📍 {option_type}
🎯 Strike: {strike}
📅 Expiry: {expiry}

💰 Option Price:
{previous_option_price} → {option_price} ↑

📈 Underlying:
{previous_underlying} → {underlying} ↑

📊 OI:
{oi} contracts

📈 COI:
{previous_coi} → {coi} ↑

📊 Volume:
{volume} contracts

🔥 OI / Volume:
{ratio:.1f}x

📈 Underlying Change:
+{price_change:.2f}%

⚠️ Data-based market interpretation.
Not proof of institutional buying.
"""


    print(
        "\nSending new alert:",
        symbol,
        option_type,
        strike
    )


    send_telegram(
        message.strip()
    )


    # Record alert
    alert_history[alert_key] = {

        "date": latest_trade_date,

        "symbol": symbol,

        "option": option_type,

        "expiry": expiry,

        "strike": float(
            row["StrkPric"]
        )

    }


    alerts_sent += 1


# ============================================================
# SAVE HISTORY
# ============================================================

with open(

    HISTORY_FILE,

    "w",

    encoding="utf-8"

) as file:

    json.dump(

        alert_history,

        file,

        indent=2

    )


print(
    "\nNew alerts sent:",
    alerts_sent
)

print(
    "F&O scanner completed."
)
