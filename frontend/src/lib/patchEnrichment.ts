import { buildValueContexts, isMissing, type PatchOperation } from "./jsonPatch";
import { groupOperations, type OperationGroup } from "./pathGrouping";
import {
  matchingRulesForOperation,
  maxSeverity,
  type ClassifierRule,
  type Severity,
} from "./pathMatching";

export type MaterialityEventDetail = {
  id: number;
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
    const category = matchedRules[0]?.category ?? null;

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
