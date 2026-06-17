from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any

from trialdiff.provenance import Provenance, canonical_json, sha256_json, utc_now_iso


MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db" / "migrations"


def connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(db_path: str | Path) -> None:
    connection = connect(db_path)
    try:
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            connection.executescript(migration.read_text(encoding="utf-8"))
        connection.commit()
    finally:
        connection.close()


def _json(value: Any) -> str:
    return canonical_json(value)


class TrialDiffStore:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def upsert_trial(self, record: dict[str, Any], provenance: Provenance) -> str:
        fields = extract_trial_fields(record)
        current_hash = sha256_json(record)
        self.connection.execute(
            """
            INSERT INTO trials (
              nct_id, brief_title, official_title, lead_sponsor, lead_sponsor_class,
              conditions_json, interventions_json, overall_status, phase_json, study_type,
              last_update_posted, first_submitted_date, has_results, current_record_json,
              current_record_hash, source, source_url, fetched_at, source_version, raw_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(nct_id) DO UPDATE SET
              brief_title=excluded.brief_title,
              official_title=excluded.official_title,
              lead_sponsor=excluded.lead_sponsor,
              lead_sponsor_class=excluded.lead_sponsor_class,
              conditions_json=excluded.conditions_json,
              interventions_json=excluded.interventions_json,
              overall_status=excluded.overall_status,
              phase_json=excluded.phase_json,
              study_type=excluded.study_type,
              last_update_posted=excluded.last_update_posted,
              first_submitted_date=excluded.first_submitted_date,
              has_results=excluded.has_results,
              current_record_json=excluded.current_record_json,
              current_record_hash=excluded.current_record_hash,
              source=excluded.source,
              source_url=excluded.source_url,
              fetched_at=excluded.fetched_at,
              source_version=excluded.source_version,
              raw_hash=excluded.raw_hash
            """,
            (
                fields["nct_id"],
                fields["brief_title"],
                fields["official_title"],
                fields["lead_sponsor"],
                fields["lead_sponsor_class"],
                _json(fields["conditions"]),
                _json(fields["interventions"]),
                fields["overall_status"],
                _json(fields["phase"]),
                fields["study_type"],
                fields["last_update_posted"],
                fields["first_submitted_date"],
                1 if fields["has_results"] else 0,
                _json(record),
                current_hash,
                provenance.source.value,
                provenance.source_url,
                provenance.fetched_at,
                provenance.source_version,
                provenance.raw_hash,
            ),
        )
        return fields["nct_id"]

    def insert_snapshot(self, nct_id: str, record: dict[str, Any], provenance: Provenance) -> None:
        record_hash = sha256_json(record)
        self.connection.execute(
            """
            INSERT OR IGNORE INTO trial_snapshots (
              nct_id, snapshot_date, record_json, record_hash, source, source_url,
              fetched_at, source_version, raw_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nct_id,
                provenance.fetched_at,
                _json(record),
                record_hash,
                provenance.source.value,
                provenance.source_url,
                provenance.fetched_at,
                provenance.source_version,
                provenance.raw_hash,
            ),
        )

    def upsert_version(self, nct_id: str, change: dict[str, Any], provenance: Provenance) -> None:
        self.connection.execute(
            """
            INSERT INTO trial_versions (
              nct_id, version, submitted_date, overall_status, study_type, module_labels_json,
              review_not_passed, unposted_events_json, source, source_url, fetched_at,
              source_version, raw_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(nct_id, version) DO UPDATE SET
              submitted_date=excluded.submitted_date,
              overall_status=excluded.overall_status,
              study_type=excluded.study_type,
              module_labels_json=excluded.module_labels_json,
              review_not_passed=excluded.review_not_passed,
              unposted_events_json=excluded.unposted_events_json,
              source=excluded.source,
              source_url=excluded.source_url,
              fetched_at=excluded.fetched_at,
              source_version=excluded.source_version,
              raw_hash=excluded.raw_hash
            """,
            (
                nct_id,
                int(change["version"]),
                change.get("date"),
                change.get("status"),
                change.get("studyType"),
                _json(change.get("moduleLabels") or []),
                1 if change.get("reviewNotPassed") else 0,
                _json(change.get("unpostedEvents") or []),
                provenance.source.value,
                provenance.source_url,
                provenance.fetched_at,
                provenance.source_version,
                provenance.raw_hash,
            ),
        )

    def update_version_record(
        self,
        *,
        nct_id: str,
        version: int,
        record: dict[str, Any],
    ) -> None:
        self.connection.execute(
            """
            UPDATE trial_versions
            SET record_json=?, record_hash=?
            WHERE nct_id=? AND version=?
            """,
            (_json(record), sha256_json(record), nct_id, version),
        )

    def insert_patch(
        self,
        *,
        nct_id: str,
        from_version: int,
        to_version: int,
        patch_kind: str,
        patch: list[dict[str, Any]],
        changed_modules: list[str],
        provenance: Provenance,
    ) -> None:
        op_counts: dict[str, int] = {}
        for operation in patch:
            op = operation.get("op", "unknown")
            op_counts[op] = op_counts.get(op, 0) + 1
        patch_hash = sha256_json(patch)
        changed_paths = [operation.get("path") for operation in patch if operation.get("path")]
        self.connection.execute(
            """
            INSERT OR IGNORE INTO trial_patches (
              nct_id, from_version, to_version, patch_kind, patch_json, patch_hash,
              changed_paths_json, changed_modules_json, op_counts_json, source, source_url,
              fetched_at, source_version, raw_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nct_id,
                from_version,
                to_version,
                patch_kind,
                _json(patch),
                patch_hash,
                _json(changed_paths),
                _json(changed_modules),
                _json(op_counts),
                provenance.source.value,
                provenance.source_url,
                provenance.fetched_at,
                provenance.source_version,
                provenance.raw_hash,
            ),
        )

    def create_ingest_run(
        self,
        *,
        corpus_label: str | None,
        query: dict[str, Any] | None = None,
        relaxation: dict[str, Any] | None = None,
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO ingest_runs (corpus_label, query_json, relaxation_json, started_at, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (corpus_label, _json(query or {}), _json(relaxation or {}), utc_now_iso(), "running"),
        )
        return int(cursor.lastrowid)

    def complete_ingest_run(self, run_id: int, status: str, notes: str | None = None) -> None:
        self.connection.execute(
            """
            UPDATE ingest_runs SET completed_at=?, status=?, notes=? WHERE id=?
            """,
            (utc_now_iso(), status, notes, run_id),
        )

    def load_active_rules(self) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT * FROM classifier_rules
                WHERE active=1
                ORDER BY id
                """
            )
        )

    def iter_patches(self, nct_id: str | None = None) -> list[sqlite3.Row]:
        if nct_id:
            return list(
                self.connection.execute(
                    """
                    SELECT * FROM trial_patches
                    WHERE nct_id=?
                    ORDER BY nct_id, from_version, to_version
                    """,
                    (nct_id,),
                )
            )
        return list(
            self.connection.execute(
                """
                SELECT * FROM trial_patches
                ORDER BY nct_id, from_version, to_version
                """
            )
        )

    def get_version_record(self, nct_id: str, version: int) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT record_json FROM trial_versions
            WHERE nct_id=? AND version=?
            """,
            (nct_id, version),
        ).fetchone()
        if not row or not row["record_json"]:
            return None
        return json.loads(row["record_json"])

    def get_version_submitted_date(self, nct_id: str, version: int) -> str | None:
        row = self.connection.execute(
            """
            SELECT submitted_date FROM trial_versions
            WHERE nct_id=? AND version=?
            """,
            (nct_id, version),
        ).fetchone()
        return None if not row else row["submitted_date"]

    def insert_materiality_event(self, event: dict[str, Any], provenance: Provenance) -> None:
        self.connection.execute(
            """
            INSERT OR IGNORE INTO materiality_events (
              nct_id, from_version, to_version, submitted_date, timing_context,
              severity_pre_timing, severity, category, categories_json, changed_paths_json,
              deterministic_rules_json, value_signals_json, summary, summary_source,
              needs_human_review, created_at, rule_set_hash, source, source_url, fetched_at,
              source_version, raw_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["nct_id"],
                event["from_version"],
                event["to_version"],
                event.get("submitted_date"),
                event.get("timing_context"),
                event["severity_pre_timing"],
                event["severity"],
                event["category"],
                _json(event.get("categories") or []),
                _json(event.get("changed_paths") or []),
                _json(event.get("deterministic_rules") or []),
                _json(event.get("value_signals") or []),
                event.get("summary"),
                event.get("summary_source"),
                1 if event.get("needs_human_review") else 0,
                event.get("created_at") or utc_now_iso(),
                event.get("rule_set_hash") or "",
                provenance.source.value,
                provenance.source_url,
                provenance.fetched_at,
                provenance.source_version,
                provenance.raw_hash,
            ),
        )

    def delete_materiality_events(self, nct_id: str | None = None) -> int:
        if nct_id:
            cursor = self.connection.execute(
                "DELETE FROM materiality_events WHERE nct_id=?",
                (nct_id,),
            )
        else:
            cursor = self.connection.execute("DELETE FROM materiality_events")
        return cursor.rowcount

    def iter_evidence_source_rows(
        self,
        nct_id: str | None = None,
        *,
        severities: tuple[str, ...] = ("high", "critical"),
    ) -> list[sqlite3.Row]:
        placeholders = ",".join("?" for _item in severities)
        params: list[Any] = list(severities)
        nct_clause = ""
        if nct_id:
            nct_clause = "AND e.nct_id=?"
            params.append(nct_id)
        return list(
            self.connection.execute(
                f"""
                SELECT
                  e.nct_id,
                  e.from_version,
                  e.to_version,
                  e.submitted_date,
                  e.timing_context,
                  e.severity_pre_timing,
                  e.severity,
                  e.category,
                  e.categories_json,
                  e.changed_paths_json,
                  e.deterministic_rules_json,
                  e.value_signals_json,
                  e.needs_human_review,
                  e.rule_set_hash,
                  e.raw_hash AS materiality_event_hash,
                  p.patch_json,
                  p.patch_hash,
                  p.source AS patch_source,
                  p.source_url AS patch_source_url,
                  p.raw_hash AS patch_raw_hash,
                  from_version.record_hash AS from_snapshot_hash,
                  to_version.record_hash AS to_snapshot_hash
                FROM materiality_events e
                JOIN trial_patches p
                  ON p.nct_id=e.nct_id
                 AND p.from_version=e.from_version
                 AND p.to_version=e.to_version
                LEFT JOIN trial_versions from_version
                  ON from_version.nct_id=e.nct_id
                 AND from_version.version=e.from_version
                LEFT JOIN trial_versions to_version
                  ON to_version.nct_id=e.nct_id
                 AND to_version.version=e.to_version
                WHERE e.severity IN ({placeholders})
                  {nct_clause}
                ORDER BY e.nct_id, e.from_version, e.to_version, e.category
                """,
                params,
            )
        )

    def evidence_record_exists(
        self,
        *,
        nct_id: str,
        from_version: int,
        to_version: int,
        rule_set_hash: str,
        evidence_version: int,
    ) -> bool:
        row = self.connection.execute(
            """
            SELECT 1 FROM evidence_records
            WHERE nct_id=?
              AND from_version=?
              AND to_version=?
              AND rule_set_hash=?
              AND evidence_version=?
            LIMIT 1
            """,
            (nct_id, from_version, to_version, rule_set_hash, evidence_version),
        ).fetchone()
        return row is not None

    def insert_evidence_record(self, record: dict[str, Any]) -> int:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO evidence_records (
              event_id, nct_id, from_version, to_version, submitted_date, timing_context,
              severity_pre_timing, severity, category, categories_json, changed_paths_json,
              deterministic_rules_json, value_signals_json, claims_supported_json,
              claims_not_supported_json, review_question, citation_text, canonical_json,
              canonical_hash, evidence_version, patch_hash, patch_source, patch_source_url,
              patch_raw_hash, from_snapshot_hash, to_snapshot_hash, materiality_event_hash,
              rule_set_hash, source, source_url, generated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["event_id"],
                record["nct_id"],
                record["from_version"],
                record["to_version"],
                record.get("submitted_date"),
                record.get("timing_context"),
                record["severity_pre_timing"],
                record["severity"],
                record["category"],
                _json(record.get("categories") or []),
                _json(record.get("changed_paths") or []),
                _json(record.get("deterministic_rules") or []),
                _json(record.get("value_signals") or []),
                _json(record.get("claims_supported") or []),
                _json(record.get("claims_not_supported") or []),
                record["review_question"],
                record["citation_text"],
                _json(record["canonical"]),
                record["canonical_hash"],
                record["evidence_version"],
                record["patch_hash"],
                record["patch_source"],
                record.get("patch_source_url") or "",
                record.get("patch_raw_hash") or "",
                record.get("from_snapshot_hash"),
                record.get("to_snapshot_hash"),
                record.get("materiality_event_hash") or "",
                record["rule_set_hash"],
                record["source"],
                record["source_url"],
                record["generated_at"],
            ),
        )
        return cursor.rowcount

    def delete_evidence_records(self, nct_id: str | None = None) -> int:
        if nct_id:
            cursor = self.connection.execute(
                "DELETE FROM evidence_records WHERE nct_id=?",
                (nct_id,),
            )
        else:
            cursor = self.connection.execute("DELETE FROM evidence_records")
        return cursor.rowcount


def extract_trial_fields(record: dict[str, Any]) -> dict[str, Any]:
    protocol = record.get("protocolSection") or {}
    identification = protocol.get("identificationModule") or {}
    sponsor = protocol.get("sponsorCollaboratorsModule") or {}
    lead_sponsor = sponsor.get("leadSponsor") or {}
    conditions = protocol.get("conditionsModule") or {}
    arms = protocol.get("armsInterventionsModule") or {}
    status = protocol.get("statusModule") or {}
    design = protocol.get("designModule") or {}
    return {
        "nct_id": identification["nctId"],
        "brief_title": identification.get("briefTitle"),
        "official_title": identification.get("officialTitle"),
        "lead_sponsor": lead_sponsor.get("name"),
        "lead_sponsor_class": lead_sponsor.get("class"),
        "conditions": conditions.get("conditions") or [],
        "interventions": arms.get("interventions") or [],
        "overall_status": status.get("overallStatus"),
        "phase": design.get("phases") or [],
        "study_type": design.get("studyType"),
        "last_update_posted": (status.get("lastUpdatePostDateStruct") or {}).get("date"),
        "first_submitted_date": status.get("studyFirstSubmitDate"),
        "has_results": bool(record.get("hasResults")),
    }
