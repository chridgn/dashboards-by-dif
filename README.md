# Dashboards by Dif

I was tired of having to visit different sites and news outlets for economic indicators so I decided to build a custom dashboard where I could add datasets of interest whenever I liked.

The resulting dashboard is available at <link> for anyone curious.

## Data Sources

| Metric | Source | API | Frequency |
|---|---|---|---|
| Overall inflation (CPI-U) | Bureau of Labor Statistics | api.bls.gov | Monthly |
| Egg prices | Bureau of Labor Statistics | api.bls.gov | Monthly |
| Beef prices | Bureau of Labor Statistics | api.bls.gov | Monthly |
| Grocery basket (CPI food at home) | Bureau of Labor Statistics | api.bls.gov | Monthly |
| Rent (CPI shelter) | Bureau of Labor Statistics | api.bls.gov | Monthly |
| Medical care (CPI) | Bureau of Labor Statistics | api.bls.gov | Monthly |
| Unemployment rate | Bureau of Labor Statistics | api.bls.gov | Monthly |
| Gas prices (LA region) | Energy Information Administration | api.eia.gov | Weekly |
| Electricity prices | Energy Information Administration | api.eia.gov | Weekly |
| Natural gas prices | Energy Information Administration | api.eia.gov | Weekly |
| Federal funds rate | Federal Reserve (FRED) | fred.stlouisfed.org/docs/api | As changed |
| 30-year mortgage rate | Federal Reserve (FRED) | fred.stlouisfed.org/docs/api | Weekly |
| Real disposable personal income | Federal Reserve (FRED) | fred.stlouisfed.org/docs/api | Monthly |
| Consumer sentiment index | Federal Reserve (FRED) | fred.stlouisfed.org/docs/api | Monthly |
| M2 money supply | Federal Reserve (FRED) | fred.stlouisfed.org/docs/api | Monthly |
| Credit card interest rate | Federal Reserve (FRED) | fred.stlouisfed.org/docs/api | Monthly |

## The Stack

This project involves a lean DE pipeline that uses an Airflow DAG to pull metrics from public APIs and ingests this data into Postgres. Raw data is landed in a staging table before being deduped and flattened into a mart-style table that is exposed via timescaledb postgres extension. A grafana dashboard then graphs the metrics so I can view them with my cats.

As for deployment, docker-compose on a single EC2 (t2.small) was enough for a workload of this size.

To see how the stack was defined and built, see src/docker-compose.yml