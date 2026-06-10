"""
Run from the repo root:
  BLS_API_KEY=your_key python src/airflow/scripts/test_bls_fetch.py
"""

import os
import sys
import json
import requests

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data"

SERIES_IDS = [
    "CUUR0000SA0",    # CPI-U overall inflation
    "APU0000708111",  # Eggs
    "APU0000703112",  # Beef
    "APU000074714",   # Gasoline
    "CUUR0000SAH1",   # Shelter / rent
    "CUUR0000SAM1",   # Medical care
    "LNS14000000",    # Unemployment rate
]

SERIES_LABELS = {
    "CUUR0000SA0":   "CPI-U overall",
    "APU0000708111": "Eggs",
    "APU0000703112": "Beef",
    "APU000074714":  "Gasoline",
    "CUUR0000SAH1":  "Shelter / rent",
    "CUUR0000SAM1":  "Medical care",
    "LNS14000000":   "Unemployment rate",
}

api_key = os.environ.get("BLS_API_KEY")
if not api_key:
    print("ERROR: BLS_API_KEY environment variable not set")
    sys.exit(1)

# Hardcode a period to test against — change as needed
year = "2025"
period = "M11"  # November 2025

print(f"Querying BLS API for {period}/{year} ...\n")

payload = {
    "seriesid": SERIES_IDS,
    "startyear": year,
    "endyear": year,
    "registrationKey": api_key,
}

response = requests.post(BLS_API_URL, json=payload, timeout=30)
response.raise_for_status()

result = response.json()

if result["status"] != "REQUEST_SUCCEEDED":
    print(f"API error: {result['message']}")
    sys.exit(1)

records = []
for series in result["Results"]["series"]:
    match = next((p for p in series["data"] if p["period"] == period), None)
    if match:
        records.append({
            "series_id": series["seriesID"],
            "label": SERIES_LABELS.get(series["seriesID"], series["seriesID"]),
            "year": int(match["year"]),
            "period": match["period"],
            "value": float(match["value"]),
        })
    else:
        print(f"  WARNING: no data for {series['seriesID']} in {period}/{year}")

print(f"{'Label':<25} {'Series ID':<20} {'Value'}")
print("-" * 60)
for r in records:
    print(f"{r['label']:<25} {r['series_id']:<20} {r['value']}")

print(f"\nRaw response saved to /tmp/bls_response.json")
with open("/tmp/bls_response.json", "w") as f:
    json.dump(result, f, indent=2)
