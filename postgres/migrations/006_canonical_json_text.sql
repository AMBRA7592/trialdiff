-- evidence_records.canonical_json must preserve the exact serialized bytes
-- that hash to canonical_hash. jsonb re-orders keys and drops the original
-- serialization, which made the stored value unverifiable against its own
-- hash. Store the canonical form as text; cast to jsonb at query time if a
-- jsonb view of it is ever needed.
ALTER TABLE evidence_records
  ALTER COLUMN canonical_json TYPE text
  USING canonical_json::text;

-- NOTE: rows imported while the column was jsonb no longer carry the
-- original canonical bytes; converting the column does not restore them.
-- Re-import from the source SQLite database (scripts/sqlite_to_postgres.py
-- with --truncate) after applying this migration so canonical_json matches
-- canonical_hash again.
