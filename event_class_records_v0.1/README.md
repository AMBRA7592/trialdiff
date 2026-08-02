# event_class_records_v0.1 — superseded stub

This package's 100 record files were **byte-identical** to those in
`event_class_records_v0.1.1/records/` (the two packages differed only in
`VALIDATION.md`). The duplicate copies were removed on 2026-07-14 to end a
6.9 MB-per-docfix duplication pattern; the equality is provable without the
files: compare the `records/*` entries in this directory's
`MANIFEST.sha256` with those in `../event_class_records_v0.1.1/MANIFEST.sha256`
— every hash matches.

Retained here for the historical record:

- `MANIFEST.sha256` — the original v0.1 manifest (its `records/*` entries
  now verify against the v0.1.1 copies)
- `VALIDATION.md` — the original v0.1 validation note

The full v0.1 tree also remains available in git history (commit
`3ffadd1`, "Add event-class evidence record package").

Note: both v0.1 and v0.1.1 carry erratum E1 (spurious
`why_stopped_removed_in_terminal_context` memberships) — see `../ERRATA.md`.
