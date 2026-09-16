from datetime import date, timedelta
from nselib import capital_market
import os
import time

START_DATE = date(2026, 6, 1)
END_DATE = date(2026, 9, 15)

output_folder = "cash_data"
os.makedirs(output_folder, exist_ok=True)

current_date = START_DATE

while current_date <= END_DATE:

    # Skip Saturday and Sunday
    if current_date.weekday() < 5:

        trade_date = current_date.strftime("%d-%m-%Y")

        print("=" * 60)
        print("Downloading NSE data for:", trade_date)

        try:
            data = capital_market.bhav_copy_with_delivery(
                trade_date=trade_date
            )

            if data is not None and len(data) > 0:

                filename = current_date.strftime(
                    "cash_%Y-%m-%d.csv"
                )

                filepath = os.path.join(
                    output_folder,
                    filename
                )

                data.to_csv(
                    filepath,
                    index=False
                )

                print("Rows received:", len(data))
                print("Saved:", filepath)

            else:
                print("No data available for:", trade_date)

        except Exception as e:
            print("ERROR for", trade_date)
            print(e)

        # Small pause between requests
        time.sleep(2)

    current_date += timedelta(days=1)

print("=" * 60)
print("90-day data collection completed.")
