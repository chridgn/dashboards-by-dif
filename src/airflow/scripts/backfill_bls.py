"""
One-time historical backfill for BLS data from 1996 to present.
Queries in two 20-year chunks (BLS API limit) and upserts into metrics.

Run from repo root:
  docker exec src-airflow-scheduler-1 python /opt/airflow/scripts/backfill_bls.py
"""

import os
import sys
from datetime import date

import psycopg2
import requests

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

SERIES_METADATA = {
    "CUUR0000SA0":   ("CPI-U overall inflation", "index"),
    "APU0000708111": ("Eggs",                    "usd"),
    "APU0000703112": ("Beef",                    "usd"),
    "APU000074714":  ("Gasoline",                "usd"),
    "CUUR0000SAH1":  ("Shelter / rent",          "index"),
    "CUUR0000SAM1":  ("Medical care",            "index"),
    "LNS14000000":   ("Unemployment rate",       "percent"),
}

# BLS API caps date ranges at 20 years per request
DATE_RANGES = [
    ("1996", "2015"),
    ("2016", "2026"),
]


def fetch_range(start_year, end_year, api_key):
    payload = {
        "seriesid": SERIES_IDS,
        "startyear": start_year,
        "endyear": end_year,
        "registrationKey": api_key,
    }
    response = requests.post(BLS_API_URL, json=payload, timeout=60)
    response.raise_for_status()
    result = response.json()
    if result["status"] != "REQUEST_SUCCEEDED":
        raise ValueError(f"BLS API error: {result['message']}")
    return result


def parse_records(result):
    records = []
    for series in result["Results"]["series"]:
        metric_name, unit = SERIES_METADATA.get(
            series["seriesID"], (series["seriesID"], "unknown")
        )
        for point in series["data"]:
            if not point["period"].startswith("M"):
                continue
            if point["value"] == "-":
                continue
            records.append((
                date(int(point["year"]), int(point["period"][1:]), 1),
                "BLS",
                series["seriesID"],
                metric_name,
                float(point["value"]),
                unit,
            ))
    return records


def upsert_records(conn, records):
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO metrics.economic_indicators
                (metric_time, source, series_id, metric_name, value, unit)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (series_id, metric_time)
            DO UPDATE SET
                value      = EXCLUDED.value,
                fetched_at = NOW()
            """,
            records,
        )
    conn.commit()


def main():
    api_key = os.environ.get("BLS_API_KEY")
    if not api_key:
        print("ERROR: BLS_API_KEY not set")
        sys.exit(1)

    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["DASHBOARD_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )

    total = 0
    try:
        for start_year, end_year in DATE_RANGES:
            print(f"Fetching {start_year}–{end_year} ...")
            result = fetch_range(start_year, end_year, api_key)
            records = parse_records(result)
            upsert_records(conn, records)
            print(f"  Upserted {len(records)} records")
            total += len(records)
    finally:
        conn.close()

    print(f"\nDone. {total} total records upserted into metrics.economic_indicators.")


if __name__ == "__main__":
    main()
