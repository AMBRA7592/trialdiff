# TrialDiff Postgres Setup

Run the migrations in order against a Neon database:

```sh
psql "$DATABASE_URL" -f postgres/migrations/001_initial.sql
psql "$DATABASE_URL" -f postgres/migrations/002_seed_classifier_rules.sql
psql "$DATABASE_URL" -f postgres/migrations/003_seed_adverse_event_rules.sql
```

Export the current SQLite corpus into Postgres-compatible SQL:

```sh
python3 scripts/sqlite_to_postgres.py trialdiff_breast_cancer_limit100.sqlite3 \
  --truncate \
  --output postgres/trialdiff_limit100_export.sql
psql "$DATABASE_URL" -f postgres/trialdiff_limit100_export.sql
```

The exporter is pure Python stdlib. It preserves provenance columns, JSON payloads as `jsonb`, booleans, and identity IDs.
