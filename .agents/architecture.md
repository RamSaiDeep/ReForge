# ReForge Architecture Blueprint

This document details the architectural boundaries, design decisions, and structured agent communication interfaces for the ReForge platform.

---

## 1. Clean Architecture Boundaries

To ensure ReForge is highly maintainable, testable, and explainable, we strictly adhere to Clean Architecture principles. The dependency graph flows **inward** toward the core domain entities:

```text
  ┌──────────────────────────────────────────────────────────┐
  │ Frameworks & Drivers (FastAPI, PostgreSQL, S3)           │
  │   ┌──────────────────────────────────────────────────┐   │
  │   │ Interface Adapters (REST Controllers, DB Repos)  │   │
  │   │   ┌──────────────────────────────────────────┐   │   │
  │   │   │ Use Cases (Supervisor Workflow Engine)   │   │   │
  │   │   │   ┌──────────────────────────────────┐   │   │   │
  │   │   │   │ Domain Entities (Data Contracts) │   │   │   │
  │   │   │   └──────────────────────────────────┘   │   │   │
  │   │   └──────────────────────────────────────────┘   │   │
  │   └──────────────────────────────────────────────────┘   │
  └──────────────────────────────────────────────────────────┘
```

* **Domain Entities (Core):** Framework-agnostic Python classes/dataclasses and Pydantic schemas defining the domain objects (`RepositoryProfile`, `HeritageReport`, `ArchitectureReport`, etc.). No dependencies on databases, AI libraries, or APIs.
* **Use Cases:** Core application logic, including the orchestrator (**Supervisor**) and individual **ArchaeologyAgent** abstract definitions.
* **Interface Adapters:** Translates data between use cases and external tools. Includes REST controllers, agent run execution wrappers, and database repository implementations.
* **Frameworks & Drivers:** Databases, HTTP servers (FastAPI), local/remote storage drivers, and the underlying AI models (LLMs).

---

## 2. The Hybrid Blackboard Pattern

Rather than direct message passing or an unstructured agent chat, ReForge uses a **Hybrid Blackboard Pattern**:

1. **Shared State Store (The Blackboard):** All excavation metadata and generated reports are stored in a central repository, partitioned by `project_id`.
2. **Supervisor Orchestration:** The Supervisor runs as the state machine controller, checking if prerequisites for each stage are met before launching the corresponding agent.
3. **Structured Contracts:** Each agent accepts the current `ExcavationState` and outputs a strongly typed Pydantic contract which updates the state.

```mermaid
graph TD
    Supervisor[Supervisor Workflow Engine] -->|1. Validate Prerequisites| DB[(Shared State / DB)]
    Supervisor -->|2. Invoke Agent| Agent[Archaeology Agent]
    Agent -->|3. Read Inputs| DB
    Agent -->|4. Execute Task| AI[AI / Tools]
    Agent -->|5. Write Typed Contract| DB
    DB -->|6. Trigger State Transition| Supervisor
```

---

## 3. Core Domain Data Contracts (Schemas)

We use **Pydantic v2** models to define the input and output boundaries of each stage. Every stage's output must be transparent, typed, and explainable.

### Stage 1: Discovery (`RepositoryProfile`)

```python
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl

class RepositoryProfile(BaseModel):
    """Output of Scout: Basic repository metadata collected without full download."""
    url: HttpUrl
    name: str
    owner: str
    primary_language: str
    languages: Dict[str, float] = Field(default_factory=dict, description="Language percentages")
    stars: int = Field(ge=0)
    forks: int = Field(ge=0)
    watchers: int = Field(ge=0)
    license: Optional[str] = None
    contributors_count: int = Field(default=0, ge=0)
    last_commit_at: datetime
    created_at: datetime
    readme_content: Optional[str] = None
```

### Stage 2: Heritage Evaluation (`HeritageReport`)

```python
class PreservationCategory(BaseModel):
    score: int = Field(ge=0, le=100)
    explanation: str = Field(..., description="Explainable rationale behind the score")

class PreservationProfile(BaseModel):
    historical_value: PreservationCategory
    community_value: PreservationCategory
    activity_sustainability: PreservationCategory
    restoration_feasibility: PreservationCategory
    educational_value: PreservationCategory
    innovation_evolution_potential: PreservationCategory

class HeritageReport(BaseModel):
    """Output of Heritage Evaluator: Multi-dimensional score and rationale."""
    repository_url: HttpUrl
    overall_score: int = Field(ge=0, le=100)
    profile: PreservationProfile
    worth_preserving: bool
    guiding_question_answer: str = Field(
        ..., 
        description="Why does this software deserve another chapter?"
    )
    explanation: str = Field(..., description="Overall summary rationale")
```

---

## 4. Supervisor Workflow State Transitions

The excavation lifecycle is modeled as a state machine managed by the `Supervisor`:

```mermaid
stateDiagram-v2
    [*] --> DISCOVERING : Scout runs
    DISCOVERING --> DISCOVERED : Scout succeeds
    DISCOVERED --> EVALUATING : Heritage Evaluator runs
    EVALUATING --> EVALUATED : Heritage succeeds
    
    state EVALUATED <<choice>>
    EVALUATED --> STOPPED : worth_preserving == False AND NOT force_continue
    EVALUATED --> UNDERSTANDING : worth_preserving == True OR force_continue
    
    UNDERSTANDING --> UNDERSTOOD : Explorer succeeds
    UNDERSTOOD --> RECONSTRUCTING : Architect runs
    RECONSTRUCTING --> RECONSTRUCTED : Architect succeeds
    RECONSTRUCTED --> RESTORATION_PLANNING : Restorer plans
    RESTORATION_PLANNING --> AWAITING_APPROVAL : Awaits human review
    
    AWAITING_APPROVAL --> RESTORING : User approves restoration
    RESTORING --> VALIDATING : Builder / Validator run
    VALIDATING --> EVOLVING : Validation passes
    EVOLVING --> COMPLETED : Evolution Planner succeeds
```

### State Definitions

* **`AWAITING_APPROVAL`:** The pipeline halts when a restoration strategy is planned. Humans retain final authority to modify and approve the code changes before execution.
* **`STOPPED`:** Indicates the software was evaluated as not worth preserving, preventing resource waste.

---

## 5. Architectural Principles

1. **Strict Type Safety:** All agents must return instantiated Pydantic models. Any unstructured output or markdown must be wrapped inside a typed property (e.g., `explanation: str`).
2. **Explainability First:** No evaluation score or restoration action can exist without a matching `explanation` property describing the *why*, *how*, and *impact*.
3. **Database Independence:** Interface repositories will hide the actual database (PostgreSQL/JSON) behind abstract interfaces, ensuring the code can run locally using mock repositories during test runs.
