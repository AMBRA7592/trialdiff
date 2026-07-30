# Releasing — Operator Runbook

Steps that require the private working databases or production credentials.
Everything here is deliberately out of scope for CI; the repo carries the
code and the frozen outputs, this file carries the procedure.

## A. Regenerate the event-class package as v0.1.2 (erratum E1 correction)

Requires an intact copy of the **frozen Snapshot C SQLite database** in
`CORPUS.md`: 100 trials and exactly 4,485 adjacent-version patches. This is a
correction release, not a registry-data refresh. **Do not run `ingest` or
backfill from live ClinicalTrials.gov for v0.1.2.** A later data refresh must
use a separate corpus/version label.

```bash
# 1. Prove the frozen input and preserve the source DB:
sqlite3 <frozen_db> "PRAGMA integrity_check;
  SELECT 'trials', count(*) FROM trials
  UNION ALL SELECT 'patches', count(*) FROM trial_patches;"
# Required output: ok; trials|100; patches|4485
cp <frozen_db> /tmp/trialdiff-v0.1.2-a.sqlite3
cp <frozen_db> /tmp/trialdiff-v0.1.2-b.sqlite3

# 2. Independently regenerate two working copies:
for db in /tmp/trialdiff-v0.1.2-{a,b}.sqlite3; do
  python3 -m trialdiff.cli classify --db "$db" --force
  python3 -m trialdiff.cli generate-evidence --db "$db" --force
done

# 3. Compare canonical identities across independent regenerations:
sqlite3 /tmp/trialdiff-v0.1.2-a.sqlite3 \
  "SELECT event_id || '  ' || canonical_hash FROM evidence_records ORDER BY event_id;" \
  > /tmp/trialdiff-v0.1.2-a.hashes
sqlite3 /tmp/trialdiff-v0.1.2-b.sqlite3 \
  "SELECT event_id || '  ' || canonical_hash FROM evidence_records ORDER BY event_id;" \
  > /tmp/trialdiff-v0.1.2-b.hashes
diff -u /tmp/trialdiff-v0.1.2-a.hashes /tmp/trialdiff-v0.1.2-b.hashes
python3 scripts/analyze_event_class_boundary.py \
  --db /tmp/trialdiff-v0.1.2-a.sqlite3
# Required: patches=4485, inclusive_primary_after_completion=73,
# results_cooccurring=63, clean=10

# 4. Record the commands, input checks, and empty diff result in this file:
$EDITOR /tmp/DETERMINISM_ATTESTATION.md

# 5. Export twice, with every cited supporting document copied into docs/
#    and covered by MANIFEST.sha256:
for suffix in a b; do
  python3 scripts/export_event_class_package.py \
    --db "/tmp/trialdiff-v0.1.2-${suffix}.sqlite3" \
    --out "/tmp/event_class_records_v0.1.2-${suffix}" \
    --package-version v0.1.2 \
    --corpus-label breast-cancer-phase2-3-limit100-v021 \
    --doc EVIDENCE_RECORD_PRIMITIVE.md \
    --doc SEVERITY_CALIBRATION_v0.2.1.md \
    --doc SEVERITY_DECOUPLING_v0.2.1.md \
    --doc ERRATA.md \
    --doc /tmp/DETERMINISM_ATTESTATION.md \
    --force
done
diff -qr /tmp/event_class_records_v0.1.2-a /tmp/event_class_records_v0.1.2-b
mv /tmp/event_class_records_v0.1.2-a event_class_records_v0.1.2

# 6. Validate and verify the release candidate:
python3 scripts/validate_event_class_package.py \
  --package event_class_records_v0.1.2 \
  --db /tmp/trialdiff-v0.1.2-a.sqlite3
python3 -m trialdiff.cli verify event_class_records_v0.1.2/records
```

Required corrected results for the frozen input are: 97 records, 54 represented
trials, 106 memberships; class counts 10 / 9 / 3 / 4 / 80; overlaps 88
one-class / 9 two-class / 0 three-class. The boundary analysis must be
recomputed over the same 4,485 patches and must equal 73 inclusive / 63
results-co-occurring / 10 clean before release. Any divergence is a stop
condition, not a count to carry forward.

Then: update `VERSIONS.md` (§4), add the package to CI validation, and tag
(`git tag -a event-class-v0.1.2 -m "Corrected whyStopped class"`).

## B. Redeploy the live database (Neon)

**Do not merge or promote the new frontend while production Neon still has
the pre-migration schema/data.** First build and inspect the PR's Vercel
preview. Temporarily pause automatic production deployment from `main` (or
change the Vercel production branch to a release-hold branch), then perform
the database operation below. This prevents the strict endpoint from going
live against unverifiable legacy rows.

```bash
# 1. Back up production rows before the destructive replacement:
pg_dump "$DATABASE_URL" --data-only --table=evidence_records \
  > /tmp/evidence_records-pre-v0.1.2.sql

# 2. Apply the new migration (canonical_json jsonb -> text):
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f postgres/migrations/006_canonical_json_text.sql

# 3. Re-export from the verified corrected SQLite and atomically re-import:
python3 scripts/sqlite_to_postgres.py /tmp/trialdiff-v0.1.2-a.sqlite3 \
  --truncate --output /tmp/trialdiff_export.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f /tmp/trialdiff_export.sql

# 4. Verify byte-verifiability in place (convert_to, NOT a ::bytea cast —
#    casting text to bytea parses escape syntax and errors on backslashes):
psql "$DATABASE_URL" -c "SELECT count(*) FROM evidence_records
  WHERE encode(sha256(convert_to(canonical_json, 'UTF8')), 'hex') <> canonical_hash;"  # must be 0

# 5. Confirm the expected 97 rows and corrected class counts in Neon.
```

Only after all database checks pass: promote the already-reviewed Vercel
preview (or merge and restore the production branch), then spot-check:

```bash
curl -fsS -D /tmp/trialdiff.headers \
  https://trialdiff.vercel.app/events/<corrected_event_id>.json \
  -o /tmp/trialdiff-record.json
sha256sum /tmp/trialdiff-record.json
grep -iE '^(etag|x-trialdiff-canonical-hash):' /tmp/trialdiff.headers
# all three hashes must agree
```

## C. Freeze policy for new packages

1. Export with `scripts/export_event_class_package.py` (writes records,
   bundled `--doc` inputs, VALIDATION.md, expected_stats.json, and
   MANIFEST.sha256).
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
   the new implementation-pinned `event_class_rule_set_hash` (`07957f8b…`).
3. Upload the v0.1.2 zip built from THIS repository. The exporter in section
   A copies the supporting files into `docs/`; the validator requires every
   package file to be listed in `MANIFEST.sha256`. Do not add files to the
   archive manually after export. Set "Is supplement to" to this
   repository's release tag.
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
