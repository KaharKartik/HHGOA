# Project Audit — Phase 1

Audit date: 2026-09-22  
Repository: `hhgoa-fraud-investigation`  
Scope: all working-tree files and Git-tracked files present at audit time. Git's internal metadata and sample hooks were inspected as repository tooling; they contain no project requirements or assets.

## Executive summary

The repository is an initial, clean scaffold (one commit: `Initial commit: repository scaffolding and project structure`). It contains no fraud dataset, data dictionary, case definitions, expected answers, fraud-policy definitions, TigerGraph schema/query/loading artifact, source code, dependency manifest, or test code. Therefore, Phase 1 can establish boundaries and decision points, but cannot specify a factual domain model or implement behavior.

## Inventory

| Area | Present | Findings |
| --- | --- | --- |
| Project documentation | `README.md` | Describes intended top-level directories and broad platform intent. It does not specify functional requirements, APIs, data, cases, or acceptance criteria. |
| Configuration | `.env.example`, `.gitignore` | Template variable names indicate anticipated application, frontend, TigerGraph, model-provider, database, cache, and data-directory configuration. Values are placeholders after this Phase 1 update. The ignore policy excludes secrets, common Python/Node outputs, data files, graph outputs, and model artifacts. |
| Source modules | `agent/`, `backend/`, `detection/`, `frontend/`, `scripts/`, `tests/`, `tigergraph/` | Each originally contained only `.gitkeep`; no implementation exists. |
| Data | `data/.gitkeep` only | No dataset, schema/data dictionary, fixtures, labels, or sample records exist. |
| Case material | None | No case IDs, prompts, expected answers, review workflow, or answer format exists. |
| Git history | One initial commit | No prior implementation or removed project artifact is available in history. |

## Available datasets and schemas

None are present. As a result, transaction fields, entity identifiers, relationship keys, timestamps, currencies, labels, and privacy classification are unknown. `DATA_MODEL.md` deliberately provides a validation-first modelling process rather than inventing these details.

## Existing scripts and code

None. The only executable-looking files are Git's standard inactive sample hooks under `.git/hooks`; they are Git-provided examples, not project scripts.

## Requirements evidenced by materials

The README establishes a planned full-stack fraud investigation platform and names intended responsibilities for backend, frontend, agent, TigerGraph, detection, data, tests, docs, and scripts. The user-provided Phase 1 request establishes the deliverables and explicitly prohibits implementation, data modification, and fabricated requirements. No other requirements are present.

## Expected outputs currently evidenced

No runtime output contract, API response shape, report template, UI mockup, case-answer schema, scoring metric, or test expectation is supplied. The only Phase 1 outputs now defined are the requested documentation, environment template, and empty module boundaries.

## Missing inputs required before implementation

1. Source datasets plus authoritative data dictionary, provenance, refresh cadence, and permitted-use/privacy constraints.
2. Case definitions: case identifier, seed transaction/entity, investigative question, expected answer contract, and evaluation rubric.
3. Fraud-policy catalogue: policy identifiers, deterministic conditions, thresholds/windows, severity, rationale, and versioning/approval owner.
4. TigerGraph deployment details and an approved logical/physical schema, including identifiers, cardinality, retention, and loading mappings.
5. User roles, authentication/authorization requirements, analyst workflow, and evidence-retention/audit requirements.
6. Non-functional requirements: scale, latency, availability, data residency, observability, and security/compliance constraints.
7. Approved model provider/model, safety policy, budget/rate constraints, and human-review boundaries for the investigation agent.

## Phase 1 changes

Created the requested planning documentation, normalized `.env.example` to placeholders, and added empty module-boundary directories. No data files were changed. No application, agent, UI, graph loading, or fraud rules were implemented.
