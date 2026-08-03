BEGIN;

CREATE TABLE evidence_record_generations (
  package_generation text PRIMARY KEY,
  is_active boolean NOT NULL DEFAULT false,
  record_count integer NOT NULL CHECK (record_count >= 0),
  represented_trial_count integer NOT NULL CHECK (represented_trial_count >= 0),
  membership_count integer NOT NULL CHECK (membership_count >= 0),
  corpus_trial_count integer NOT NULL CHECK (corpus_trial_count >= 0),
  corpus_patch_count integer NOT NULL CHECK (corpus_patch_count >= 0),
  material_event_count integer NOT NULL CHECK (material_event_count >= 0),
  critical_event_count integer NOT NULL CHECK (critical_event_count >= 0),
  high_event_count integer NOT NULL CHECK (high_event_count >= 0),
  severity_counts_json jsonb NOT NULL,
  corpus_max_submitted_date text,
  rule_set_hash text NOT NULL CHECK (length(rule_set_hash) = 64),
  source_database_sha256 text CHECK (
    source_database_sha256 IS NULL OR length(source_database_sha256) = 64
  ),
  imported_at timestamptz NOT NULL DEFAULT now(),
  CHECK (package_generation ~ '^v[0-9]+\.[0-9]+\.[0-9]+$')
);

CREATE UNIQUE INDEX idx_evidence_record_generations_one_active
  ON evidence_record_generations ((is_active))
  WHERE is_active;

-- Migration 006 production contains exactly the published v0.1.2 generation.
-- A clean database has no evidence rows yet; its first importer invocation
-- creates generation metadata instead.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM evidence_records)
     AND (SELECT count(DISTINCT rule_set_hash) FROM evidence_records) <> 1 THEN
    RAISE EXCEPTION 'existing evidence_records contain multiple rule-set hashes';
  END IF;
END
$$;

INSERT INTO evidence_record_generations (
  package_generation,
  is_active,
  record_count,
  represented_trial_count,
  membership_count,
  corpus_trial_count,
  corpus_patch_count,
  material_event_count,
  critical_event_count,
  high_event_count,
  severity_counts_json,
  corpus_max_submitted_date,
  rule_set_hash,
  source_database_sha256
)
SELECT
  'v0.1.2',
  true,
  count(*)::integer,
  count(DISTINCT nct_id)::integer,
  coalesce(sum(jsonb_array_length(event_classes_json)), 0)::integer,
  (SELECT count(*)::integer FROM trials),
  (SELECT count(*)::integer FROM trial_patches),
  (SELECT count(*)::integer FROM materiality_events),
  (SELECT count(*)::integer FROM materiality_events WHERE severity = 'critical'),
  (SELECT count(*)::integer FROM materiality_events WHERE severity = 'high'),
  (
    SELECT coalesce(jsonb_object_agg(severity, count ORDER BY severity), '{}'::jsonb)
    FROM (
      SELECT severity, count(*)::integer AS count
      FROM materiality_events
      GROUP BY severity
    ) severity_counts
  ),
  (SELECT max(submitted_date) FROM materiality_events),
  min(rule_set_hash),
  NULL
FROM evidence_records
HAVING count(*) > 0;

ALTER TABLE evidence_records RENAME TO evidence_record_store;

ALTER TABLE evidence_record_store
  ADD COLUMN package_generation text;

UPDATE evidence_record_store
SET package_generation = 'v0.1.2';

ALTER TABLE evidence_record_store
  ALTER COLUMN package_generation SET NOT NULL,
  ADD CONSTRAINT evidence_record_store_generation_fk
    FOREIGN KEY (package_generation)
    REFERENCES evidence_record_generations(package_generation)
    ON DELETE RESTRICT;

CREATE UNIQUE INDEX idx_evidence_record_store_generation_transition
  ON evidence_record_store(package_generation, nct_id, from_version, to_version);

CREATE INDEX idx_evidence_record_store_generation_date
  ON evidence_record_store(package_generation, submitted_date DESC);

CREATE TABLE evidence_record_supersessions (
  superseded_event_id text PRIMARY KEY
    REFERENCES evidence_record_store(event_id) ON DELETE RESTRICT,
  successor_event_id text NOT NULL UNIQUE
    REFERENCES evidence_record_store(event_id) ON DELETE RESTRICT,
  recorded_at timestamptz NOT NULL DEFAULT now(),
  CHECK (superseded_event_id <> successor_event_id)
);

-- The legacy object name remains an active-only compatibility view. The
-- pre-coexistence frontend can continue querying it during migration without
-- seeing both generations. New exact-ID resolvers query the backing store.
CREATE VIEW evidence_records AS
SELECT er.*
FROM evidence_record_store er
JOIN evidence_record_generations generation
  ON generation.package_generation = er.package_generation
WHERE generation.is_active;

CREATE FUNCTION trialdiff_activate_evidence_generation(target_generation text)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  previous_generation text;
  previous_count integer;
  target_count integer;
  target_expected_count integer;
  target_rule_hash_count integer;
  target_canonical_mismatches integer;
  mapped_count integer;
BEGIN
  LOCK TABLE evidence_record_generations IN EXCLUSIVE MODE;

  IF NOT EXISTS (
    SELECT 1
    FROM evidence_record_generations
    WHERE package_generation = target_generation
  ) THEN
    RAISE EXCEPTION 'unknown evidence package generation: %', target_generation;
  END IF;

  SELECT record_count
  INTO target_expected_count
  FROM evidence_record_generations
  WHERE package_generation = target_generation;

  SELECT count(*), count(DISTINCT rule_set_hash)
  INTO target_count, target_rule_hash_count
  FROM evidence_record_store
  WHERE package_generation = target_generation;

  SELECT count(*)
  INTO target_canonical_mismatches
  FROM evidence_record_store
  WHERE package_generation = target_generation
    AND encode(sha256(convert_to(canonical_json, 'UTF8')), 'hex') <> canonical_hash;

  IF target_count = 0
     OR target_count <> target_expected_count
     OR target_rule_hash_count <> 1
     OR target_canonical_mismatches <> 0 THEN
    RAISE EXCEPTION 'generation % is not activatable: expected %, stored %, rule hashes %, canonical mismatches %',
      target_generation, target_expected_count, target_count,
      target_rule_hash_count, target_canonical_mismatches;
  END IF;

  SELECT package_generation
  INTO previous_generation
  FROM evidence_record_generations
  WHERE is_active;

  IF previous_generation = target_generation THEN
    RETURN;
  END IF;

  IF previous_generation IS NOT NULL THEN
    SELECT count(*) INTO previous_count
    FROM evidence_record_store
    WHERE package_generation = previous_generation;

    SELECT count(*) INTO mapped_count
    FROM evidence_record_supersessions mapping
    JOIN evidence_record_store old_record
      ON old_record.event_id = mapping.superseded_event_id
     AND old_record.package_generation = previous_generation
    JOIN evidence_record_store new_record
      ON new_record.event_id = mapping.successor_event_id
     AND new_record.package_generation = target_generation;

    IF previous_count = 0
       OR previous_count <> target_count
       OR mapped_count <> previous_count THEN
      RAISE EXCEPTION 'activation requires a complete one-to-one map from % to %: old %, new %, mapped %',
        previous_generation, target_generation, previous_count, target_count, mapped_count;
    END IF;
  END IF;

  UPDATE evidence_record_generations
  SET is_active = false
  WHERE is_active;

  UPDATE evidence_record_generations
  SET is_active = true
  WHERE package_generation = target_generation;
END;
$$;

COMMIT;
