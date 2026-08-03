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
4. `004_evidence_records_table.sql` — the original Evidence Record table
5. `005_v021_rule_tightening.sql` — v0.2.1 rule tightening updates
6. `006_canonical_json_text.sql` — store `canonical_json` as text so the exact
   bytes hashing to `canonical_hash` survive the copy (rows imported while the
   column was `jsonb` must be re-imported afterwards)
7. `007_evidence_generation_coexistence.sql` — preserve every package
   generation in `evidence_record_store`, expose the active generation through
   the compatibility view `evidence_records`, and record one-to-one successor
   mappings without changing canonical record bytes

Export the current SQLite corpus into Postgres-compatible SQL and apply it:

```sh
python3 scripts/sqlite_to_postgres.py trialdiff_breast_cancer_limit100.sqlite3 \
  --truncate \
  --package-generation v0.1.3 \
  --activate-generation \
  --output postgres/trialdiff_limit100_export.sql
psql "$DATABASE_URL" -f postgres/trialdiff_limit100_export.sql
```

`--truncate` is for local/bootstrap databases only. Production correction
releases use an additive, initially inactive import:

```sh
python3 scripts/sqlite_to_postgres.py corrected.sqlite3 \
  --evidence-only \
  --package-generation v0.1.3 \
  --supersedes v0.1.2 \
  --output postgres/trialdiff_v013_evidence.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f postgres/trialdiff_v013_evidence.sql
# Verify the inactive generation and its complete transition map first.
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -c "SELECT trialdiff_activate_evidence_generation('v0.1.3');"
```

The additive SQL refuses to activate its own generation. It verifies its
record/membership/rule-hash metadata against the inserted rows, verifies its
corpus metadata against the target database, and requires a complete
one-to-one transition map. Activation is a separate transaction and refuses
to switch unless that map remains complete. The same stored forward map
authorizes a checked rollback from successor to predecessor; reverse duplicate
rows are neither required nor permitted.

Generation totals are immutable release attestations checked at import and
activation time, not live aggregates over subsequently mutable corpus tables.
If no generation is active, consumer surfaces must report unavailable rather
than presenting zero-valued corpus totals.

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

Use `evidence_records` for active-only compatibility reads. Exact-ID and audit
queries that must retain superseded records use `evidence_record_store` plus
`evidence_record_generations`. See `RELEASING.md` section B for the controlled
production sequence and rollback checks.

For local development without the private corpus databases, see
`scripts/seed_from_records.py`, which seeds a database from the committed
`records/*.json` files (documented in `frontend/README.md`).
