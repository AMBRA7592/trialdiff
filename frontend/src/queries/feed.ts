import { getSql, hasDatabaseUrl } from "@/db/client";

import { getPostCompletionEvidenceRecords } from "./evidence";
import { mapEventRow, mapTrialLensRow, numberValue } from "./mappers";
import type { HomeData, SeverityCount, SummaryCounts } from "./types";

const emptySummary: SummaryCounts = {
  trialCount: 0,
  patchCount: 0,
  materialEventCount: 0,
  criticalCount: 0,
  highCount: 0,
};

export function normalizeLens(value: string | null | undefined) {
  if (
    value === "post-completion" ||
    value === "recent" ||
    value === "critical-density" ||
    value === "amendment-intensity"
  ) {
    return value;
  }
  return "post-completion";
}

async function getSummary(): Promise<SummaryCounts> {
  const sql = getSql();
  const rows = await sql<Record<string, unknown>[]>`
    SELECT
      (SELECT count(*)::int FROM trials) AS trial_count,
      (SELECT count(*)::int FROM trial_patches) AS patch_count,
      (SELECT count(*)::int FROM materiality_events) AS material_event_count,
      (SELECT count(*)::int FROM materiality_events WHERE severity = 'critical') AS critical_count,
      (SELECT count(*)::int FROM materiality_events WHERE severity = 'high') AS high_count
  `;
  const row = rows[0] ?? {};

  return {
    trialCount: numberValue(row.trial_count),
    patchCount: numberValue(row.patch_count),
    materialEventCount: numberValue(row.material_event_count),
    criticalCount: numberValue(row.critical_count),
    highCount: numberValue(row.high_count),
  };
}

async function getSeverityCounts(): Promise<SeverityCount[]> {
  const sql = getSql();
  const rows = await sql<Record<string, unknown>[]>`
    SELECT severity, count(*)::int AS count
    FROM materiality_events
    GROUP BY severity
    ORDER BY CASE severity
      WHEN 'critical' THEN 1
      WHEN 'high' THEN 2
      WHEN 'medium' THEN 3
      WHEN 'low' THEN 4
      ELSE 5
    END
  `;

  return rows.map((row) => ({
    severity: String(row.severity ?? "unknown"),
    count: numberValue(row.count),
  }));
}

async function getRecentEvents(limit = 40) {
  const sql = getSql();
  const rows = await sql<Record<string, unknown>[]>`
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
    ORDER BY e.submitted_date DESC NULLS LAST, e.id DESC
    LIMIT ${limit}
  `;

  return rows.map(mapEventRow);
}

async function getCriticalDensityTrials(limit = 25) {
  const sql = getSql();
  const rows = await sql<Record<string, unknown>[]>`
    WITH patch_counts AS (
      SELECT nct_id, count(*)::int AS patch_count
      FROM trial_patches
      GROUP BY nct_id
    ),
    event_counts AS (
      SELECT
        nct_id,
        count(*)::int AS event_count,
        count(*) FILTER (WHERE severity = 'critical')::int AS critical_count,
        count(*) FILTER (WHERE severity = 'high')::int AS high_count,
        max(submitted_date) AS latest_event_date
      FROM materiality_events
      GROUP BY nct_id
    )
    SELECT
      t.nct_id,
      t.brief_title,
      t.lead_sponsor,
      coalesce(p.patch_count, 0)::int AS patch_count,
      coalesce(e.event_count, 0)::int AS event_count,
      coalesce(e.critical_count, 0)::int AS critical_count,
      coalesce(e.high_count, 0)::int AS high_count,
      coalesce(round(100.0 * e.critical_count / nullif(p.patch_count, 0), 2), 0)::float AS critical_density_pct,
      e.latest_event_date
    FROM trials t
    LEFT JOIN patch_counts p ON p.nct_id = t.nct_id
    LEFT JOIN event_counts e ON e.nct_id = t.nct_id
    WHERE coalesce(p.patch_count, 0) >= 10
    ORDER BY critical_density_pct DESC, critical_count DESC, high_count DESC, patch_count DESC
    LIMIT ${limit}
  `;

  return rows.map(mapTrialLensRow);
}

async function getAmendmentIntensityTrials(limit = 25) {
  const sql = getSql();
  const rows = await sql<Record<string, unknown>[]>`
    WITH patch_counts AS (
      SELECT nct_id, count(*)::int AS patch_count
      FROM trial_patches
      GROUP BY nct_id
    ),
    event_counts AS (
      SELECT
        nct_id,
        count(*)::int AS event_count,
        count(*) FILTER (WHERE severity = 'critical')::int AS critical_count,
        count(*) FILTER (WHERE severity = 'high')::int AS high_count,
        max(submitted_date) AS latest_event_date
      FROM materiality_events
      GROUP BY nct_id
    )
    SELECT
      t.nct_id,
      t.brief_title,
      t.lead_sponsor,
      coalesce(p.patch_count, 0)::int AS patch_count,
      coalesce(e.event_count, 0)::int AS event_count,
      coalesce(e.critical_count, 0)::int AS critical_count,
      coalesce(e.high_count, 0)::int AS high_count,
      coalesce(round(100.0 * e.critical_count / nullif(p.patch_count, 0), 2), 0)::float AS critical_density_pct,
      e.latest_event_date
    FROM trials t
    LEFT JOIN patch_counts p ON p.nct_id = t.nct_id
    LEFT JOIN event_counts e ON e.nct_id = t.nct_id
    ORDER BY patch_count DESC, event_count DESC, critical_count DESC
    LIMIT ${limit}
  `;

  return rows.map(mapTrialLensRow);
}

export async function getHomeData(): Promise<HomeData> {
  if (!hasDatabaseUrl()) {
    return {
      databaseReady: false,
      databaseError: "DATABASE_URL is not configured.",
      summary: emptySummary,
      severityCounts: [],
      postCompletionEvidenceRecords: [],
      recentEvents: [],
      criticalDensityTrials: [],
      amendmentIntensityTrials: [],
    };
  }

  try {
    const [
      summary,
      severityCounts,
      postCompletionEvidenceRecords,
      recentEvents,
      criticalDensityTrials,
      amendmentIntensityTrials,
    ] = await Promise.all([
      getSummary(),
      getSeverityCounts(),
      getPostCompletionEvidenceRecords(),
      getRecentEvents(),
      getCriticalDensityTrials(),
      getAmendmentIntensityTrials(),
    ]);

    return {
      databaseReady: true,
      summary,
      severityCounts,
      postCompletionEvidenceRecords,
      recentEvents,
      criticalDensityTrials,
      amendmentIntensityTrials,
    };
  } catch (error) {
    return {
      databaseReady: false,
      databaseError: error instanceof Error ? error.message : "Database query failed.",
      summary: emptySummary,
      severityCounts: [],
      postCompletionEvidenceRecords: [],
      recentEvents: [],
      criticalDensityTrials: [],
      amendmentIntensityTrials: [],
    };
  }
}
