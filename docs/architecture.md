# ARCHITECTURE.md

# ReForge Architecture

```text
                Frontend (Next.js)
                       │
                FastAPI Backend
                       │
               Supervisor Agent
                       │
 ┌──────────┬──────────┬──────────┬──────────┐
 ▼          ▼          ▼          ▼
Scout   Heritage   Explorer   Architect
                       │
                 Historian
                       │
                 Restoration
                       │
               Evolution Planner
                       │
                  Validator
                       │
                 PostgreSQL
                       │
               Object Storage
```

## Components

### Frontend

Interactive software archaeology workspace.

### Backend

API, orchestration and business logic.

### Supervisor

Controls workflow execution.

### Agents

Each agent performs one specialized task.

### Database

Stores metadata, reports and history.

### Object Storage

Stores repositories, artifacts and generated reports.

## Design Principles

* Modular
* Explainable
* Human-in-the-loop
* Agent-first
* Extensible
* Reproducible
