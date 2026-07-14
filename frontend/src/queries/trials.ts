import { getSql, hasDatabaseUrl } from "@/db/client";

import { mapEventRow, nullableString, numberValue } from "./mappers";
import type { TrialDetailData } from "./types";

export async function getTrialDetail(nctId: string): Promise<TrialDetailData> {
  if (!hasDatabaseUrl()) {
    return {
      databaseReady: false,
      databaseError: "DATABASE_URL is not configured.",
      patchCount: 0,
      versionCount: 0,
      events: [],
    };
  }

  try {
    const sql = getSql();
    const [trialRows, countRows, eventRows] = await Promise.all([
      sql<Record<string, unknown>[]>`
        SELECT nct_id, brief_title, official_title, lead_sponsor, overall_status, last_update_posted, has_results
        FROM trials
        WHERE nct_id = ${nctId}
        LIMIT 1
      `,
      sql<Record<string, unknown>[]>`
        SELECT
          (SELECT count(*)::int FROM trial_patches WHERE nct_id = ${nctId}) AS patch_count,
          (SELECT count(*)::int FROM trial_versions WHERE nct_id = ${nctId}) AS version_count
      `,
      sql<Record<string, unknown>[]>`
        SELECT
          e.id,
          er.event_id AS evidence_event_id,
          e.nct_id,
          t.brief_title,
          t.lead_sponsor,
          e.from_version,
          e.to_version,
          e.submitted_date,
          e.severity,
          e.severity_pre_timing,
          e.timing_context,
          e.category,
          e.categories_json,
          e.changed_paths_json,
          e.needs_human_review
        FROM materiality_events e
        LEFT JOIN trials t ON t.nct_id = e.nct_id
        LEFT JOIN LATERAL (
          SELECT event_id
          FROM evidence_records er
          WHERE er.nct_id = e.nct_id
            AND er.from_version = e.from_version
            AND er.to_version = e.to_version
            AND er.rule_set_hash = e.rule_set_hash
          ORDER BY er.evidence_version DESC
          LIMIT 1
        ) er ON true
        WHERE e.nct_id = ${nctId}
        ORDER BY e.from_version, e.to_version, e.id
      `,
    ]);

    const trialRow = trialRows[0];
    const countRow = countRows[0] ?? {};

    return {
      databaseReady: true,
      trial: trialRow
        ? {
            nctId: String(trialRow.nct_id ?? ""),
            briefTitle: nullableString(trialRow.brief_title),
            officialTitle: nullableString(trialRow.official_title),
            leadSponsor: nullableString(trialRow.lead_sponsor),
            overallStatus: nullableString(trialRow.overall_status),
            lastUpdatePosted: nullableString(trialRow.last_update_posted),
            hasResults: Boolean(trialRow.has_results),
          }
        : undefined,
      patchCount: numberValue(countRow.patch_count),
      versionCount: numberValue(countRow.version_count),
      events: eventRows.map(mapEventRow),
    };
  } catch (error) {
    console.error("getTrialDetail failed:", error);
    return {
      databaseReady: false,
      databaseError: error instanceof Error ? error.message : "Database query failed.",
      patchCount: 0,
      versionCount: 0,
      events: [],
    };
  }
}
