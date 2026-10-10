<img src="../assets/tiet-logo.png" alt="TIET Logo" width="100">

**UCS503: Software Engineering (Project)**  
**TIET Patiala**

# AutoClean AI

> **Automated, Auditable and Loss-Aware Data Preprocessing for Machine Learning**
>
> A preprocessing system that turns messy tabular datasets into model-ready data, records every change it makes, and aborts rather than silently discarding rows.

[![Course](https://img.shields.io/badge/UCS503-Software%20Engineering-blue.svg)](https://thapar.edu)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![Backend](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Data](https://img.shields.io/badge/pandas%20%7C%20scikit--learn-150458.svg?logo=pandas&logoColor=white)](https://pandas.pydata.org)
[![Frontend](https://img.shields.io/badge/React%20%2B%20TypeScript-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Tests](https://img.shields.io/badge/Tests-pytest-0A9EDC.svg?logo=pytest&logoColor=white)](https://pytest.org)


---

## The Problem

Preparing a dataset for machine learning is slow, repetitive and error-prone, especially when several data-quality issues occur together:

- **Issues are found manually**: Missing values, duplicates, outliers and inconsistent data types must be located by inspection.
- **Work is repeated**: The same preprocessing steps are rewritten for every dataset.
- **Changes are opaque**: It is often unclear which transformation altered which part of the data.
- **Data can be lost silently**: A careless step can drop rows or columns without anyone noticing.
- **Feature handling is ambiguous**: Deciding how to treat categorical, datetime and text columns requires judgement for each dataset.
- **Guidance is disconnected**: Algorithm advice is rarely tied to the dataset actually being processed.

**AutoClean AI** accepts a messy file, profiles it, applies a fixed and deterministic preprocessing pipeline, and returns a clean dataset together with an audit trail of what changed at every step.

---

## Design Principle: No Silent Data Loss

Row-count preservation is enforced by the system, not left to convention. After every pipeline step the orchestrator checks that the row count matches what the step is allowed to do. An unexpected change raises `DataLossError` and aborts the pipeline.

| Operation Category | Permitted Row-Count Change |
| :--- | :--- |
| Row-preserving transformations | No change |
| Duplicate removal | Decrease only when explicitly enabled |
| Outlier removal | Decrease only when explicitly configured |
| Dataset combination / stacking | Increase allowed |
| Synthetic data generation | Increase allowed |
| Any other change | Abort with `DataLossError` |

---

## Core Capabilities

| Capability | How It Works | Benefit |
| :--- | :--- | :--- |
| **Multi-format ingestion** | Accepts CSV, TSV, Excel and JSON, with encoding and delimiter sniffing for CSV/TSV. | Works with common real-world files without manual conversion. |
| **Semantic profiling** | Infers a kind for each column (numeric, boolean, datetime, categorical, text, identifier, empty) and reports missing percentage, cardinality and outlier count. | Downstream steps decide based on what a column means, not only its dtype. |
| **Cleaning** | Type coercion, missing-value imputation, and duplicate removal when enabled. | Produces consistent, usable columns. |
| **Outlier handling** | Three strategies: flag (default, non-destructive), clip, remove. | Extreme values are handled without unintended row loss. |
| **Categorical encoding** | One-hot or label encoding, chosen using column cardinality. | Model-ready categorical features. |
| **Feature engineering** | Datetime decomposition; text length and word count. | Useful features derived from raw date and text columns. |
| **Feature scaling** | Standard, Min-Max or Robust scaling; the dataframe is re-profiled before scaling. | Scaling decisions reflect the current state of the data. |
| **Audit trail** | Each step reports rows, columns and nulls before and after, with details and warnings. | Every change is traceable and reviewable. |
| **Multi-dataset operations** | Stack (vertical concat) and join (merge on keys), without silently discarding mismatched columns or unmatched rows. | Combine sources safely. |
| **Synthetic data** | Samples new rows from the distributions of existing columns, standalone or as augmentation. | Supports augmentation and testing. |
| **Algorithm recommender** | Rule-based scoring of a fixed candidate list using problem type, class balance, cardinality, outliers and feature-to-row ratio, with reasons and caveats. | Recommendations tied to the selected dataset, no API key needed. |
| **Chat and voice assistant** | Keyword-based intent detection over the profiler, audit trail and recommender; optional browser-native voice via the Web Speech API. | Quick answers about the current dataset. |

---

<!-- ## Preprocessing Pipeline -->

## System Architecture

AutoClean AI is a frontend-backend system. The deterministic preprocessing pipeline is independent of any LLM.

| Layer | Responsibility |
| :--- | :--- |
| **Frontend** | Holds app state (datasets, selected dataset, profile, preview, pipeline config, audit trail). All backend calls go through `api/client.ts`. |
| **API** | FastAPI routes for upload, profiling, preprocessing, combination, synthetic data, audit retrieval, download, recommendations and assistant queries. |
| **Pipeline** | Independent modules for cleaning, outliers, encoding, feature engineering and scaling, run by an orchestrator that enforces the row-count invariant. |
| **Profiling** | Semantic column-type inference, reused by preprocessing, the recommender and the assistant. |
| **Audit** | Structured before/after report for every step. |
| **Session** | In-memory map from dataset ID to dataset record. Derived datasets keep parent information and audit metadata. |
| **Assistant** | Rule-based recommendations and explanations. An `AdvisorBackend` protocol (`llm_advisor.py`) is implemented by a `HeuristicAdvisor`; a real LLM can replace it later without touching the pipeline. |

<!-- TODO: add diagrams once exported, e.g.
### Functional Scope (Use Cases)
<p align="center"><img src="docs/diagrams/use_case_diagram/use_case_diagram.png" alt="Use Case Diagram" width="70%" /></p>

### Activity Diagram
<p align="center"><img src="docs/diagrams/activity_diagram/activity_diagram.png" alt="Activity Diagram" width="70%" /></p>
-->

---

## Tech Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend** | Python 3.11+, FastAPI | Typed, asynchronous API with automatic OpenAPI documentation; same language as the data stack. |
| **Data processing** | pandas, scikit-learn | Mature engines for transformation, imputation, encoding and scaling. |
| **Frontend** | React, TypeScript, Vite | Component-based UI with static typing and fast builds. |
| **UI effects** | CSS, Canvas, Framer Motion | Lightweight visuals without a heavyweight WebGL scene graph. |
| **Data exchange** | JSON (pandas serialization) | Simple contract between frontend and backend. |
| **Voice interface** | Browser Web Speech API | No external service; controls are hidden when the browser lacks support. |
| **Testing** | pytest | Unit, pipeline and invariant tests. |
| **Environment** | Python virtual environment (`backend/.venv`) | Isolated, reproducible backend dependencies. |

---

## Testing

The pytest suite focuses on the correctness of individual operations and on the no-data-loss invariant.

| Category | Scope |
| :--- | :--- |
| **Unit** | Preprocessing and utility functions tested independently (e.g. scaling, cleaning). |
| **Pipeline** | Orchestrator behaviour across multiple stages. |
| **Invariant** | Row-preserving operations must not change the row count (e.g. imputation removes no rows). |
| **Integration** | Backend routes and frontend-backend data flow. |

---

## Known Limitations and Roadmap

| Limitation | Planned Direction |
| :--- | :--- |
| Session store is in-memory and lost on restart. | Persistent database or object storage for datasets. |
| LLM advisor is a heuristic stub. | Real LLM implementation behind the existing `AdvisorBackend` protocol. |
| Recommendations are rule-based. | Validation-driven recommendations using empirical model performance. |
| No benchmarks for latency or memory. | Larger benchmark datasets and formal performance evaluation. |
| Single-user, no authentication. | Authentication, multi-user sessions, persistent audit histories. |
| Limited scalability for large files. | Chunked ingestion, streaming or distributed processing. |

Further planned work: richer visualizations (missing values, distributions, outliers, correlations) and exportable audit reports.

---

## Repository Structure

<details>
<summary><b>📂 Repository Structure</b> (Click to expand)</summary>

```text

├── README.md                          # Project overview and architecture entry point
├── LICENSE
├── Makefile                           # Build and documentation automation
├── mkdocs.yml                         # Documentation site configuration
├── pyproject.toml                     # Python project metadata
├── .github/
│   └── workflows/
│       └── mkdocs.yml                 # CI: build and deploy documentation
├── assets/                            # Docs site assets (icons, stylesheets, logos)
├── backend/                           # FastAPI service and preprocessing pipeline
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                    # Application entry point
│   │   ├── api/                       # HTTP routes
│   │   │   ├── routes_assistant.py
│   │   │   ├── routes_dataset.py
│   │   │   └── routes_pipeline.py
│   │   ├── core/
│   │   │   ├── audit.py               # StepReport / audit trail
│   │   │   └── pipeline/              # Deterministic preprocessing modules
│   │   │       ├── ingestion.py
│   │   │       ├── profiling.py
│   │   │       ├── cleaning.py
│   │   │       ├── outliers.py
│   │   │       ├── encoding.py
│   │   │       ├── feature_engineering.py
│   │   │       ├── scaling.py
│   │   │       ├── combine.py
│   │   │       ├── synthetic.py
│   │   │       ├── orchestrator.py    # Fixed step order + row-count invariant
│   │   │       ├── recommender.py     # Rule-based algorithm recommender
│   │   │       ├── chat_assistant.py  # Keyword-based chat assistant
│   │   │       └── llm_advisor.py     # AdvisorBackend protocol + HeuristicAdvisor
│   │   ├── schemas/                   # Request/response models
│   │   │   ├── assistant.py
│   │   │   └── pipeline.py
│   │   └── services/
│   │       └── session_store.py       # In-memory dataset store
│   └── tests/                         # pytest suite
│       ├── conftest.py
│       ├── test_cleaning.py
│       ├── test_encoding.py
│       ├── test_orchestrator_no_data_loss.py
│       ├── test_outliers.py
│       ├── test_recommender.py
│       └── test_scaling.py
├── frontend/                          # React + TypeScript (Vite) client
│   ├── package.json
│   ├── vite.config.ts
│   ├── public/
│   └── src/
│       ├── App.tsx                    # Application state
│       ├── main.tsx
│       ├── types.ts
│       ├── api/client.ts              # Single point of backend communication
│       ├── components/                # UI components (upload, profile, audit, chat, ...)
│       └── hooks/                     # useTilt, useVoice
├── code/                              # Course-template C++ skeleton (unused by the project)
├── docs/                              # MkDocs sources
│   ├── index.md
│   ├── criteria-for-project-selection.md
│   └── journals/                      # Linked from ../journals
├── journals/                          # Weekly engineering logs, one folder per member
│   ├── 1024160036-Nipun-Mahajan/
│   ├── 1024160043-Ishwinder-Kaur-Ahluwalia/
│   └── 1024160061-Shreshth-Verma/
├── project-proposal/                  # Proposal report (LaTeX source and PDF)
├── project-report-prototype-stage/    # Prototype-stage report (pending)
└── project-report-final/              # Final report (pending)
```
</details>

---

<!--
## Getting Started

### 1. Clone the Repository
```bash
git clone <TODO: repository URL>
cd <TODO: repository name>
```

### 2. Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # TODO: confirm dependency file
# TODO: add the command that starts the FastAPI server
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

### 4. Run Tests
```bash
cd backend
pytest
```
-->

## Academic Context

This project is submitted as part of **UCS503: Software Engineering** at **Thapar Institute of Engineering and Technology (TIET)**, Patiala.

- **Course Instructor**: Prof. Sandeep Kaur
- **Group**: L2 (3P12), B.Tech Third Year, CSE
- **Team Members**:
  - [**Shreshth Verma**](https://github.com/Shreshth1805) (Roll No: `1024160061`) - sverma_be24@thapar.edu
  - [**Nipun Mahajan**](https://github.com/nipunmah) (Roll No: `1024160036`) - nmahajan_be24@thapar.edu
  - [**Ishwinder Kaur**](https://github.com/IshwinderKaur8) (Roll No: `1024160043`) - iahluwalia_be24@thapar.edu

---
