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
   python3 scripts/sqlite_to_postgres.py seed_demo.sqlite3 --truncate --output seed_demo.sql
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

## Seeded-data limitation

The seed pipeline builds the database from exported Evidence Records, and
version snapshots (`trial_versions.record_json`) are not part of exported
records. The patch inspector therefore shows before-values as `<MISSING>` for
seeded data; op-level after-values and all record/hash data are unaffected. A
database populated by the full ingest pipeline does not have this limitation.
