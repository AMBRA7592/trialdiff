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
set -euo pipefail

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

# 7. Preserve the accepted DB and build release artifacts outside /tmp and
#    outside the Git working tree. Set this to a durable private directory:
export RELEASE_PRIVATE=<durable-private-release-directory>
mkdir -p "$RELEASE_PRIVATE"
chmod 700 "$RELEASE_PRIVATE"
test ! -e "$RELEASE_PRIVATE/a.sqlite3"
cp /tmp/trialdiff-v0.1.2-a.sqlite3 "$RELEASE_PRIVATE/a.sqlite3"
cmp /tmp/trialdiff-v0.1.2-a.sqlite3 "$RELEASE_PRIVATE/a.sqlite3"

# Produce the production import twice in fresh processes. The empty cmp is a
# stop condition: the importer must be byte-deterministic across hash seeds.
test ! -e "$RELEASE_PRIVATE/trialdiff-v0.1.2-neon.sql"
PYTHONHASHSEED=0 python3 scripts/sqlite_to_postgres.py \
  "$RELEASE_PRIVATE/a.sqlite3" --truncate \
  --output "$RELEASE_PRIVATE/trialdiff-v0.1.2-neon.sql"
PYTHONHASHSEED=4242 python3 scripts/sqlite_to_postgres.py \
  "$RELEASE_PRIVATE/a.sqlite3" --truncate \
  --output /tmp/trialdiff-v0.1.2-neon.verify.sql
cmp "$RELEASE_PRIVATE/trialdiff-v0.1.2-neon.sql" \
  /tmp/trialdiff-v0.1.2-neon.verify.sql

# Build the one ZIP used unchanged for both the GitHub Release and Zenodo.
# Running from inside the package preserves the v0.1.1 archive's root layout.
test ! -e "$RELEASE_PRIVATE/trialdiff_event_class_records_v0.1.2.zip"
(
  cd event_class_records_v0.1.2
  COPYFILE_DISABLE=1 LC_ALL=C find . -type f -print \
    | LC_ALL=C sort \
    | COPYFILE_DISABLE=1 zip -X -q \
        "$RELEASE_PRIVATE/trialdiff_event_class_records_v0.1.2.zip" -@
)

(
  cd "$RELEASE_PRIVATE"
  shasum -a 256 a.sqlite3 trialdiff-v0.1.2-neon.sql \
    trialdiff_event_class_records_v0.1.2.zip > RELEASE_ARTIFACTS.sha256
  shasum -a 256 -c RELEASE_ARTIFACTS.sha256
)
```

Required corrected results for the frozen input are: 97 records, 54 represented
trials, 106 memberships; class counts 10 / 9 / 3 / 4 / 80; overlaps 88
one-class / 9 two-class / 0 three-class. The boundary analysis must be
recomputed over the same 4,485 patches and must equal 73 inclusive / 63
results-co-occurring / 10 clean before release. Any divergence is a stop
condition, not a count to carry forward.

Then: update `VERSIONS.md` (§4), add the package to CI validation, and require
green CI. The annotated release tag is created and pushed in section D.

### Accepted v0.1.2 release artifacts

The controlled freeze produced the following fixed release inputs. Do not
rebuild or silently substitute any of them during the production window:

- generator code commit: `6176b2121bdcd1cac6ce859d7749ab188de4b183`
- frozen package commit: `8777d04c11e7e660a22db51d3589498911e7d086`
- regenerated SQLite A SHA-256: `8105dbad8ec65a83fa8304b17b193e71a69bef0a0e38c935fd3299cc182e1238`
- production import SQL SHA-256: `3a0f26f81544415c88a8f3d34fd5426feb8d804434b3bcca9aee258e361067e7`
- release ZIP SHA-256: `4681fb0e5baaab53fb9352721a49aaa7b5e2027a18c9029547592ff7dfb709e7`
- release ZIP MD5: `39bbc1d58ad295a60cbebdec1fdc5ff2`
- package manifest SHA-256: `2211d918a4f840ab9150160389856e6315a0fe1e358ac1be4580f8a1cac4c8ec`

## B. Redeploy the live database (Neon)

**Do not merge or promote the new frontend while production Neon still has
the pre-migration schema/data.** First build and inspect the PR's Vercel
preview. Temporarily pause automatic production deployment from `main` (or
change the Vercel production branch to a release-hold branch), then perform
the database operation below. This prevents the strict endpoint from going
live against unverifiable legacy rows.

Use a direct, non-pooled Neon connection for administrative work. Neon's
[connection-pooling guidance](https://neon.com/docs/connect/connection-pooling)
documents direct connections for migrations, `pg_dump`, and `pg_restore`.
A pooled hostname contains `-pooler`; do not use it in this section. Before
changing production, create a named manual snapshot in Neon's Backup & Restore
page when the account offers it. The full custom-format dump below remains
mandatory because the import replaces nine tables, not only
`evidence_records`.

```bash
set -euo pipefail

