# TrialDiff frontend

Server-rendered dashboard for TrialDiff evidence records: it reads a Postgres
database of ClinicalTrials.gov trials, adjacent amendment patches, materiality
events, and Evidence Records, and renders feeds, trial timelines, a
field-level patch inspector, and citeable per-record pages (HTML plus a
hash-verifiable canonical JSON endpoint).

Stack: [Astro 6](https://astro.build) with `output: "server"`, the
`@astrojs/vercel` adapter, [postgres.js](https://github.com/porsager/postgres)
for queries, plain CSS. No client-side JavaScript framework.

## Prerequisites

- Node.js >= 20 and npm
- PostgreSQL 16 (via Docker or a local install)
- Python 3.11+ (only for seeding demo data from the committed record files)
- `psql` client

## Local development

1. Start Postgres. Either use the compose file at the repo root:

   ```bash
   docker compose up -d db
   ```

   or run a local server yourself (`initdb` + `pg_ctl start`, then
   `createdb -U trialdiff trialdiff`). The compose service exposes
   `postgres://trialdiff:trialdiff@localhost:5432/trialdiff`.

2. Apply the schema migrations in order (from the repo root):

   ```bash
   export DATABASE_URL='postgres://trialdiff:trialdiff@localhost:5432/trialdiff?sslmode=disable'
   for f in postgres/migrations/*.sql; do psql "$DATABASE_URL" -f "$f"; done
   ```

3. Seed demo data from the committed Evidence Record files:

   ```bash
   python3 scripts/seed_from_records.py --db seed_demo.sqlite3
   python3 scripts/sqlite_to_postgres.py seed_demo.sqlite3 \
     --truncate --package-generation v0.1.2 --activate-generation \
     --output seed_demo.sql
   psql "$DATABASE_URL" -f seed_demo.sql
   ```

4. Configure and run the app:

   ```bash
   cd frontend
   cp .env.example .env   # edit if your DATABASE_URL differs
   npm install
   npm run dev
   ```

   The dev server picks up `frontend/.env`; open http://localhost:4321.

## Commands

| Command | Effect |
| --- | --- |
| `npm run dev` | Start the dev server on 0.0.0.0:4321 |
| `npm run build` | Production build (Vercel adapter output in `.vercel/`) |
| `npm run check` / `npx astro check` | Type-check the project |

## Environment variables

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | yes | Postgres connection string. If it carries an `sslmode=` parameter (Neon URLs do; local URLs should use `sslmode=disable`), it is honored as-is; otherwise TLS defaults to `require`. Read from `frontend/.env` under `astro dev` and from the process environment in production. |
| `DATABASE_POOL_MAX` | no | Max postgres.js pool connections (default 5). |

## Deployment

The app deploys to Vercel with the `@astrojs/vercel` adapter and a Neon
Postgres database; set `DATABASE_URL` (and optionally `DATABASE_POOL_MAX`) in
the Vercel project environment. `/methodology` and the case-study pages are
prerendered at build time; everything else renders per-request against the
database.

## Published generations

Active feeds and corpus totals are selected explicitly from
`evidence_record_generations`. Exact event URLs resolve against
`evidence_record_store`, so a superseded published ID remains HTTP 200 with
its original canonical JSON bytes and hash. Supersession state is carried in
HTML and response headers, never added to the hashed JSON body.

An exact ID from an imported but inactive generation is also intentionally
retrievable as HTTP 200 with `x-trialdiff-record-status: inactive`. This makes
the frozen candidate bytes verifiable during the production hold without
making that candidate current or discoverable: feeds, links, corpus totals,
and the supersession index continue to expose only the active generation.

Homepage counts are attested generation metadata captured and checked during
import, not mutable live aggregates. They describe the frozen generation; a
later corpus mutation does not rewrite those counts and requires a new
generation/import to become public. If no generation is active, the homepage
returns its database-unavailable state instead of rendering zero counts.

`/events/supersessions.json` is the revalidated discovery index for active and
superseded published IDs. Canonical record responses remain independently
cacheable for one year with `immutable`; the index and HTML record pages use
`max-age=0, must-revalidate` so a previously cached record need not be mutated
to publish its successor. Only canonical JSON is immutable.

## Seeded-data limitation

The seed pipeline builds the database from exported Evidence Records, and
version snapshots (`trial_versions.record_json`) are not part of exported
records. The patch inspector therefore shows before-values as `<MISSING>` for
seeded data; op-level after-values and all record/hash data are unaffected. A
database populated by the full ingest pipeline does not have this limitation.
