# FlightOps dbt project

This directory contains the transformation project for FlightOps Intelligence.
It declares the existing `raw.bts_on_time_performance` source and contains the
BTS staging layer plus the implemented Core star schema under
`models/marts/core/`: `dim_dates`, `dim_airlines`, `dim_airports`, and
`fact_flights`. Detailed grains, keys, validation results, and limitations are
documented in [`../docs/phase1_core_modeling.md`](../docs/phase1_core_modeling.md).

## Local setup

From the repository root:

```bash
source .venv/bin/activate
set -a
source .env
set +a
cp dbt/profiles.yml.example dbt/profiles.yml  # only if the local file is absent
```

`dbt/profiles.yml` is ignored because profiles may contain local connection
configuration. This project's profile contains only environment-variable
references; database credentials remain in the ignored root `.env` file.

## Validate the project

Run commands from the repository root so paths are unambiguous:

```bash
dbt debug --project-dir dbt --profiles-dir dbt
dbt parse --project-dir dbt --profiles-dir dbt
dbt compile --project-dir dbt --profiles-dir dbt
dbt ls --project-dir dbt --profiles-dir dbt
dbt build --project-dir dbt --profiles-dir dbt
dbt test --project-dir dbt --profiles-dir dbt
dbt docs generate --project-dir dbt --profiles-dir dbt
```

With the default `DBT_TARGET_SCHEMA=analytics`, staging resolves to
`analytics_staging` as a view and Core resolves to `analytics_marts` as tables.
The generated documentation artifacts are written under `dbt/target/`; this
directory contains build artifacts and is not source documentation.

