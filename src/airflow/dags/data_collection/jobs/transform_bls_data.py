from datetime import date
from airflow.decorators import task
from data_collection.jobs.db import get_dashboard_conn

# Maps series_id -> (metric_name, unit)
SERIES_METADATA = {
    "CUUR0000SA0":   ("CPI-U overall inflation", "index"),
    "APU0000708111": ("Eggs",                    "usd"),
    "APU0000703112": ("Beef",                    "usd"),
    "APU000074714":  ("Gasoline",                "usd"),
    "CUUR0000SAH1":  ("Shelter / rent",          "index"),
    "CUUR0000SAM1":  ("Medical care",            "index"),
    "LNS14000000":   ("Unemployment rate",       "percent"),
}


@task
def transform_bls_data(staging_id: int):
    conn = get_dashboard_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT logical_date, raw_json FROM staging.bls_responses WHERE id = %s",
                (staging_id,),
            )
            logical_date, raw_json = cur.fetchone()

            # Target period is logical_date - 1 month
            target_month = logical_date.month - 1 if logical_date.month > 1 else 12
            target_year  = logical_date.year if logical_date.month > 1 else logical_date.year - 1
            target_period = f"M{target_month:02d}"

            records = []
            for series in raw_json["Results"]["series"]:
                monthly = [p for p in series["data"] if p["period"].startswith("M")]
                if not monthly:
                    continue
                # Use the target period; fall back to latest if not yet published
                match = next(
                    (p for p in monthly if p["year"] == str(target_year) and p["period"] == target_period),
                    max(monthly, key=lambda p: (p["year"], p["period"]))
                )
                metric_time = date(int(match["year"]), int(match["period"][1:]), 1)
                metric_name, unit = SERIES_METADATA.get(
                    series["seriesID"], (series["seriesID"], "unknown")
                )
                records.append((
                    metric_time,
                    "BLS",
                    series["seriesID"],
                    metric_name,
                    float(match["value"]),
                    unit,
                ))

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
    finally:
        conn.close()
