# TrialDiff frontend — agent notes

This is an **Astro 6** app (`output: "server"`, `@astrojs/vercel` adapter),
not Next.js. Queries go through **postgres.js** tagged templates. There is no
client-side JavaScript: every page is server-rendered; interactivity is plain
HTML (`<details>`, links).

## Directory map

- `src/pages/` — routes: `index.astro` (dashboard/feeds), `methodology.astro`
  and `case-studies/` (prerendered static), `trials/[nctId].astro`,
  `trials/[nctId]/patches/[range].astro` (range format `"{from}-to-{to}"`,
  e.g. `5-to-6`), `events/[event_id].astro`, and
  `events/[event_id].json.ts` (canonical-bytes JSON endpoint).
- `src/queries/` — all SQL (`feed.ts`, `trials.ts`, `patches.ts`,
  `evidence.ts`) plus row mappers (`mappers.ts`) and shared types
  (`types.ts`).
- `src/lib/` — pure helpers: `jsonPatch.ts`, `pathMatching.ts`,
  `pathGrouping.ts`, `pathRanking.ts`, `patchEnrichment.ts`, `format.ts`.
- `src/db/client.ts` — postgres.js singleton; reads `DATABASE_URL` /
  `DATABASE_POOL_MAX` from `import.meta.env` (dev `.env`) or `process.env`.
- `src/layouts/BaseLayout.astro`, `src/components/`, `src/styles/global.css`.

## Commands

- `npm run dev` — dev server (0.0.0.0:4321, reads `frontend/.env`)
- `npm run build` — production build
- `npx astro check` — type-check; keep it at 0 errors

## Conventions

- Server-rendered only; do not add client frameworks or island scripts
  without discussion.
- SQL goes through postgres.js tagged templates so values are parameterized;
  never interpolate user input into query strings.
- Keep pipeline parity with the Python modules in `trialdiff/`:
  `src/lib/jsonPatch.ts` mirrors `trialdiff/jsonpatch.py`,
  `src/lib/pathMatching.ts` mirrors `trialdiff/classifier/pathmatch.py`, and
  severity/category/suppression logic mirrors
  `trialdiff/classifier/materiality.py`. If you change one side, check the
  other.
- Severity is deterministic, uncalibrated triage metadata — copy in the UI is
  written to avoid implying validated review priority; keep new copy
  consistent with that.
- `evidence_records.canonical_json` is a text column whose exact bytes hash
  to `canonical_hash`; never re-encode it when serving.

## Local database

See `README.md` in this directory for the full local-dev flow (Docker/local
Postgres, `postgres/migrations/*.sql` in order, then
`scripts/seed_from_records.py` + `scripts/sqlite_to_postgres.py` + `psql`).
