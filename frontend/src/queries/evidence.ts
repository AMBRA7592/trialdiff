import { getSql, hasDatabaseUrl } from "@/db/client";

import { mapEvidenceRecordDetail, mapEvidenceRecordRow } from "./mappers";
import type { EvidenceCanonicalData, EvidenceRecordData, EvidenceRecordRow } from "./types";

export async function getPostRecruitmentEvidenceRecords(limit = 40): Promise<EvidenceRecordRow[]> {
  const sql = getSql();
  // The results-posting confound check mirrors the pipeline's semantics
  // (trialdiff/classifier/materiality.py is_results_reconciliation_patch):
  // "/resultsSection" itself, any nested "/resultsSection/..." path, or
  // "/hasResults". A jsonb `?` exact match would miss nested paths.
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
          AND (
            EXISTS (
              SELECT 1 FROM jsonb_array_elements_text(er.changed_paths_json) p
              WHERE p = '/resultsSection' OR p LIKE '/resultsSection/%'
            )
            OR er.changed_paths_json ? '/hasResults'
          )
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

    // Since migration 006 canonical_json is a text column, so postgres.js
    // returns the exact stored string whose bytes hash to canonical_hash.
    // A legacy jsonb column arrives as a parsed object instead; serving a
    // re-encoded body then cannot be byte-verified against the hash.
    const raw = row.canonical_json;
    const canonicalVerifiable = typeof raw === "string";
    const canonicalText = canonicalVerifiable ? (raw as string) : JSON.stringify(raw ?? null);

    return {
      databaseReady: true,
      canonicalText,
      canonicalVerifiable,
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
