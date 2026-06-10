import os
import requests
from airflow.decorators import task

EIA_BASE_URL = "https://api.eia.gov/v2"


@task
def fetch_eia_data() -> dict:
    key = os.environ["EIA_API_KEY"]
    return {
        "gas":         _fetch(key, "petroleum/pri/gnd/data", {
            "data[]":            "value",
            "facets[duoarea][]": "SCA",
            "facets[product][]": "EPMR",
            "frequency":         "weekly",
            "sort[0][column]":   "period",
            "sort[0][direction]":"desc",
            "length":            8,
        }),
        "electricity": _fetch(key, "electricity/retail-sales/data", {
            "data[]":            "price",
            "facets[stateid][]": "CA",
            "facets[sectorid][]":"RES",
            "frequency":         "monthly",
            "sort[0][column]":   "period",
            "sort[0][direction]":"desc",
            "length":            3,
        }),
        "natural_gas": _fetch(key, "natural-gas/pri/sum/data", {
            "data[]":            "value",
            "facets[duoarea][]": "SCA",
            "facets[process][]": "PRS",
            "frequency":         "monthly",
            "sort[0][column]":   "period",
            "sort[0][direction]":"desc",
            "length":            3,
        }),
    }


def _fetch(key: str, route: str, params: dict) -> dict:
    r = requests.get(
        f"{EIA_BASE_URL}/{route}",
        params={"api_key": key, **params},
        timeout=30,
    )
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        raise ValueError(f"EIA API error ({route}): {result['error']}")
    return result
