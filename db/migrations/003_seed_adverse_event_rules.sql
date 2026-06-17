INSERT OR IGNORE INTO classifier_rules (
  rule_key, path_pattern, op_filter_json, value_filter_json, severity,
  category, timing_sensitive, description, active, created_at
) VALUES
(
  'serious_adverse_event_addition',
  '/resultsSection/adverseEventsModule/seriousEvents/**',
  '["add"]',
  '{}',
  'high',
  'serious_adverse_event_addition',
  0,
  'Addition of reported serious adverse event data after results posting is high review priority.',
  1,
  datetime('now')
),
(
  'serious_adverse_event_modification',
  '/resultsSection/adverseEventsModule/seriousEvents/**',
  '["replace"]',
  '{}',
  'high',
  'serious_adverse_event_modification',
  0,
  'Modification of reported serious adverse event data after results posting is high review priority.',
  1,
  datetime('now')
),
(
  'serious_adverse_event_removal',
  '/resultsSection/adverseEventsModule/seriousEvents/**',
  '["remove"]',
  '{}',
  'critical',
  'serious_adverse_event_removal',
  0,
  'Removal of reported serious adverse event data is critical review priority.',
  1,
  datetime('now')
),
(
  'other_adverse_event_addition',
  '/resultsSection/adverseEventsModule/otherEvents/**',
  '["add"]',
  '{}',
  'medium',
  'other_adverse_event_addition',
  0,
  'Addition of other adverse event result data is medium review priority.',
  1,
  datetime('now')
),
(
  'other_adverse_event_modification',
  '/resultsSection/adverseEventsModule/otherEvents/**',
  '["replace"]',
  '{}',
  'medium',
  'other_adverse_event_modification',
  0,
  'Modification of other adverse event result data is medium review priority.',
  1,
  datetime('now')
),
(
  'other_adverse_event_removal',
  '/resultsSection/adverseEventsModule/otherEvents/**',
  '["remove"]',
  '{}',
  'high',
  'other_adverse_event_removal',
  0,
  'Removal of other adverse event result data is high review priority.',
  1,
  datetime('now')
),
(
  'adverse_event_group_change',
  '/resultsSection/adverseEventsModule/eventGroups/**',
  '["add","remove","replace"]',
  '{}',
  'high',
  'adverse_event_group_change',
  0,
  'Changes to adverse event group-level denominators or affected counts are high review priority.',
  1,
  datetime('now')
);
