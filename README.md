# AutoClean AI

Automated data preprocessing: upload messy CSV/Excel/JSON data and get back
cleaned, encoded, normalized, model-ready data plus a full audit trail of
every change made — no silent row/column loss.

## Features

- **Ingestion**: CSV/TSV/Excel/JSON, with encoding & delimiter sniffing.
- **Profiling**: per-column type inference, missing %, cardinality, outliers.
- **Cleaning**: type coercion, missing-value imputation, duplicate detection/removal.
- **Outlier handling**: flag (default, non-destructive) / clip / remove.
- **Encoding**: one-hot or label encoding chosen by cardinality.
- **Feature engineering**: datetime decomposition, text length/word count.
- **Scaling**: standard / min-max / robust normalization.
- **Combine datasets**: stack (concat) or join (merge) multiple uploads without dropping mismatched columns or unmatched rows.
- **Synthetic data generation**: sample new rows from each column's distribution, standalone or as augmentation.
- **Audit trail**: every pipeline step reports rows/columns/nulls before & after, plus human-readable warnings — the pipeline aborts rather than silently dropping data if an invariant is violated.
- **LLM-assist stub**: heuristic column-role suggestions and step explanations, structured so a real Claude API call can be swapped in later (`backend/app/core/pipeline/llm_advisor.py`) with no other code changes.
- **Algorithm recommendations**: a rule-based scoring engine (`backend/app/core/pipeline/recommender.py`, no LLM/API key needed) detects the problem type (classification/regression/clustering), auto-detects or accepts a target column, and scores a candidate list of scikit-learn-style algorithms with human-readable reasons/caveats based on the dataset's actual characteristics (size, class balance, cardinality, outliers, feature-to-row ratio).
- **Chat + voice assistant**: a floating chat widget answers free-text questions about whichever dataset is currently selected ("what algorithm should I use?", "is my data clean?", "any outliers?") using the same rule-based engine — fully offline, no API key. Voice input/output uses the browser's native Web Speech API (mic button for speech-to-text, speaker toggle to read replies aloud); both gracefully hide if the browser doesn't support them.
- **Immersive UI**: animated particle-network canvas background, dark glassmorphism panels, and framer-motion transitions/pointer-tilt on cards.

## Project layout

```
backend/   FastAPI + pandas/scikit-learn pipeline (also usable as a standalone library)
frontend/  React + TypeScript UI (Vite)
```

## Running it

**Backend** (needs Python 3.11+). Use a virtual environment so these
dependencies never touch your global/Anaconda `pip` — installing them
globally can silently downgrade unrelated tools you have installed:

```bash
cd backend
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt   # Windows; use .venv/bin/pip on macOS/Linux
./.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

**Frontend**:

```bash
cd frontend
npm install
npm run dev
```

Then open the printed Vite URL (default `http://localhost:5173`). The frontend expects the backend at `http://127.0.0.1:8000` (see `frontend/src/api/client.ts`).

## Tests

```bash
cd backend
./.venv/Scripts/python -m pytest tests/ -v
```
