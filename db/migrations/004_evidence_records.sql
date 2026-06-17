CREATE TABLE IF NOT EXISTS evidence_records (
  event_id TEXT PRIMARY KEY,
  nct_id TEXT NOT NULL REFERENCES trials(nct_id) ON DELETE CASCADE,
  from_version INTEGER NOT NULL,
  to_version INTEGER NOT NULL,
  submitted_date TEXT,
  timing_context TEXT,
  severity_pre_timing TEXT NOT NULL,
  severity TEXT NOT NULL,
  category TEXT NOT NULL,
  categories_json TEXT NOT NULL DEFAULT '[]',
  changed_paths_json TEXT NOT NULL DEFAULT '[]',
  deterministic_rules_json TEXT NOT NULL DEFAULT '[]',
  value_signals_json TEXT NOT NULL DEFAULT '[]',
  claims_supported_json TEXT NOT NULL DEFAULT '[]',
  claims_not_supported_json TEXT NOT NULL DEFAULT '[]',
  review_question TEXT NOT NULL,
  citation_text TEXT NOT NULL,
  canonical_json TEXT NOT NULL,
  canonical_hash TEXT NOT NULL,
  evidence_version INTEGER NOT NULL,
  patch_hash TEXT NOT NULL,
  patch_source TEXT NOT NULL,
  patch_source_url TEXT NOT NULL DEFAULT '',
  patch_raw_hash TEXT NOT NULL DEFAULT '',
  from_snapshot_hash TEXT,
  to_snapshot_hash TEXT,
  materiality_event_hash TEXT NOT NULL DEFAULT '',
  rule_set_hash TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'derived_evidence_record',
  source_url TEXT NOT NULL DEFAULT 'trialdiff://evidence-record',
  generated_at TEXT NOT NULL,
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
