CREATE DATABASE dashboard;

\connect dashboard

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE SCHEMA staging;
CREATE SCHEMA metrics;

-- ---------------------------------------------------------------------------
-- Staging: one table per source, preserving the raw API response
-- ---------------------------------------------------------------------------

CREATE TABLE staging.bls_responses (
    id           BIGSERIAL    PRIMARY KEY,
    fetched_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    logical_date DATE         NOT NULL,
    raw_json     JSONB        NOT NULL
);

CREATE TABLE staging.eia_responses (
    id           BIGSERIAL    PRIMARY KEY,
    fetched_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    logical_date DATE         NOT NULL,
    raw_json     JSONB        NOT NULL
);

CREATE TABLE staging.fred_responses (
    id           BIGSERIAL    PRIMARY KEY,
    fetched_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    logical_date DATE         NOT NULL,
    raw_json     JSONB        NOT NULL
);

-- ---------------------------------------------------------------------------
-- Metrics: flattened, unified hypertable — one row per series per period
-- ---------------------------------------------------------------------------

CREATE TABLE metrics.economic_indicators (
    metric_time  DATE         NOT NULL,
    source       VARCHAR(20)  NOT NULL,
    series_id    VARCHAR(50)  NOT NULL,
    metric_name  VARCHAR(100) NOT NULL,
    value        NUMERIC      NOT NULL,
    unit         VARCHAR(20)  NOT NULL,
    fetched_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

SELECT create_hypertable(
    'metrics.economic_indicators',
    'metric_time',
    chunk_time_interval => INTERVAL '1 year'
);

-- Prevents duplicate ingestion; also used for upserts
CREATE UNIQUE INDEX ON metrics.economic_indicators (series_id, metric_time);
