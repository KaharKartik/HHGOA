# Proposed Architecture

## Status and scope

This is a proposed, modular target architecture—not an implemented design or a claim about available data. It must be finalized only after the missing inputs in `PROJECT_AUDIT.md` are supplied.

## System shape

```text
Analyst UI
   | authenticated API requests
Backend API / case orchestration
   |-- Detection engine (deterministic, versioned policies)
   |-- Investigation agent (tool-mediated, bounded workflow)
   |-- TigerGraph adapter (schema/query boundary)
   |-- Evidence & audit service (immutable event records)
   `-- Answer validator (case-specific contract)
             |
      approved operational stores and TigerGraph
```

## Components and responsibilities

| Component | Responsibility | Boundary |
| --- | --- | --- |
| Frontend | Presents cases, evidence, relationship views, policy findings, agent progress, and review/submission controls. | Consumes versioned API contracts; contains no fraud-policy decisions. |
| Backend API | Authenticates/authorizes callers, validates requests, orchestrates case runs, and returns stable case/evidence/result resources. | Does not embed graph query language or model-provider calls in routes. |
| Detection engine | Runs only approved deterministic policies against normalized facts and emits explainable findings. | Policy definitions are versioned data/configuration; findings retain input references and policy version. |
| Investigation agent | Builds an investigation plan, calls read-only, typed tools, synthesizes a cited narrative, and requests human review where required. | Cannot directly query storage, mutate case evidence, set a final disposition, or bypass the validator. |
| TigerGraph adapter | Encapsulates connection handling, graph query invocation, graph result mapping, and schema compatibility checks. | Other modules use domain-level repository interfaces rather than GSQL. |
| Evidence/audit service | Records source references, derived facts, tool calls, policy evaluations, prompts/model metadata as permitted, reviewer actions, and result versions. | Append-only logical event model; sensitive content access is controlled. |
| Answer validator | Validates a proposed case answer against the supplied case contract and expected-answer rubric. | It reports validation results; it does not create answers or fabricate correctness criteria. |

## Investigation flow

1. An authorized user opens or creates a supplied case.
2. The API resolves its immutable case input version and starts an investigation run.
3. The detection engine produces deterministic findings; graph and history adapters return read-only, source-referenced facts.
4. The agent may invoke only registered, typed investigation tools and cites returned evidence IDs in its draft.
5. The evidence service appends each material action and artifact to the audit trail.
6. A reviewer approves, rejects, or amends a disposition when the agreed workflow requires it.
7. The answer validator evaluates the submitted answer only when an authoritative case contract exists.

## Production-quality design principles

- Make source data and derived outputs version-addressable and reproducible.
- Separate policy execution from AI reasoning; model output is evidence-cited analysis, not policy truth.
- Use least-privilege service identities and read-only agent tools by default.
- Correlate every request, case run, graph query, policy evaluation, and agent tool call with trace and audit identifiers.
- Treat graph/schema mappings and case contracts as deployable, reviewed artifacts.
- Protect sensitive data with role-based access, secret management, encryption in transit/at rest, redaction where required, and retention rules supplied by stakeholders.

## Recommended technology stack (proposal)

| Layer | Recommendation | Rationale |
| --- | --- | --- |
| Frontend | React + TypeScript + Vite | Strong typed UI ecosystem and fast hackathon iteration. |
| Backend API | Python + FastAPI + Pydantic | Typed request/response validation, async I/O, and a natural fit for data/agent orchestration. |
| Graph | TigerGraph + GSQL, isolated through adapter interfaces | Meets the project goal while keeping storage-specific logic contained. |
| Relational metadata/audit store | PostgreSQL | Suitable for cases, audit events, workflow state, and version metadata. |
| Background work | Redis-backed worker only if asynchronous execution is required | Keep optional until volume and latency needs are known. |
| Agent integration | Provider-neutral tool-calling interface | Defers model/provider selection to approved requirements. |
| Observability | OpenTelemetry-compatible tracing and structured logs | Supports reproducibility and audit correlation. |
| Delivery | Docker Compose for local development; CI with lint, tests, and contract checks | Repeatable local setup and deployment gates. |

These are recommendations, not dependencies to install in Phase 1.
