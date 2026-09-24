# Data Model Discovery and Contract

## Current state

No data files, data dictionary, TigerGraph schema, case definitions, or field-level requirements are present. This document intentionally does not name transaction columns, entity types, vertices, edges, or fraud patterns.

## Required discovery artifact

Before physical modelling or TigerGraph loading, obtain an authoritative data dictionary for every source. For each field, record:

| Required metadata | Purpose |
| --- | --- |
| Source dataset and version | Reproducibility and provenance. |
| Field name and business meaning | Prevents semantic guessing. |
| Type, format, nullability, and permitted values | Input validation and query correctness. |
| Entity/relationship identifier role | Determines keys and graph mapping. |
| Event-time and ingestion-time semantics | Supports history windows and replay. |
| Sensitivity classification and access controls | Enables privacy-aware handling. |
| Source-of-truth and quality constraints | Makes evidence defensible. |

## Logical model proposal

After discovery, model the system in five separately versioned layers:

1. **Source records** — immutable references to supplied source rows/files, including provenance and source version.
2. **Normalized facts** — validated, typed representations of source facts; no inferred relationships are silently embedded.
3. **Graph projection** — TigerGraph vertices/edges mapped from approved normalized identifiers and relationship semantics.
4. **Investigation records** — case, investigation run, evidence item, finding, review decision, and answer submission.
5. **Governance metadata** — policy/model/schema/case-contract versions, access classification, and audit events.

The TigerGraph vertex and edge catalogue must be produced from the source dictionary and approved relationship definitions. Until then, its schema is intentionally unspecified.

## Evidence contract proposal

Each derived finding or agent assertion should reference stable evidence identifiers, source/projection version, retrieval timestamp, producing component, and applicable policy/model version. Evidence content and retention rules must follow the supplied governance requirements.

## Validation gates before loading

- Validate schema conformance, identifier uniqueness, referential integrity, allowed values, timestamps, and required fields against the approved dictionary.
- Quarantine/reject invalid rows with reasons; do not silently coerce unknown semantics.
- Produce a load manifest with source checksums/counts and graph-projection counts.
- Reconcile graph counts and sampled relationships to the approved mapping before exposing data to investigations.
