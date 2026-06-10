# Energy Information Administration (EIA) API

## Overview

The EIA Open Data API provides access to energy price data including gasoline, electricity, and natural gas. Registration is free at [eia.gov/opendata](https://www.eia.gov/opendata/). The current version is **v2**, which replaced the legacy v1 API (deprecated January 2023).

## Authentication

An API key is required for all requests. There is no anonymous tier.

- Register at eia.gov/opendata to get a key
- Pass it as the `api_key` query parameter — **URL only**, not in headers
- Store it as `EIA_API_KEY` in your `.env` file

## API Structure

The v2 API is hierarchical and self-documenting. Routes are nested paths under `https://api.eia.gov/v2/`. Querying any parent route (without `/data`) returns metadata describing its child datasets, available facets, and supported frequencies.

```
https://api.eia.gov/v2/petroleum           # metadata: list of child routes
https://api.eia.gov/v2/petroleum/pri/gnd   # metadata: facets & frequencies available
https://api.eia.gov/v2/petroleum/pri/gnd/data?api_key=KEY&...   # actual data
```

This makes the API exploratory — when in doubt, drop `/data` and inspect the parent.

## Common Query Parameters

| Parameter | Purpose | Example |
|---|---|---|
| `api_key` | Authentication (required) | `?api_key=YOUR_KEY` |
| `data[]` | Columns to return | `&data[]=value` |
| `facets[X][]` | Filter by dimension X | `&facets[stateid][]=CA` |
| `frequency` | Data periodicity | `&frequency=weekly` |
| `start` | Date range start | `&start=2020-01-01` |
| `end` | Date range end | `&end=2026-01-01` |
| `sort[0][column]` | Sort by field | `&sort[0][column]=period` |
| `sort[0][direction]` | Sort direction | `&sort[0][direction]=desc` |
| `offset` | Pagination start row | `&offset=0` |
| `length` | Rows per request (max 5000) | `&length=5000` |

## Response Format

All endpoints return the same envelope:

```json
{
  "response": {
    "total": "312",
    "dateFormat": "YYYY-MM-DD",
    "frequency": "weekly",
    "data": [
      {
        "period": "2026-01-06",
        "duoarea": "SCA",
        "area-name": "California",
        "product": "EPMR",
        "process": "PTE",
        "series": "EMM_EPMR_PTE_SCA_DPG",
        "series-description": "Weekly California Regular Conventional Gas Price",
        "value": "4.102",
        "units": "Dollars per Gallon"
      }
    ]
  },
  "request": {
    "command": "/v2/petroleum/pri/gnd/data",
    "params": {}
  },
  "apiVersion": "2.1.12"
}
```

- `period` format varies by frequency: `YYYY-MM-DD` (weekly/daily), `YYYY-MM` (monthly), `YYYY` (annual)
- `value` is always a string — cast to `float` before storing
- `total` reflects matching rows, not rows returned — use pagination if `total > length`

## Endpoints Used in This Project

### Gasoline Prices — California (Weekly)

**Route:** `https://api.eia.gov/v2/petroleum/pri/gnd/data`

California-specific weekly retail gasoline prices. The `duoarea` facet maps to geographic zones; `SCA` is California statewide.

```
GET /v2/petroleum/pri/gnd/data
  ?api_key=KEY
  &data[]=value
  &facets[duoarea][]=SCA
  &facets[product][]=EPMR
  &frequency=weekly
  &sort[0][column]=period
  &sort[0][direction]=desc
```

| Facet | Value | Meaning |
|---|---|---|
| `duoarea` | `SCA` | California statewide |
| `product` | `EPMR` | Regular conventional gasoline |
| `process` | `PTE` | Retail (optional, default for this series) |

Other `duoarea` values for reference: `R50` = PADD 5 (West Coast), `SCO` = Colorado, `STX` = Texas.

Discover all valid area codes: `GET /v2/petroleum/pri/gnd/facet/duoarea/?api_key=KEY`

**Series ID (legacy v1):** `PET.EMM_EPMR_PTE_SCA_DPG.W`

If you need to use the v1 series ID directly (for backfilling or compatibility), the `/seriesid/` route translates it:
```
GET /v2/seriesid/PET.EMM_EPMR_PTE_SCA_DPG.W?api_key=KEY
```

---

### Electricity Prices — California Residential (Monthly)

**Route:** `https://api.eia.gov/v2/electricity/retail-sales/data`

State-level retail electricity prices by customer sector.

```
GET /v2/electricity/retail-sales/data
  ?api_key=KEY
  &data[]=price
  &facets[stateid][]=CA
  &facets[sectorid][]=RES
  &frequency=monthly
  &sort[0][column]=period
  &sort[0][direction]=desc
```

| Facet | Value | Meaning |
|---|---|---|
| `stateid` | `CA` | California (two-letter code) |
| `sectorid` | `RES` | Residential customers |

Other `sectorid` values: `COM` = commercial, `IND` = industrial, `ALL` = all sectors combined.

The `price` column returns cents per kilowatthour (¢/kWh). Divide by 100 for dollars.

Discover valid state codes: `GET /v2/electricity/retail-sales/facet/stateid/?api_key=KEY`

---

### Natural Gas Prices — California Residential (Monthly)

**Route:** `https://api.eia.gov/v2/natural-gas/pri/sum/data`

Delivered natural gas prices to end-use customers by state.

```
GET /v2/natural-gas/pri/sum/data
  ?api_key=KEY
  &data[]=value
  &facets[duoarea][]=SCA
  &facets[process][]=PRS
  &frequency=monthly
  &sort[0][column]=period
  &sort[0][direction]=desc
```

| Facet | Value | Meaning |
|---|---|---|
| `duoarea` | `SCA` | California statewide |
| `process` | `PRS` | Residential delivered price |

Price units are dollars per thousand cubic feet ($/Mcf).

If this route returns unexpected structure, query the parent to verify facets:
```
GET /v2/natural-gas/pri/sum?api_key=KEY
```

---

## Rate Limits & Pagination

- **Max rows per request:** 5,000 (JSON), 300 (XML)
- **No published rate limit**, but EIA will temporarily suspend keys that make aggressive bulk requests
- For large backfills, paginate using `offset` + `length` and add a brief delay between requests

```python
offset = 0
length = 5000
all_data = []

while True:
    resp = requests.get(url, params={**params, "offset": offset, "length": length})
    data = resp.json()["response"]["data"]
    all_data.extend(data)
    if len(data) < length:
        break
    offset += length
```

---

## Series Used in This Project

| Metric | Route | Key Facets | Unit | Frequency |
|---|---|---|---|---|
| Gas price (CA) | `/v2/petroleum/pri/gnd/data` | `duoarea=SCA`, `product=EPMR` | $/gallon | Weekly |
| Electricity price (CA residential) | `/v2/electricity/retail-sales/data` | `stateid=CA`, `sectorid=RES` | ¢/kWh | Monthly |
| Natural gas price (CA residential) | `/v2/natural-gas/pri/sum/data` | `duoarea=SCA`, `process=PRS` | $/Mcf | Monthly |

These will be stored in `metrics.economic_indicators` with `source = 'EIA'` and a stable `series_id` derived from the route + facets (e.g., `EIA_GAS_CA_WEEKLY`).

## Data Release Schedule

| Metric | Release cadence |
|---|---|
| Gasoline prices | Every Monday, reflecting the prior week |
| Electricity prices | ~4–6 weeks after the end of the reference month |
| Natural gas prices | ~4–6 weeks after the end of the reference month |

The weekly gasoline task in Airflow runs on Mondays (`is_weekly` short-circuit checks `logical_date.weekday() == 0`), which aligns with EIA's Monday release. The monthly energy price tasks can share the same `is_monthly` gate as BLS.
