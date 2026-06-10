import json
from airflow.decorators import task
from airflow.operators.python import get_current_context
from data_collection.jobs.db import get_dashboard_conn


@task
def stage_fred_data(raw_response: dict) -> int:
    ctx = get_current_context()
    logical_date = ctx["logical_date"].date()
    conn = get_dashboard_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO staging.fred_responses (logical_date, raw_json) VALUES (%s, %s) RETURNING id",
                (logical_date, json.dumps(raw_response)),
            )
            staging_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    return staging_id
