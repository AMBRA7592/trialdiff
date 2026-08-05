# TrialDiff

TrialDiff converts public ClinicalTrials.gov record-version history into
replayable, source-linked, deterministic **Evidence Records**: exact changed
paths, the registry's own JSON Patch payloads, content hashes, deterministic
classification rules, timing context, and explicit claims-supported /
claims-not-supported boundaries.

This is not a product launch, monitoring service, pharma SaaS, misconduct
detector, or allegation engine.

> Severity is deterministic, reproducible, uncalibrated triage metadata. It
> is not validated review priority and not proven wrongdoing.

New here? `METHODOLOGY.md` is the documentation map and reading order.
Known defects in published artifacts are recorded in `ERRATA.md`.

## Repository Authority

**This repository (`AMBRA7592/trialdiff`) is the active, canonical
repository.** The companion `AMBRA7592/trialdiff-public` repository is the
immutable historical snapshot backing the published v0.1/v0.1.1 Zenodo
dataset and is not developed further; its Zenodo linkage is left intact.

Published dataset DOIs (Zenodo): concept DOI
[10.5281/zenodo.20801956](https://doi.org/10.5281/zenodo.20801956) (always
resolves to the latest version) · v0.1.3
[10.5281/zenodo.21811845](https://doi.org/10.5281/zenodo.21811845) · v0.1.2
[10.5281/zenodo.21755258](https://doi.org/10.5281/zenodo.21755258) · v0.1.1
[10.5281/zenodo.20816639](https://doi.org/10.5281/zenodo.20816639) · v0.1
[10.5281/zenodo.20801957](https://doi.org/10.5281/zenodo.20801957).
Note: the published v0.1.1 dataset carries erratum E1 (`ERRATA.md`). The
v0.1.2 package corrected E1 and is published under the same concept DOI; it
remains immutable and carries the subsequently discovered false-negative
erratum E4. The v0.1.3 package corrects E4, has been active in production
since 2026-08-04, and was published on 2026-08-05 under the same concept DOI.

## Live Demo

Live site: <https://trialdiff.vercel.app>

The live demo is backed by Neon Postgres and renders the **regenerated
100-study breast-cancer corpus** under the v0.2.1 triage generation and active
v0.3 event-class generation:

- 100 breast-cancer-related interventional trials
- 4,485 adjacent version patches
- 868 materiality events (87 critical / 396 high / 217 medium / 168 low triage)
- 97 event-class Evidence Records from the published v0.1.3 generation

The 97-record v0.1.3 layer has been active in Neon and Vercel production since
2026-08-04. Its public JSON endpoint serves canonical record bytes with a
matching ETag and `x-trialdiff-canonical-hash`, while exact v0.1.2 IDs remain
resolvable as immutable superseded records. The corrected v0.1.3 dataset was
published on 2026-08-05 at
[10.5281/zenodo.21811845](https://doi.org/10.5281/zenodo.21811845). The
immutable v0.1.2 dataset remains at
[10.5281/zenodo.21755258](https://doi.org/10.5281/zenodo.21755258) and carries
E4; published v0.1.1 remains the historical artifact that carries E1. The
historical count of 483 refers to the earlier
materiality-filter inclusion policy, not the current event-class criterion.
See `CORPUS.md` for the full population/version reconciliation.

## Frozen Packages

Four frozen, hash-pinned data packages live in this repository:

- **`records/`** — the v0.1-alpha demo: 40 selected high/critical Evidence
  Records from the 25-study alpha corpus (25 trials, 280 patches, 122
  events, 86 records at freeze). Pinned by `MANIFEST.sha256`.
- **`event_class_records_v0.1.1/`** — 100 event-class Evidence Records over
  52 trials from the 100-study corpus, with its own manifest. Carries
  erratum E1 (see `ERRATA.md`): 9 of 13 `why_stopped_removed_in_terminal_context`
  memberships are spurious.
- **`event_class_records_v0.1.2/`** — the dual-regenerated E1 correction:
  97 Evidence Records over 54 trials, with 106 event-class memberships and a
  manifest-pinned determinism attestation. Frozen on 2026-07-31 and published
  on 2026-08-02 as [10.5281/zenodo.21755258](https://doi.org/10.5281/zenodo.21755258).
  It remains immutable and carries E4 for three missed secondary-outcome
  memberships.
- **`event_class_records_v0.1.3/`** — the dual-regenerated E4 correction:
  97 Evidence Records over 54 trials, with 109 event-class memberships and a
  manifest-pinned determinism attestation. Frozen on 2026-08-03, activated in
  production on 2026-08-04, and published on 2026-08-05 as
  [10.5281/zenodo.21811845](https://doi.org/10.5281/zenodo.21811845).

Key documents:

- `CLAIMS.md` / `NON_CLAIMS.md` — what is and is not claimed
- `EVIDENCE_RECORD_PRIMITIVE.md` — the operational primitive specification
- `DATA_DICTIONARY.md` + `schemas/` — both record schemas
- `VALIDATION.md` — validation and audit status of the alpha package
- `VERSIONS.md` — disambiguates the spec/release/calibration/package version lines

## Selection Rule (frozen alpha)

The v0.1-alpha package exports 40 Evidence Records from the 25-study corpus:

1. all records carrying the critical triage label first;
2. then records carrying the high triage label;
3. ordered by timing context, with post-recruitment and late-recruitment records before earlier records;
4. capped at 40 records.

This produces a deterministic, bounded inspection slice rather than a full
product dataset or validated priority feed.

## Verify The Frozen Packages

Anyone can verify the committed records offline — no database required:

```bash
# Offline integrity verification of any record file or directory:
python3 -m trialdiff.cli verify records \
  event_class_records_v0.1.1/records \
  event_class_records_v0.1.2/records \
  event_class_records_v0.1.3/records

# Package validators (structure, counts, manifests, recomputed hashes):
python3 scripts/validate_alpha_demo.py
python3 scripts/validate_event_class_package.py --package event_class_records_v0.1.1
python3 scripts/validate_event_class_package.py --package event_class_records_v0.1.2
python3 scripts/validate_event_class_package.py --package event_class_records_v0.1.3

# Manifests:
sha256sum -c MANIFEST.sha256
sha256sum -c MANIFEST.calibration.sha256
(cd event_class_records_v0.1.1 && sha256sum -c MANIFEST.sha256)
(cd event_class_records_v0.1.2 && sha256sum -c MANIFEST.sha256)
(cd event_class_records_v0.1.3 && sha256sum -c MANIFEST.sha256)
```

`trialdiff verify` recomputes canonical hashes, patch hashes, and (for
current-format records) the deterministic `event_id` from the record's own
contents. A record that fails any of these has been altered.

Scope of that guarantee, precisely:

- **`trialdiff verify` alone** proves canonical form and internal
  self-consistency. Its checks are recomputed from the record's own
  contents, so an editor who re-serializes canonically (and re-derives the
  self-referential hashes) can alter fields without failing it. The
  **authenticity anchors are the manifests** (`MANIFEST.sha256`, the
  package manifests) and the database `canonical_hash` values — always
  verify against those when provenance matters.
- Hashes and manifests together prove **byte integrity** — the artifact is
  exactly what was published. They do not prove **semantic correctness** —
  that the claims inside it are true. The published v0.1.1 dataset passes
  every integrity check and still carries a false class claim in 9 records
  (`ERRATA.md` E1); v0.1.2 likewise verifies perfectly while omitting three
  qualifying secondary-outcome memberships (E4); the published v0.1.3 package
  corrects those omissions. Correctness lives in the errata,
  regeneration, and rule-set-hash discipline, not in the checksums.
- The v0.1.2 and v0.1.3 records are not fully source-closed. They carry patches
  and source hashes but omit some source fields consumed by four predicates,
  so they do not support independent clean-room reconstruction of every
  membership from packaged bytes alone.

## What A Reviewer Can Inspect

For each exported record, a reviewer can answer:

1. What changed?
2. Where did it change?
3. When did it change?
4. Which deterministic rule or value signal classified it?
5. Which deterministic event class or triage signal caused it to be selected?
6. What source/provenance/hash fields support the record?
7. Can the record be verified against the frozen manifest?
8. What is explicitly not being claimed?

## Run It Locally

The pipeline is stdlib-only Python 3.11+. Install and use the CLI:

```bash
pip install .          # or: pip install -e ".[dev]" for development
trialdiff --help       # init-db, ingest, classify, inspect, select-corpus,
                       # generate-evidence, verify
```

The corpus SQLite databases are not committed (they are large, regenerable
working files), but a runnable demo database can be built from the committed
records:

```bash
python3 scripts/seed_from_records.py --db seed_demo.sqlite3
```

To run the web frontend against it locally, see `frontend/README.md`
(docker-compose Postgres + seed import). To regenerate corpora from the live
registry, see the `select-corpus`, `ingest`, `classify`, and
`generate-evidence` CLI commands — note that the live registry moves, so
fresh ingests will not byte-reproduce the frozen packages; those are
verified, not re-derived (see `EVIDENCE_RECORD_PRIMITIVE.md`).

Regenerating the *frozen alpha* exactly additionally requires the original
25-study database and the v0.1-alpha code generation; at current HEAD the
generator gates on event classes and emits additional fields, so the
`records/` package is preserved as a verified historical artifact rather
than re-derived (see `VERSIONS.md`).

## Current Status

Technical proof cleared; 30-day artifact closed as a v0.1 alpha; severity
calibration attempted and failed; severity decoupled from review priority.

The v0.2/v0.2.1 severity calibration failed the pre-registered
review-priority gate (≥24/30 critical confirmations required):

- v0.2: 6/30 (reviewer 1) and 3/30 (reviewer 2)
- v0.2.1 re-certification: 17/30 (reviewer 1) and 4/30 (reviewer 2)
- v0.2.1 critical-stratum fresh applications: 4/30, 5/30, 12/30, 17/30

Severity labels are therefore retained only as deterministic uncalibrated
triage metadata. The evidence-record primitive remains supported; the
certified-severity claim and buyer-facing priority brief remain blocked.
See `EVIDENCE_RECORD_PRIMITIVE.md`, `SEVERITY_CALIBRATION_v0.2.1.md`, and
`SEVERITY_DECOUPLING_v0.2.1.md`; the full arc is indexed in
`METHODOLOGY.md`.

## License and Citation

Code and functional schemas are licensed under Apache-2.0 (`LICENSE`);
datasets and project prose documentation are licensed under CC BY 4.0
(`DATA_LICENSE.md`). Cite via `CITATION.cff`, or cite an individual record
by its `event_id` and embedded `citation_text`.
