# Releasing — Operator Runbook

Steps that require the private working databases or production credentials.
Everything here is deliberately out of scope for CI; the repo carries the
code and the frozen outputs, this file carries the procedure.

## A. Regenerate the event-class package as v0.1.2 (erratum E1 correction)

Requires the regenerated 100-study SQLite database (Snapshot C in
`CORPUS.md`).

```bash
# 1. Backfill missing TO-version snapshots if desired (optional but
#    recommended: 30/100 package records had to_snapshot_hash=null):
python3 -m trialdiff.cli ingest --db <db> --nct-file corpora/breast_cancer_phase2_3_20260520_limit100.txt

# 2. Re-classify and regenerate under the corrected v0.2 definitions:
python3 -m trialdiff.cli classify --db <db> --force
python3 -m trialdiff.cli generate-evidence --db <db> --force

# 3. Export the corrected package:
python3 scripts/export_event_class_package.py --db <db> \
  --out event_class_records_v0.1.2 --package-version v0.1.2 \
  --corpus-label breast-cancer-phase2-3-limit100-v021 --force

# 4. Validate and verify:
python3 scripts/validate_event_class_package.py --package event_class_records_v0.1.2 --db <db>
python3 -m trialdiff.cli verify event_class_records_v0.1.2/records
```

Expect `why_stopped_removed_in_terminal_context` to drop from 13 to ~4
memberships (exact count depends on backfilled snapshots; every membership
must now be evidenced). Note re-ingest also pulls registry changes made
since the snapshot, so overall counts may grow — record the new counts in
the package's VALIDATION.md and update `ERRATA.md` E1 status.

Then: update `VERSIONS.md` (§4), add the package to CI validation, and tag
(`git tag -a event-class-v0.1.2 -m "Corrected whyStopped class"`).

## B. Redeploy the live database (Neon)

```bash
# 1. Apply the new migration (canonical_json jsonb -> text):
psql "$DATABASE_URL" -f postgres/migrations/006_canonical_json_text.sql

# 2. Re-export from the regenerated SQLite and re-import:
python3 scripts/sqlite_to_postgres.py <db> --truncate --output /tmp/trialdiff_export.sql
psql "$DATABASE_URL" -f /tmp/trialdiff_export.sql

# 3. Verify byte-verifiability in place (convert_to, NOT a ::bytea cast —
#    casting text to bytea parses escape syntax and errors on backslashes):
psql "$DATABASE_URL" -c "SELECT count(*) FROM evidence_records
  WHERE encode(sha256(convert_to(canonical_json, 'UTF8')), 'hex') <> canonical_hash;"  # must be 0

# 4. Spot-check the live endpoint:
curl -s https://trialdiff.vercel.app/events/<event_id>.json | sha256sum
# must equal the ETag / x-trialdiff-canonical-hash header value
```

## C. Freeze policy for new packages

1. Export with `scripts/export_event_class_package.py` (writes records,
   VALIDATION.md, expected_stats.json, MANIFEST.sha256).
2. Never edit files inside a frozen package afterwards; corrections go to a
   new package version + `ERRATA.md`.
3. Root-manifest policy (documentation vs record entries) is defined in
   `ERRATA.md`.

## D. Tags, releases, DOI

Zenodo state (already published, from `AMBRA7592/trialdiff-public`):
concept DOI `10.5281/zenodo.20801956`; version DOIs v0.1
`10.5281/zenodo.20801957` (2026-06-22) and v0.1.1
`10.5281/zenodo.20816639` (2026-06-23, author Amadeus Brandes, CC-BY-4.0,
linked to trialdiff-public commit `7a11808`).

Rules for v0.1.2 and later:

1. **Never mutate or withdraw v0.1.1.** It stays as published; `ERRATA.md`
   E1 is its correction record. On the Zenodo v0.1.1 page, add a link to
   `ERRATA.md` in the description ("Errata: see …") — editing metadata
   description is allowed without changing the deposited files.
2. **Publish v0.1.2 as a NEW VERSION under the existing concept DOI**
   (Zenodo → the v0.1.1 record → "New version"), so
   `10.5281/zenodo.20801956` keeps resolving to the latest corrected
   dataset. Include the erratum text in the version description and cite
   the new `event_class_rule_set_hash` (`b57fd656…`).
3. Upload the v0.1.2 zip built from THIS repository
   (`tar`/`zip` of `event_class_records_v0.1.2/` plus a `docs/` folder with
   `EVIDENCE_RECORD_PRIMITIVE.md`, `SEVERITY_CALIBRATION_v0.2.1.md`,
   `SEVERITY_DECOUPLING_v0.2.1.md`, and `ERRATA.md`, mirroring the v0.1.1
   layout), and set "Is supplement to" to this repository's release tag.
4. Tag in git and cut a GitHub Release with the same archive as asset:

```bash
git tag -a v0.1-alpha <freeze-commit> -m "Frozen 25-study evidence demo"
git tag -a event-class-v0.1.1 <package-commit> -m "Event-class package v0.1.1 (see ERRATA.md E1)"
git tag -a event-class-v0.1.2 <new-package-commit> -m "Corrected event-class package"
git push origin --tags
```

5. Update `CITATION.cff`, `README.md`, and `VERSIONS.md` with the new
   version DOI once minted. The paper must cite **v0.1.2**, not v0.1.1.

## D2. Repository authority (one-time)

`AMBRA7592/trialdiff` is the active canonical repository;
`AMBRA7592/trialdiff-public` is the immutable snapshot behind the
published DOIs. To make that legible on GitHub:

1. In `trialdiff-public`, add a final commit prepending a banner to its
   README: "Historical snapshot backing Zenodo 10.5281/zenodo.20816639
   (v0.1.1, carries erratum E1) — active development:
   github.com/AMBRA7592/trialdiff", then **archive** the repository
   (Settings → Archive). Archiving is reversible and preserves the Zenodo
   'Is supplement to' link.
2. Do not delete or rename `trialdiff-public`: the DOI metadata points at
   it by URL and commit hash.

## E. Blinded-review hygiene for future calibration rounds

The `CALIBRATION_REVIEW_CROSSWALK_UNBLINDING_KEY_*.csv` files map blinded
`review_record_id`s to everything reviewers must not see. For completed
rounds they are published for auditability; for any FUTURE round, do not
commit the key while review is open. Use commit-reveal instead:

1. generate the crosswalk, compute `sha256sum` of it, commit ONLY the hash
   (e.g. in the round's sample plan);
2. run the blinded review and adjudication;
3. then commit the crosswalk itself — the pre-committed hash proves it was
   not altered after the reviews.

## F. GitHub repository metadata (one-time)

Set in Settings → General: description ("Deterministic, hash-verifiable
Evidence Records for ClinicalTrials.gov amendment history — with a published
failed severity calibration"), website (https://trialdiff.vercel.app), and
topics (clinical-trials, clinicaltrials-gov, meta-research, provenance,
reproducibility, dataset, registered-report).
