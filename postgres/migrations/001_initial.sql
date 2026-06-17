CREATE TABLE IF NOT EXISTS trials (
  nct_id text PRIMARY KEY,
  brief_title text,
  official_title text,
  lead_sponsor text,
  lead_sponsor_class text,
  conditions_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  interventions_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  overall_status text,
  phase_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  study_type text,
  last_update_posted text,
  first_submitted_date text,
  has_results boolean NOT NULL DEFAULT false,
  current_record_json jsonb NOT NULL,
  current_record_hash text NOT NULL,
  source text NOT NULL,
  source_url text NOT NULL,
  fetched_at timestamptz NOT NULL,
  source_version text,
  raw_hash text NOT NULL
);

CREATE TABLE IF NOT EXISTS trial_snapshots (
  id bigserial PRIMARY KEY,
  nct_id text NOT NULL REFERENCES trials(nct_id) ON DELETE CASCADE,
  snapshot_date text NOT NULL,
  record_json jsonb NOT NULL,
  record_hash text NOT NULL,
  source text NOT NULL,
  source_url text NOT NULL,
  fetched_at timestamptz NOT NULL,
  source_version text,
  raw_hash text NOT NULL,
  UNIQUE(nct_id, record_hash)
);

CREATE TABLE IF NOT EXISTS trial_versions (
  id bigserial PRIMARY KEY,
  nct_id text NOT NULL REFERENCES trials(nct_id) ON DELETE CASCADE,
  version integer NOT NULL,
  submitted_date text,
  overall_status text,
  study_type text,
  module_labels_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  review_not_passed boolean NOT NULL DEFAULT false,
  unposted_events_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  record_json jsonb,
  record_hash text,
  source text NOT NULL,
  source_url text NOT NULL,
  fetched_at timestamptz NOT NULL,
  source_version text,
  raw_hash text NOT NULL,
  UNIQUE(nct_id, version)
);

CREATE TABLE IF NOT EXISTS trial_patches (
  id bigserial PRIMARY KEY,
  nct_id text NOT NULL REFERENCES trials(nct_id) ON DELETE CASCADE,
  from_version integer NOT NULL,
  to_version integer NOT NULL,
  patch_kind text NOT NULL,
  patch_json jsonb NOT NULL,
  patch_hash text NOT NULL,
  changed_paths_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  changed_modules_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  op_counts_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  source text NOT NULL,
  source_url text NOT NULL,
  fetched_at timestamptz NOT NULL,
  source_version text,
  raw_hash text NOT NULL,
  UNIQUE(nct_id, from_version, to_version, patch_hash)
);

CREATE TABLE IF NOT EXISTS materiality_events (
  id bigserial PRIMARY KEY,
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
  summary text,
  summary_source text,
  needs_human_review boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  rule_set_hash text NOT NULL DEFAULT '',
  source text NOT NULL DEFAULT 'derived_classifier',
  source_url text NOT NULL DEFAULT '',
  fetched_at timestamptz NOT NULL DEFAULT now(),
  source_version text,
  raw_hash text NOT NULL DEFAULT '',
  -- Postgres btree index rows cap at 2704 bytes; hash the wide JSON for the uniqueness key.
  changed_paths_hash text GENERATED ALWAYS AS (md5(changed_paths_json::text)) STORED,
  UNIQUE(nct_id, from_version, to_version, category, severity, changed_paths_hash)
);

CREATE TABLE IF NOT EXISTS classifier_rules (
  id bigserial PRIMARY KEY,
  rule_key text NOT NULL UNIQUE,
  path_pattern text NOT NULL,
  op_filter_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  value_filter_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  severity text NOT NULL,
  category text NOT NULL,
  timing_sensitive boolean NOT NULL DEFAULT false,
  description text NOT NULL,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS case_studies (
  id bigserial PRIMARY KEY,
  nct_id text NOT NULL REFERENCES trials(nct_id) ON DELETE CASCADE,
  case_type text NOT NULL,
  status text NOT NULL,
  public_claim_level text NOT NULL,
  notes text,
  verified_at timestamptz
);

CREATE TABLE IF NOT EXISTS ingest_runs (
  id bigserial PRIMARY KEY,
  corpus_label text,
  query_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  relaxation_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  started_at timestamptz NOT NULL,
  completed_at timestamptz,
  status text NOT NULL,
  notes text
);

CREATE INDEX IF NOT EXISTS idx_trial_patches_nct_versions
  ON trial_patches(nct_id, from_version, to_version);

CREATE INDEX IF NOT EXISTS idx_materiality_events_nct_versions
  ON materiality_events(nct_id, from_version, to_version);

CREATE INDEX IF NOT EXISTS idx_materiality_events_submitted_date
  ON materiality_events(submitted_date DESC);

CREATE INDEX IF NOT EXISTS idx_materiality_events_severity
  ON materiality_events(severity);

CREATE INDEX IF NOT EXISTS idx_materiality_events_category
  ON materiality_events(category);

CREATE INDEX IF NOT EXISTS idx_trial_versions_nct_version
  ON trial_versions(nct_id, version);
