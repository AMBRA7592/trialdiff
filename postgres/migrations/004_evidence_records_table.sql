CREATE TABLE IF NOT EXISTS evidence_records (
  event_id text PRIMARY KEY,
  nct_id text NOT NULL REFERENCES trials(nct_id) ON DELETE CASCADE,
  from_version integer NOT NULL,
  to_version integer NOT NULL,
  submitted_date text,
  timing_context text,
  severity_pre_timing text NOT NULL,
  severity text NOT NULL,
  category text NOT NULL,
  categories_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  changed_paths_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  deterministic_rules_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  value_signals_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  claims_supported_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  claims_not_supported_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  review_question text NOT NULL,
  citation_text text NOT NULL,
  canonical_json jsonb NOT NULL,
  canonical_hash text NOT NULL,
  evidence_version integer NOT NULL,
  patch_hash text NOT NULL,
  patch_source text NOT NULL,
  patch_source_url text NOT NULL DEFAULT '',
  patch_raw_hash text NOT NULL DEFAULT '',
  from_snapshot_hash text,
  to_snapshot_hash text,
  materiality_event_hash text NOT NULL DEFAULT '',
  rule_set_hash text NOT NULL,
  source text NOT NULL DEFAULT 'derived_evidence_record',
  source_url text NOT NULL DEFAULT 'trialdiff://evidence-record',
  generated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(nct_id, from_version, to_version, rule_set_hash, evidence_version)
);

CREATE INDEX IF NOT EXISTS idx_evidence_records_nct_versions
  ON evidence_records(nct_id, from_version, to_version);

CREATE INDEX IF NOT EXISTS idx_evidence_records_submitted_date
  ON evidence_records(submitted_date DESC);

CREATE INDEX IF NOT EXISTS idx_evidence_records_severity
  ON evidence_records(severity);

CREATE INDEX IF NOT EXISTS idx_evidence_records_category
  ON evidence_records(category);
