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

            records = []
            for series in raw_json["Results"]["series"]:
                # Take the most recent available period — BLS series have different
                # release dates so not all will have the same latest month.
                monthly = [p for p in series["data"] if p["period"].startswith("M")]
                if not monthly:
                    continue
                latest = max(monthly, key=lambda p: (p["year"], p["period"]))
                metric_time = date(int(latest["year"]), int(latest["period"][1:]), 1)
                metric_name, unit = SERIES_METADATA.get(
                    series["seriesID"], (series["seriesID"], "unknown")
                )
                records.append((
                    metric_time,
                    "BLS",
                    series["seriesID"],
                    metric_name,
                    float(latest["value"]),
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
