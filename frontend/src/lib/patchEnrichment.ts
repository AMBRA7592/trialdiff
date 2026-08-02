import { buildValueContexts, isMissing, type PatchOperation } from "./jsonPatch";
import { groupOperations, type OperationGroup } from "./pathGrouping";
import {
  matchingRulesForOperation,
  maxSeverity,
  severityRank,
  type ClassifierRule,
  type Severity,
} from "./pathMatching";

// Mirror of category_priority() in trialdiff/classifier/materiality.py:
// when several rules share the max severity, the highest-priority category
// wins (Python choose_category sorts by (severity_rank, category_priority)).
const CATEGORY_PRIORITY: Record<string, number> = {
  primary_outcome_change: 100,
  design_change: 90,
  arm_intervention_change: 85,
  serious_adverse_event_removal: 82,
  status_termination: 80,
  secondary_outcome_change: 70,
  serious_adverse_event_addition: 68,
  serious_adverse_event_modification: 67,
  eligibility_change: 60,
  adverse_event_group_change: 58,
  other_adverse_event_removal: 56,
  enrollment_change: 50,
  timeline_major_slip: 45,
  timeline_significant_shift: 44,
  timeline_shift: 40,
  timeline_minor_adjustment: 30,
  timeline_actual_date_correction: 28,
  timeline_actualized_earlier: 27,
  milestone_realized: 25,
  other_adverse_event_addition: 22,
  other_adverse_event_modification: 21,
};

function categoryPriority(category: string): number {
  return CATEGORY_PRIORITY[category] ?? 0;
}

// Pick the category from the max-severity rule (tie-break by category
// priority, then original rule order), instead of blindly taking rule[0]
// while severity takes the max — those can disagree.
function primaryCategory(matchedRules: ClassifierRule[]): string | null {
  let best: ClassifierRule | null = null;
  for (const rule of matchedRules) {
    if (
      !best ||
      severityRank[rule.severity] > severityRank[best.severity] ||
      (severityRank[rule.severity] === severityRank[best.severity] &&
        categoryPriority(rule.category) > categoryPriority(best.category))
    ) {
      best = rule;
    }
  }
  return best?.category ?? null;
}

export type MaterialityEventDetail = {
  id: number;
  evidenceEventId: string | null;
  nctId: string;
  fromVersion: number;
  toVersion: number;
  submittedDate: string | null;
  timingContext: string | null;
  severityPreTiming: string;
  severity: string;
  category: string;
  categories: string[];
  changedPaths: string[];
  deterministicRules: string[];
  valueSignals: Record<string, unknown>[];
  summary: string | null;
  summarySource: string | null;
  needsHumanReview: boolean;
  ruleSetHash: string;
};

export type PatchProvenance = {
  source: string;
  sourceUrl: string;
  fetchedAt: string | null;
  sourceVersion: string | null;
  rawHash: string;
};

export type PatchInspectionInput = {
  operations: PatchOperation[];
  fromRecord: unknown;
  rules: ClassifierRule[];
};

export type EnrichedPatchOperation = {
  index: number;
  op: string;
  path: string;
  oldValue: unknown;
  newValue: unknown;
  severity: Severity;
  category: string | null;
  matchedRules: ClassifierRule[];
};

export type EnrichedPatch = {
  operations: EnrichedPatchOperation[];
  groups: OperationGroup[];
};

export function enrichPatch(input: PatchInspectionInput): EnrichedPatch {
  const contexts = buildValueContexts(input.fromRecord, input.operations);
  const operations = contexts.map((context): EnrichedPatchOperation => {
    const oldValue = readableValue(context.oldValue);
    const newValue = readableValue(context.newValue);
    const matchedRules = matchingRulesForOperation(
      {
        op: context.op,
        path: context.path,
        oldValue,
        newValue,
      },
      input.rules,
    );
    const severity = maxSeverity(matchedRules.map((rule) => rule.severity));
    const category = primaryCategory(matchedRules);

    return {
      index: context.index,
      op: context.op,
      path: context.path,
      oldValue,
      newValue,
      severity,
      category,
      matchedRules,
    };
  });

  return {
    operations,
    groups: groupOperations(operations),
  };
}

function readableValue(value: unknown) {
  return isMissing(value) ? "<MISSING>" : value;
}

export function formatPatchValue(value: unknown) {
  if (value === "<MISSING>") return "<MISSING>";
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}
