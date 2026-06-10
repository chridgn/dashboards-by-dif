import os
import requests
from datetime import date, timedelta
from airflow.decorators import task

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

SERIES_IDS = [
    "FEDFUNDS",     # Federal funds rate (monthly)
    "MORTGAGE30US", # 30-year fixed mortgage rate (weekly)
    "DSPIC96",      # Real disposable personal income (monthly)
    "UMCSENT",      # Consumer sentiment — Univ. of Michigan (monthly)
    "M2SL",         # M2 money supply (monthly)
]


@task
def fetch_fred_data() -> dict:
    key = os.environ["FRED_API_KEY"]
    start = (date.today() - timedelta(days=120)).isoformat()
    result = {}
    for sid in SERIES_IDS:
        r = requests.get(FRED_BASE_URL, params={
            "api_key":           key,
            "series_id":         sid,
            "file_type":         "json",
            "sort_order":        "asc",
            "observation_start": start,
        }, timeout=30)
        r.raise_for_status()
        data = r.json()
        if "error_code" in data:
            raise ValueError(f"FRED API error ({sid}): {data.get('error_message')}")
        result[sid] = data
    return result
