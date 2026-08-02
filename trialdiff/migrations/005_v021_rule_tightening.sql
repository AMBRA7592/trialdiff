UPDATE classifier_rules
SET severity='high',
    description='Design information changes can alter allocation, masking, model, or purpose and need review.'
WHERE rule_key='design_info_change';

UPDATE classifier_rules
SET severity='high',
    description='Trial phase changes are high review-priority design changes.'
WHERE rule_key='phase_change';

UPDATE classifier_rules
SET severity='high',
    description='Arms or interventions changes can alter treatment/comparator structure.'
WHERE rule_key='arms_or_interventions_change';

UPDATE classifier_rules
SET severity='high',
    description='Status changed to terminated, suspended, or withdrawn; whyStopped content determines whether critical review is warranted.'
WHERE rule_key='terminal_status_change';
