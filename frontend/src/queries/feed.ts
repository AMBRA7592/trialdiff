import { getSql, hasDatabaseUrl } from "@/db/client";

import { getPostRecruitmentEvidenceRecords } from "./evidence";
import { mapEventRow, mapTrialLensRow, numberValue, stringArray } from "./mappers";
import type { CorpusStamp, HomeData, SeverityCount, SummaryCounts } from "./types";

const emptySummary: SummaryCounts = {
  trialCount: 0,
  patchCount: 0,
  materialEventCount: 0,
  criticalCount: 0,
  highCount: 0,
};

const emptyCorpusStamp: CorpusStamp = {
  maxSubmittedDate: null,
  ruleSetHashes: [],
  packageGeneration: null,
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
      corpus_trial_count AS trial_count,
      corpus_patch_count AS patch_count,
      material_event_count,
      critical_event_count AS critical_count,
      high_event_count AS high_count
    FROM evidence_record_generations
    WHERE is_active
    LIMIT 1
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
    SELECT counts.key AS severity, counts.value::int AS count
    FROM evidence_record_generations generation
    CROSS JOIN LATERAL jsonb_each_text(generation.severity_counts_json) counts
    WHERE generation.is_active
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

async function getCorpusStamp(): Promise<CorpusStamp> {
  const sql = getSql();
  const rows = await sql<Record<string, unknown>[]>`
    SELECT
      corpus_max_submitted_date AS max_submitted_date,
      jsonb_build_array(rule_set_hash) AS rule_set_hashes,
      package_generation
    FROM evidence_record_generations
    WHERE is_active
    LIMIT 1
  `;
  const row = rows[0] ?? {};

  return {
    maxSubmittedDate: typeof row.max_submitted_date === "string" ? row.max_submitted_date : null,
    ruleSetHashes: stringArray(row.rule_set_hashes),
    packageGeneration: typeof row.package_generation === "string" ? row.package_generation : null,
  };
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
      jsonb_array_length(e.changed_paths_json) AS changed_path_count,
      (
        SELECT jsonb_agg(p.value)
        FROM (
          SELECT value
          FROM jsonb_array_elements_text(e.changed_paths_json) WITH ORDINALITY AS t(value, ord)
          ORDER BY ord
          LIMIT 200
        ) p
      ) AS changed_paths_json,
      (e.categories_json ? 'results_reconciliation') AS results_confound,
      e.needs_human_review
    FROM materiality_events e
    LEFT JOIN trials t ON t.nct_id = e.nct_id
    LEFT JOIN LATERAL (
      SELECT event_id
      FROM evidence_record_store er
      JOIN evidence_record_generations generation
        ON generation.package_generation = er.package_generation
       AND generation.is_active
      WHERE er.nct_id = e.nct_id
        AND er.from_version = e.from_version
        AND er.to_version = e.to_version
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
      corpusStamp: emptyCorpusStamp,
      postRecruitmentEvidenceRecords: [],
      recentEvents: [],
      criticalDensityTrials: [],
      amendmentIntensityTrials: [],
    };
  }

  try {
    const [
      summary,
      severityCounts,
      corpusStamp,
      postRecruitmentEvidenceRecords,
      recentEvents,
      criticalDensityTrials,
      amendmentIntensityTrials,
    ] = await Promise.all([
      getSummary(),
      getSeverityCounts(),
      getCorpusStamp(),
      getPostRecruitmentEvidenceRecords(),
      getRecentEvents(),
      getCriticalDensityTrials(),
      getAmendmentIntensityTrials(),
    ]);

    return {
      databaseReady: true,
      summary,
      severityCounts,
      corpusStamp,
      postRecruitmentEvidenceRecords,
      recentEvents,
      criticalDensityTrials,
      amendmentIntensityTrials,
    };
  } catch (error) {
    console.error("getHomeData failed:", error);
    return {
      databaseReady: false,
      databaseError: error instanceof Error ? error.message : "Database query failed.",
      summary: emptySummary,
      severityCounts: [],
      corpusStamp: emptyCorpusStamp,
      postRecruitmentEvidenceRecords: [],
      recentEvents: [],
      criticalDensityTrials: [],
      amendmentIntensityTrials: [],
    };
  }
}
