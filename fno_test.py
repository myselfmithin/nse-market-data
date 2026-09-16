from nselib import derivatives


print("=" * 60)
print("Testing NSE F&O data")
print("=" * 60)

trade_date = "16-09-2026"

print("Downloading F&O data for:", trade_date)

try:

    data = derivatives.fno_bhav_copy(
        trade_date=trade_date
    )

    print("Rows received:", len(data))

    print("\nColumns:")
    print(list(data.columns))

    print("\nFirst 10 rows:")
    print(data.head(10))

    data.to_csv(
        "fno_test.csv",
        index=False
    )

    print("\nF&O test CSV created successfully.")

except Exception as e:

    print("\nF&O download failed.")

    print("Error:")
    print(e)

    raise
