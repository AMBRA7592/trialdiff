import { getSql, hasDatabaseUrl } from "@/db/client";
import { enrichPatch, type MaterialityEventDetail, type PatchProvenance } from "@/lib/patchEnrichment";
import type { ClassifierRule } from "@/lib/pathMatching";

import { nullableString, numberValue, stringArray } from "./mappers";

export type PatchInspectionData = {
  databaseReady: boolean;
  databaseError?: string;
  trial?: {
    nctId: string;
    briefTitle: string | null;
    leadSponsor: string | null;
    overallStatus: string | null;
  };
  fromVersion: number;
  toVersion: number;
  patch?: {
    operations: Array<{ op: string; path: string; value?: unknown; from?: string }>;
    provenance: PatchProvenance;
    enriched: ReturnType<typeof enrichPatch>;
  };
  events: MaterialityEventDetail[];
};

export async function getPatchInspection(
  nctId: string,
  fromVersion: number,
  toVersion: number,
): Promise<PatchInspectionData> {
  if (!hasDatabaseUrl()) {
    return {
      databaseReady: false,
      databaseError: "DATABASE_URL is not configured.",
      fromVersion,
      toVersion,
      events: [],
    };
  }

  try {
    const sql = getSql();
    const [patchRows, eventRows, ruleRows] = await Promise.all([
      sql<Record<string, unknown>[]>`
        SELECT
          p.nct_id,
          p.from_version,
          p.to_version,
          p.patch_json,
          p.source,
          p.source_url,
          p.fetched_at::text AS fetched_at,
          p.source_version,
          p.raw_hash,
          v.record_json AS from_record_json,
          t.brief_title,
          t.lead_sponsor,
          t.overall_status
        FROM trial_patches p
        LEFT JOIN trial_versions v
          ON v.nct_id = p.nct_id
         AND v.version = p.from_version
        LEFT JOIN trials t ON t.nct_id = p.nct_id
        WHERE p.nct_id = ${nctId}
          AND p.from_version = ${fromVersion}
          AND p.to_version = ${toVersion}
        ORDER BY p.id
        LIMIT 1
      `,
      sql<Record<string, unknown>[]>`
        SELECT
          id,
          nct_id,
          from_version,
          to_version,
          submitted_date,
          timing_context,
          severity_pre_timing,
          severity,
          category,
          categories_json,
          changed_paths_json,
          deterministic_rules_json,
          value_signals_json,
          summary,
          summary_source,
          needs_human_review,
          rule_set_hash
        FROM materiality_events
        WHERE nct_id = ${nctId}
          AND from_version = ${fromVersion}
          AND to_version = ${toVersion}
        ORDER BY CASE severity
          WHEN 'critical' THEN 1
          WHEN 'high' THEN 2
          WHEN 'medium' THEN 3
          WHEN 'low' THEN 4
          ELSE 5
        END, id
      `,
      sql<Record<string, unknown>[]>`
        SELECT
          rule_key,
          path_pattern,
          op_filter_json,
          value_filter_json,
          severity,
          category,
          timing_sensitive,
          description
        FROM classifier_rules
        WHERE active = true
        ORDER BY id
      `,
    ]);

    const patchRow = patchRows[0];
    if (!patchRow) {
      return {
        databaseReady: true,
        fromVersion,
        toVersion,
        events: eventRows.map(mapMaterialityEvent),
      };
    }

    const operations = patchOperations(patchRow.patch_json);
    const rules = ruleRows.map(mapRule);
    const fromRecord = patchRow.from_record_json ?? {};

    return {
      databaseReady: true,
      trial: {
        nctId: String(patchRow.nct_id ?? nctId),
        briefTitle: nullableString(patchRow.brief_title),
        leadSponsor: nullableString(patchRow.lead_sponsor),
        overallStatus: nullableString(patchRow.overall_status),
      },
      fromVersion,
      toVersion,
      patch: {
        operations,
        provenance: {
          source: String(patchRow.source ?? ""),
          sourceUrl: String(patchRow.source_url ?? ""),
          fetchedAt: nullableString(patchRow.fetched_at),
          sourceVersion: nullableString(patchRow.source_version),
          rawHash: String(patchRow.raw_hash ?? ""),
        },
        enriched: enrichPatch({
          operations,
          fromRecord,
          rules,
        }),
      },
      events: eventRows.map(mapMaterialityEvent),
    };
  } catch (error) {
    return {
      databaseReady: false,
      databaseError: error instanceof Error ? error.message : "Database query failed.",
      fromVersion,
      toVersion,
      events: [],
    };
  }
}

function patchOperations(value: unknown): Array<{ op: string; path: string; value?: unknown; from?: string }> {
  if (!Array.isArray(value)) return [];
  return value.filter(isPatchOperation);
}

function isPatchOperation(value: unknown): value is { op: string; path: string; value?: unknown; from?: string } {
  return (
    typeof value === "object" &&
    value !== null &&
    "op" in value &&
    "path" in value &&
    typeof (value as { op: unknown }).op === "string" &&
    typeof (value as { path: unknown }).path === "string"
  );
}

function mapMaterialityEvent(row: Record<string, unknown>): MaterialityEventDetail {
  return {
    id: numberValue(row.id),
    nctId: String(row.nct_id ?? ""),
    fromVersion: numberValue(row.from_version),
    toVersion: numberValue(row.to_version),
    submittedDate: nullableString(row.submitted_date),
    timingContext: nullableString(row.timing_context),
    severityPreTiming: String(row.severity_pre_timing ?? "unknown"),
    severity: String(row.severity ?? "unknown"),
    category: String(row.category ?? "unknown_material_change"),
    categories: stringArray(row.categories_json),
    changedPaths: stringArray(row.changed_paths_json),
    deterministicRules: stringArray(row.deterministic_rules_json),
    valueSignals: recordArray(row.value_signals_json),
    summary: nullableString(row.summary),
    summarySource: nullableString(row.summary_source),
    needsHumanReview: Boolean(row.needs_human_review),
    ruleSetHash: String(row.rule_set_hash ?? ""),
  };
}

function mapRule(row: Record<string, unknown>): ClassifierRule {
  return {
    ruleKey: String(row.rule_key ?? ""),
    pathPattern: String(row.path_pattern ?? ""),
    opFilter: stringArray(row.op_filter_json),
    valueFilter: recordValue(row.value_filter_json),
    severity: ruleSeverity(row.severity),
    category: String(row.category ?? ""),
    timingSensitive: Boolean(row.timing_sensitive),
    description: String(row.description ?? ""),
  };
}

function recordArray(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null);
}

function recordValue(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value : {};
}

function ruleSeverity(value: unknown): ClassifierRule["severity"] {
  if (value === "ignore" || value === "low" || value === "medium" || value === "high" || value === "critical") {
    return value;
  }
  return "ignore";
}
