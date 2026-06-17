INSERT INTO classifier_rules (
  rule_key, path_pattern, op_filter_json, value_filter_json, severity,
  category, timing_sensitive, description, active, created_at
) VALUES
(
  'serious_adverse_event_addition',
  '/resultsSection/adverseEventsModule/seriousEvents/**',
  '["add"]'::jsonb,
  '{}'::jsonb,
  'high',
  'serious_adverse_event_addition',
  false,
  'Addition of reported serious adverse event data after results posting is high review priority.',
  true,
  now()
),
(
  'serious_adverse_event_modification',
  '/resultsSection/adverseEventsModule/seriousEvents/**',
  '["replace"]'::jsonb,
  '{}'::jsonb,
  'high',
  'serious_adverse_event_modification',
  false,
  'Modification of reported serious adverse event data after results posting is high review priority.',
  true,
  now()
),
(
  'serious_adverse_event_removal',
  '/resultsSection/adverseEventsModule/seriousEvents/**',
  '["remove"]'::jsonb,
  '{}'::jsonb,
  'critical',
  'serious_adverse_event_removal',
  false,
  'Removal of reported serious adverse event data is critical review priority.',
  true,
  now()
),
(
  'other_adverse_event_addition',
  '/resultsSection/adverseEventsModule/otherEvents/**',
  '["add"]'::jsonb,
  '{}'::jsonb,
  'medium',
  'other_adverse_event_addition',
  false,
  'Addition of other adverse event result data is medium review priority.',
  true,
  now()
),
(
  'other_adverse_event_modification',
  '/resultsSection/adverseEventsModule/otherEvents/**',
  '["replace"]'::jsonb,
  '{}'::jsonb,
  'medium',
  'other_adverse_event_modification',
  false,
  'Modification of other adverse event result data is medium review priority.',
  true,
  now()
),
(
  'other_adverse_event_removal',
  '/resultsSection/adverseEventsModule/otherEvents/**',
  '["remove"]'::jsonb,
  '{}'::jsonb,
  'high',
  'other_adverse_event_removal',
  false,
  'Removal of other adverse event result data is high review priority.',
  true,
  now()
),
(
  'adverse_event_group_change',
  '/resultsSection/adverseEventsModule/eventGroups/**',
  '["add","remove","replace"]'::jsonb,
  '{}'::jsonb,
  'high',
  'adverse_event_group_change',
  false,
  'Changes to adverse event group-level denominators or affected counts are high review priority.',
  true,
  now()
)
ON CONFLICT (rule_key) DO NOTHING;
