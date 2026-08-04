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
  `events/[event_id].json.ts` (canonical-bytes JSON endpoint), and
  `events/supersessions.json.ts` (always-revalidated discovery index).
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
- `evidence_record_store.canonical_json` is a text column whose exact bytes
  hash to `canonical_hash`; never re-encode it when serving. Exact-ID routes
  query this all-generation store. The `evidence_records` compatibility view
  exposes only the active generation.
- Every feed, corpus total, and trial/patch Evidence Record link must join
  `evidence_record_generations` with `is_active`; never infer the active
  generation from `generated_at`, `evidence_version`, or hash ordering.
- Supersession metadata belongs in HTML, origin-served 200 response headers,
  and the non-immutable index, not in canonical JSON. An edge-served 304 may
  omit application-defined metadata headers; assert its status and empty body,
  then use the index as the authoritative discovery surface. Before activation,
  an imported inactive successor must not make the active predecessor appear
  superseded.
- Exact inactive-generation IDs intentionally remain retrievable for hold-stage
  byte verification, with `x-trialdiff-record-status: inactive`; never expose
  them through feeds, active links, totals, or the supersession index.
- Homepage counts are import-attested generation metadata. No active generation
  is an unavailable state, not a zero-count corpus.

## Local database

See `README.md` in this directory for the full local-dev flow (Docker/local
Postgres, `postgres/migrations/*.sql` in order, then
`scripts/seed_from_records.py` + `scripts/sqlite_to_postgres.py` + `psql`).
