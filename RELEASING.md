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
  --out event_class_records_v0.1.2 --corpus-label breast-cancer-phase2-3-limit100-v021 --force

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

# 3. Verify byte-verifiability in place:
psql "$DATABASE_URL" -c "SELECT count(*) FROM evidence_records
  WHERE encode(sha256(canonical_json::bytea), 'hex') <> canonical_hash;"  # must be 0

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

```bash
git tag -a v0.1-alpha <freeze-commit> -m "Frozen 25-study evidence demo"
git tag -a event-class-v0.1.1 <package-commit> -m "Event-class package v0.1.1"
git push origin --tags
```

Then create GitHub Releases per tag with the package tarballs as assets
(`tar czf event_class_records_v0.1.1.tar.gz event_class_records_v0.1.1/`),
and enable the Zenodo–GitHub integration to mint a DOI on the next release
(the repository-independent deposit both package VALIDATION notes list as
TODO). Add the DOI to `CITATION.cff` and `README.md`.

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
