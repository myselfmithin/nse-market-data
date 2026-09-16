from nselib import derivatives
from datetime import datetime, timedelta
import pandas as pd
import os
import time


OUTPUT_DIRECTORY = "fno_data"

os.makedirs(
    OUTPUT_DIRECTORY,
    exist_ok=True
)


today = datetime.now()

print("=" * 60)
print("STARTING F&O DATA COLLECTION")
print("=" * 60)


# Find the latest available NSE trading day

latest_date = None

for i in range(7):

    test_date = today - timedelta(days=i)

    date_string = test_date.strftime(
        "%d-%m-%Y"
    )

    print(
        "Trying F&O date:",
        date_string
    )

    try:

        data = derivatives.fno_bhav_copy(
            trade_date=date_string
        )

        if data is not None and len(data) > 0:

            latest_date = test_date

            print(
                "F&O data found:",
                date_string
            )

            break

    except Exception as e:

        print(
            "No F&O data:",
            date_string,
            "-",
            str(e)
        )

    time.sleep(2)


if latest_date is None:

    raise Exception(
        "Could not find F&O data in the last 7 days."
    )


# Download latest F&O data

latest_date_string = latest_date.strftime(
    "%d-%m-%Y"
)

print(
    "\nDownloading latest F&O data:",
    latest_date_string
)

latest_data = derivatives.fno_bhav_copy(
    trade_date=latest_date_string
)


latest_file = os.path.join(

    OUTPUT_DIRECTORY,

    "fno_" +
    latest_date.strftime("%Y-%m-%d") +
    ".csv"

)


latest_data.to_csv(

    latest_file,

    index=False

)


print(
    "Saved:",
    latest_file
)

print(
    "Rows:",
    len(latest_data)
)


# Find previous trading day

previous_date = None

for i in range(1, 8):

    test_date = latest_date - timedelta(days=i)

    date_string = test_date.strftime(
        "%d-%m-%Y"
    )

    print(
        "Trying previous F&O date:",
        date_string
    )

    try:

        previous_data = derivatives.fno_bhav_copy(
            trade_date=date_string
        )

        if (
            previous_data is not None
            and len(previous_data) > 0
        ):

            previous_date = test_date

            print(
                "Previous F&O data found:",
                date_string
            )

            break

    except Exception as e:

        print(
            "No data:",
            date_string
        )

    time.sleep(2)


if previous_date is None:

    raise Exception(
        "Could not find previous F&O trading day."
    )


# Save previous trading day

previous_date_string = previous_date.strftime(
    "%d-%m-%Y"
)

print(
    "\nDownloading previous F&O data:",
    previous_date_string
)

previous_data = derivatives.fno_bhav_copy(
    trade_date=previous_date_string
)


previous_file = os.path.join(

    OUTPUT_DIRECTORY,

    "fno_" +
    previous_date.strftime("%Y-%m-%d") +
    ".csv"

)


previous_data.to_csv(

    previous_file,

    index=False

)


print(
    "Saved:",
    previous_file
)

print(
    "Rows:",
    len(previous_data)
)


print("=" * 60)

print(
    "F&O 2-DAY DATA COLLECTION COMPLETED"
)

print(
    "Latest:",
    latest_date.strftime("%Y-%m-%d")
)

print(
    "Previous:",
    previous_date.strftime("%Y-%m-%d")
)

print("=" * 60)
