import pendulum
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from data_collection.jobs.fetch_bls_data import fetch_bls_data
from data_collection.jobs.stage_bls_data import stage_bls_data
from data_collection.jobs.transform_bls_data import transform_bls_data
from data_collection.jobs.fetch_eia_data import fetch_eia_data


@dag(
    dag_id="data_collection",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule="@daily",
    catchup=False,
)
def data_collection():

    @task.short_circuit
    def is_monthly():
        ctx = get_current_context()
        return ctx["logical_date"].day == 1

    @task.short_circuit
    def is_weekly():
        ctx = get_current_context()
        return ctx["logical_date"].weekday() == 0  # Monday

    # BLS pipeline: fetch → stage → transform
    raw = fetch_bls_data()
    staging_id = stage_bls_data(raw)
    transform_bls_data(staging_id)
    is_monthly() >> raw

    # EIA pipeline (weekly)
    is_weekly() >> fetch_eia_data()


data_collection()
