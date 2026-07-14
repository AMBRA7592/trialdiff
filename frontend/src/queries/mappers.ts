import type { EventRow, EvidenceRecordDetail, EvidenceRecordRow, TrialLensRow } from "./types";

export function numberValue(value: unknown): number {
  const next = Number(value ?? 0);
  return Number.isFinite(next) ? next : 0;
}

export function nullableString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

// postgres.js returns timestamptz columns as Date instances; plain
// nullableString() would silently map them to null.
export function nullableTimestamp(value: unknown): string | null {
  if (value instanceof Date) return value.toISOString();
  return nullableString(value);
}

export function stringArray(value: unknown): string[] {
  const parsed = parseJsonish(value);
  if (Array.isArray(parsed)) {
    return parsed.filter((item): item is string => typeof item === "string");
  }
  return [];
}

export function recordArray(value: unknown): Record<string, unknown>[] {
  const parsed = parseJsonish(value);
  if (!Array.isArray(parsed)) return [];
  return parsed.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null);
}

export function recordValue(value: unknown): Record<string, unknown> {
  const parsed = parseJsonish(value);
  return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
    ? (parsed as Record<string, unknown>)
    : {};
}

export function mapEventRow(row: Record<string, unknown>): EventRow {
  const categories = stringArray(row.categories_json);
  const changedPaths = stringArray(row.changed_paths_json);
  return {
    id: numberValue(row.id),
    evidenceEventId: nullableString(row.evidence_event_id),
    nctId: String(row.nct_id ?? ""),
    briefTitle: nullableString(row.brief_title),
    leadSponsor: nullableString(row.lead_sponsor),
    fromVersion: numberValue(row.from_version),
    toVersion: numberValue(row.to_version),
    submittedDate: nullableString(row.submitted_date),
    severity: String(row.severity ?? "unknown"),
    severityPreTiming: String(row.severity_pre_timing ?? "unknown"),
    timingContext: nullableString(row.timing_context),
    category: String(row.category ?? "unknown_material_change"),
    categories,
    changedPaths,
    changedPathCount: row.changed_path_count != null ? numberValue(row.changed_path_count) : changedPaths.length,
    resultsConfound:
      row.results_confound != null ? Boolean(row.results_confound) : categories.includes("results_reconciliation"),
    needsHumanReview: Boolean(row.needs_human_review),
  };
}

// The results-posting confound is the pipeline's persisted tag, never a
// re-derived path heuristic: the outcome_edit_cooccurs_with_results_posting
// event class, or the results_reconciliation category.
export function resultsConfoundFromTags(eventClasses: string[], categories: string[]): boolean {
  return (
    eventClasses.includes("outcome_edit_cooccurs_with_results_posting") ||
    categories.includes("results_reconciliation")
  );
}

export function mapEvidenceRecordRow(row: Record<string, unknown>): EvidenceRecordRow {
  const categories = stringArray(row.categories_json);
  const eventClasses = stringArray(row.event_classes_json);
  const changedPaths = stringArray(row.changed_paths_json);
  return {
    eventId: String(row.event_id ?? ""),
    nctId: String(row.nct_id ?? ""),
    briefTitle: nullableString(row.brief_title),
    leadSponsor: nullableString(row.lead_sponsor),
    fromVersion: numberValue(row.from_version),
    toVersion: numberValue(row.to_version),
    submittedDate: nullableString(row.submitted_date),
    timingContext: nullableString(row.timing_context),
    severityPreTiming: String(row.severity_pre_timing ?? "unknown"),
    severity: String(row.severity ?? "unknown"),
    category: String(row.category ?? "unknown_material_change"),
    categories,
    eventClasses,
    changedPaths,
    // Feed queries ship a capped path preview plus the true count; detail
    // queries (er.*) ship the full array and no count column.
    changedPathCount: row.changed_path_count != null ? numberValue(row.changed_path_count) : changedPaths.length,
    resultsConfound:
      row.results_confound != null
        ? Boolean(row.results_confound)
        : resultsConfoundFromTags(eventClasses, categories),
    deterministicRules: stringArray(row.deterministic_rules_json),
    claimsSupported: stringArray(row.claims_supported_json),
    claimsNotSupported: stringArray(row.claims_not_supported_json),
    reviewQuestion: String(row.review_question ?? ""),
    evidenceVersion: numberValue(row.evidence_version),
    canonicalHash: String(row.canonical_hash ?? ""),
  };
}

export function mapEvidenceRecordDetail(row: Record<string, unknown>): EvidenceRecordDetail {
  return {
    ...mapEvidenceRecordRow(row),
    valueSignals: recordArray(row.value_signals_json),
    citationText: String(row.citation_text ?? ""),
    canonicalJson: recordValue(row.canonical_json),
    patchHash: String(row.patch_hash ?? ""),
    patchSource: String(row.patch_source ?? ""),
    patchSourceUrl: nullableString(row.patch_source_url),
    patchRawHash: String(row.patch_raw_hash ?? ""),
    fromSnapshotHash: nullableString(row.from_snapshot_hash),
    toSnapshotHash: nullableString(row.to_snapshot_hash),
    materialityEventHash: String(row.materiality_event_hash ?? ""),
    ruleSetHash: String(row.rule_set_hash ?? ""),
    source: String(row.source ?? ""),
    sourceUrl: String(row.source_url ?? ""),
    generatedAt: nullableTimestamp(row.generated_at),
    trial: {
      overallStatus: nullableString(row.overall_status),
      hasResults: Boolean(row.has_results),
    },
  };
}

export function mapTrialLensRow(row: Record<string, unknown>): TrialLensRow {
  return {
    nctId: String(row.nct_id ?? ""),
    briefTitle: nullableString(row.brief_title),
    leadSponsor: nullableString(row.lead_sponsor),
    patchCount: numberValue(row.patch_count),
    eventCount: numberValue(row.event_count),
    criticalCount: numberValue(row.critical_count),
    highCount: numberValue(row.high_count),
    criticalDensityPct: numberValue(row.critical_density_pct),
    latestEventDate: nullableString(row.latest_event_date),
  };
}

function parseJsonish(value: unknown): unknown {
  if (typeof value !== "string") return value;
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}
