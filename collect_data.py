from nselib import capital_market

# Test one trading day first
trade_date = "15-09-2026"

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
