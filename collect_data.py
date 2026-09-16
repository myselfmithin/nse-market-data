from datetime import date
from nselib import capital_market

# Test one trading day first
trade_date = date(2026, 9, 15)

print("Downloading NSE data for:", trade_date)

data = capital_market.bhav_copy_with_delivery(
    trade_date=trade_date
)

print("Rows received:", len(data))
print(data.head())

# Save the result
data.to_csv(
    "cash_2026-09-15.csv",
    index=False
)

print("CSV created successfully.")
