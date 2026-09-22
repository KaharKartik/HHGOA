# HHGOA Fraud Investigation

A full-stack intelligence and investigation platform designed for fraud detection, graph analytics, and automated agent workflows.

---

## Repository Structure & Directory Purpose

```text
hhgoa-fraud-investigation/
├── backend/          # REST/GraphQL API server, routing, business logic, and database connectors
├── frontend/         # Web dashboard, investigation UI, visualization components, and user interfaces
├── agent/            # Autonomous AI investigation agents, reasoning chains, tool definitions, and LLM integrations
├── tigergraph/       # TigerGraph schema definitions, GSQL queries, loading jobs, and graph setup scripts
├── detection/        # Fraud detection models, anomaly scoring algorithms, heuristic rules, and ML pipelines
├── data/             # Local data stores, sample datasets, schemas, and staging directories (git-ignored)
├── tests/            # Automated test suites (unit, integration, and end-to-end tests)
├── docs/             # Project documentation, architecture diagrams, API specs, and runbooks
├── scripts/          # Automation, deployment, data ingestion, database migrations, and utility scripts
├── .env.example      # Environment variables template with placeholder configuration
├── .gitignore        # Git ignore rules for Python, Node/TS, artifacts, secrets, and environments
└── README.md         # Repository overview and directory reference
```

---

## Directory Overview

| Directory | Purpose |
| :--- | :--- |
| **`backend/`** | Hosts the backend server API, service layer, authentication, and core application workflows. |
| **`frontend/`** | Contains the client-side user interface for analysts and investigators (React / TypeScript / Next / Vite). |
| **`agent/`** | Houses agentic reasoning systems, tool dispatchers, prompts, and orchestration for AI-driven fraud investigation. |
| **`tigergraph/`** | Stores graph database schemas, GSQL queries, graph algorithms, and TigerGraph connection helpers. |
| **`detection/`** | Implements fraud detection algorithms, statistical models, rule engines, and machine learning components. |
| **`data/`** | Holds sample data files, test fixtures, and raw/processed investigation records. Large and generated files are ignored by git. |
| **`tests/`** | Centralizes unit, integration, and system tests across backend, agent, graph, and detection modules. |
| **`docs/`** | Includes architectural design documents, API specifications, sequence diagrams, and operational guides. |
| **`scripts/`** | Provides operational scripts for setup, database seeding, schema installation, and batch processing. |

---

## Getting Started

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Populate the required environment variables with your local or staging credentials.
3. Refer to upcoming modules for backend and frontend setup.
