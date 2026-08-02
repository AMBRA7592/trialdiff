# Releasing — Operator Runbook

Steps that require the private working databases or production credentials.
Everything here is deliberately out of scope for CI; the repo carries the
code and the frozen outputs, this file carries the procedure.

## A. Regenerate event-class v0.1.3 (erratum E4 correction)

v0.1.3 is a correction release over the exact accepted v0.1.2 source database,
not a registry refresh. Do not ingest, backfill, or alter source tables. Keep
`event_class_records_v0.1.2/`, its tag, hashes, IDs, GitHub Release, DOI, and
production bytes unchanged as historical provenance.

The accepted source is the durable v0.1.2 SQLite A artifact with SHA-256
`8105dbad8ec65a83fa8304b17b193e71a69bef0a0e38c935fd3299cc182e1238`.
Before regeneration, the read-only E4 audit is a stop gate:

```bash
set -euo pipefail
export RELEASE_PRIVATE=<durable-private-v0.1.3-release-directory>
export FROZEN_V012_DB=<durable-v0.1.2-release-directory>/a.sqlite3

echo "8105dbad8ec65a83fa8304b17b193e71a69bef0a0e38c935fd3299cc182e1238  $FROZEN_V012_DB" \
  | shasum -a 256 -c -
python3 scripts/audit_event_class_inputs.py \
  --db "$FROZEN_V012_DB" --expect-v0.3
# Required: op counts add/remove/replace = 25076/22710/99332; 4485 replayed;
# 4385 stored TO matches; 100 reconstructed TO; primary = 148 relevant / 73
# after completion / 63 reconciled / 10 clean with zero old/new disagreement;
# secondary = 16 candidates / 12 corrected with exactly three disagreements:
# NCT01224678 v109->v110, NCT03094169 v11->v12, and NCT03734029 v29->v30.
# All 11 post-completion secondary-array count decreases must be covered by the
# independently defined structural candidate surface; uncovered list = [].
# Event-class totals are also enforced here: 97 records / 54 trials / 109
# memberships, with classes 10 / 12 / 3 / 4 / 80.

mkdir -p "$RELEASE_PRIVATE"
chmod 700 "$RELEASE_PRIVATE"
cp "$FROZEN_V012_DB" "$RELEASE_PRIVATE/v0.1.3-a.sqlite3"
cp "$FROZEN_V012_DB" "$RELEASE_PRIVATE/v0.1.3-b.sqlite3"

for db in "$RELEASE_PRIVATE"/v0.1.3-{a,b}.sqlite3; do
  python3 -m trialdiff.cli classify --db "$db" --force
  python3 -m trialdiff.cli generate-evidence --db "$db" --force
done

for suffix in a b; do
  sqlite3 "$RELEASE_PRIVATE/v0.1.3-${suffix}.sqlite3" \
    "SELECT event_id || '  ' || canonical_hash FROM evidence_records ORDER BY event_id;" \
    > "$RELEASE_PRIVATE/v0.1.3-${suffix}.hashes"
done
diff -u "$RELEASE_PRIVATE/v0.1.3-a.hashes" \
  "$RELEASE_PRIVATE/v0.1.3-b.hashes"
python3 scripts/analyze_event_class_boundary.py \
  --db "$RELEASE_PRIVATE/v0.1.3-a.sqlite3"
# Required boundary: 4485 / 73 / 63 / 10.

$EDITOR "$RELEASE_PRIVATE/DETERMINISM_ATTESTATION_v0.1.3.md"
# The attestation must state that stored-TO equality proves internal ingestion
# consistency, not independent registry fidelity. It must also distinguish the
# 100 successful missing-TO replays from externally checked reconstructions.
for suffix in a b; do
  python3 scripts/export_event_class_package.py \
    --db "$RELEASE_PRIVATE/v0.1.3-${suffix}.sqlite3" \
    --out "$RELEASE_PRIVATE/event_class_records_v0.1.3-${suffix}" \
    --package-version v0.1.3 \
    --corpus-label breast-cancer-phase2-3-limit100-v021 \
    --doc EVIDENCE_RECORD_PRIMITIVE.md \
    --doc SEVERITY_CALIBRATION_v0.2.1.md \
    --doc SEVERITY_DECOUPLING_v0.2.1.md \
    --doc ERRATA.md \
    --doc "$RELEASE_PRIVATE/DETERMINISM_ATTESTATION_v0.1.3.md" \
    --force
done
diff -qr "$RELEASE_PRIVATE/event_class_records_v0.1.3-a" \
  "$RELEASE_PRIVATE/event_class_records_v0.1.3-b"
python3 scripts/validate_event_class_package.py \
  --package "$RELEASE_PRIVATE/event_class_records_v0.1.3-a" \
  --db "$RELEASE_PRIVATE/v0.1.3-a.sqlite3"
python3 -m trialdiff.cli verify \
  "$RELEASE_PRIVATE/event_class_records_v0.1.3-a/records"
```

