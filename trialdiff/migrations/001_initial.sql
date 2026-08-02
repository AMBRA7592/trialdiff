PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS trials (
  nct_id TEXT PRIMARY KEY,
  brief_title TEXT,
  official_title TEXT,
  lead_sponsor TEXT,
  lead_sponsor_class TEXT,
  conditions_json TEXT NOT NULL DEFAULT '[]',
  interventions_json TEXT NOT NULL DEFAULT '[]',
  overall_status TEXT,
  phase_json TEXT NOT NULL DEFAULT '[]',
  study_type TEXT,
  last_update_posted TEXT,
  first_submitted_date TEXT,
  has_results INTEGER NOT NULL DEFAULT 0,
  current_record_json TEXT NOT NULL,
  current_record_hash TEXT NOT NULL,
  source TEXT NOT NULL,
  source_url TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  source_version TEXT,
  raw_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trial_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nct_id TEXT NOT NULL REFERENCES trials(nct_id) ON DELETE CASCADE,
  snapshot_date TEXT NOT NULL,
  record_json TEXT NOT NULL,
  record_hash TEXT NOT NULL,
  source TEXT NOT NULL,
  source_url TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  source_version TEXT,
  raw_hash TEXT NOT NULL,
  UNIQUE(nct_id, record_hash)
);

CREATE TABLE IF NOT EXISTS trial_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nct_id TEXT NOT NULL REFERENCES trials(nct_id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  submitted_date TEXT,
  overall_status TEXT,
  study_type TEXT,
  module_labels_json TEXT NOT NULL DEFAULT '[]',
  review_not_passed INTEGER NOT NULL DEFAULT 0,
  unposted_events_json TEXT NOT NULL DEFAULT '[]',
  record_json TEXT,
  record_hash TEXT,
  source TEXT NOT NULL,
  source_url TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  source_version TEXT,
  raw_hash TEXT NOT NULL,
  UNIQUE(nct_id, version)
);

CREATE TABLE IF NOT EXISTS trial_patches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nct_id TEXT NOT NULL REFERENCES trials(nct_id) ON DELETE CASCADE,
  from_version INTEGER NOT NULL,
  to_version INTEGER NOT NULL,
  patch_kind TEXT NOT NULL,
  patch_json TEXT NOT NULL,
  patch_hash TEXT NOT NULL,
  changed_paths_json TEXT NOT NULL DEFAULT '[]',
  changed_modules_json TEXT NOT NULL DEFAULT '[]',
  op_counts_json TEXT NOT NULL DEFAULT '{}',
  source TEXT NOT NULL,
  source_url TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  source_version TEXT,
  raw_hash TEXT NOT NULL,
  UNIQUE(nct_id, from_version, to_version, patch_hash)
);

CREATE TABLE IF NOT EXISTS materiality_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
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
  summary TEXT,
  summary_source TEXT,
  needs_human_review INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  rule_set_hash TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT 'derived_classifier',
  source_url TEXT NOT NULL DEFAULT '',
  fetched_at TEXT NOT NULL DEFAULT '',
  source_version TEXT,
  raw_hash TEXT NOT NULL DEFAULT '',
  UNIQUE(nct_id, from_version, to_version, category, severity, changed_paths_json)
);

CREATE TABLE IF NOT EXISTS classifier_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rule_key TEXT NOT NULL UNIQUE,
  path_pattern TEXT NOT NULL,
  op_filter_json TEXT NOT NULL DEFAULT '[]',
  value_filter_json TEXT NOT NULL DEFAULT '{}',
  severity TEXT NOT NULL,
  category TEXT NOT NULL,
  timing_sensitive INTEGER NOT NULL DEFAULT 0,
  description TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS case_studies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nct_id TEXT NOT NULL,
  case_type TEXT NOT NULL,
  status TEXT NOT NULL,
  public_claim_level TEXT NOT NULL,
  notes TEXT,
  verified_at TEXT
);

CREATE TABLE IF NOT EXISTS ingest_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  corpus_label TEXT,
  query_json TEXT NOT NULL DEFAULT '{}',
  relaxation_json TEXT NOT NULL DEFAULT '{}',
  started_at TEXT NOT NULL,
  completed_at TEXT,
  status TEXT NOT NULL,
  notes TEXT
);
