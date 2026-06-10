# Bureau of Labor Statistics (BLS) API

## Overview

The BLS Public Data API provides access to time-series economic data including CPI, unemployment, and average consumer prices. Registration is free at [bls.gov/developers](https://www.bls.gov/developers/home.htm).

## Authentication

An API key is optional but required for practical use. Without one, requests are limited to 1 series at a time and 10 years of history.

| | Without key | With key |
|---|---|---|
| Series per request | 1 | 25 |
| History available | Last 10 years | Full |
| Requests per hour | 120 | 500 |

Pass the key as `registrationKey` in the request body. Store it as `BLS_API_KEY` in your `.env` file.

## Endpoint

```
POST https://api.bls.gov/publicAPI/v2/timeseries/data
Content-Type: application/json
```

## Request Format

```json
{
  "seriesid": ["CUUR0000SA0", "LNS14000000"],
  "startyear": "2025",
  "endyear": "2026",
  "registrationKey": "your_key_here"
}
```

The API always returns all months between `startyear` and `endyear` — there is no way to request a single month. Filter the response to the period you need.

## Response Format

```json
{
  "status": "REQUEST_SUCCEEDED",
  "responseTime": 25,
  "message": [],
  "Results": {
    "series": [
      {
        "seriesID": "CUUR0000SA0",
        "data": [
          {
            "year": "2026",
            "period": "M05",
            "periodName": "May",
            "value": "316.5",
            "footnotes": [{}]
          }
        ]
      }
    ]
  }
}
```

- `period` is `M01`–`M12` for monthly data
- `value` is always a string — cast to `float` before storing
- Check `status == "REQUEST_SUCCEEDED"` before reading results

## Series IDs Used in This Project

| Metric | Series ID | Type |
|---|---|---|
| CPI-U overall inflation | `CUUR0000SA0` | Index |
| Eggs | `APU0000708111` | Average price |
| Beef | `APU0000703112` | Average price |
| Gasoline | `APU000074714` | Average price |
| Shelter / rent | `CUUR0000SAH1` | Index |
| Medical care | `CUUR0000SAM1` | Index |
| Unemployment rate | `LNS14000000` | Rate |

`CUU` series are CPI index values (base period = 1982–84). `APU` series are average prices in USD. These are not directly comparable to each other.

## Series ID Format

Series IDs follow a structured format. For CPI-U (`CUU`) series:

```
C U U R 0 0 0 0 S A 0
│ │ │ │ └──┬──┘ └─┬─┘
│ │ │ │  area    item
│ │ │ └─ seasonal adjustment (R = unadjusted, S = adjusted)
│ │ └─── U = urban
│ └───── U = CPI-U
└─────── C = CPI
```

For average price (`APU`) series:

```
A P U 0 0 0 0 7 0 8 1 1 1
│ │ │ └──┬──┘ └────┬────┘
│ │ │  area       item
│ │ └─ U = urban
│ └─── P = average price
└───── A = average
```

Full series ID format documentation: [bls.gov/help/hlpforma.htm](https://www.bls.gov/help/hlpforma.htm)

## Data Release Schedule

BLS releases monthly CPI and average price data around the **10th of the following month**. The Airflow task queries `logical_date - 1 month` to ensure data is published before the task runs on the 1st.

| logical_date | Queries period | Data released around |
|---|---|---|
| 2026-06-01 | May 2026 (M05) | June 10, 2026 |
| 2026-07-01 | June 2026 (M06) | July 10, 2026 |
