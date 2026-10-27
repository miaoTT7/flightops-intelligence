# FlightOps dbt project

This directory contains the transformation project for FlightOps Intelligence.
It declares the existing `raw.bts_on_time_performance` source and contains the
BTS staging layer. The planned Core models are configured under
`models/marts/core/`, but no Core SQL models have been implemented yet.

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
dbt ls --project-dir dbt --profiles-dir dbt
```

`dbt ls` lists the source, staging model, and their data tests. Until Core SQL
models are added, it does not list any Core nodes or relations.

