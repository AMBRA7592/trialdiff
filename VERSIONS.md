# Version Lines

Four unrelated version sequences coexist in this repository and previously
collided (two different things named "v0.2"; a spec "v1.1" that predates the
shipped "v0.1-alpha"). This file is the disambiguation table.

## 1. Product specs (design documents — archived, largely retracted)

| Label | Date | Status |
| --- | --- | --- |
| Spec v0.2 | 2026-05-20 | Archived (`docs/archive/`). First full spec: rules-first classifier, SQLite→Neon, breast-cancer MVP |
| Spec v0.3 | 2026-05-20 | Archived. Adds timing as severity modifier + reproducible corpus selection |
| Spec v1.0 | — | **Never existed.** v1.1's header references "v1.0 positioning" — that positioning lived in conversation/working notes, not in a committed document |
| Spec v1.1 | 2026-05-21 | Archived. Repositioned as "open amendment evidence layer"; its buyer-facing severity brief was later blocked by the failed calibration. Despite the highest number, this is a *pre-release* document |

Spec version numbers do **not** track releases. No future document should
use bare "vN.N" without one of the prefixes below.

## 2. Releases (shipped artifacts)

| Label | Date | Status |
| --- | --- | --- |
| v0.1-alpha | 2026-06-17 | The frozen evidence demo package (`records/`, `MANIFEST.sha256`) and the live deployment. Still the only release |

## 3. Severity calibration (validation attempts)

| Label | Date | Result |
| --- | --- | --- |
| Calibration v0.2 | 2026-06-18 | Failed gate: 6/30 (R1) and 3/30 (R2) critical confirmations vs ≥24/30 required |
| Calibration v0.2.1 | 2026-06-18/20 | Failed gate again: 17/30 and 4/30; additional fresh applications 5/30 and 12/30. Outcome: severity decoupled from review priority (`SEVERITY_DECOUPLING_v0.2.1.md`) |

"Calibration v0.2" and "Spec v0.2" are unrelated; the shared number is
historical accident.

## 4. Event-class record packages (data exports)

| Label | Date | Status |
| --- | --- | --- |
| event-class v0.1 | 2026-06-22 | Superseded stub — records were byte-identical to v0.1.1. Zenodo DOI [10.5281/zenodo.20801957](https://doi.org/10.5281/zenodo.20801957) |
| event-class v0.1.1 | 2026-06-23 | Frozen; carries erratum E1 (`ERRATA.md`) for the whyStopped class. Zenodo DOI [10.5281/zenodo.20816639](https://doi.org/10.5281/zenodo.20816639), published from the `trialdiff-public` snapshot |
| event-class v0.1.2 | pending | Planned corrected regeneration under `trialdiff.event_classes.v0.2` definitions; to be published as a new version under concept DOI [10.5281/zenodo.20801956](https://doi.org/10.5281/zenodo.20801956) (see `RELEASING.md`) |

## 5. Event-class definitions (code semantics)

| Label | Hash | Status |
| --- | --- | --- |
| `trialdiff.event_classes.v0.1` | `a6734d37…` | Produced the v0.1/v0.1.1 packages; whyStopped predicate defect (E1) |
| `trialdiff.event_classes.v0.2` | `07957f8b…` | Current at HEAD; the TO-version view is derived from the patch when no snapshot is stored, and the hash pins normalized implementation source bytes as well as definitions |
