import type { EventRow, EvidenceRecordDetail, EvidenceRecordRow, TrialLensRow } from "./types";

export function numberValue(value: unknown): number {
  const next = Number(value ?? 0);
  return Number.isFinite(next) ? next : 0;
}

export function nullableString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
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
    categories: stringArray(row.categories_json),
    changedPaths: stringArray(row.changed_paths_json),
    needsHumanReview: Boolean(row.needs_human_review),
  };
}

export function mapEvidenceRecordRow(row: Record<string, unknown>): EvidenceRecordRow {
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
    categories: stringArray(row.categories_json),
    eventClasses: stringArray(row.event_classes_json),
    changedPaths: stringArray(row.changed_paths_json),
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
    generatedAt: nullableString(row.generated_at),
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
