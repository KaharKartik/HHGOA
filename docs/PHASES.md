# Delivery Phases

## Phase 1 — Repository audit and architecture (complete)

Audit the existing repository, document factual gaps, propose modular architecture and data-modelling process, create empty module boundaries, and provide a placeholder-only environment template. No application behavior, graph loading, data edits, policies, UI, or agent implementation belongs in this phase.

## Phase 2 — Requirements and contracts (recommended next)

1. Ingest the authoritative datasets and data dictionaries without altering originals.
2. Define versioned case contracts, expected-answer/rubric artifacts, and acceptance tests.
3. Approve the graph logical model and TigerGraph physical schema/loading mapping.
4. Define the deterministic fraud-policy catalogue with thresholds, owners, versions, and test fixtures.
5. Agree roles, security/privacy controls, retention, operational objectives, and model governance.
6. Produce API, evidence, and tool contracts; then scaffold testable interfaces.

**Exit criteria:** stakeholders approve source mappings, case/answer contracts, policy contracts, graph design, and implementation acceptance criteria.

## Phase 3 — Foundation implementation

Implement the backend skeleton, typed contracts, auth boundary, audit-event storage, TigerGraph adapter, data-validation pipeline, and automated contract/unit tests. Load only approved data through reproducible jobs.

## Phase 4 — Investigation capabilities

Implement approved deterministic policies, graph/history retrieval queries, evidence assembly, and reviewer workflow. Validate outcomes against supplied cases before enabling any agent-driven synthesis.

## Phase 5 — Agent and analyst experience

Implement the bounded investigation agent with typed read-only tools and citations, then build the analyst UI around case progression, evidence review, graph exploration, and answer submission.

## Phase 6 — Assurance and delivery

Run security/privacy review, load/performance testing, policy regression tests, answer-validation tests, observability checks, deployment rehearsal, and operational documentation.
