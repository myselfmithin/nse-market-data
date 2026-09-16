import os
import json
import time
import pandas as pd
import requests


HISTORY_FILE = "Cash_Historical.csv"
ALERT_HISTORY_FILE = "alert_history.json"

MIN_DELIVERY_QTY = 500000


def load_alert_history():

    if not os.path.exists(ALERT_HISTORY_FILE):
        return []

    try:

        with open(
            ALERT_HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return []


def save_alert_history(alert_history):

    with open(
        ALERT_HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            alert_history,
            file,
            indent=2
        )


def send_telegram_message(message):

    bot_token = os.environ.get(
        "TELEGRAM_BOT_TOKEN"
    )

    chat_id = os.environ.get(
        "TELEGRAM_CHAT_ID"
    )

    if not bot_token:
        raise Exception(
            "TELEGRAM_BOT_TOKEN is missing."
        )

    if not chat_id:
        raise Exception(
            "TELEGRAM_CHAT_ID is missing."
        )

    url = (
        "https://api.telegram.org/bot"
        + bot_token
        + "/sendMessage"
    )

    response = requests.post(

        url,

        data={
            "chat_id": chat_id,
            "text": message
        },

        timeout=30
    )

    response.raise_for_status()


def clean_number(series):

    return pd.to_numeric(

        series
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip(),

        errors="coerce"
    )


def scan_delivery_accumulation():

    print("=" * 60)
    print("STARTING DELIVERY ACCUMULATION SCANNER")
    print("=" * 60)

    if not os.path.exists(HISTORY_FILE):

        raise Exception(
            "Cash_Historical.csv not found."
        )

    df = pd.read_csv(
        HISTORY_FILE
    )

    print(
        "Total rows loaded:",
        len(df)
    )

    required_columns = [

        "SYMBOL",
        "SERIES",
        "DATE1",
        "CLOSE_PRICE",
        "TTL_TRD_QNTY",
        "DELIV_QTY",
        "DELIV_PER"

    ]

    for column in required_columns:

        if column not in df.columns:

            raise Exception(
                "Missing column: " + column
            )

    # Keep only equity stocks

    df = df[
        df["SERIES"]
        .astype(str)
        .str.strip()
        .str.upper()
        == "EQ"
    ].copy()

    print(
        "EQ rows:",
        len(df)
    )

    # Convert dates

    df["TRADE_DATE"] = pd.to_datetime(

        df["DATE1"],

        format="%d-%b-%Y",

        errors="coerce"
    )

    # Convert numeric columns

    df["CLOSE"] = clean_number(
        df["CLOSE_PRICE"]
    )

    df["VOLUME"] = clean_number(
        df["TTL_TRD_QNTY"]
    )

    df["DELIVERY_QTY"] = clean_number(
        df["DELIV_QTY"]
    )

    df["DELIVERY_PER"] = clean_number(
        df["DELIV_PER"]
    )

    df = df.dropna(

        subset=[
            "SYMBOL",
            "TRADE_DATE",
            "CLOSE",
            "VOLUME",
            "DELIVERY_QTY",
            "DELIVERY_PER"
        ]

    )

    df = df.sort_values(

        [
            "SYMBOL",
            "TRADE_DATE"
        ]

    )

    alert_history = load_alert_history()

    candidates = []

    for symbol, stock in df.groupby(
        "SYMBOL"
    ):

        stock = stock.sort_values(
            "TRADE_DATE"
        ).reset_index(
            drop=True
        )

        # Need at least:
        # 3 sessions for delivery trend
        # 5D return
        # 3 months baseline

        if len(stock) < 30:
            continue

        latest = stock.iloc[-1]

        previous_1 = stock.iloc[-2]

        previous_2 = stock.iloc[-3]

        # ------------------------------------------------
        # 1. Delivery percentage increasing
        # ------------------------------------------------

        delivery_increasing = (

            latest["DELIVERY_PER"]
            > previous_1["DELIVERY_PER"]

            and

            previous_1["DELIVERY_PER"]
            > previous_2["DELIVERY_PER"]

        )

        if not delivery_increasing:
            continue

        # ------------------------------------------------
        # 2. Delivery quantity > 5 lakh
        # ------------------------------------------------

        if latest["DELIVERY_QTY"] <= MIN_DELIVERY_QTY:
            continue

        # ------------------------------------------------
        # 3. Previous 3-month baseline
        #
        # Exclude today's data.
        # Use up to previous 60 trading sessions
        # to represent approximately 3 months.
        # ------------------------------------------------

        historical = stock.iloc[:-1]

        baseline = historical.tail(
            60
        )

        if len(baseline) < 30:
            continue

        avg_volume_3m = baseline[
            "VOLUME"
        ].mean()

        avg_delivery_3m = baseline[
            "DELIVERY_QTY"
        ].mean()

        if avg_volume_3m <= 0:
            continue

        if avg_delivery_3m <= 0:
            continue

        # ------------------------------------------------
        # 4. Volume > 3-month average
        # ------------------------------------------------

        if latest["VOLUME"] <= avg_volume_3m:
            continue

        # ------------------------------------------------
        # 5. Delivery Qty > 3-month average
        # ------------------------------------------------

        if latest["DELIVERY_QTY"] <= avg_delivery_3m:
            continue

        # ------------------------------------------------
        # 6. Positive 5-day return
        # ------------------------------------------------

        if len(stock) < 6:
            continue

        price_5d_ago = stock.iloc[-6]["CLOSE"]

        if price_5d_ago <= 0:
            continue

        return_5d = (

            (
                latest["CLOSE"]
                / price_5d_ago
            )
            - 1
        ) * 100

        if return_5d <= 0:
            continue

        # ------------------------------------------------
        # Calculate ratios
        # ------------------------------------------------

        volume_vs_3m = (

            latest["VOLUME"]
            / avg_volume_3m
        ) * 100

        delivery_vs_3m = (

            latest["DELIVERY_QTY"]
            / avg_delivery_3m
        ) * 100

        date_key = (
            latest["TRADE_DATE"]
            .strftime("%Y-%m-%d")
        )

        alert_id = (
            str(symbol)
            + "_"
            + date_key
        )

        if alert_id in alert_history:
            continue

        candidates.append({

            "symbol": str(symbol),

            "date": date_key,

            "close": latest["CLOSE"],

            "delivery_qty":
                latest["DELIVERY_QTY"],

            "delivery_per":
                latest["DELIVERY_PER"],

            "previous_delivery_per":
                previous_1["DELIVERY_PER"],

            "previous_previous_delivery_per":
                previous_2["DELIVERY_PER"],

            "volume_vs_3m":
                volume_vs_3m,

            "delivery_vs_3m":
                delivery_vs_3m,

            "return_5d":
                return_5d

        })

    # Sort strongest delivery expansion first

    candidates.sort(

        key=lambda x:
            x["delivery_vs_3m"],

        reverse=True

    )

    # Avoid Telegram spam.
    # Maximum 20 alerts per day.

    candidates = candidates[:20]

    print(
        "New alert candidates:",
        len(candidates)
    )

    for item in candidates:

        delivery_lakh = (
            item["delivery_qty"]
            / 100000
        )

        message = f"""🔥 DELIVERY ACCUMULATION

📌 {item["symbol"]}
📅 {item["date"]}

💰 Close: ₹{item["close"]:.2f}

📦 Delivery Qty: {delivery_lakh:.2f} Lakh

📊 Delivery %:
{item["previous_previous_delivery_per"]:.2f}% → {item["previous_delivery_per"]:.2f}% → {item["delivery_per"]:.2f}% ↑

📈 Volume vs 3M Avg:
{item["volume_vs_3m"]:.0f}%

📦 Delivery Qty vs 3M Avg:
{item["delivery_vs_3m"]:.0f}%

📈 5D Return:
{item["return_5d"]:+.2f}%

⚠️ Participation-based signal.
Not proof of institutional buying.
"""

        try:

            send_telegram_message(
                message
            )

            print(
                "Telegram alert sent:",
                item["symbol"]
            )

            alert_history.append(
                item["symbol"]
                + "_"
                + item["date"]
            )

            save_alert_history(
                alert_history
            )

            time.sleep(0.5)

        except Exception as e:

            print(
                "Telegram failed for",
                item["symbol"],
                ":",
                str(e)
            )

    print("=" * 60)
    print("DELIVERY SCANNER COMPLETED")
    print("=" * 60)


if __name__ == "__main__":

    scan_delivery_accumulation()
