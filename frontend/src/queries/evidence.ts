import { getSql, hasDatabaseUrl } from "@/db/client";

import { mapEvidenceRecordDetail, mapEvidenceRecordRow, recordValue } from "./mappers";
import type { EvidenceCanonicalData, EvidenceRecordData, EvidenceRecordRow } from "./types";

export async function getPostCompletionEvidenceRecords(limit = 40): Promise<EvidenceRecordRow[]> {
  const sql = getSql();
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
      er.changed_paths_json,
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
        WHEN er.category IN ('primary_outcome_change', 'secondary_outcome_change')
          AND (er.changed_paths_json ? '/resultsSection' OR er.changed_paths_json ? '/hasResults')
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
    return {
      databaseReady: true,
      canonicalJson: row ? recordValue(row.canonical_json) : undefined,
      canonicalHash: row ? String(row.canonical_hash ?? "") : undefined,
    };
  } catch (error) {
    return {
      databaseReady: false,
      databaseError: error instanceof Error ? error.message : "Database query failed.",
    };
  }
}
