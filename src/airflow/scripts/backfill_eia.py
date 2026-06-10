"""
One-time historical backfill for EIA data (gasoline, electricity, natural gas).
Fetches all available California history and upserts into metrics.

Run from repo root:
  docker exec src-airflow-scheduler-1 python /opt/airflow/scripts/backfill_eia.py
"""

import os
import sys
import time
from datetime import date

import psycopg2
import requests

EIA_BASE_URL = "https://api.eia.gov/v2"

# value_scale converts raw API units to what we store:
#   electricity: cents/kWh → dollars/kWh (*0.01)
#   gas, natural gas: already in dollars (*1.0)
SERIES_CONFIG = [
    {
        "label":       "California Regular Gasoline (weekly)",
        "route":       "petroleum/pri/gnd/data",
        "params": {
            "data[]":            "value",
            "facets[duoarea][]": "SCA",
            "facets[product][]": "EPMR",
            "frequency":         "weekly",
            "sort[0][column]":   "period",
            "sort[0][direction]":"asc",
        },
        "series_id":   "EIA_GAS_CA",
        "metric_name": "California Regular Gasoline",
        "unit":        "usd",
        "value_field": "value",
        "monthly":     False,
        "value_scale": 1.0,
    },
    {
        "label":       "California Residential Electricity (monthly)",
        "route":       "electricity/retail-sales/data",
        "params": {
            "data[]":             "price",
            "facets[stateid][]":  "CA",
            "facets[sectorid][]": "RES",
            "frequency":          "monthly",
            "sort[0][column]":    "period",
            "sort[0][direction]": "asc",
        },
        "series_id":   "EIA_ELEC_CA",
        "metric_name": "California Residential Electricity",
        "unit":        "usd",
        "value_field": "price",
        "monthly":     True,
        "value_scale": 0.01,
    },
    {
        "label":       "California Residential Natural Gas (monthly)",
        "route":       "natural-gas/pri/sum/data",
        "params": {
            "data[]":            "value",
            "facets[duoarea][]": "SCA",
            "facets[process][]": "PRS",
            "frequency":         "monthly",
            "sort[0][column]":   "period",
            "sort[0][direction]":"asc",
        },
        "series_id":   "EIA_NATGAS_CA",
        "metric_name": "California Residential Natural Gas",
        "unit":        "usd",
        "value_field": "value",
        "monthly":     True,
        "value_scale": 1.0,
    },
]


def fetch_all(api_key, route, params):
    url = f"{EIA_BASE_URL}/{route}"
    all_rows = []
    offset = 0
    length = 5000

    while True:
        r = requests.get(
            url,
            params={"api_key": api_key, **params, "offset": offset, "length": length},
            timeout=60,
        )
        r.raise_for_status()
        result = r.json()
        if "error" in result:
            raise ValueError(f"EIA API error ({route}): {result['error']}")
        rows = result["response"]["data"]
        total = int(result["response"].get("total", 0))
        all_rows.extend(rows)
        print(f"    fetched {len(all_rows)}/{total} rows", end="\r")
        if len(rows) < length:
            break
        offset += length
        time.sleep(0.5)

    print()
    return all_rows


def parse_records(rows, series_id, metric_name, unit, value_field, monthly, value_scale):
    records = []
    for row in rows:
        raw = row.get(value_field)
        if raw is None:
            continue
        value = float(raw) * value_scale
        period = row["period"]
        metric_time = date.fromisoformat(period + "-01" if monthly else period)
        records.append((metric_time, "EIA", series_id, metric_name, value, unit))
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
    api_key = os.environ.get("EIA_API_KEY")
    if not api_key:
        print("ERROR: EIA_API_KEY not set")
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
        for cfg in SERIES_CONFIG:
            print(f"\nFetching {cfg['label']} ...")
            rows = fetch_all(api_key, cfg["route"], cfg["params"])
            records = parse_records(
                rows,
                cfg["series_id"],
                cfg["metric_name"],
                cfg["unit"],
                cfg["value_field"],
                cfg["monthly"],
                cfg["value_scale"],
            )
            upsert_records(conn, records)
            print(f"  Upserted {len(records)} records")
            total += len(records)
    finally:
        conn.close()

    print(f"\nDone. {total} total records upserted into metrics.economic_indicators.")


if __name__ == "__main__":
    main()
