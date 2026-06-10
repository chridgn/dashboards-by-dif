"""
One-time historical backfill for FRED data (all available history).
Fetches full observation history for all five series and upserts into metrics.

Run from repo root:
  docker exec src-airflow-scheduler-1 python /opt/airflow/scripts/backfill_fred.py
"""

import os
import sys
from datetime import date

import psycopg2
import requests

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

SERIES_METADATA = {
    "FEDFUNDS":     ("Federal Funds Rate",               "percent"),
    "MORTGAGE30US": ("30-Year Fixed Mortgage Rate",      "percent"),
    "DSPIC96":      ("Real Disposable Personal Income",  "usd_bn"),
    "UMCSENT":      ("Consumer Sentiment",               "index"),
    "M2SL":         ("M2 Money Supply",                  "usd_bn"),
}


def fetch_series(api_key, series_id):
    r = requests.get(FRED_BASE_URL, params={
        "api_key":    api_key,
        "series_id":  series_id,
        "file_type":  "json",
        "sort_order": "asc",
        "limit":      100000,
    }, timeout=60)
    r.raise_for_status()
    data = r.json()
    if "error_code" in data:
        raise ValueError(f"FRED API error ({series_id}): {data.get('error_message')}")
    return data["observations"]


def parse_records(observations, series_id, metric_name, unit):
    records = []
    for obs in observations:
        if obs["value"] == ".":
            continue
        records.append((
            date.fromisoformat(obs["date"]),
            "FRED",
            series_id,
            metric_name,
            float(obs["value"]),
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
            ON CONFLICT (series_id, metric_time) DO UPDATE
                SET value = EXCLUDED.value, fetched_at = NOW()
            """,
            records,
        )
    conn.commit()


def main():
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print("ERROR: FRED_API_KEY not set")
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
        for series_id, (metric_name, unit) in SERIES_METADATA.items():
            print(f"Fetching {metric_name} ({series_id}) ...")
            observations = fetch_series(api_key, series_id)
            records = parse_records(observations, series_id, metric_name, unit)
            upsert_records(conn, records)
            print(f"  Upserted {len(records)} records")
            total += len(records)
    finally:
        conn.close()

    print(f"\nDone. {total} total records upserted into metrics.economic_indicators.")


if __name__ == "__main__":
    main()
