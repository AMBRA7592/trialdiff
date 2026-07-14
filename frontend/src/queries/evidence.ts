import { getSql, hasDatabaseUrl } from "@/db/client";

import { mapEvidenceRecordDetail, mapEvidenceRecordRow } from "./mappers";
import type { EvidenceCanonicalData, EvidenceRecordData, EvidenceRecordRow } from "./types";

// Cards preview at most two paths; shipping full arrays is wasted transfer
// (one corpus record carries 7,000+ paths). The cap leaves plenty of headroom
// for ranking signal paths ahead of administrative noise.
const PATH_PREVIEW_CAP = 200;

export async function getPostRecruitmentEvidenceRecords(limit = 40): Promise<EvidenceRecordRow[]> {
  const sql = getSql();
  // The results-posting confound comes from the pipeline's own persisted
  // tags (the outcome_edit_cooccurs_with_results_posting event class, or the
  // results_reconciliation category) — not from a re-derived path heuristic,
  // which had already drifted from the Python op-level semantics.
  const rows = await sql<Record<string, unknown>[]>`
    SELECT
      er.event_id,
      er.nct_id,
      t.brief_title,
      t.lead_sponsor,
      er.from_version,
      er.to_version,
      er.submitted_date,
      er.timing_context,
      er.severity_pre_timing,
      er.severity,
      er.category,
      er.categories_json,
      er.event_classes_json,
      jsonb_array_length(er.changed_paths_json) AS changed_path_count,
      (
        SELECT jsonb_agg(p.value)
        FROM (
          SELECT value
          FROM jsonb_array_elements_text(er.changed_paths_json) WITH ORDINALITY AS t(value, ord)
          ORDER BY ord
          LIMIT ${PATH_PREVIEW_CAP}
        ) p
      ) AS changed_paths_json,
      (
        er.event_classes_json ? 'outcome_edit_cooccurs_with_results_posting'
        OR er.categories_json ? 'results_reconciliation'
      ) AS results_confound,
      er.deterministic_rules_json,
      er.claims_supported_json,
      er.claims_not_supported_json,
      er.review_question,
      er.evidence_version,
      er.canonical_hash
    FROM evidence_records er
    LEFT JOIN trials t ON t.nct_id = er.nct_id
    WHERE er.timing_context = 'post_recruitment'
    ORDER BY
      CASE
        WHEN (
          er.event_classes_json ? 'outcome_edit_cooccurs_with_results_posting'
          OR er.categories_json ? 'results_reconciliation'
        ) AND er.category IN ('primary_outcome_change', 'secondary_outcome_change')
          THEN 1
        ELSE 0
      END,
      CASE er.severity
      WHEN 'critical' THEN 1
      WHEN 'high' THEN 2
      ELSE 3
    END, er.submitted_date DESC NULLS LAST, er.event_id
    LIMIT ${limit}
  `;

  return rows.map(mapEvidenceRecordRow);
}

export async function getEvidenceRecord(eventId: string): Promise<EvidenceRecordData> {
  if (!hasDatabaseUrl()) {
    return {
      databaseReady: false,
      databaseError: "DATABASE_URL is not configured.",
    };
  }

  try {
    const sql = getSql();
    const rows = await sql<Record<string, unknown>[]>`
      SELECT
        er.*,
        t.brief_title,
        t.lead_sponsor,
        t.overall_status,
        t.has_results
      FROM evidence_records er
      LEFT JOIN trials t ON t.nct_id = er.nct_id
      WHERE er.event_id = ${eventId}
      LIMIT 1
    `;
    const row = rows[0];
    return {
      databaseReady: true,
      record: row ? mapEvidenceRecordDetail(row) : undefined,
    };
  } catch (error) {
    console.error("getEvidenceRecord failed:", error);
    return {
      databaseReady: false,
      databaseError: error instanceof Error ? error.message : "Database query failed.",
    };
  }
}

export async function getEvidenceCanonical(eventId: string): Promise<EvidenceCanonicalData> {
  if (!hasDatabaseUrl()) {
    return {
      databaseReady: false,
      databaseError: "DATABASE_URL is not configured.",
    };
  }

  try {
    const sql = getSql();
    const rows = await sql<Record<string, unknown>[]>`
      SELECT canonical_json, canonical_hash
      FROM evidence_records
      WHERE event_id = ${eventId}
      LIMIT 1
    `;
    const row = rows[0];
    if (!row) {
      return { databaseReady: true };
    }

    // Since migration 006 canonical_json is a text column whose exact bytes
    // hash to canonical_hash; a legacy jsonb column would arrive as a parsed
    // object. Whether the text actually hashes to canonical_hash is decided
    // by the endpoint (a `USING ::text` conversion without the mandated
    // re-import yields strings that do NOT) — column type alone proves
    // nothing.
    const raw = row.canonical_json;
    const canonicalText = typeof raw === "string" ? raw : JSON.stringify(raw ?? null);

    return {
      databaseReady: true,
      canonicalText,
      canonicalHash: String(row.canonical_hash ?? ""),
    };
  } catch (error) {
    console.error("getEvidenceCanonical failed:", error);
    return {
      databaseReady: false,
      databaseError: error instanceof Error ? error.message : "Database query failed.",
    };
  }
}

export async function getEvidenceCanonicalHash(
  eventId: string,
): Promise<{ databaseReady: boolean; canonicalHash?: string }> {
  // Conditional-request precheck: answering an If-None-Match must not pull
  // the full canonical body (records run to ~2 MB) from the database.
  if (!hasDatabaseUrl()) {
    return { databaseReady: false };
  }
  try {
    const sql = getSql();
    const rows = await sql<Record<string, unknown>[]>`
      SELECT canonical_hash FROM evidence_records WHERE event_id = ${eventId} LIMIT 1
    `;
    const row = rows[0];
    return { databaseReady: true, canonicalHash: row ? String(row.canonical_hash ?? "") : undefined };
  } catch (error) {
    console.error("getEvidenceCanonicalHash failed:", error);
    return { databaseReady: false };
  }
}