Required v0.1.3 results are 97 records, 54 represented trials, and 109
memberships; class counts primary / secondary / enrollment / whyStopped /
results co-occurrence = 10 / 12 / 3 / 4 / 80; overlaps = 85 one-class / 12
two-class / 0 three-class. The boundary remains 4,485 / 73 / 63 / 10. Any
different count, replay failure, stored-TO mismatch, identity diff, or package
diff halts the release. Never reconcile a divergence by editing generated
records or `expected_stats.json`.

CI exercises the audit implementation against synthetic fixtures; it cannot
attest the private frozen-corpus totals. The manifest-covered determinism
attestation must record the retained-DB audit command and complete output.

Before freezing or deploying v0.1.3, the production compatibility work in
section B must exist and be independently reviewed: every superseded v0.1.2
event ID must continue serving its exact immutable JSON bytes and original
hashes, with superseded/successor metadata. Do not redirect or 404 a published
ID. Active feeds may move to v0.1.3 only after this resolver is verified.

## A1. Historical accepted v0.1.2 procedure (erratum E1 correction)

> **ARCHIVE ONLY - DO NOT EXECUTE.** This block records the completed v0.1.2
> release. Current operators must use section A and must not substitute these
> commands, counts, IDs, or artifact hashes into a v0.1.3 release.

Requires an intact copy of the **frozen Snapshot C SQLite database** in
`CORPUS.md`: 100 trials and exactly 4,485 adjacent-version patches. This is a
correction release, not a registry-data refresh. **Do not run `ingest` or
backfill from live ClinicalTrials.gov for v0.1.2.** A later data refresh must
use a separate corpus/version label.

```text
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
green CI. The accepted v0.1.2 tag evidence is retained in section D1.

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

## B. Preserve published IDs and promote v0.1.3 manually

v0.1.3 rotates every event ID because the implementation-pinned rule-set hash
changes. Published v0.1.2 IDs are permanent citation keys. Before replacing the
active generation, implement and test a version-aware resolver with these
requirements:

1. The active feed and corpus counts select only v0.1.3.
2. A v0.1.2 HTML event URL returns HTTP 200 with a visible superseded notice and
   the v0.1.3 successor link.
3. A v0.1.2 JSON event URL returns HTTP 200 with the exact immutable v0.1.2
   canonical bytes and original ETag/hash. It does not redirect.
4. The successor metadata is outside the immutable JSON body, for example in
   response headers and the HTML view; never rewrite a published record to add
   it.
5. An unknown event ID still returns 404.
6. Backup and rollback cover both active and superseded generations.

The existing `scripts/sqlite_to_postgres.py --truncate` path is prohibited for
v0.1.3 because it deletes the published v0.1.2 rows. The production design must
add a package-generation column (distinct from the record-schema
`evidence_version`), import v0.1.3 additively, and make the active generation an
explicit configuration value. Every feed, corpus count, trial/patch evidence
lookup, and rule-set query must filter that value; correctness must not depend
on `generated_at`, hash ordering, or a single-row assumption.

Canonical JSON bodies remain immutable. Supersession state belongs in response
headers and HTML, never in the hashed record body. Because published JSON uses
one-year immutable caching, also expose a non-immutable supersession index that
maps every published event ID to its package generation and successor, if any.
The index must be independently queryable without fetching or mutating a cached
record response.

TrialDiff uses manual Vercel promotion; no Git-triggered production deployment
is configured. Build and verify a preview, migrate/import Neon under a hold,
then promote that exact reviewed deployment ID with `vercel promote`. Do not
trigger a fresh production rebuild between preview verification and promotion.

The production gate must capture anonymous evidence for one superseded v0.1.2
ID, its v0.1.3 successor, and an unknown control: response status, headers,
saved body, body SHA-256, ETag, and offline `trialdiff verify`. Promotion fails
unless both generations match their frozen package files byte-for-byte.

## B1. Historical v0.1.2 Neon migration procedure

> **ARCHIVE ONLY - DO NOT EXECUTE.** This destructive truncate-and-reload
> procedure records the completed v0.1.2 migration. It violates the v0.1.3
> coexistence policy and must not be adapted as the current production path.

**Do not merge or promote the new frontend while production Neon still has
the pre-migration schema/data.** First build and inspect the PR's Vercel
preview. Because production promotion is manual and no Git-triggered deploy is
configured, leave the existing production deployment in place while performing
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

```text
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