# 1. Set the direct URL and prove it is not the pooled application URL:
export DATABASE_URL_DIRECT=<direct-non-pooler-neon-url>
case "$DATABASE_URL_DIRECT" in
  *-pooler*) echo "Refusing pooled Neon URL" >&2; exit 1 ;;
esac

# 2. Re-check the staged artifacts immediately before the hold window:
(
  cd "$RELEASE_PRIVATE"
  shasum -a 256 -c RELEASE_ARTIFACTS.sha256
)

# 3. Make a full rollback archive before the destructive replacement. A dump
#    of evidence_records alone is insufficient: --truncate replaces all nine
#    exported tables. pg_restore --list must succeed and produce a nonempty
#    inventory before continuing.
umask 077
export PRE_RELEASE_DUMP="$RELEASE_PRIVATE/neon-pre-v0.1.2.dump"
pg_dump --dbname="$DATABASE_URL_DIRECT" --format=custom \
  --no-owner --no-acl --file="$PRE_RELEASE_DUMP"
pg_restore --list "$PRE_RELEASE_DUMP" \
  > "$RELEASE_PRIVATE/neon-pre-v0.1.2.dump.list"
test -s "$PRE_RELEASE_DUMP"
test -s "$RELEASE_PRIVATE/neon-pre-v0.1.2.dump.list"
shasum -a 256 "$PRE_RELEASE_DUMP" \
  > "$RELEASE_PRIVATE/neon-pre-v0.1.2.dump.sha256"
shasum -a 256 -c "$RELEASE_PRIVATE/neon-pre-v0.1.2.dump.sha256"

# 4. Apply the new migration (canonical_json jsonb -> text):
psql "$DATABASE_URL_DIRECT" -v ON_ERROR_STOP=1 \
  -f postgres/migrations/006_canonical_json_text.sql

# 5. Atomically import the already-verified SQL. The file contains BEGIN,
#    TRUNCATE/INSERT statements, sequence resets, and COMMIT; ON_ERROR_STOP
#    makes any SQL error abort instead of carrying a partial load forward.
psql "$DATABASE_URL_DIRECT" -v ON_ERROR_STOP=1 \
  -f "$RELEASE_PRIVATE/trialdiff-v0.1.2-neon.sql"

# 6. Verify byte-verifiability in place (convert_to, NOT a ::bytea cast —
#    casting text to bytea parses escape syntax and errors on backslashes):
psql "$DATABASE_URL_DIRECT" -v ON_ERROR_STOP=1 -c "
SELECT count(*) AS canonical_mismatches
FROM evidence_records
WHERE encode(sha256(convert_to(canonical_json, 'UTF8')), 'hex') <> canonical_hash;
"  # must be 0

# 7. Confirm the release population in Neon. Required counts are
#    100 / 4485 / 868 / 97 / 54 / 106.
psql "$DATABASE_URL_DIRECT" -v ON_ERROR_STOP=1 -c "
SELECT 'trials' AS measure, count(*)::bigint AS value FROM trials
UNION ALL SELECT 'trial_patches', count(*) FROM trial_patches
UNION ALL SELECT 'materiality_events', count(*) FROM materiality_events
UNION ALL SELECT 'evidence_records', count(*) FROM evidence_records
UNION ALL SELECT 'evidence_record_trials', count(DISTINCT nct_id) FROM evidence_records
UNION ALL SELECT 'event_class_memberships',
  sum(jsonb_array_length(event_classes_json)) FROM evidence_records;
"

