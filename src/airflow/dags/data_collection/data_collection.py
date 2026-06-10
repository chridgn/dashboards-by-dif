import pendulum
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from data_collection.jobs.fetch_bls_data import fetch_bls_data
from data_collection.jobs.stage_bls_data import stage_bls_data
from data_collection.jobs.transform_bls_data import transform_bls_data
from data_collection.jobs.fetch_eia_data import fetch_eia_data
from data_collection.jobs.stage_eia_data import stage_eia_data
from data_collection.jobs.transform_eia_data import transform_eia_data
from data_collection.jobs.fetch_fred_data import fetch_fred_data
from data_collection.jobs.stage_fred_data import stage_fred_data
from data_collection.jobs.transform_fred_data import transform_fred_data


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

    # EIA + FRED pipelines share the weekly gate
    weekly = is_weekly()

    eia_raw = fetch_eia_data()
    eia_staging_id = stage_eia_data(eia_raw)
    transform_eia_data(eia_staging_id)
    weekly >> eia_raw

    fred_raw = fetch_fred_data()
    fred_staging_id = stage_fred_data(fred_raw)
    transform_fred_data(fred_staging_id)
    weekly >> fred_raw


data_collection()
