from datetime import date
from airflow.decorators import task
from data_collection.jobs.db import get_dashboard_conn

# series_id, metric_name, unit, value_field, is_monthly_period
SERIES_CONFIG = [
    ("EIA_GAS_CA",    "California Regular Gasoline",        "usd",   "value", False),
    ("EIA_ELEC_CA",   "California Residential Electricity",  "usd",   "price", True),
    ("EIA_NATGAS_CA", "California Residential Natural Gas",  "usd",   "value", True),
]

# Keys in the raw_json dict that map to each series
RAW_KEYS = ["gas", "electricity", "natural_gas"]


@task
def transform_eia_data(staging_id: int):
    conn = get_dashboard_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT raw_json FROM staging.eia_responses WHERE id = %s",
                (staging_id,),
            )
            (raw_json,) = cur.fetchone()

            records = []
            for raw_key, (series_id, metric_name, unit, value_field, monthly_period) in zip(
                RAW_KEYS, SERIES_CONFIG
            ):
                rows = raw_json.get(raw_key, {}).get("response", {}).get("data", [])
                for row in rows:
                    raw_value = row.get(value_field)
                    if raw_value is None:
                        continue
                    value = float(raw_value)
                    if series_id == "EIA_ELEC_CA":
                        value = value / 100  # cents per kWh → dollars per kWh

                    period_str = row["period"]
                    if monthly_period:
                        metric_time = date.fromisoformat(period_str + "-01")
                    else:
                        metric_time = date.fromisoformat(period_str)

                    records.append((metric_time, "EIA", series_id, metric_name, value, unit))

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
    finally:
        conn.close()
