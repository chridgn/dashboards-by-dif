import os
import requests
from airflow.decorators import task
from airflow.operators.python import get_current_context

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data"

SERIES_IDS = [
    "CUUR0000SA0",    # CPI-U overall inflation
    "APU0000708111",  # Eggs
    "APU0000703112",  # Beef
    "APU000074714",   # Gasoline
    "CUUR0000SAH1",   # Shelter / rent
    "CUUR0000SAM1",   # Medical care
    "LNS14000000",    # Unemployment rate
]


@task
def fetch_bls_data():
    ctx = get_current_context()
    logical_date = ctx["logical_date"]

    # BLS releases month M data around the 10th of M+1.
    # Running on the 1st, we query M-1 to ensure the data is published.
    target = logical_date.subtract(months=1)
    year = str(target.year)

    payload = {
        "seriesid": SERIES_IDS,
        "startyear": year,
        "endyear": year,
        "registrationKey": os.environ["BLS_API_KEY"],
    }

    response = requests.post(BLS_API_URL, json=payload, timeout=30)
    response.raise_for_status()

    result = response.json()
    if result["status"] != "REQUEST_SUCCEEDED":
        raise ValueError(f"BLS API error: {result['message']}")

    return result