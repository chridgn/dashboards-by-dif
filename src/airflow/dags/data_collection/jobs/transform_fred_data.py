from datetime import date
from airflow.decorators import task
from data_collection.jobs.db import get_dashboard_conn

SERIES_METADATA = {
    "FEDFUNDS":     ("Federal Funds Rate",               "percent"),
    "MORTGAGE30US": ("30-Year Fixed Mortgage Rate",      "percent"),
    "DSPIC96":      ("Real Disposable Personal Income",  "usd_bn"),
    "UMCSENT":      ("Consumer Sentiment",               "index"),
    "M2SL":         ("M2 Money Supply",                  "usd_bn"),
}


@task
def transform_fred_data(staging_id: int):
    conn = get_dashboard_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT raw_json FROM staging.fred_responses WHERE id = %s",
                (staging_id,),
            )
            (raw_json,) = cur.fetchone()

            records = []
            for series_id, observations_data in raw_json.items():
                metric_name, unit = SERIES_METADATA.get(
                    series_id, (series_id, "unknown")
                )
                for obs in observations_data.get("observations", []):
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