Only after all database checks pass: promote the exact already-reviewed Vercel
preview deployment ID, then spot-check:

```text
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

## D. Tags, releases, and DOI for v0.1.3

Only after the v0.1.3 freeze commit and independent audit:

1. Create and push an annotated `event-class-v0.1.3` tag at the exact freeze
   commit. Confirm the tag on `origin` before publishing or deleting any branch.
2. Build one deterministic ZIP from the accepted package, pin its SHA-256, and
   use that same file unchanged for the GitHub Release and Zenodo.
3. Complete the version-aware production migration and anonymous live checks in
   section B before publishing the new Zenodo version.
4. Add a metadata-only E4 notice to Zenodo v0.1.2. Do not alter its deposited
   ZIP or version DOI.
5. Publish v0.1.3 as a new version under concept DOI
   `10.5281/zenodo.20801956`, with `Is supplement to` pointing at the immutable
   GitHub Release tag.
6. Verify the anonymous Zenodo download against the staged ZIP and its internal
   manifest, then update `CITATION.cff`, `README.md`, `VERSIONS.md`, and any
   manuscript citation with the minted version DOI.

No v0.1.3 hash, event ID, tag, GitHub Release, DOI, or live URL may be filled in
from an expectation. Record them only from the accepted frozen artifacts.

## D1. Historical accepted v0.1.2 tags, release, and DOI

> **ARCHIVE ONLY - DO NOT EXECUTE.** These commands and identifiers document a
> completed publication. Use section D for v0.1.3.

This section records the completed v0.1.2 publication workflow and its exact
anchors. Do not rerun it or replace its hashes with v0.1.3 values.

Zenodo state: concept DOI `10.5281/zenodo.20801956`; version DOIs v0.1
`10.5281/zenodo.20801957` (2026-06-22) and v0.1.1
`10.5281/zenodo.20816639` (2026-06-23, author Amadeus Brandes, CC-BY-4.0,
linked to trialdiff-public commit `7a11808`), plus the E1-corrected v0.1.2
`10.5281/zenodo.21755258` (2026-08-02, CC-BY-4.0, linked to this repository's
`event-class-v0.1.2` GitHub Release).

Historical v0.1.2 rules (completed 2026-08-02):

1. **Never mutate or withdraw v0.1.1.** It stays as published; `ERRATA.md`
   E1 is its correction record. On the Zenodo v0.1.1 page, add a link to
   `ERRATA.md` in the description ("Errata: see …") — editing metadata
   description is allowed without changing the deposited files.
2. **Publish v0.1.2 as a NEW VERSION under the existing concept DOI**
   (Zenodo → the v0.1.1 record → "New version"), so
   `10.5281/zenodo.20801956` keeps resolving to the latest corrected
   dataset. Include the erratum text in the version description and cite
   the new implementation-pinned `event_class_rule_set_hash` (`07957f8b…`).
3. Upload the v0.1.2 zip built from THIS repository. The exporter in historical
   section A1 copies the supporting files into `docs/`; the validator requires every
   package file to be listed in `MANIFEST.sha256`. Do not add files to the
   archive manually after export. Set "Is supplement to" to this
   repository's release tag.
4. Before Zenodo publication, merge, branch deletion, or any history-rewriting
   operation, create and push the annotated v0.1.2 tag at the frozen package
   commit. The published Zenodo v0.1.1 erratum description pins commit
   `6176b21`; `8777d04` descends from it, so the pushed tag keeps that cited
   SHA reachable even if PR #1 is later squashed or rebased. Keep Zenodo's
   link pointed at the immutable SHA; the tag supplies reachability.

```text
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

5. `CITATION.cff`, `README.md`, and `VERSIONS.md` were updated with the minted
   v0.1.2 DOI. After E4, a manuscript may cite v0.1.2 only as the historical
   affected artifact with E4 disclosed; corrected event-class counts must cite
   the eventual v0.1.3 DOI.

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
