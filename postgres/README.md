# TrialDiff Postgres Setup

The Astro frontend reads a Postgres database (Neon in production). The
Python pipeline writes SQLite; this directory holds the Postgres dialect of
the same schema plus a one-shot import path.

Run ALL migrations in order against the target database:

```sh
for f in postgres/migrations/*.sql; do
  psql "$DATABASE_URL" -f "$f"
done
```

That currently means:

1. `001_initial.sql` — core tables and indexes
2. `002_seed_classifier_rules.sql` — deterministic classifier rule seeds
3. `003_seed_adverse_event_rules.sql` — adverse-event rule seeds
4. `004_evidence_records_table.sql` — the `evidence_records` table the frontend queries
5. `005_v021_rule_tightening.sql` — v0.2.1 rule tightening updates
6. `006_canonical_json_text.sql` — store `canonical_json` as text so the exact
   bytes hashing to `canonical_hash` survive the copy (rows imported while the
   column was `jsonb` must be re-imported afterwards)

Export the current SQLite corpus into Postgres-compatible SQL and apply it:

```sh
python3 scripts/sqlite_to_postgres.py trialdiff_breast_cancer_limit100.sqlite3 \
  --truncate \
  --output postgres/trialdiff_limit100_export.sql
psql "$DATABASE_URL" -f postgres/trialdiff_limit100_export.sql
```

The exporter is pure Python stdlib. It preserves provenance columns, JSON
payloads as `jsonb`, booleans, identity IDs, and `canonical_json` as opaque
text (so evidence records stay byte-verifiable against `canonical_hash`).

After an import, spot-check verifiability (note `convert_to`, not a
`::bytea` cast — casting text to bytea parses bytea escape syntax and
errors on the backslash escapes canonical JSON contains):

```sql
SELECT count(*) FROM evidence_records
WHERE encode(sha256(convert_to(canonical_json, 'UTF8')), 'hex') <> canonical_hash;
-- must return 0
```

For local development without the private corpus databases, see
`scripts/seed_from_records.py`, which seeds a database from the committed
`records/*.json` files (documented in `frontend/README.md`).