# Required classes: enrollment/results/primary/secondary/whyStopped =
# 3 / 80 / 10 / 9 / 4.
psql "$DATABASE_URL_DIRECT" -v ON_ERROR_STOP=1 -c "
SELECT cls.event_class, count(*)::int
FROM evidence_records er
CROSS JOIN LATERAL jsonb_array_elements_text(er.event_classes_json)
  AS cls(event_class)
GROUP BY cls.event_class
ORDER BY cls.event_class;
"

# Required overlaps: 88 one-class / 9 two-class / no three-class row.
psql "$DATABASE_URL_DIRECT" -v ON_ERROR_STOP=1 -c "
SELECT jsonb_array_length(event_classes_json) AS event_class_count,
  count(*)::int
FROM evidence_records
GROUP BY event_class_count
ORDER BY event_class_count;
"

# The corrected former flagship must exist under its rotated ID, carry two
# classes, and hash to the frozen v0.1.2 value.
psql "$DATABASE_URL_DIRECT" -v ON_ERROR_STOP=1 -c "
SELECT event_id, canonical_hash, event_classes_json
FROM evidence_records
WHERE event_id = 'evt_NCT04278144_v33_v34_f64d3dc78625';
"
```

Only after all database checks pass: promote the already-reviewed Vercel
preview (or merge and restore the production branch), then spot-check:

```bash
curl -fsS -D /tmp/trialdiff.headers \
  https://trialdiff.vercel.app/events/evt_NCT04278144_v33_v34_f64d3dc78625.json \
  -o /tmp/trialdiff-record.json
shasum -a 256 /tmp/trialdiff-record.json
grep -iE '^(etag|x-trialdiff-canonical-hash):' /tmp/trialdiff.headers
# All three hashes must equal:
# d96faa8297dc182164e63da59def65b831533a0780ecdbeb133325d273d616f0
```

## C. Freeze policy for new packages

1. Export with `scripts/export_event_class_package.py` (writes records,
   bundled `--doc` inputs, VALIDATION.md, expected_stats.json, and
   MANIFEST.sha256).
2. Never edit files inside a frozen package afterwards; corrections go to a
   new package version + `ERRATA.md`.
3. Root-manifest policy (documentation vs record entries) is defined in
   `ERRATA.md`.

### Implementation-hash maintenance

The implementation hashes cover exact normalized source bytes in these files:
`trialdiff/event_classes.py`, `trialdiff/classifier/materiality.py`,
`trialdiff/classifier/pathmatch.py`, `trialdiff/classifier/timing.py`,
`trialdiff/jsonpatch.py`, and `trialdiff/ruleset.py`. Any byte edit, including
a comment-only edit, intentionally rotates at least one published rule hash.
Before merging such an edit, update the golden pins and record the transition
in `ERRATA.md` and `VERSIONS.md`; regenerate records for the affected release.

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
4. Before Zenodo publication, merge, branch deletion, or any history-rewriting
   operation, create and push the annotated v0.1.2 tag at the frozen package
   commit. The published Zenodo v0.1.1 erratum description pins commit
   `6176b21`; `8777d04` descends from it, so the pushed tag keeps that cited
   SHA reachable even if PR #1 is later squashed or rebased. Keep Zenodo's
   link pointed at the immutable SHA; the tag supplies reachability.

```bash
git tag -a event-class-v0.1.2 \
  8777d04c11e7e660a22db51d3589498911e7d086 \
  -m "Corrected event-class package v0.1.2"
git push origin refs/tags/event-class-v0.1.2
git ls-remote --tags origin refs/tags/event-class-v0.1.2
git merge-base --is-ancestor \
  6176b2121bdcd1cac6ce859d7749ab188de4b183 event-class-v0.1.2
```

Every commit SHA cited by published DOI metadata must be retained by a pushed
tag before its branch can be deleted or its commits rewritten. Do not rely on
an unpushed local tag or on an open pull-request branch for long-term
reachability.

Cut the GitHub Release from `event-class-v0.1.2` and attach the already-staged
`trialdiff_event_class_records_v0.1.2.zip` without rebuilding it. Its SHA-256
must remain `4681fb0e5baaab53fb9352721a49aaa7b5e2027a18c9029547592ff7dfb709e7`.

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
