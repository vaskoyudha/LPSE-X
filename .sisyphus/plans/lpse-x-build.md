# LPSE-X Full Build Plan — Find IT! 2026 Hackathon

## TL;DR

> **Quick Summary**: Build the complete LPSE-X application — an Explainable AI platform for Indonesian procurement fraud detection — implementing 5 core mechanisms (73+12 feature engineering, Leiden cartel detection, Tri-Method AI, Oracle Sandwich 5-layer XAI, auto pre-investigation reports) with React frontend + FastAPI backend, fully offline-capable and runtime-injection-ready for 24h hackathon sprint.
>
> **Deliverables**:
> - Offline-ready data pipeline ingesting 1.1M tenders from opentender.net (OCDS format)
> - Tri-Method AI engine (Isolation Forest + XGBoost + ICW weak labels) with ONNX-exported models
> - Leiden-based graph cartel detection module
> - Oracle Sandwich 5-layer XAI (SHAP + DiCE + Anchors + Leiden graph + Benford's Law)
> - React dashboard with Plotly visualizations + Folium geographic heatmaps
> - FastAPI REST API with runtime injection endpoint (`PUT /api/config/inject`)
> - Auto pre-investigation report generator (IIA 2025 format)
> - Portable offline bundle (single folder, runs from USB, no internet required)
>
> **Estimated Effort**: XL (4-5 person team, multi-week Stage 2 + 24h Stage 3)
> **Parallel Execution**: YES — 6 waves
> **Critical Path**: T1 (scaffold) → T3 (data pipeline) → T6 (feature eng) → T8 (ML models) → T11 (ONNX) → T13 (XAI) → T17 (dashboard integration) → T20 (offline bundle) → Final Verification


## Context

### Original Request
Build the complete LPSE-X application for Find IT! 2026 Hackathon at UGM, Track C: "The Explainable Oracle" (Predictive Analytics / XAI). The proposal (UPGRADE 3, 340 lines, scored 9.4/10) is finalized. This plan covers Stage 2 (pre-hackathon development) and Stage 3 (24h on-site sprint readiness).

### Interview Summary
**Key Discussions**:
- **Scope**: Full build — data pipeline, ML models, XAI layers, React dashboard, FastAPI API, runtime injection, offline packaging
- **Frontend**: React + FastAPI (user explicitly chose over Streamlit for production quality and flexibility)
- **Team**: 4-5 people — enables parallel task assignment across waves
- **Deadlines**: User said "just focusing create the plan" — no specific dates given. Stage 2 is pre-hackathon, Stage 3 is 24h on-site sprint
- **Localhost-only**: No cloud server. Demo runs on participant's laptop
- **No retraining during 24h**: Model must be production-ready from Stage 2
- **Runtime injection mandatory**: Hardcoded apps get disqualified

**Research Findings**:
- opentender.net is PRIMARY data source (1,106,096 tenders, OCDS format, bulk export via REST API)
- Cardinal library (OCP) auto-computes 73 red flags from OCDS — massive time saver
- ICW `total_score` on 1.1M tenders = usable weak labels without manual annotation
- ONNX Runtime for inference ensures <200ms/prediction on CPU
- 4 XLSX files already downloaded from LKPP CKAN to `C:\Hackthon\`
- pyproc needs local testing (script at `C:\Hackthon\test_pyproc_local.py`)
- Complete research synthesis at `C:\Hackthon\DEEP_RESEARCH_SYNTHESIS.md` (474 lines, 21 papers, 6 tools)

### Metis Review
**Identified Gaps** (all addressed in this plan):
- **Offline packaging not planned**: Added Task 20 — portable bundle with FastAPI serving React static files, auto port selection, AppDir convention
- **ONNX parity testing missing**: Added parity test (native vs ONNX predictions) as acceptance criteria in Task 11
- **XAI latency SLA undefined**: Added per-layer time budgets — SHAP <2s, DiCE cached/async, Anchors <5s with seed fixing
- **Leiden reproducibility risk**: Added seed + version logging requirement, determinism test in Task 7
- **Benford applicability caveat**: Added pre-check gating — layer returns "not_applicable" when data doesn't span orders of magnitude
- **DiCE real-time scope creep**: Locked to cached templates with explicit timeout; NOT blocking main inference
- **Port conflict on demo laptop**: Auto-detect free port, expose to frontend config
- **Native dependency compilation**: Added leidenalg/igraph pre-compilation check in Wave 1 scaffold
- **Map tiles offline**: Folium locked to offline-safe mode (bundled tiles or disabled)


## Work Objectives

### Core Objective
Build a fully-functional, offline-capable LPSE-X application that implements ALL 5 core mechanisms from the proposal, passes all competition scoring criteria, and is ready for the 24h on-site sprint with zero retraining required.

### Concrete Deliverables
- `lpse-x/` — Complete application folder (portable, runs offline)
- `lpse-x/backend/` — FastAPI server with ML inference, XAI, graph analysis, report generation
- `lpse-x/frontend/` — React SPA with Plotly charts, Folium maps, cartel graph viz
- `lpse-x/models/` — ONNX-exported XGBoost + Isolation Forest + preprocessing pipeline
- `lpse-x/data/` — SQLite DB with ingested tender data, precomputed features, graph cache
- `lpse-x/config/runtime_config.yaml` — Externalized runtime parameters
- `lpse-x/reports/` — Generated pre-investigation reports (IIA 2025 format)
- `lpse-x/evidence/` — QA evidence screenshots, terminal output, API responses

### Definition of Done
- [ ] `python -m lpse_x.main` starts server on auto-detected port, serves React frontend + API
- [ ] Runtime injection via `PUT /api/config/inject` changes behavior without restart
- [ ] All 5 XAI layers produce output for any flagged tender within latency SLA
- [ ] Tri-Method AI returns 4-level risk classification with ensemble disagreement protocol
- [ ] Graph analysis detects and visualizes cartel communities
- [ ] Pre-investigation report generates IIA-format narrative in Bahasa Indonesia
- [ ] Entire app runs offline from a single folder on a clean laptop (Wi-Fi disabled)
- [ ] All tests pass: `pytest tests/ -q` (unit + integration + parity + determinism)

### Must Have
- 73 OCP red flags computed via Cardinal library from OCDS data
- 12 custom forensic behavioral ML features (as specified in proposal Table)
- Tri-Method AI: Isolation Forest + XGBoost + ICW weak labels with disagreement protocol
- Oracle Sandwich 5-layer XAI: SHAP + DiCE + Anchors + Leiden graph + Benford's Law
- Runtime injection via YAML config + `PUT /api/config/inject` endpoint
- Pydantic validation for all injected parameters (reject invalid, apply valid instantly)
- `custom_params` wildcard dictionary for unexpected parameters
- 4-level risk classification: Aman / Perlu Pantauan / Risiko Tinggi / Risiko Kritis
- ONNX-exported models for <200ms inference on CPU
- SQLite database (zero-config, localhost-ready)
- Offline-capable: zero external API calls, zero cloud dependencies
- MVP scope: Construction sector, 5 LPSE instances, 2022-2024

### Must NOT Have (Guardrails)
- ❌ NO calls to external APIs (OpenAI, Google AI, etc.) — fully sovereign
- ❌ NO cloud server dependencies — localhost only
- ❌ NO model retraining during Stage 3 — inference only
- ❌ NO hardcoded parameters — everything via runtime_config.yaml
- ❌ NO Streamlit — React frontend only
- ❌ NO fixed port numbers — auto-detect free port
- ❌ NO temp/user-profile file paths — all artifacts under AppDir
- ❌ NO blocking DiCE computation on main inference endpoint — use cached/async
- ❌ NO Benford flags when pre-check fails — return "not_applicable" with reason
- ❌ NO random seeds without logging — all stochastic processes must be reproducible
- ❌ NO "as any" / "@ts-ignore" / empty catches in frontend code
- ❌ NO console.log in production — use structured logging
- ❌ NO excessive comments / over-abstraction / AI slop patterns
- ❌ NO online map tiles without offline fallback


## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.
> Acceptance criteria requiring "user manually tests/confirms" are FORBIDDEN.

### Test Decision
- **Infrastructure exists**: NO (greenfield project)
- **Automated tests**: YES (Tests-after — practical for hackathon pace)
- **Framework**: pytest (backend) + vitest (frontend React)
- **Strategy**: Each task includes specific test files. Tests verify behavior, not implementation details.

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Frontend/UI**: Use Playwright — navigate, interact, assert DOM, screenshot
- **API/Backend**: Use Bash (curl/httpie) — send requests, assert status + response fields
- **ML/Data**: Use Bash (python -c / pytest) — import modules, call functions, compare output
- **Offline**: Use network-disabled test — verify no outbound connections

---

## Execution Strategy

### Parallel Execution Waves

> Maximize throughput by grouping independent tasks into parallel waves.
> Each wave completes before the next begins.
> Team of 4-5 people enables high parallelism.

```
Wave 1 (Foundation — scaffolding + types + config):
├── Task 1: Project scaffolding + monorepo structure + dependency install [quick]
├── Task 2: TypeScript types + Pydantic schemas + shared contracts [quick]
├── Task 3: Data pipeline — opentender.net ingestion + SQLite storage [deep]
├── Task 4: Runtime config system (YAML + Pydantic + injection endpoint) [quick]
└── Task 5: React app scaffold + routing + design system tokens [visual-engineering]

Wave 2 (Core Engine — features + models + graph):
├── Task 6: Feature engineering — 73 OCP red flags (Cardinal) + 12 custom features [deep]
├── Task 7: Graph construction + Leiden cartel detection module [deep]
├── Task 8: Tri-Method AI — IF + XGBoost + ICW weak labels + disagreement protocol [ultrabrain]
└── Task 9: Benford's Law analysis module with applicability gating [unspecified-high]

Wave 3 (XAI + Reports + ONNX):
├── Task 10: SHAP + Anchors XAI layer (global + rules) [deep]
├── Task 11: ONNX export pipeline + parity tests [deep]
├── Task 12: DiCE counterfactual explanations (cached/async) [unspecified-high]
├── Task 13: Auto pre-investigation report generator (IIA 2025, NLG) [unspecified-high]
└── Task 14: API endpoints — inference, XAI, graph, reports [unspecified-high]

Wave 4 (Frontend — dashboard + visualization):
├── Task 15: Dashboard layout + risk overview + tender table [visual-engineering]
├── Task 16: SHAP/XAI visualization components + DiCE display [visual-engineering]
├── Task 17: Cartel graph visualization (NetworkX → D3/vis.js) [visual-engineering]
├── Task 18: Geographic heatmap (Folium/offline tiles) [visual-engineering]
└── Task 19: Report viewer + PDF export component [visual-engineering]

Wave 5 (Integration + Packaging):
├── Task 20: Offline portable bundle (FastAPI serves React, auto port, AppDir) [deep]
├── Task 21: End-to-end integration tests (full pipeline) [deep]
├── Task 22: Runtime injection stress test (all parameter combinations) [unspecified-high]
└── Task 23: Stage 3 sprint playbook + demo script [writing]

Wave FINAL (Independent review — 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA — Playwright + curl (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: T1 → T3 → T6 → T8 → T11 → T14 → T17 → T20 → T21 → F1-F4
Parallel Speedup: ~65% faster than sequential
Max Concurrent: 5 (Waves 1, 2, 4)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| T1 | — | T2-T5, all | 1 |
| T2 | T1 | T6-T14 | 1 |
| T3 | T1 | T6, T7, T8, T9 | 1 |
| T4 | T1 | T14, T20, T22 | 1 |
| T5 | T1 | T15-T19 | 1 |
| T6 | T2, T3 | T8, T9, T10 | 2 |
| T7 | T2, T3 | T10, T17 | 2 |
| T8 | T2, T6 | T10, T11, T12, T14 | 2 |
| T9 | T6 | T10, T14 | 2 |
| T10 | T8, T7 | T14, T16 | 3 |
| T11 | T8 | T14, T20 | 3 |
| T12 | T8 | T14, T16 | 3 |
| T13 | T2, T6 | T14, T19 | 3 |
| T14 | T4, T10, T11, T12, T13 | T15-T19, T20 | 3 |
| T15 | T5, T14 | T20 | 4 |
| T16 | T5, T10, T12, T14 | T20 | 4 |
| T17 | T5, T7, T14 | T20 | 4 |
| T18 | T5, T14 | T20 | 4 |
| T19 | T5, T13, T14 | T20 | 4 |
| T20 | T14, T15-T19 | T21 | 5 |
| T21 | T20 | F1-F4 | 5 |
| T22 | T4, T14, T20 | F1-F4 | 5 |
| T23 | T20, T21 | F1-F4 | 5 |
| F1-F4 | T21, T22, T23 | — | FINAL |

### Agent Dispatch Summary

| Wave | Tasks | Categories |
|------|-------|-----------|
| 1 | 5 | T1→`quick`, T2→`quick`, T3→`deep`, T4→`quick`, T5→`visual-engineering` |
| 2 | 4 | T6→`deep`, T7→`deep`, T8→`ultrabrain`, T9→`unspecified-high` |
| 3 | 5 | T10→`deep`, T11→`deep`, T12→`unspecified-high`, T13→`unspecified-high`, T14→`unspecified-high` |
| 4 | 5 | T15-T19→`visual-engineering` |
| 5 | 4 | T20→`deep`, T21→`deep`, T22→`unspecified-high`, T23→`writing` |
| FINAL | 4 | F1→`oracle`, F2→`unspecified-high`, F3→`unspecified-high`, F4→`deep` |

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.
> **A task WITHOUT QA Scenarios is INCOMPLETE. No exceptions.**

 [x] 1. Project Scaffolding + Monorepo Structure + Dependency Install

  **What to do**:
  - Create monorepo structure: `lpse-x/backend/`, `lpse-x/frontend/`, `lpse-x/models/`, `lpse-x/data/`, `lpse-x/config/`, `lpse-x/reports/`, `lpse-x/tests/`
  - Initialize Python backend: `pyproject.toml` with pinned dependencies (fastapi, uvicorn, xgboost, scikit-learn, onnxruntime, shap, dice-ml, alibi, benford_py, leidenalg, igraph, networkx, cardinal, pyproc, pydantic, pyyaml, plotly, folium, jinja2, openpyxl, httpx, aiosqlite)
  - Initialize React frontend: `package.json` with Vite + React + TypeScript + Plotly.js + react-force-graph (for D3 graph viz) + Leaflet (for maps)
  - Verify critical native deps compile: `python -c "import leidenalg; import igraph; print('OK')"` — if fails, document workaround
  - Create `lpse-x/config/runtime_config.yaml` with default MVP parameters
  - Create `.env.example` with all environment variables documented
  - Create `Makefile` or `scripts/` with: `start`, `test`, `build-frontend`, `bundle`
  - Pin ALL dependency versions (no floating ranges) for reproducibility
  - Create `lpse-x/__init__.py` and `lpse-x/main.py` (entry point stub)

  **Must NOT do**:
  - Do NOT install Streamlit
  - Do NOT use floating version ranges (e.g., `>=1.0` — use `==1.0.0`)
  - Do NOT create cloud deployment files (Dockerfile, docker-compose, etc.)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Scaffolding is mechanical — create dirs, init files, install deps
  - **Skills**: []
    - No special skills needed for project setup

  **Parallelization**:
  - **Can Run In Parallel**: NO — this is Wave 1 foundation, must complete first
  - **Parallel Group**: Wave 1 (starts immediately)
  - **Blocks**: Tasks 2, 3, 4, 5, and all subsequent tasks
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `C:\Users\vasco\Downloads\UPGRADE 3` lines 155-168 — Technology table specifying exact stack
  - `C:\Hackthon\DEEP_RESEARCH_SYNTHESIS.md` lines 130-141 — Tools & libraries with install commands

  **External References**:
  - Cardinal: https://github.com/open-contracting/cardinal — verify install command
  - leidenalg: https://pypi.org/project/leidenalg/ — may need igraph C library
  - dice-ml: https://pypi.org/project/dice-ml/ — Microsoft DiCE for counterfactuals
  - alibi: https://pypi.org/project/alibi/ — Seldon Anchors for rule explanations
  - benford_py: https://pypi.org/project/benford_py/ — Benford's Law analysis

  **WHY Each Reference Matters**:
  - Proposal tech table is the CONTRACT — every library listed must be installed
  - Research synthesis has verified install commands — use them directly
  - leidenalg has C dependency (igraph) that may fail on Windows — check early

  **Acceptance Criteria**:
  - [ ] `cd lpse-x && python -c "import fastapi, xgboost, shap, dice_ml, alibi, benford, leidenalg, igraph, networkx, onnxruntime; print('ALL OK')"` → success
  - [ ] `cd lpse-x/frontend && npm install && npm run build` → success
  - [ ] Directory structure matches: backend/, frontend/, models/, data/, config/, reports/, tests/
  - [ ] `runtime_config.yaml` exists with documented default parameters
  - [ ] All dependency versions pinned in pyproject.toml and package.json

  **QA Scenarios:**

  ```
  Scenario: All Python dependencies import successfully
    Tool: Bash
    Preconditions: Fresh virtual environment created
    Steps:
      1. Run `cd lpse-x && python -c "import fastapi, xgboost, shap, dice_ml, alibi, benford, leidenalg, igraph, networkx, onnxruntime, cardinal; print('ALL OK')"`
      2. Check exit code is 0
      3. Verify output contains 'ALL OK'
    Expected Result: All imports succeed, exit code 0
    Failure Indicators: ImportError, ModuleNotFoundError, or C compilation errors
    Evidence: .sisyphus/evidence/task-1-python-deps.txt

  Scenario: React frontend builds successfully
    Tool: Bash
    Preconditions: Node.js installed
    Steps:
      1. Run `cd lpse-x/frontend && npm install`
      2. Run `npm run build`
      3. Verify `dist/` folder created with index.html
    Expected Result: Build completes with zero errors, dist/index.html exists
    Failure Indicators: npm ERR!, TypeScript errors, missing modules
    Evidence: .sisyphus/evidence/task-1-react-build.txt

  Scenario: leidenalg native dependency works (Windows compatibility)
    Tool: Bash
    Preconditions: Python venv active
    Steps:
      1. Run `python -c "import leidenalg; import igraph; G = igraph.Graph.Famous('Petersen'); part = leidenalg.find_partition(G, leidenalg.ModularityVertexPartition); print(f'Communities: {len(part)}')"`
      2. Verify no segfault or DLL errors
    Expected Result: Prints number of communities, no errors
    Failure Indicators: DLL load failed, segfault, ImportError
    Evidence: .sisyphus/evidence/task-1-leidenalg-check.txt
  ```

  **Commit**: YES
  - Message: `feat(scaffold): initialize LPSE-X monorepo with all dependencies`
  - Files: `lpse-x/`, `pyproject.toml`, `package.json`, `Makefile`
  - Pre-commit: `python -c "import fastapi; print('ok')"`

- [ ] 2. TypeScript Types + Pydantic Schemas + Shared Contracts

  **What to do**:
  - Define Pydantic models in `backend/schemas/`:
    - `TenderRecord` — full tender data from OCDS (55+ fields)
    - `RiskPrediction` — risk_level (enum: Aman/Perlu Pantauan/Risiko Tinggi/Risiko Kritis), score (float 0-1), model_scores (dict per model), disagreement_flag (bool)
    - `XAIExplanation` — shap_values, dice_counterfactuals, anchor_rules, leiden_community, benford_analysis
    - `GraphCommunity` — community_id, members (list of vendor IDs), edge_weights, tender_ids
    - `RuntimeConfig` — procurement_scope, institution_filter, risk_threshold, year_range, anomaly_method, output_format, custom_params (dict)
    - `InvestigationReport` — tender_id, risk_level, findings (list), recommendations, template_version
    - `InjectionRequest` / `InjectionResponse` — for PUT /api/config/inject
  - Define TypeScript interfaces in `frontend/src/types/`:
    - Mirror all Pydantic models for frontend consumption
    - `api.ts` — API response shapes, pagination, error responses
  - Create `backend/schemas/__init__.py` barrel export
  - Ensure Pydantic models use `model_json_schema()` for OpenAPI generation

  **Must NOT do**:
  - Do NOT use `Any` type — all fields must be explicitly typed
  - Do NOT create business logic — schemas only

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Type definitions are straightforward data modeling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after T1 completes)
  - **Parallel Group**: Wave 1 (with T3, T4, T5)
  - **Blocks**: Tasks 6-14 (all core engine and API tasks need these types)
  - **Blocked By**: Task 1 (needs project structure)

  **References**:

  **Pattern References**:
  - `C:\Users\vasco\Downloads\UPGRADE 3` lines 69-76 — Output descriptions (risk scores, XAI, graphs, reports)
  - `C:\Users\vasco\Downloads\UPGRADE 3` lines 170-179 — Runtime config parameters (exact list of injectable variables)
  - `C:\Users\vasco\Downloads\UPGRADE 3` lines 110-124 — 12 forensic feature table (field names)

  **API/Type References**:
  - opentender.net API: `GET /api/tender/{id}/` returns 55+ fields — map to TenderRecord
  - ICW PFA scoring: 7 indicators with score ranges — map to weak label schema

  **External References**:
  - Pydantic v2 docs: https://docs.pydantic.dev/latest/ — model_json_schema for OpenAPI
  - OCDS schema: https://standard.open-contracting.org/latest/en/schema/ — tender record fields

  **WHY Each Reference Matters**:
  - Proposal lines 69-76 define EXACT outputs — schemas must match these 5 output types
  - Lines 170-179 are the runtime injection contract — RuntimeConfig must support ALL listed parameters
  - OCDS schema ensures TenderRecord matches the data format from opentender.net

  **Acceptance Criteria**:
  - [ ] All Pydantic models validate with sample data: `python -c "from backend.schemas import *; print('OK')"`
  - [ ] TypeScript types compile: `cd frontend && npx tsc --noEmit`
  - [ ] RuntimeConfig includes all 7 injectable parameters from proposal (procurement_scope, institution_filter, risk_threshold, year_range, anomaly_method, output_format, custom_params)
  - [ ] No `Any` types used anywhere

  **QA Scenarios:**

  ```
  Scenario: Pydantic models validate sample tender data
    Tool: Bash
    Preconditions: Task 1 complete, venv active
    Steps:
      1. Run `python -c "
        from backend.schemas import TenderRecord, RiskPrediction, RuntimeConfig
        t = TenderRecord(tender_id='ID-2024-0847', buyer='Kemenkeu', amount=1000000000, hps=1100000000, method='open', year=2024)
        r = RiskPrediction(risk_level='Risiko Tinggi', score=0.91, model_scores={'xgboost': 0.93, 'iforest': 0.88, 'icw': 0.92}, disagreement_flag=False)
        c = RuntimeConfig(procurement_scope='konstruksi', risk_threshold=0.7, year_range=[2022, 2024])
        print(f'Tender: {t.tender_id}, Risk: {r.risk_level}, Config: {c.procurement_scope}')
      "`
      2. Verify output shows all three models instantiated correctly
    Expected Result: Models instantiate without ValidationError, fields populated
    Failure Indicators: ValidationError, ImportError, missing fields
    Evidence: .sisyphus/evidence/task-2-pydantic-validation.txt

  Scenario: RuntimeConfig handles custom_params wildcard
    Tool: Bash
    Preconditions: Schemas module available
    Steps:
      1. Run `python -c "
        from backend.schemas import RuntimeConfig
        c = RuntimeConfig(custom_params={'secret_judge_param': 42, 'extra_filter': 'DKI Jakarta'})
        print(f'Custom params: {c.custom_params}')
        assert 'secret_judge_param' in c.custom_params
      "`
    Expected Result: custom_params accepts arbitrary key-value pairs without schema errors
    Failure Indicators: ValidationError on unknown keys
    Evidence: .sisyphus/evidence/task-2-custom-params.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(types): Pydantic schemas + TypeScript interfaces for all contracts`
  - Files: `backend/schemas/`, `frontend/src/types/`

- [ ] 3. Data Pipeline — opentender.net Ingestion + SQLite Storage

  **What to do**:
  - Create `backend/data/ingestion.py`:
    - Bulk download from opentender.net: `GET /api/tender/export/` and `/api/tender/export_hhi/` and `/api/tender/export-ocds-batch/`
    - Filter: Construction sector (`procurement_scope=konstruksi`), 5 LPSE instances, 2022-2024
    - Parse OCDS JSON responses into TenderRecord Pydantic models
    - Handle pagination (1.1M records — use bulk export, not paginated API)
    - Rate limiting: 1 request/2 seconds with exponential backoff
    - Progress logging with estimated completion time
  - Create `backend/data/storage.py`:
    - SQLite database at `data/lpse_x.db`
    - Tables: `tenders` (raw OCDS data), `features` (computed features), `predictions` (model outputs), `communities` (Leiden results), `reports` (generated reports)
    - Use aiosqlite for async access from FastAPI
    - Schema migrations via simple version table
  - Create `backend/data/lkpp_loader.py`:
    - Load 4 XLSX files already at `C:\Hackthon\lkpp_*.xlsx` into SQLite
    - Parse: tender_winners, lpse_data, monitoring, sirup planning data
  - Create `backend/data/pyproc_loader.py`:
    - Integrate pyproc for real-time LPSE data (with fallback if LPSE hosts unreachable)
    - Rate limit: 1 req/2s, cache to SQLite
  - NPWP anonymization: Hash NPWP values for privacy (store hash + last 4 digits only)
  - Schema validation: Validate all ingested data against OCDS schema before storage
  - Offline mode: After initial ingestion, all queries served from local SQLite

  **Must NOT do**:
  - Do NOT store raw NPWP (hash only for privacy)
  - Do NOT depend on network after initial ingestion
  - Do NOT use ORM (raw SQL + aiosqlite for speed and simplicity)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Data pipeline with multiple sources, rate limiting, schema validation, async storage — requires careful orchestration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after T1 completes)
  - **Parallel Group**: Wave 1 (with T2, T4, T5)
  - **Blocks**: Tasks 6, 7, 8, 9 (all engine tasks need data)
  - **Blocked By**: Task 1 (needs dependencies installed)

  **References**:

  **Pattern References**:
  - `C:\Users\vasco\Downloads\UPGRADE 3` lines 194-205 — Data source table with exact URLs and methods
  - `C:\Hackthon\DEEP_RESEARCH_SYNTHESIS.md` lines 171-193 — opentender.net complete data access picture
  - `C:\Hackthon\test_pyproc_local.py` — pyproc integration script (91 lines, working example)

  **API/Type References**:
  - opentender.net REST API:
    - `GET https://opentender.net/api/tender/?page=1` → paginated tenders
    - `GET https://opentender.net/api/tender/{id}/` → full tender detail (55+ fields)
    - `GET https://pro.opentender.net/api/tender/export/` → bulk export
    - `GET https://pro.opentender.net/api/tender/export_hhi/` → HHI export
    - `GET https://pro.opentender.net/api/tender/export-ocds-batch/` → OCDS format bulk
  - LKPP CKAN API: `https://data.lkpp.go.id/api/3/action/package_list`

  **External References**:
  - OCDS schema: https://standard.open-contracting.org/latest/en/schema/
  - aiosqlite: https://pypi.org/project/aiosqlite/
  - Kingfisher Collect (alternative OCDS bulk download): https://kingfisher-collect.readthedocs.io

  **WHY Each Reference Matters**:
  - Proposal data table is the CONTRACT for which sources to ingest
  - Research synthesis confirmed exact API endpoints and their response formats
  - pyproc script already tested — adapt its patterns for the data loader
  - OCDS schema needed for Cardinal library compatibility (next task)

  **Acceptance Criteria**:
  - [ ] SQLite DB created at `data/lpse_x.db` with all 5 tables
  - [ ] At minimum 10,000 tender records ingested (for development; full 1.1M for production)
  - [ ] LKPP XLSX files loaded into SQLite
  - [ ] NPWP values hashed (no raw NPWP in database)
  - [ ] Offline query works: `python -c "import sqlite3; conn = sqlite3.connect('data/lpse_x.db'); print(conn.execute('SELECT COUNT(*) FROM tenders').fetchone())"` → returns count > 0

  **QA Scenarios:**

  ```
  Scenario: Bulk data ingestion from opentender.net
    Tool: Bash
    Preconditions: Network available, opentender.net reachable
    Steps:
      1. Run `python -m backend.data.ingestion --scope konstruksi --years 2022-2024 --limit 10000`
      2. Check SQLite DB: `python -c "import sqlite3; c=sqlite3.connect('data/lpse_x.db'); print(c.execute('SELECT COUNT(*) FROM tenders').fetchone()[0])"` 
      3. Verify count >= 10000
      4. Check OCDS fields present: `python -c "import sqlite3; c=sqlite3.connect('data/lpse_x.db'); row=c.execute('SELECT * FROM tenders LIMIT 1').fetchone(); print(len(row))"` — expect 55+ columns
    Expected Result: 10,000+ records in tenders table with 55+ fields each
    Failure Indicators: Network timeout, JSON parse error, schema mismatch, count < 10000
    Evidence: .sisyphus/evidence/task-3-ingestion-count.txt

  Scenario: NPWP anonymization enforced
    Tool: Bash
    Preconditions: Data ingested
    Steps:
      1. Run `python -c "import sqlite3; c=sqlite3.connect('data/lpse_x.db'); rows=c.execute('SELECT npwp_hash FROM tenders LIMIT 5').fetchall(); print(rows)"` 
      2. Verify all values are hex hashes (64 chars for SHA-256), not raw NPWP format (XX.XXX.XXX.X-XXX.XXX)
    Expected Result: All NPWP values are SHA-256 hashes, no raw format found
    Failure Indicators: Values matching NPWP format (dots and dashes pattern)
    Evidence: .sisyphus/evidence/task-3-npwp-anonymized.txt

  Scenario: Offline data access (no network required after ingestion)
    Tool: Bash
    Preconditions: Data already ingested to SQLite
    Steps:
      1. Run `python -c "import sqlite3; c=sqlite3.connect('data/lpse_x.db'); results=c.execute('SELECT tender_id, buyer, amount FROM tenders WHERE year=2023 LIMIT 5').fetchall(); print(results)"` 
      2. Verify results returned without network access
    Expected Result: Query returns data from local SQLite, no HTTP calls made
    Failure Indicators: Network error, empty results, connection timeout
    Evidence: .sisyphus/evidence/task-3-offline-query.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(data): opentender.net ingestion pipeline + SQLite storage + NPWP anonymization`
  - Files: `backend/data/`, `data/lpse_x.db`

- [ ] 4. Runtime Config System (YAML + Pydantic + Injection Endpoint)

  **What to do**:
  - Create `backend/config/runtime.py`:
    - Load `runtime_config.yaml` at startup
    - Pydantic model `RuntimeConfig` with all 7 injectable parameters:
      - `procurement_scope`: str = 'konstruksi' (enum: konstruksi/barang/jasa_konsultansi/jasa_lainnya)
      - `institution_filter`: Optional[list[str]] = ['Kemenkeu', 'Kemen-PUPR', 'Pemprov DKI Jakarta', 'Kemenkes', 'Pemprov Sumbar']
      - `risk_threshold`: float = 0.7 (range: 0.0-1.0)
      - `year_range`: tuple[int, int] = (2022, 2024)
      - `anomaly_method`: str = 'ensemble' (enum: isolation_forest/xgboost/ensemble)
      - `output_format`: str = 'dashboard' (enum: dashboard/api_json/audit_report)
      - `custom_params`: dict[str, Any] = {} — wildcard for judge's surprise parameters
    - Validation: Pydantic validates all fields; invalid values rejected with descriptive errors
    - Thread-safe singleton: Config accessible from all modules via `get_config()`
  - Create `backend/config/injection.py`:
    - FastAPI router: `PUT /api/config/inject`
    - Accepts partial updates (only changed fields)
    - Validates via Pydantic before applying
    - Returns: old values, new values, validation errors (if any)
    - Applies instantly — no server restart, no model retraining
    - Logs every injection with timestamp for audit trail
  - Create `config/runtime_config.yaml`:
    - Default values for MVP scope
    - Comments explaining each parameter
    - Example custom_params section

  **Must NOT do**:
  - Do NOT hardcode any parameter that should be configurable
  - Do NOT require server restart for config changes
  - Do NOT accept `custom_params` without logging them

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Config system is well-defined — YAML loading + Pydantic validation + one FastAPI endpoint
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after T1 completes)
  - **Parallel Group**: Wave 1 (with T2, T3, T5)
  - **Blocks**: Tasks 14, 20, 22 (API integration, bundle, injection stress test)
  - **Blocked By**: Task 1 (needs FastAPI installed)

  **References**:

  **Pattern References**:
  - `C:\Users\vasco\Downloads\UPGRADE 3` lines 170-179 — EXACT list of injectable parameters (this is the contract)
  - `C:\Hackthon\DEEP_RESEARCH_SYNTHESIS.md` lines 314-362 — Runtime Variable Strategy with code examples

  **External References**:
  - Pydantic Settings Management: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
  - PyYAML: https://pypi.org/project/PyYAML/

  **WHY Each Reference Matters**:
  - Proposal lines 170-179 are THE contract — every parameter must be implemented exactly
  - Research synthesis has sample implementation code for RuntimeConfig class
  - Competition rules MANDATE this: "Aplikasi Anda WAJIB mampu menerima dan memproses variabel/logika dadakan"

  **Acceptance Criteria**:
  - [ ] `runtime_config.yaml` loads correctly with all 7 parameters
  - [ ] `PUT /api/config/inject` accepts partial updates and returns old/new values
  - [ ] Invalid values rejected: `curl -X PUT ... -d '{"risk_threshold": 2.0}'` → 422 with descriptive error
  - [ ] `custom_params` accepts arbitrary keys: `curl -X PUT ... -d '{"custom_params": {"judge_secret": 42}}'` → 200 OK
  - [ ] Config changes apply instantly without restart

  **QA Scenarios:**

  ```
  Scenario: Runtime injection via API changes active config
    Tool: Bash (curl)
    Preconditions: FastAPI server running on port {port}
    Steps:
      1. GET current config: `curl http://localhost:{port}/api/config` → note risk_threshold value
      2. PUT injection: `curl -X PUT http://localhost:{port}/api/config/inject -H 'Content-Type: application/json' -d '{"risk_threshold": 0.9, "institution_filter": ["Kemenkeu"]}'`
      3. Assert response status 200
      4. Assert response body contains old_values and new_values
      5. GET config again: `curl http://localhost:{port}/api/config` → verify risk_threshold=0.9
    Expected Result: Config updated instantly, response shows old=0.7 new=0.9
    Failure Indicators: 500 error, config not updated, server restart required
    Evidence: .sisyphus/evidence/task-4-injection-success.txt

  Scenario: Invalid injection rejected with descriptive error
    Tool: Bash (curl)
    Preconditions: FastAPI server running
    Steps:
      1. `curl -X PUT http://localhost:{port}/api/config/inject -H 'Content-Type: application/json' -d '{"risk_threshold": 2.0}'`
      2. Assert response status 422
      3. Assert response body contains validation error mentioning range 0.0-1.0
    Expected Result: 422 status with clear error: "risk_threshold must be between 0.0 and 1.0"
    Failure Indicators: 200 (accepted invalid), 500 (crash), vague error message
    Evidence: .sisyphus/evidence/task-4-injection-validation.txt

  Scenario: custom_params wildcard accepts unexpected judge parameters
    Tool: Bash (curl)
    Preconditions: FastAPI server running
    Steps:
      1. `curl -X PUT http://localhost:{port}/api/config/inject -H 'Content-Type: application/json' -d '{"custom_params": {"secret_province": "Jawa Barat", "penalty_multiplier": 1.5, "enable_extra_check": true}}'`
      2. Assert response status 200
      3. GET config: verify custom_params contains all 3 keys
    Expected Result: All arbitrary params accepted and stored, accessible via get_config().custom_params
    Failure Indicators: Rejected as unknown fields, schema validation error
    Evidence: .sisyphus/evidence/task-4-custom-params.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(config): runtime injection system with YAML + Pydantic + PUT endpoint`
  - Files: `backend/config/`, `config/runtime_config.yaml`
---

- [ ] 5. React App Scaffold + Routing + Design System Tokens

  **What to do**:
  - Initialize Vite + React + TypeScript project in `frontend/`
  - Install core deps: `react-router-dom`, `tailwindcss`, `plotly.js`, `react-plotly.js`, `@tanstack/react-query`
  - Configure Tailwind with design system tokens: risk colors (aman=#22c55e, pantauan=#f59e0b, tinggi=#ef4444, kritis=#7c2d12)
  - Create 6 route shells: `/` (Dashboard), `/tender/:id` (TenderDetail), `/graph` (CartelGraph), `/map` (RiskMap), `/reports` (Reports), `/config` (ConfigPanel)
  - Create `frontend/src/api/client.ts` with configurable baseURL targeting FastAPI backend
  - Create layout skeleton: sidebar navigation + header + main content area
  - Configure Vite proxy to forward `/api/*` to FastAPI backend during dev
  - `npm run build` must produce `frontend/dist/` with zero errors

  **Must NOT do**:
  - Do NOT implement actual data fetching, only API client shell
  - Do NOT install Streamlit
  - Do NOT use CSS-in-JS, Tailwind only
  - Do NOT create complex components, route shells with placeholder text only

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Frontend scaffolding with design tokens, routing, layout
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Design system tokens, layout composition, Tailwind config

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1-4)
  - **Blocks**: Tasks 15, 16, 17, 18, 19
  - **Blocked By**: Task 1

  **References**:
  - `UPGRADE 3:155-168` Tech stack table confirming React + Plotly + Folium + FastAPI
  - `UPGRADE 3:71-75` 5 output types that map to 6 routes
  - `backend/models/schemas.py` (Task 2) Response types for API client
  - Vite docs: https://vitejs.dev/guide/
  - React Router v6: https://reactrouter.com/en/main
  - Tailwind CSS: https://tailwindcss.com/docs/configuration

  **Acceptance Criteria**:
  - [ ] `frontend/` exists with `package.json`, `vite.config.ts`, `tailwind.config.ts`
  - [ ] `npm run build` zero errors, produces `frontend/dist/`
  - [ ] `npm run dev` starts dev server
  - [ ] All 6 routes render placeholder content
  - [ ] Tailwind tokens include 4 risk-level colors
  - [ ] API client module exports typed functions
  - [ ] Vite proxy forwards `/api/*` to `http://localhost:8000`

  **QA Scenarios**:
  ```
  Scenario: React app builds and serves all routes
    Tool: Bash
    Preconditions: Node.js installed, frontend/ exists
    Steps:
      1. `npm run build` in frontend/ assert exit code 0, dist/ exists
      2. `npx serve dist -l 5173` start serving built app
      3. `curl -s http://localhost:5173/` assert contains root div
    Expected Result: Build succeeds, dist/ contains index.html
    Failure Indicators: Build errors, missing dist/, 404 on root
    Evidence: .sisyphus/evidence/task-5-react-build.txt

  Scenario: Design tokens configured correctly
    Tool: Bash
    Preconditions: frontend/tailwind.config.ts exists
    Steps:
      1. Read tailwind.config.ts assert contains aman, pantauan, tinggi, kritis
      2. Assert #22c55e, #f59e0b, #ef4444, #7c2d12 present
    Expected Result: All 4 risk-level colors defined
    Failure Indicators: Missing color keys, wrong hex values
    Evidence: .sisyphus/evidence/task-5-design-tokens.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(frontend): React scaffold with routing, design tokens, API client`
  - Files: `frontend/`
  - Pre-commit: `npm run build`

- [ ] 6. Feature Engineering — 73 OCP Red Flags (Cardinal) + 12 Custom Forensic ML Features

  **What to do**:
  - Create `backend/features/cardinal_flags.py`:
    - Import Cardinal library from OCP (Open Contracting Partnership, December 2024)
    - Load OCDS-format tenders from SQLite into Cardinal's expected input structure
    - Compute all 73 red flag indicators across 4 phases: Planning (flags 1-18), Tender (19-41), Award (42-58), Implementation (59-73)
    - Each flag produces a numeric score (0.0-1.0) per tender
    - Output: 73-column DataFrame indexed by tender_id
    - Handle missing fields gracefully: if an OCDS field is absent, set that flag to `NaN` (not 0)
    - Log which flags could not be computed and why
  - Create `backend/features/custom_features.py` — implement ALL 12 features from proposal lines 110-124:
    - `bid_clustering_score`: std_dev of bid amounts / HPS for each tender — low spread = suspicious
    - `vendor_win_concentration`: wins_by_vendor_at_institution / total_tenders_at_institution
    - `hps_deviation_ratio`: (contract_value - HPS) / HPS — extreme values flag HPS leakage
    - `participant_count_anomaly`: (tender_participants - category_mean) / category_std — z-score
    - `geographic_concentration`: count of distinct vendor_regions / total_bidders per tender
    - `repeat_pairing_index`: frequency of same vendor-pair co-bidding across tenders (SQL join)
    - `temporal_submission_pattern`: time variance of bid submissions within a tender
    - `historical_win_rate`: vendor total_wins / total_participations (all-time)
    - `phantom_bidder_score`: vendor participations_with_zero_wins / total_participations — highest = most suspicious
    - `benford_anomaly`: first-digit distribution chi-squared p-value (delegated to Task 9, placeholder here)
    - `interlocking_directorates`: NPWP-hash prefix overlap between bidders in same tender
    - `bid_rotation_pattern`: sequential win rotation detection within Leiden communities (delegated to Task 7, placeholder here)
  - Create `backend/features/pipeline.py`:
    - Orchestrate: load tenders → compute Cardinal flags → compute custom features → merge into 85-column feature matrix
    - Extract ICW `total_score` from opentender.net data as separate column (used as weak label in Task 8)
    - Save feature matrix to `features` table in SQLite
    - Handle temporal split: tag each row with train/val/test based on year (2018-2021/2022/2023-2024)
    - Validate: assert no duplicate tender_ids, assert feature count = 73 + 12 = 85 (excluding label columns)

  **Must NOT do**:
  - Do NOT hardcode feature thresholds — all thresholds come from `runtime_config.yaml`
  - Do NOT drop NaN flags — downstream models handle missing values
  - Do NOT compute Benford or bid rotation here — only placeholders (computed in Tasks 9, 7)
  - Do NOT train any models — this task is feature engineering only

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex feature engineering across 85 signals, Cardinal library integration requiring OCDS data mapping, multiple SQL joins for relational features
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction needed
    - `frontend-ui-ux`: Backend data processing only

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Wave 1 completes)
  - **Parallel Group**: Wave 2 (with Tasks 7, 8, 9)
  - **Blocks**: Tasks 8 (needs feature matrix), 9 (Benford plugs into feature pipeline), 10 (SHAP needs features)
  - **Blocked By**: Tasks 2 (schemas), 3 (data in SQLite)

  **References**:

  **Pattern References**:
  - `C:\Users\vasco\Downloads\UPGRADE 3` lines 104-124 — Complete specification of all 85 features (73 Cardinal + 12 custom)
  - `C:\Users\vasco\Downloads\UPGRADE 3` lines 203-205 — Data custom section describing vendor history extraction
  - `C:\Hackthon\DEEP_RESEARCH_SYNTHESIS.md` lines 130-161 — Cardinal library details, 73 red flag indicator breakdown, OCP PDF link

  **API/Type References**:
  - Cardinal library: `from cardinal import Dataset, calculate_indicators` (OCP library for OCDS red flags)
  - Pydantic schemas from Task 2: `TenderRecord`, `FeatureVector` (85 fields), `RiskPrediction`
  - SQLite tables from Task 3: `tenders` (raw data), `features` (output destination)

  **External References**:
  - Cardinal GitHub: https://github.com/open-contracting/cardinal
  - OCP 73 Red Flags PDF (Dec 2024): https://www.open-contracting.org/wp-content/uploads/2024/12/OCP2024-RedFlagProcurement-1.pdf
  - Cardinal blog: https://www.open-contracting.org/2024/06/12/cardinal-an-open-source-library-to-calculate-public-procurement-red-flags/
  - OCDS schema: https://standard.open-contracting.org/latest/en/schema/

  **WHY Each Reference Matters**:
  - Proposal lines 104-124 are the CONTRACT — every feature listed there MUST appear in the feature matrix
  - Cardinal library automates 73/85 features — learn its API to avoid reimplementation
  - OCP PDF has exact formulas for each red flag — needed when Cardinal doesn't cover all 73
  - OCDS schema tells you which fields map to which Cardinal indicators

  **Acceptance Criteria**:
  - [ ] `backend/features/cardinal_flags.py` computes 73 flags from OCDS data
  - [ ] `backend/features/custom_features.py` implements all 12 custom features
  - [ ] `backend/features/pipeline.py` produces 85-column DataFrame
  - [ ] Feature matrix saved to SQLite `features` table
  - [ ] ICW `total_score` extracted as separate weak-label column
  - [ ] Temporal split tags applied (train/val/test)
  - [ ] `pytest tests/test_features.py -q` → ALL PASS

  **QA Scenarios**:
  ```
  Scenario: Cardinal produces 73 flags from sample OCDS data
    Tool: Bash
    Preconditions: SQLite DB has >=100 tenders in OCDS format from Task 3
    Steps:
      1. Run `python -c "
        from backend.features.cardinal_flags import compute_cardinal_flags
        df = compute_cardinal_flags(limit=100)
        print(f'Shape: {df.shape}')
        print(f'Columns: {len(df.columns)}')
        print(f'Sample flags: {list(df.columns[:5])}')
        print(f'NaN ratio: {df.isna().mean().mean():.2f}')
        assert df.shape[1] == 73, f'Expected 73 columns, got {df.shape[1]}'
      "
      2. Verify output shape is (100, 73)
    Expected Result: 73-column DataFrame with numeric scores, NaN ratio < 0.5
    Failure Indicators: ImportError (Cardinal not installed), shape mismatch, all NaN
    Evidence: .sisyphus/evidence/task-6-cardinal-flags.txt

  Scenario: Custom features produce 12 signals
    Tool: Bash
    Preconditions: SQLite DB populated, cardinal_flags computed
    Steps:
      1. Run `python -c "
        from backend.features.custom_features import compute_custom_features
        df = compute_custom_features(limit=100)
        expected = ['bid_clustering_score', 'vendor_win_concentration', 'hps_deviation_ratio',
                    'participant_count_anomaly', 'geographic_concentration', 'repeat_pairing_index',
                    'temporal_submission_pattern', 'historical_win_rate', 'phantom_bidder_score',
                    'benford_anomaly', 'interlocking_directorates', 'bid_rotation_pattern']
        print(f'Shape: {df.shape}')
        print(f'Columns: {list(df.columns)}')
        for feat in expected:
          assert feat in df.columns, f'Missing: {feat}'
        print('All 12 custom features present')
      "
    Expected Result: 12-column DataFrame with all named features present
    Failure Indicators: Missing feature column, KeyError on SQL join
    Evidence: .sisyphus/evidence/task-6-custom-features.txt

  Scenario: Full pipeline produces 85-column feature matrix with temporal tags
    Tool: Bash
    Preconditions: Both cardinal and custom feature modules working
    Steps:
      1. Run `python -c "
        from backend.features.pipeline import run_feature_pipeline
        df = run_feature_pipeline(limit=100)
        print(f'Total features: {df.shape[1]}')
        assert df.shape[1] >= 85, f'Expected >=85 columns, got {df.shape[1]}'
        assert 'temporal_split' in df.columns
        assert 'icw_total_score' in df.columns
        print(f'Splits: {df.temporal_split.value_counts().to_dict()}')
        print('Pipeline OK')
      "
    Expected Result: >=85 columns (73 Cardinal + 12 custom + label columns), temporal_split present
    Failure Indicators: Column count < 85, missing temporal_split, missing icw_total_score
    Evidence: .sisyphus/evidence/task-6-full-pipeline.txt

  Scenario: Pipeline handles empty/corrupt tender gracefully
    Tool: Bash
    Preconditions: Insert a tender with all-null fields into SQLite
    Steps:
      1. Run `python -c "
        import sqlite3
        conn = sqlite3.connect('data/lpse_x.db')
        conn.execute('INSERT INTO tenders (tender_id) VALUES (\"TEST_EMPTY\")')
        conn.commit()
        from backend.features.pipeline import run_feature_pipeline
        df = run_feature_pipeline()
        row = df[df.index == 'TEST_EMPTY']
        print(f'Empty tender NaN count: {row.isna().sum().sum()}')
        print('Graceful handling OK')
      "
    Expected Result: Pipeline completes without crash, empty tender row has NaN values (not zeros)
    Failure Indicators: Exception, crash, zeros instead of NaN
    Evidence: .sisyphus/evidence/task-6-empty-tender.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(features): Cardinal 73 red flags + 12 custom forensic ML features pipeline`
  - Files: `backend/features/`
  - Pre-commit: `pytest tests/test_features.py -q`

- [ ] 7. Graph Construction + Leiden Cartel Detection Module

  **What to do**:
  - Create `backend/graph/builder.py`:
    - Build bipartite graph from SQLite data using NetworkX: nodes = Vendors + Tenders
    - Edge: vendor participated in tender (weight = bid amount / HPS)
    - Add vendor attributes: win_rate, region, NPWP_hash_prefix, total_participations
    - Add tender attributes: value, sector, institution, year, participant_count
    - Project to vendor-vendor unipartite graph (shared tender participation)
    - Edge weight in projection = number of shared tenders between vendor pair
  - Create `backend/graph/leiden.py`:
    - Run Leiden community detection using `leidenalg.find_partition()` with `ModularityVertexPartition`
    - **CRITICAL: Set fixed seed** (`seed=42`) for reproducibility (Metis gap requirement)
    - Log leidenalg version + igraph version + seed in every run
    - Extract communities: list of vendor groups with community_id, member_count, internal_edge_density
    - Compute cartel suspicion score per community:
      - `intra_bid_frequency`: how often community members co-bid
      - `win_rotation`: sequential wins among members (feeds `bid_rotation_pattern` in Task 6)
      - `price_similarity`: bid amount clustering within community
      - `geographic_overlap`: members from same region percentage
    - Export communities as JSON for frontend graph viz (Task 17)
    - Save communities to `communities` table in SQLite
  - Create `backend/graph/cartel_scorer.py`:
    - Combine community-level signals into cartel suspicion score (0-1)
    - Score = weighted average of intra_bid_frequency (0.3) + win_rotation (0.3) + price_similarity (0.2) + geographic_overlap (0.2)
    - Threshold from `runtime_config.yaml` (configurable via injection)
  - Create `tests/test_graph.py`:
    - Test Leiden seed determinism: run twice with same data and seed → identical communities
    - Test bipartite graph construction from known data
    - Test cartel scorer with known input → expected output range

  **Must NOT do**:
  - Do NOT use Louvain (proposal specifies Leiden as superior — Traag et al., 2019)
  - Do NOT use random seeds without logging — always seed=42 with version logging
  - Do NOT block on large graph computation — compute async and cache results
  - Do NOT store raw vendor identities in graph export — use NPWP hashes

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Graph theory + community detection + reproducibility requirements need deep understanding. Leiden seed behavior and bipartite projection are non-trivial
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction needed
    - `frontend-ui-ux`: Backend graph computation only

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Wave 1 completes)
  - **Parallel Group**: Wave 2 (with Tasks 6, 8, 9)
  - **Blocks**: Tasks 10 (Leiden XAI layer), 17 (graph visualization)
  - **Blocked By**: Tasks 2 (schemas), 3 (data in SQLite)

  **References**:

  **Pattern References**:
  - `C:\Users\vasco\Downloads\UPGRADE 3` lines 125-128 — Graf bipartit specification, Leiden justification, Swiss Commission validation
  - `C:\Hackthon\DEEP_RESEARCH_SYNTHESIS.md` lines 27-60 — All graph-based papers (Imhof et al. 91% accuracy, Santos et al., Pompeu GraphSAGE)
  - `C:\Hackthon\DEEP_RESEARCH_SYNTHESIS.md` lines 139 — leidenalg library details

  **API/Type References**:
  - Pydantic schema from Task 2: `GraphCommunity` (community_id, members, edge_weights, tender_ids)
  - SQLite tables from Task 3: `tenders` table for graph construction, `communities` table for output
  - leidenalg API: `leidenalg.find_partition(graph, partition_type, seed=42)`
  - igraph API: `igraph.Graph.Bipartite()`, `.community_leiden()`

  **External References**:
  - Traag, Waltman & van Eck (2019) — "From Louvain to Leiden": https://www.nature.com/articles/s41598-019-41695-z
  - Imhof, Viklund & Huber (2025) — Swiss Competition Commission bid-rigging with GATs: arXiv:2507.12369
  - Sahu (Oct 2024) — Dynamic Leiden for evolving procurement networks
  - leidenalg docs: https://leidenalg.readthedocs.io/
  - NetworkX bipartite: https://networkx.org/documentation/stable/reference/algorithms/bipartite.html

  **WHY Each Reference Matters**:
  - Proposal lines 125-128 are the CONTRACT for graph approach — bipartite + Leiden, not Louvain
  - Imhof paper validates graph-based cartel detection at 91% accuracy — cite for judges
  - leidenalg docs needed for seed parameter and partition type selection
  - NetworkX bipartite docs for projection algorithm (weighted shared neighbors)

  **Acceptance Criteria**:
  - [ ] Bipartite graph builds from SQLite tender data (vendors + tenders as node types)
  - [ ] Leiden detects communities with seed=42 reproducibility
  - [ ] Cartel suspicion score computed per community (0-1 scale)
  - [ ] Graph exported as JSON for frontend consumption
  - [ ] Communities saved to SQLite `communities` table
  - [ ] `pytest tests/test_graph.py -q` -> ALL PASS
  - [ ] Seed determinism test: two runs produce identical community memberships

  **QA Scenarios**:
  ```
  Scenario: Leiden produces deterministic communities with fixed seed
    Tool: Bash
    Preconditions: SQLite DB populated with tender data from Task 3
    Steps:
      1. Run `python -c "
        from backend.graph.leiden import detect_communities
        result1 = detect_communities(seed=42)
        result2 = detect_communities(seed=42)
        assert result1['communities'] == result2['communities'], 'Non-deterministic!'
        print(f'Communities: {len(result1[\"communities\"])}')
        print(f'Largest community: {max(len(c[\"members\"]) for c in result1[\"communities\"])}')
        print('Determinism OK')
      "
    Expected Result: Both runs produce identical community lists, >0 communities detected
    Failure Indicators: Communities differ between runs, 0 communities, crash
    Evidence: .sisyphus/evidence/task-7-leiden-determinism.txt

  Scenario: Bipartite graph correctly connects vendors to tenders
    Tool: Bash
    Preconditions: SQLite DB has tender data with vendor participation
    Steps:
      1. Run `python -c "
        from backend.graph.builder import build_bipartite_graph
        G = build_bipartite_graph(limit=500)
        vendors = [n for n, d in G.nodes(data=True) if d['bipartite'] == 0]
        tenders = [n for n, d in G.nodes(data=True) if d['bipartite'] == 1]
        print(f'Vendors: {len(vendors)}, Tenders: {len(tenders)}, Edges: {G.number_of_edges()}')
        assert len(vendors) > 0 and len(tenders) > 0
        assert G.number_of_edges() > 0
        print('Bipartite graph OK')
      "
    Expected Result: Graph has both vendor and tender nodes with connecting edges
    Failure Indicators: Zero nodes, zero edges, all nodes same type
    Evidence: .sisyphus/evidence/task-7-bipartite-graph.txt

  Scenario: Cartel scorer produces valid scores
    Tool: Bash
    Preconditions: Leiden communities computed
    Steps:
      1. Run `python -c "
        from backend.graph.cartel_scorer import score_communities
        from backend.graph.leiden import detect_communities
        communities = detect_communities(seed=42)['communities']
        scores = score_communities(communities)
        for s in scores[:5]:
          assert 0.0 <= s['score'] <= 1.0, f'Score out of range: {s[\"score\"]}'
          print(f'Community {s[\"community_id\"]}: score={s[\"score\"]:.3f}')
        print(f'Total scored communities: {len(scores)}')
      "
    Expected Result: All scores between 0.0 and 1.0, every community has a score
    Failure Indicators: Score outside 0-1, missing communities, KeyError
    Evidence: .sisyphus/evidence/task-7-cartel-scores.txt

  Scenario: Graph JSON export is valid for frontend consumption
    Tool: Bash
    Preconditions: Communities computed
    Steps:
      1. Run `python -c "
        import json
        from backend.graph.builder import export_graph_json
        data = export_graph_json(limit=200)
        parsed = json.loads(data)
        assert 'nodes' in parsed and 'links' in parsed
        assert len(parsed['nodes']) > 0
        print(f'Nodes: {len(parsed[\"nodes\"])}, Links: {len(parsed[\"links\"])}')
        print(f'Node keys: {list(parsed[\"nodes\"][0].keys())}')
        print('JSON export OK')
      "
    Expected Result: Valid JSON with nodes array + links array, each node has id + type + attributes
    Failure Indicators: Invalid JSON, missing nodes/links keys, empty arrays
    Evidence: .sisyphus/evidence/task-7-graph-json.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(graph): bipartite graph + Leiden cartel detection with seed determinism`
  - Files: `backend/graph/`
  - Pre-commit: `pytest tests/test_graph.py -q`


### Task 8 — Tri-Method AI: Isolation Forest + XGBoost + ICW Weak Labels + Disagreement Protocol
- **Wave**: 2 (parallel group B)
- **Depends on**: T2 (types), T6 (features)
- **Blocks**: T10 (SHAP+Anchors), T11 (ONNX export), T12 (DiCE), T14 (API)

  **What to do**:
  - Create `backend/models/` package with `__init__.py`
  - Implement `backend/models/isolation_forest.py`:
    - Wrap `sklearn.ensemble.IsolationForest`
    - Accept feature matrix from T6 pipeline output
    - `contamination='auto'` by default, overridable via runtime config
    - Return anomaly scores (continuous, -1 to 0 range normalized to 0-1 risk)
    - No labels needed — unsupervised, immune to class imbalance (UPGRADE 3 line 215)
  - Implement `backend/models/xgboost_model.py`:
    - Wrap `xgboost.XGBClassifier` with four-level risk classification
    - Risk levels: LOW (0-25), MEDIUM (26-50), HIGH (51-75), CRITICAL (76-100)
    - Class imbalance handling (UPGRADE 3 lines 214-218):
      - SMOTE oversampling via `imblearn.over_sampling.SMOTE`
      - Class weighting with `scale_pos_weight` — higher penalty on false negatives
    - Optuna hyperparameter tuning (UPGRADE 3 line 225):
      - `learning_rate`: 0.01–0.3
      - `max_depth`: 3–10
      - `n_estimators`: 100–1000
      - `subsample`: 0.6–1.0
      - Objective: maximize macro F1-score
      - `n_trials=100`, `timeout=3600` (1h max)
    - Save best params to `models/xgb_best_params.json`
  - Implement `backend/models/icw_weak_labels.py`:
    - Consume `total_score` from opentender.net as weakly supervised signal (UPGRADE 3 line 133, 216)
    - Normalize ICW scores to 0-1 risk range
    - Map ICW risk bands: Low (0-40 → 0.0-0.4), Medium (41-70 → 0.41-0.7), High (71-100 → 0.71-1.0)
    - This is NOT a model — it's a score transformer that provides weak labels
  - Implement `backend/models/ensemble.py`:
    - Tri-method ensemble: weighted average of IF score + XGBoost probability + ICW normalized score
    - Default weights: `{"isolation_forest": 0.35, "xgboost": 0.40, "icw": 0.25}` — configurable via runtime YAML
    - **Disagreement Protocol** (UPGRADE 3 line 134): when any two models disagree by >0.3 on risk classification, flag tender as `"Manual Review Priority"`
    - Return `EnsembleResult` with: `final_score`, `risk_level`, `individual_scores`, `disagreement_flag`, `disagreement_detail`
  - Implement `backend/models/temporal_split.py`:
    - Temporal split logic (UPGRADE 3 lines 220-228):
      - Training: 2018-2021 (~70%)
      - Validation: 2022 (~15%)
      - Test: 2023-2024 (~15%)
    - 5-Fold `TimeSeriesSplit` cross-validation within training set
    - NEVER shuffle — preserve temporal order
  - Implement `backend/models/train.py`:
    - Orchestrate full training pipeline:
      1. Load features from T6 output (Parquet)
      2. Apply temporal split
      3. Fit Isolation Forest on training set
      4. Fit XGBoost with Optuna on training set, evaluate on validation set
      5. Load ICW scores
      6. Evaluate ensemble on test set
      7. Log metrics: macro F1, recall, precision@K, per-class metrics
      8. Save trained models to `models/` directory (joblib for sklearn, XGBoost native format)
    - Target: F1-Score 0.85–0.92 (Westerski et al., 2021 benchmark — UPGRADE 3 line 135)
  - Create `backend/models/predict.py`:
    - Single-tender prediction function
    - Accept feature vector → return `EnsembleResult`
    - This is the function T14 (API) will call
  - Write comprehensive tests in `tests/test_models.py`:
    - Test IF returns scores in 0-1 range
    - Test XGBoost trains without error on synthetic data
    - Test ICW score normalization
    - Test ensemble weighted average math
    - Test disagreement protocol triggers correctly
    - Test temporal split produces non-overlapping year ranges
    - Test 5-fold TimeSeriesSplit preserves order

  **Must NOT do**:
  - Do NOT use `accuracy` as primary metric — use macro F1 (UPGRADE 3 line 218)
  - Do NOT shuffle data in temporal split — temporal leakage is fatal
  - Do NOT retrain at runtime — models must be production-ready from Stage 2
  - Do NOT hardcode ensemble weights — must be configurable via `runtime_config.yaml`
  - Do NOT use `as any` or suppress type warnings
  - Do NOT add deep learning models (no PyTorch/TensorFlow) — the proposal specifies XGBoost + IF only
  - Do NOT skip SMOTE — it's explicitly stated in UPGRADE 3 line 217

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`
  - **Reason**: Core ML pipeline with multiple interacting components, Optuna tuning, and ensemble logic. Requires deep understanding of ML training workflows, temporal validation, and class imbalance handling. The `deep` category provides autonomous problem-solving needed for this complex but well-specified ML engineering task.

  **Parallelization**:
  - Can Run In Parallel: YES — with T7 (graph) and T9 (Benford)
  - Parallel Group: Wave 2B
  - Blocks: T10, T11, T12, T14
  - Blocked By: T2, T6

  **References**:
  - Pattern References:
    - `backend/features/` (T6 output) — feature matrix format, column names, Parquet schema
    - `backend/types.py` (T2) — `EnsembleResult`, `RiskLevel`, `TenderPrediction` types
    - `config/runtime_config.yaml` (T4) — ensemble weights, contamination, risk thresholds
  - API/Type References:
    - `sklearn.ensemble.IsolationForest` — `contamination`, `n_estimators`, `random_state`
    - `xgboost.XGBClassifier` — `scale_pos_weight`, `eval_metric='mlogloss'`
    - `imblearn.over_sampling.SMOTE` — `random_state`, `k_neighbors`
    - `optuna.create_study` — `direction='maximize'`, `sampler=TPESampler`
    - `sklearn.model_selection.TimeSeriesSplit` — `n_splits=5`
  - External References:
    - UPGRADE 3 lines 130-135 — Tri-Method AI specification
    - UPGRADE 3 lines 214-228 — Data preparation, imbalance handling, temporal split
    - Westerski et al. (2021) — F1 0.85-0.92 benchmark on real procurement data
    - DEEP_RESEARCH_SYNTHESIS.md lines 99-103 — Thanathamathee & Sawangarreerak (2024) SHAP + XGBoost + Optuna pattern
  - WHY Each Reference Matters:
    - T6 output: defines the exact feature matrix schema the models consume
    - T2 types: ensures type-safe results that T10/T11/T12/T14 can consume
    - Runtime config: enables Dynamic Injection of ensemble weights and thresholds
    - Westerski benchmark: sets realistic F1 target backed by published research

  **Acceptance Criteria**:
  - [ ] `backend/models/isolation_forest.py` returns anomaly scores in 0-1 range for any valid feature matrix
  - [ ] `backend/models/xgboost_model.py` trains with SMOTE + class weighting, Optuna finds best params
  - [ ] `backend/models/icw_weak_labels.py` normalizes ICW `total_score` to 0-1 with correct band mapping
  - [ ] `backend/models/ensemble.py` computes weighted average and triggers disagreement flag when models diverge >0.3
  - [ ] `backend/models/temporal_split.py` produces non-overlapping temporal partitions (2018-21/2022/2023-24)
  - [ ] `backend/models/train.py` runs end-to-end and logs macro F1, recall, precision@K
  - [ ] `backend/models/predict.py` accepts single feature vector and returns `EnsembleResult`
  - [ ] `pytest tests/test_models.py -q` — all tests pass
  - [ ] Ensemble weights are read from `runtime_config.yaml`, not hardcoded
  - [ ] No temporal leakage — validation/test years never appear in training set
  - [ ] `lsp_diagnostics` clean on all files in `backend/models/`

  **QA Scenarios**:
  ```
  Scenario: Ensemble disagreement detection
    Tool: pytest
    Preconditions: Synthetic feature data with known scores
    Steps:
      1. Create mock IF score=0.9 (high risk), XGBoost prob=0.2 (low risk), ICW=0.5 (medium)
      2. Run ensemble.predict()
      3. Check disagreement_flag is True
      4. Check disagreement_detail mentions IF vs XGBoost divergence
    Expected Result: disagreement_flag=True, tender marked 'Manual Review Priority'
    Failure Indicators: disagreement_flag=False, no detail provided
    Evidence: .sisyphus/evidence/task-8-disagreement.txt

  Scenario: Temporal split integrity
    Tool: pytest
    Preconditions: DataFrame with date column spanning 2018-2024
    Steps:
      1. Run temporal_split(df)
      2. Extract unique years from train/val/test
      3. Assert train years ⊆ {2018,2019,2020,2021}
      4. Assert val years == {2022}
      5. Assert test years ⊆ {2023,2024}
      6. Assert no overlap between any partition
    Expected Result: Clean temporal separation, no leakage
    Failure Indicators: Year appearing in multiple partitions
    Evidence: .sisyphus/evidence/task-8-temporal-split.txt

  Scenario: XGBoost training with SMOTE
    Tool: pytest
    Preconditions: Imbalanced synthetic dataset (95% normal, 5% suspicious)
    Steps:
      1. Apply SMOTE to training set
      2. Verify class distribution is balanced after SMOTE
      3. Train XGBoost on balanced data
      4. Predict on test set
      5. Compute macro F1
    Expected Result: SMOTE balances classes, XGBoost trains successfully, F1 > 0.5 on synthetic data
    Failure Indicators: SMOTE fails, XGBoost error, F1 near random (0.25 for 4-class)
    Evidence: .sisyphus/evidence/task-8-xgb-smote.txt

  Scenario: Full pipeline smoke test
    Tool: python script
    Preconditions: Sample Parquet from T6 exists
    Steps:
      python -c "
        from backend.models.train import run_training_pipeline
        metrics = run_training_pipeline('data/features/sample.parquet')
        assert 'f1_macro' in metrics
        assert metrics['f1_macro'] > 0.0
        print(f'F1 macro: {metrics["f1_macro"]:.4f}')
        print('Pipeline smoke test OK')
      "
    Expected Result: Pipeline completes, metrics dictionary returned with valid F1
    Failure Indicators: Import error, training crash, missing metrics
    Evidence: .sisyphus/evidence/task-8-pipeline-smoke.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(models): tri-method AI with IF + XGBoost + ICW weak labels + disagreement protocol`
  - Files: `backend/models/`
  - Pre-commit: `pytest tests/test_models.py -q`


### Task 9 — Benford's Law Analysis Module with Applicability Gating
- **Wave**: 2 (parallel group B)
- **Depends on**: T6 (features)
- **Blocks**: T10 (SHAP+Anchors), T14 (API)

  **What to do**:
  - Create `backend/analysis/benford.py`:
    - Use `benford_py` library (DEEP_RESEARCH_SYNTHESIS.md line 137, 163-167)
    - Accept array of bid prices for a tender cluster
    - **Applicability Gating** (Metis gap — CRITICAL):
      - Pre-check: data must span at least 2 orders of magnitude (e.g., 1M to 100M IDR)
      - Pre-check: minimum 50 data points for statistical validity
      - If pre-checks fail → return `BenfordResult(applicable=False, reason="...")` — do NOT compute
      - This prevents false positives on small/narrow datasets
    - When applicable:
      - Compute first-digit distribution of bid prices
      - Chi-squared goodness-of-fit test against Benford's expected distribution
      - Return p-value, chi-squared statistic, observed vs expected digit frequencies
      - Deviation magnitude: how far each digit's frequency deviates from Benford's
    - Return `BenfordResult` dataclass with:
      - `applicable: bool`
      - `reason: Optional[str]` (why not applicable, or None)
      - `chi_squared: Optional[float]`
      - `p_value: Optional[float]`
      - `digit_distribution: Optional[Dict[int, float]]` (observed)
      - `expected_distribution: Dict[int, float]` (Benford's theoretical)
      - `anomaly_flag: bool` (True if p_value < 0.05 AND applicable)
      - `deviation_details: Optional[List[Dict]]` (per-digit deviation)
  - Create `backend/analysis/__init__.py` barrel export
  - Integrate with feature pipeline:
    - `Benford's Law Anomaly` is feature #10 in the 12 custom features (UPGRADE 3 line 121)
    - The feature value for ML = chi-squared statistic (or 0.0 if not applicable)
    - The full BenfordResult is used by XAI layer (Task 10) for the Statistical layer explanation
  - Write tests in `tests/test_benford.py`:
    - Test with data following Benford's (generated from log-uniform distribution) → should NOT flag
    - Test with fabricated uniform data → should flag as anomalous
    - Test applicability gating: <50 data points → not_applicable
    - Test applicability gating: narrow range (all values 1M-2M) → not_applicable
    - Test edge case: all identical values → not_applicable
    - Test empty input → not_applicable with reason

  **Must NOT do**:
  - Do NOT compute Benford when pre-checks fail — this is the Metis gap, return not_applicable (UPGRADE 3 line 121 + Metis review)
  - Do NOT use Benford as a standalone fraud detector — it's one of 5 XAI layers
  - Do NOT hardcode significance threshold — read from runtime config (default 0.05)
  - Do NOT require scipy — `benford_py` handles the chi-squared test internally

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`
  - **Reason**: Statistical analysis module with clear spec. Not trivial (gating logic, edge cases) but not deeply complex. `unspecified-high` provides enough reasoning for the gating logic and statistical validation.

  **Parallelization**:
  - Can Run In Parallel: YES — with T7 (graph) and T8 (ML models)
  - Parallel Group: Wave 2B
  - Blocks: T10, T14
  - Blocked By: T6

  **References**:
  - Pattern References:
    - `backend/features/` (T6 output) — bid price arrays, cluster groupings
    - `backend/types.py` (T2) — `BenfordResult` type definition
  - API/Type References:
    - `benford_py.Benford` — main class, accepts `pandas.Series`
    - Chi-squared test: `benford_py` computes internally, access via `.chi_square`
  - External References:
    - UPGRADE 3 line 121 — Benford's Law Anomaly feature specification
    - UPGRADE 3 line 147 — Oracle Sandwich Layer 5 (Statistical)
    - DEEP_RESEARCH_SYNTHESIS.md lines 163-167 — benford_py library details + academic backing
    - Fu (2025, ODU) — "Leveraging Benford's Law and ML for Financial Fraud Detection"
    - ACFE + World Bank endorse Benford's for procurement fraud (cited in proposal)
  - WHY Each Reference Matters:
    - Feature spec: Benford score feeds into the 12-feature ML pipeline
    - Oracle Sandwich: Benford is Layer 5 — judges will evaluate it as XAI output
    - Gating requirement: Metis identified this as critical — false Benford flags undermine credibility

  **Acceptance Criteria**:
  - [ ] `backend/analysis/benford.py` computes first-digit distribution and chi-squared test
  - [ ] Applicability gating rejects datasets with <50 points or <2 orders of magnitude
  - [ ] Returns `BenfordResult(applicable=False, reason=...)` when gating fails
  - [ ] Returns valid chi-squared and p-value when applicable
  - [ ] `anomaly_flag=True` only when `applicable=True AND p_value < threshold`
  - [ ] Significance threshold read from runtime config, not hardcoded
  - [ ] `pytest tests/test_benford.py -q` — all tests pass
  - [ ] `lsp_diagnostics` clean on `backend/analysis/`

  **QA Scenarios**:
  ```
  Scenario: Benford detects fabricated data
    Tool: pytest
    Preconditions: None
    Steps:
      1. Generate 500 values from uniform distribution (100K-999K IDR)
      2. Run benford_analysis(values)
      3. Assert applicable=True
      4. Assert anomaly_flag=True (fabricated data violates Benford)
      5. Assert p_value < 0.05
    Expected Result: Benford flags the fabricated data as anomalous
    Failure Indicators: applicable=False, anomaly_flag=False, p_value > 0.05
    Evidence: .sisyphus/evidence/task-9-benford-fabricated.txt

  Scenario: Benford accepts natural data
    Tool: pytest
    Preconditions: None
    Steps:
      1. Generate 500 values from log-uniform distribution (spanning 3 orders of magnitude)
      2. Run benford_analysis(values)
      3. Assert applicable=True
      4. Assert anomaly_flag=False (natural data follows Benford)
    Expected Result: Benford does NOT flag natural data
    Failure Indicators: anomaly_flag=True on natural data (false positive)
    Evidence: .sisyphus/evidence/task-9-benford-natural.txt

  Scenario: Gating rejects narrow-range data
    Tool: pytest
    Preconditions: None
    Steps:
      1. Generate 100 values all between 1.0M-1.5M IDR (same order of magnitude)
      2. Run benford_analysis(values)
      3. Assert applicable=False
      4. Assert reason contains 'order of magnitude' or similar
    Expected Result: Gating prevents analysis, returns not_applicable
    Failure Indicators: applicable=True, Benford computed on invalid data
    Evidence: .sisyphus/evidence/task-9-benford-gating.txt

  Scenario: Gating rejects small datasets
    Tool: pytest
    Preconditions: None
    Steps:
      1. Generate 10 values (below 50-point threshold)
      2. Run benford_analysis(values)
      3. Assert applicable=False
      4. Assert reason mentions minimum data points
    Expected Result: Gating prevents analysis due to insufficient data
    Failure Indicators: applicable=True on 10 data points
    Evidence: .sisyphus/evidence/task-9-benford-small.txt
  ```

  **Commit**: YES (groups with Wave 2)
  - Message: `feat(benford): Benford's Law analysis with applicability gating`
  - Files: `backend/analysis/`
  - Pre-commit: `pytest tests/test_benford.py -q`


### Task 10 — SHAP + Anchors XAI Layer (Global Importance + Rule Extraction)
- **Wave**: 3 (parallel group A)
- **Depends on**: T8 (trained XGBoost + IF models), T7 (Leiden communities)
- **Blocks**: T14 (API), T16 (XAI visualization components)

  **What to do**:
  - Create `backend/xai/shap_explainer.py`:
    - Use **TreeSHAP** for XGBoost global feature importance (DEEP_RESEARCH_SYNTHESIS.md lines 217-220)
    - Compute global SHAP summary: `shap.TreeExplainer(xgb_model)` → `shap_values` matrix
    - Compute per-tender local SHAP: individual feature contributions for a single prediction
    - Generate SHAP summary plot data (not image) — return as JSON-serializable dict:
      - Feature names, mean absolute SHAP values (sorted), per-sample SHAP matrix
    - **Encoding sensitivity** (Hwang et al., 2025 — DEEP_RESEARCH_SYNTHESIS.md lines 122-126):
      - CRITICAL: SHAP values are sensitive to One-Hot vs Target Encoding on categorical features
      - Use Target Encoding for categorical procurement features (institution, category) to avoid SHAP fragmentation
      - Document encoding choice in code comments with citation
    - Performance SLA: Global SHAP computation <2s for batch of 100 tenders (Metis gap)
    - Cache global SHAP results — recompute only when model or data changes
  - Create `backend/xai/anchor_explainer.py`:
    - Use **Anchors** from `alibi` library (UPGRADE 3 line 145, DEEP_RESEARCH_SYNTHESIS.md line 141)
    - Generate human-readable if-then rules for each prediction
    - Example output: `IF HPS_Deviation > 0.15 AND Participant_Count < 3 THEN High Risk (precision=0.95)`
    - Return `AnchorResult` dataclass:
      - `anchor_rules: List[str]` — human-readable rules
      - `precision: float` — how often the anchor holds
      - `coverage: float` — fraction of instances covered
      - `features_used: List[str]` — features in the anchor
    - Performance SLA: <5s per individual tender explanation (Metis gap)
    - Use `alibi.explainers.AnchorTabular` with the training data as background
  - Create `backend/xai/__init__.py` barrel export
  - Create orchestrator `backend/xai/oracle_sandwich.py`:
    - Combines all 5 XAI layers (SHAP, DiCE, Anchors, Leiden, Benford) into unified response
    - Each layer runs independently — one layer failing does NOT block others
    - Returns `OracleSandwichResult` with all 5 layers + metadata + timing
    - Timeout per layer: configurable in runtime config (defaults: SHAP 2s, DiCE 10s, Anchors 5s, Leiden 3s, Benford 1s)
  - Write tests in `tests/test_xai.py`:
    - Test SHAP returns valid feature importances for trained XGBoost
    - Test SHAP values sum to model output (SHAP additivity property)
    - Test Anchors return non-empty rules with precision > 0.8
    - Test Oracle Sandwich gracefully handles individual layer failures
    - Test latency SLAs with synthetic data

  **Must NOT do**:
  - Do NOT generate SHAP plot images in backend — return data only, frontend renders (UPGRADE 3 line 143)
  - Do NOT use One-Hot encoding for SHAP — use Target Encoding (Hwang et al., 2025)
  - Do NOT make Anchors block inference — it's a separate async call
  - Do NOT use LIME — proposal specifies SHAP + Anchors, not LIME
  - Do NOT call external APIs — all XAI computation is local

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`
  - **Reason**: XAI layer requires understanding statistical properties of SHAP (additivity, encoding sensitivity) and configuring alibi Anchors correctly. Deep reasoning needed for Oracle Sandwich orchestration with fault tolerance. No special skills needed — pure Python ML work.

  **Parallelization**:
  - Can Run In Parallel: YES — with T11 (ONNX), T12 (DiCE), T13 (Reports)
  - Parallel Group: Wave 3A
  - Blocks: T14, T16
  - Blocked By: T8, T7

  **References**:
  - Pattern References:
    - `backend/models/train.py` (T8 output) — trained XGBoost model object for TreeExplainer
    - `backend/models/isolation_forest.py` (T8 output) — IF model for anomaly SHAP
    - `backend/graph/leiden.py` (T7 output) — community results for Layer 4
    - `backend/analysis/benford.py` (T9 output) — Benford results for Layer 5
    - `backend/types.py` (T2) — `SHAPResult`, `AnchorResult`, `OracleSandwichResult` types
  - API/Type References:
    - `shap.TreeExplainer` — fast exact SHAP for tree models
    - `alibi.explainers.AnchorTabular` — tabular Anchors for classification
    - Return types defined in T2's `backend/types.py`
  - External References:
    - UPGRADE 3 lines 137-148 — Oracle Sandwich 5-layer architecture specification
    - UPGRADE 3 line 143 — SHAP summary plots (Global layer)
    - UPGRADE 3 line 145 — Anchors from `alibi` (Rules layer)
    - DEEP_RESEARCH_SYNTHESIS.md lines 99-103 — Thanathamathee & Sawangarreerak (2024): SHAP + Anchors + XGBoost combination validated
    - DEEP_RESEARCH_SYNTHESIS.md lines 122-126 — Hwang et al. (2025): SHAP encoding sensitivity warning
    - DEEP_RESEARCH_SYNTHESIS.md lines 210-238 — Oracle Sandwich enhanced architecture
  - WHY Each Reference Matters:
    - Oracle Sandwich spec: judges evaluate XAI quality — must match proposal exactly
    - Encoding sensitivity: wrong encoding = misleading SHAP values = judge deduction
    - Thanathamathee: validates our SHAP+Anchors+XGBoost stack academically
    - Performance SLAs: live demo can't have >5s waits for explanations

  **Acceptance Criteria**:
  - [ ] `backend/xai/shap_explainer.py` computes global + local SHAP for XGBoost
  - [ ] SHAP values use Target Encoding (NOT One-Hot) for categoricals
  - [ ] Global SHAP computation <2s for batch of 100 tenders
  - [ ] `backend/xai/anchor_explainer.py` returns human-readable if-then rules
  - [ ] Anchors precision > 0.8 on test data
  - [ ] Anchors computation <5s per individual tender
  - [ ] `backend/xai/oracle_sandwich.py` combines all 5 layers with fault tolerance
  - [ ] One layer failing does NOT crash the others — returns partial result with error info
  - [ ] `pytest tests/test_xai.py -q` — all tests pass
  - [ ] `lsp_diagnostics` clean on `backend/xai/`

  **QA Scenarios**:
  ```
  Scenario: SHAP global feature importance
    Tool: pytest
    Preconditions: Trained XGBoost model from T8 exists at models/xgboost.pkl
    Steps:
      1. Load trained model + training data
      2. Run shap_global_importance(model, X_train)
      3. Assert result has 'feature_names' and 'mean_abs_shap' keys
      4. Assert len(feature_names) == 85 (73 Cardinal + 12 custom)
      5. Assert all mean_abs_shap values >= 0
      6. Assert top-5 features are reasonable (not all zeros)
      7. Measure wall time
    Expected Result: Valid SHAP importances for all 85 features, computation <2s
    Failure Indicators: Missing features, negative SHAP means, timeout >2s
    Evidence: .sisyphus/evidence/task-10-shap-global.txt

  Scenario: SHAP local explanation for single tender
    Tool: pytest
    Preconditions: Trained model + single tender feature vector
    Steps:
      1. Run shap_local_explain(model, single_tender_features)
      2. Assert result has per-feature SHAP values
      3. Assert sum(shap_values) + base_value ≈ model_prediction (additivity)
      4. Assert top contributing features have non-zero values
    Expected Result: SHAP values sum to model output (additivity holds)
    Failure Indicators: Additivity violation > 0.01, all-zero SHAP values
    Evidence: .sisyphus/evidence/task-10-shap-local.txt

  Scenario: Anchors rule extraction
    Tool: pytest
    Preconditions: Trained model + training data + single test tender
    Steps:
      1. Initialize AnchorTabular with training data
      2. Run explain(single_tender_features)
      3. Assert result.anchor_rules is non-empty list of strings
      4. Assert result.precision > 0.8
      5. Assert result.coverage > 0.0
      6. Assert all features_used exist in feature_names
      7. Measure wall time
    Expected Result: Human-readable rules with >0.8 precision, <5s compute
    Failure Indicators: Empty rules, precision <0.8, timeout >5s
    Evidence: .sisyphus/evidence/task-10-anchors.txt

  Scenario: Oracle Sandwich fault tolerance
    Tool: pytest
    Preconditions: Trained model + feature data, but mock DiCE to raise exception
    Steps:
      1. Patch dice_explain to raise RuntimeError
      2. Run oracle_sandwich_explain(tender_id, features)
      3. Assert result is NOT None (did not crash)
      4. Assert result.shap is valid (unaffected by DiCE failure)
      5. Assert result.dice.error contains error message
      6. Assert result.anchors is valid (unaffected)
    Expected Result: Partial result returned with 4/5 layers OK, DiCE shows error
    Failure Indicators: Full crash, None result, other layers affected by DiCE failure
    Evidence: .sisyphus/evidence/task-10-fault-tolerance.txt
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(xai): SHAP + Anchors + Oracle Sandwich orchestrator with fault tolerance`
  - Files: `backend/xai/`
  - Pre-commit: `pytest tests/test_xai.py -q`


---


### Task 11 — ONNX Export Pipeline + Parity Tests
- **Wave**: 3 (parallel group A)
- **Depends on**: T8 (trained XGBoost + Isolation Forest models)
- **Blocks**: T14 (API needs ONNX inference), T20 (offline bundle includes ONNX models)

  **What to do**:
  - Create `backend/models/onnx_export.py`:
    - Export trained XGBoost model to ONNX format using `skl2onnx` or `onnxmltools`
    - Export trained Isolation Forest to ONNX format
    - Export preprocessing pipeline (scaler, encoder) to ONNX or pickle with ONNX-compatible transforms
    - Save to `models/xgboost.onnx`, `models/isolation_forest.onnx`
    - Include metadata: training date, feature names, model version, hyperparameters hash
    - Versioned output — new export doesn't overwrite old until parity verified
  - Create `backend/models/onnx_inference.py`:
    - Load ONNX models via `onnxruntime.InferenceSession`
    - `predict(features: np.ndarray) -> PredictionResult`
    - `predict_batch(features: np.ndarray) -> List[PredictionResult]`
    - Performance target: **<200ms per prediction** on standard CPU (UPGRADE 3 line 164)
    - Warm-up: run dummy prediction on startup to avoid cold-start latency
    - Error handling: if ONNX model file missing, raise clear error with path
  - Create `tests/test_onnx_parity.py` (Metis gap — CRITICAL):
    - Load native XGBoost model + ONNX-exported model
    - Run SAME 100 test samples through both
    - Assert `np.allclose(native_predictions, onnx_predictions, atol=1e-6)`
    - Test both classification output (risk level) and probability scores
    - This verifies export didn't corrupt the model
  - Create `tests/test_onnx_latency.py`:
    - Run 100 sequential predictions, measure mean + p99 latency
    - Assert mean <200ms, p99 <500ms
    - Test with realistic feature vector size (85 features)
  - Export script: `python -m backend.models.onnx_export` — one-command export

  **Must NOT do**:
  - Do NOT keep native model as fallback in production — ONNX is the ONLY inference path (ensures consistency)
  - Do NOT use GPU-specific ONNX providers — CPU only (demo laptop may not have GPU)
  - Do NOT skip parity tests — this is a Metis-identified gap
  - Do NOT hardcode model paths — read from runtime config
  - Do NOT retrain during export — export the already-trained model from T8

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`
  - **Reason**: ONNX export requires understanding model serialization formats, numerical precision, and performance benchmarking. Parity testing is subtle (floating point tolerance). Deep agent ensures correctness.

  **Parallelization**:
  - Can Run In Parallel: YES — with T10 (SHAP), T12 (DiCE), T13 (Reports)
  - Parallel Group: Wave 3A
  - Blocks: T14, T20
  - Blocked By: T8

  **References**:
  - Pattern References:
    - `backend/models/train.py` (T8 output) — trained model objects to export
    - `backend/models/` directory structure (T8) — follow existing organization
  - API/Type References:
    - `onnxruntime.InferenceSession` — ONNX model loading and inference
    - `skl2onnx.convert_sklearn` or `onnxmltools.convert_xgboost` — conversion API
    - `backend/types.py` (T2) — `PredictionResult` type
  - External References:
    - UPGRADE 3 line 164 — "ONNX Runtime (<200 ms/prediksi, CPU standar)"
    - DEEP_RESEARCH_SYNTHESIS.md — ONNX mentioned as inference runtime
    - Metis review — parity testing identified as critical gap
  - WHY Each Reference Matters:
    - 200ms SLA: competition judges will test inference speed in live demo
    - Parity: if ONNX predictions differ from training, all evaluation metrics are invalid
    - CPU-only: demo laptop constraint — no CUDA/GPU assumptions

  **Acceptance Criteria**:
  - [ ] `backend/models/onnx_export.py` exports XGBoost + IF to ONNX format
  - [ ] `models/xgboost.onnx` and `models/isolation_forest.onnx` created
  - [ ] `backend/models/onnx_inference.py` loads and runs ONNX models
  - [ ] `np.allclose(native, onnx, atol=1e-6)` for 100 test samples (parity)
  - [ ] Mean inference latency <200ms per prediction
  - [ ] P99 latency <500ms
  - [ ] Warm-up prediction runs on module load
  - [ ] `pytest tests/test_onnx_parity.py -q` — all pass
  - [ ] `pytest tests/test_onnx_latency.py -q` — all pass
  - [ ] `lsp_diagnostics` clean on `backend/models/onnx_*.py`

  **QA Scenarios**:
  ```
  Scenario: ONNX parity with native XGBoost
    Tool: pytest
    Preconditions: Trained XGBoost from T8 exists, ONNX export completed
    Steps:
      1. Load native XGBoost model
      2. Load ONNX XGBoost model via InferenceSession
      3. Generate 100 test feature vectors (85 features each)
      4. Run predictions through both models
      5. Assert np.allclose(native_preds, onnx_preds, atol=1e-6)
      6. Compare probability distributions for all 4 risk classes
    Expected Result: Native and ONNX predictions match within 1e-6 tolerance
    Failure Indicators: Any prediction differs by >1e-6, class probabilities diverge
    Evidence: .sisyphus/evidence/task-11-onnx-parity.txt

  Scenario: ONNX inference latency under 200ms
    Tool: pytest
    Preconditions: ONNX model loaded and warmed up
    Steps:
      1. Create realistic feature vector (85 features)
      2. Run 100 sequential predictions with time.perf_counter()
      3. Compute mean and p99 latency
      4. Assert mean < 200ms
      5. Assert p99 < 500ms
    Expected Result: Mean <200ms, p99 <500ms on CPU
    Failure Indicators: Mean >200ms, p99 >500ms
    Evidence: .sisyphus/evidence/task-11-onnx-latency.txt

  Scenario: ONNX model file integrity
    Tool: Bash
    Preconditions: Export script has been run
    Steps:
      1. Verify models/xgboost.onnx exists and size > 0
      2. Verify models/isolation_forest.onnx exists and size > 0
      3. Load each with onnxruntime and verify session creation succeeds
      4. Check metadata is present (feature names, version)
    Expected Result: Both ONNX files valid and loadable
    Failure Indicators: File missing, size 0, load error, missing metadata
    Evidence: .sisyphus/evidence/task-11-onnx-integrity.txt
  ```

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(onnx): ONNX export pipeline with parity verification and latency tests`
  - Files: `backend/models/onnx_export.py`, `backend/models/onnx_inference.py`, `tests/test_onnx_*.py`
  - Pre-commit: `pytest tests/test_onnx_parity.py tests/test_onnx_latency.py -q`


### Task 12 — DiCE Counterfactual Explanations (Cached/Async)

  **Wave**: 3 (parallel with T13, T14 after T10-T11 complete)
  **Depends on**: T8 (XGBoost model trained)
  **Blocks**: T14 (API needs DiCE endpoint), T16 (frontend XAI viz needs counterfactual data)

  **What to do**:
  - Create `backend/xai/dice_explainer.py` — DiCE counterfactual explanation module:
    - Load the trained XGBoost model (from `models/xgboost_model.pkl` or ONNX)
    - Initialize `dice_ml.Dice` with the training data schema (continuous/categorical feature declarations)
    - Implement `generate_counterfactuals(input_features: dict, total_cfs: int = 3, desired_class: str = "low_risk") -> dict`
    - Return structure: `{"original": {...}, "counterfactuals": [{"features": {...}, "changes": [...], "risk_score": float}], "generation_time_ms": float}`
    - Each counterfactual must include a `changes` list: `[{"feature": str, "from": val, "to": val, "direction": "increase"|"decrease"}]`
    - Implement **template caching**: pre-compute 10-20 representative counterfactual templates at startup for common risk archetypes (single-bidder, high-value, repeat-winner)
    - Async wrapper: `async_generate_counterfactuals()` that uses `asyncio.to_thread()` with **10-second hard timeout**
    - If timeout exceeded → return cached template closest to input (cosine similarity on normalized features)
    - Configure DiCE with `method="genetic"` (faster than KD-tree for mixed feature types)
  - Create `backend/xai/dice_cache.py` — template cache manager:
    - `DiceCacheManager` class: loads/saves cache from `models/dice_cache.json`
    - `build_cache(model, X_train, n_templates=20)` — generate diverse counterfactual templates
    - `find_nearest_template(input_features: dict) -> dict` — cosine similarity fallback
    - Cache invalidation: re-build when model version changes (check `models/metadata.json` version field)
  - Create `tests/test_dice_explainer.py`:
    - Test counterfactual generation with mock model → verify output structure
    - Test timeout fallback → verify cached template returned within 10s
    - Test cache build → verify templates generated and saved
    - Test nearest template lookup → verify cosine similarity selects correctly
    - Test with categorical features → verify DiCE handles mixed types

  **Must NOT do**:
  - Do NOT make DiCE synchronous/blocking on the main inference path — always async with timeout
  - Do NOT use `method="random"` — genetic method produces higher-quality counterfactuals
  - Do NOT skip the cache fallback — DiCE can be slow on complex models, cache is mandatory
  - Do NOT hardcode feature names — read from model metadata or config
  - Do NOT generate more than 5 counterfactuals per request — diminishing returns + latency

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: DiCE integration requires careful async/timeout handling, cache design, and understanding of counterfactual ML concepts
  - **Skills**: []
    - No specialized skills needed — pure Python ML/async work
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction in this task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13, 14)
  - **Blocks**: T14 (API routes need DiCE endpoint), T16 (frontend counterfactual display)
  - **Blocked By**: T8 (needs trained XGBoost model)

  **References**:

  **Pattern References** (existing code to follow):
  - `backend/xai/shap_explainer.py` (T10) — Follow the same module structure: class-based explainer with `explain()` method, consistent return format, startup pre-computation
  - `backend/xai/anchor_explainer.py` (T10) — Timeout pattern: how T10 handles Anchor explanation timeouts is the template for DiCE timeout handling
  - `backend/models/onnx_inference.py` (T11) — Model loading pattern: how to load model + metadata consistently

  **API/Type References** (contracts to implement against):
  - `backend/xai/__init__.py` (T10) — XAI module exports; DiCE explainer must register here
  - `backend/config/settings.yaml` (T4) — `xai.dice.timeout_seconds`, `xai.dice.n_counterfactuals`, `xai.dice.cache_size` settings

  **External References** (libraries and frameworks):
  - dice-ml docs: https://interpret.ml/DiCE/notebooks/DiCE_getting_started.html — Basic usage, Dice object creation, genetic method
  - dice-ml API: `dice_ml.Dice(data=data_interface, model=model_interface, method="genetic")` → `.generate_counterfactuals(query_instance, total_CFs, desired_class)`
  - asyncio.to_thread: https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread — Thread-based async wrapper for CPU-bound DiCE generation

  **Proposal References** (UPGRADE 3):
  - Lines 137-148: Oracle Sandwich XAI architecture — DiCE is Layer 2 ("What-If Scenarios")
  - Lines 111-113: "DiCE counterfactual scenarios" listed as core XAI feature

  **Research References** (DEEP_RESEARCH_SYNTHESIS.md):
  - Lines 86-127: XAI techniques overview — DiCE positioning within counterfactual explanation landscape
  - Lines 130-168: XAI tools/libraries — dice-ml usage patterns

  **WHY Each Reference Matters**:
  - T10 shap_explainer.py: Copy the class structure so ALL XAI explainers share consistent interface — critical for T14 API unification
  - T10 anchor timeout pattern: DiCE has same latency risk as Anchors; reuse the proven timeout+fallback approach
  - UPGRADE 3 lines 137-148: DiCE is Layer 2 of 5 in Oracle Sandwich — must produce output format compatible with layers 1,3,4,5

  **Acceptance Criteria**:

  - [ ] `backend/xai/dice_explainer.py` exists with `DiceExplainer` class
  - [ ] `backend/xai/dice_cache.py` exists with `DiceCacheManager` class
  - [ ] `pytest tests/test_dice_explainer.py -q` → PASS (5+ tests, 0 failures)
  - [ ] Counterfactual generation returns valid structure with `original`, `counterfactuals`, `generation_time_ms` keys
  - [ ] Timeout enforced: generation exceeding 10s returns cached template instead
  - [ ] Cache pre-builds 10-20 templates at initialization
  - [ ] Nearest-template fallback uses cosine similarity correctly

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Happy path — generate counterfactuals for high-risk tender
    Tool: Bash (python)
    Preconditions: XGBoost model trained (T8 output exists at models/xgboost_model.pkl)
    Steps:
      1. python -c "
         from backend.xai.dice_explainer import DiceExplainer
         import json
         explainer = DiceExplainer(model_path='models/xgboost_model.pkl')
         result = explainer.generate_counterfactuals({
           'n_bidders': 1, 'winner_repeat_count': 5, 'price_ratio': 0.98,
           'same_city_pct': 0.8, 'benford_pvalue': 0.01
         }, total_cfs=3, desired_class='low_risk')
         print(json.dumps(result, indent=2, default=str))
         assert 'counterfactuals' in result
         assert len(result['counterfactuals']) <= 3
         assert all('changes' in cf for cf in result['counterfactuals'])
         assert result['generation_time_ms'] > 0
         print('PASS: Counterfactual generation successful')
         "
      2. Verify each counterfactual has 'features', 'changes', 'risk_score' keys
      3. Verify 'changes' list entries have 'feature', 'from', 'to', 'direction' keys
    Expected Result: 3 counterfactuals generated, each showing what feature changes would reduce risk
    Failure Indicators: ImportError, KeyError on result structure, empty counterfactuals list, generation_time_ms=0
    Evidence: .sisyphus/evidence/task-12-dice-happy-path.txt

  Scenario: Timeout fallback — slow generation returns cached template
    Tool: Bash (python)
    Preconditions: DiceCacheManager initialized with pre-built templates
    Steps:
      1. python -c "
         import asyncio, time
         from backend.xai.dice_explainer import DiceExplainer
         explainer = DiceExplainer(model_path='models/xgboost_model.pkl')
         original_gen = explainer._raw_generate
         def slow_gen(*a, **kw): time.sleep(15); return original_gen(*a, **kw)
         explainer._raw_generate = slow_gen
         result = asyncio.run(explainer.async_generate_counterfactuals({
           'n_bidders': 1, 'winner_repeat_count': 5, 'price_ratio': 0.98,
           'same_city_pct': 0.8, 'benford_pvalue': 0.01
         }))
         assert result['from_cache'] == True
         assert result['generation_time_ms'] <= 11000
         print('PASS: Timeout fallback to cache working')
         "
    Expected Result: Result returned within ~10s with from_cache=True, using nearest cached template
    Failure Indicators: Hangs beyond 12s, from_cache missing or False, no result returned
    Evidence: .sisyphus/evidence/task-12-dice-timeout-fallback.txt

  Scenario: Cache build — verify templates generated at initialization
    Tool: Bash (python)
    Preconditions: Training data and model available
    Steps:
      1. python -c "
         import json, os
         from backend.xai.dice_cache import DiceCacheManager
         cache = DiceCacheManager(model_path='models/xgboost_model.pkl')
         cache.build_cache(n_templates=10)
         assert os.path.exists('models/dice_cache.json')
         with open('models/dice_cache.json') as f:
           data = json.load(f)
         assert len(data['templates']) >= 10
         assert 'version' in data
         print(f'PASS: Cache built with {len(data[chr(34)+"templates"+chr(34)])} templates')
         "
    Expected Result: models/dice_cache.json created with 10+ templates and version metadata
    Failure Indicators: File not created, fewer than 10 templates, missing version field
    Evidence: .sisyphus/evidence/task-12-dice-cache-build.txt
  ```

  **Evidence to Capture:**
  - [ ] task-12-dice-happy-path.txt — Full counterfactual output
  - [ ] task-12-dice-timeout-fallback.txt — Timeout fallback verification
  - [ ] task-12-dice-cache-build.txt — Cache generation output

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(xai): DiCE counterfactual explainer with async timeout and template caching`
  - Files: `backend/xai/dice_explainer.py`, `backend/xai/dice_cache.py`, `tests/test_dice_explainer.py`
  - Pre-commit: `pytest tests/test_dice_explainer.py -q`


### Task 13 — Auto Pre-Investigation Report Generator (IIA 2025, NLG)

  **Wave**: 3 (parallel with T12, T14)
  **Depends on**: T2 (schemas), T6 (feature engineering output)
  **Blocks**: T14 (API needs report endpoint), T19 (frontend report viewer)

  **What to do**:
  - Create `backend/reports/generator.py` — natural language report generator:
    - Implement `generate_report(tender_id: str, risk_assessment: dict, xai_results: dict, graph_results: dict) -> ReportOutput`
    - Use Jinja2 templates for narrative generation in **Bahasa Indonesia**
    - Follow IIA (Institute of Internal Auditors) 2025 report format:
      - Executive Summary (Ringkasan Eksekutif)
      - Background & Scope (Latar Belakang & Lingkup)
      - Risk Findings (Temuan Risiko) — with XAI-backed evidence
      - Evidence Matrix (Matriks Bukti) — cross-referencing SHAP, DiCE, Anchors, Benford, graph findings
      - Recommendations (Rekomendasi) — actionable steps for auditors
      - Appendix (Lampiran) — technical details, raw scores, model metadata
    - Each section populated from real analysis outputs — NOT hardcoded text
    - Risk findings must reference specific XAI layers: "Berdasarkan analisis SHAP, fitur X berkontribusi Y% terhadap skor risiko"
    - Include severity classification per finding: Kritis / Tinggi / Sedang / Rendah
    - Generate both HTML (for viewer) and plain text (for export) formats
  - Create `backend/reports/templates/` directory with Jinja2 templates:
    - `report_base.html.j2` — HTML report template with CSS styling
    - `report_base.txt.j2` — Plain text version for export
    - `section_findings.j2` — Reusable finding block template
    - `section_evidence.j2` — Evidence matrix template
  - Create `backend/reports/nlg.py` — natural language generation helpers:
    - `risk_narrative(risk_level: str, score: float, top_features: list) -> str` — generates Bahasa Indonesia risk description
    - `feature_explanation(feature_name: str, shap_value: float, direction: str) -> str` — human-readable feature contribution sentence
    - `recommendation_text(finding_type: str, severity: str) -> str` — maps finding types to standardized recommendations
    - All text output in Bahasa Indonesia with proper grammatical structure
  - Create `tests/test_report_generator.py`:
    - Test report generation with mock risk assessment + XAI data → verify all 6 sections present
    - Test Bahasa Indonesia output → verify no English text in report body
    - Test HTML and text format outputs
    - Test with missing XAI layer data → verify graceful degradation (section shows "Data tidak tersedia")
    - Test NLG helpers → verify grammatically correct Bahasa Indonesia output

  **Must NOT do**:
  - Do NOT hardcode report text — all narrative from Jinja2 templates + NLG functions
  - Do NOT use English in report body — output must be Bahasa Indonesia (variable names/keys in English are OK)
  - Do NOT require all XAI layers to be present — report must degrade gracefully if any layer failed
  - Do NOT embed CSS inline in generator code — keep in template files
  - Do NOT use markdown for report output — use HTML (for viewer) and plain text (for export)
  - Do NOT hallucinate IIA format — use the actual structure from IIA 2025 standards (Executive Summary, Findings, Evidence, Recommendations)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Report generation combines NLG, Jinja2 templating, IIA compliance, and Bahasa Indonesia language — moderately complex but well-scoped
  - **Skills**: []
    - No specialized skills needed — Python templating + string formatting
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction
    - `writing`: This is code generation, not prose writing

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 12, 14)
  - **Blocks**: T14 (API report endpoint), T19 (frontend report viewer component)
  - **Blocked By**: T2 (needs Pydantic schemas for report structure), T6 (needs feature engineering output format)

  **References**:

  **Pattern References** (existing code to follow):
  - `backend/xai/shap_explainer.py` (T10) — How XAI output is structured; report must consume this format
  - `backend/xai/dice_explainer.py` (T12) — DiCE output format; report evidence matrix references counterfactual data
  - `backend/config/settings.yaml` (T4) — Runtime config may override report language, institution name, etc.

  **API/Type References** (contracts to implement against):
  - `backend/schemas/report.py` (T2) — `ReportOutput` Pydantic model: `{"report_id": str, "tender_id": str, "generated_at": datetime, "format": "html"|"text", "sections": [...], "metadata": {...}}`
  - `backend/schemas/risk.py` (T2) — `RiskAssessment` model that feeds into report generator

  **External References** (libraries and frameworks):
  - Jinja2 docs: https://jinja.palletsprojects.com/en/3.1.x/templates/ — Template syntax, filters, macros
  - IIA Standards 2025: The report structure follows professional audit report format (Executive Summary → Findings → Evidence → Recommendations → Appendix)

  **Proposal References** (UPGRADE 3):
  - Lines 151-153: "Sistem otomatis menghasilkan laporan pra-investigasi berformat IIA 2025" — the exact feature specification
  - Lines 104-124: Feature descriptions that must appear as human-readable explanations in report findings
  - Lines 137-148: Oracle Sandwich layers — each layer's output feeds into the evidence matrix section

  **Research References** (DEEP_RESEARCH_SYNTHESIS.md):
  - Lines 210-230: Oracle Sandwich architecture — how XAI layers combine into a unified explanation narrative
  - Lines 171-193: opentender.net data fields — tender metadata that appears in report header

  **WHY Each Reference Matters**:
  - T10/T12 XAI output formats: Report must correctly parse and narrate each layer's output — wrong format = broken evidence matrix
  - UPGRADE 3 lines 151-153: This is the EXACT competition requirement — "laporan pra-investigasi berformat IIA 2025"
  - IIA Standards: Judges will evaluate whether report follows professional audit format; must be credible

  **Acceptance Criteria**:

  - [ ] `backend/reports/generator.py` exists with `generate_report()` function
  - [ ] `backend/reports/nlg.py` exists with NLG helper functions
  - [ ] `backend/reports/templates/` contains 4 Jinja2 template files
  - [ ] `pytest tests/test_report_generator.py -q` → PASS (5+ tests, 0 failures)
  - [ ] Generated report contains all 6 IIA sections (Ringkasan Eksekutif through Lampiran)
  - [ ] Report body is in Bahasa Indonesia (no English sentences in body text)
  - [ ] Both HTML and plain text formats generate successfully
  - [ ] Missing XAI layer data → section shows "Data tidak tersedia" (graceful degradation)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Happy path — generate full report for high-risk tender
    Tool: Bash (python)
    Preconditions: Mock risk_assessment, xai_results (all 5 layers), graph_results available
    Steps:
      1. python -c "
         from backend.reports.generator import generate_report
         import json
         # Mock data for all XAI layers
         risk = {'risk_level': 'Risiko Kritis', 'score': 0.92, 'model': 'ensemble'}
         xai = {
           'shap': {'top_features': [{'name': 'n_bidders', 'value': -0.45}]},
           'dice': {'counterfactuals': [{'changes': [{'feature': 'n_bidders', 'from': 1, 'to': 3}]}]},
           'anchors': {'rules': ['IF n_bidders = 1 AND price_ratio > 0.95 THEN high_risk']},
           'benford': {'result': 'anomaly_detected', 'p_value': 0.003},
           'graph': {'community_id': 5, 'community_size': 8}
         }
         graph = {'communities': [{'id': 5, 'members': ['PT A', 'PT B'], 'risk': 'high'}]}
         report = generate_report('TND-2023-001', risk, xai, graph)
         assert report.format == 'html'
         assert 'Ringkasan Eksekutif' in report.sections[0].title
         assert 'Temuan Risiko' in report.sections[2].title
         assert 'Rekomendasi' in report.sections[4].title
         assert len(report.sections) == 6
         print('PASS: Full report generated with all 6 sections')
         "
      2. Verify report body text contains Bahasa Indonesia (check for 'terhadap', 'risiko', 'berdasarkan')
      3. Verify no English sentences in body (section titles/keys can be English)
    Expected Result: Complete IIA-format report with 6 sections, Bahasa Indonesia narrative, all XAI evidence referenced
    Failure Indicators: Missing sections, English body text, KeyError on XAI data, empty findings
    Evidence: .sisyphus/evidence/task-13-report-happy-path.txt

  Scenario: Graceful degradation — missing DiCE and Benford layers
    Tool: Bash (python)
    Preconditions: Only SHAP and Anchors XAI data available (DiCE and Benford returned errors)
    Steps:
      1. python -c "
         from backend.reports.generator import generate_report
         risk = {'risk_level': 'Risiko Tinggi', 'score': 0.78, 'model': 'xgboost'}
         xai = {
           'shap': {'top_features': [{'name': 'winner_repeat_count', 'value': 0.32}]},
           'dice': None,  # Layer failed
           'anchors': {'rules': ['IF winner_repeat_count > 3 THEN high_risk']},
           'benford': None,  # Layer not applicable
           'graph': {'community_id': None}
         }
         report = generate_report('TND-2023-002', risk, xai, {})
         html_content = report.to_html()
         assert 'Data tidak tersedia' in html_content
         assert 'Ringkasan Eksekutif' in html_content
         assert len(report.sections) == 6  # All sections present even with missing data
         print('PASS: Report generated with graceful degradation')
         "
    Expected Result: Report still generates all 6 sections; missing layers show "Data tidak tersedia"
    Failure Indicators: Exception on None XAI data, missing sections, crash on empty graph
    Evidence: .sisyphus/evidence/task-13-report-degradation.txt

  Scenario: NLG helpers — verify Bahasa Indonesia output quality
    Tool: Bash (python)
    Preconditions: NLG module available
    Steps:
      1. python -c "
         from backend.reports.nlg import risk_narrative, feature_explanation, recommendation_text
         narrative = risk_narrative('Risiko Kritis', 0.92, [{'name': 'n_bidders', 'value': -0.45}])
         assert isinstance(narrative, str)
         assert len(narrative) > 50  # Not a stub
         assert 'risiko' in narrative.lower()
         feat_exp = feature_explanation('n_bidders', -0.45, 'decrease')
         assert 'n_bidders' in feat_exp or 'jumlah penawar' in feat_exp
         rec = recommendation_text('single_bidder', 'Kritis')
         assert isinstance(rec, str)
         assert len(rec) > 30
         print('PASS: NLG helpers produce valid Bahasa Indonesia text')
         "
    Expected Result: All NLG functions return non-empty Bahasa Indonesia strings
    Failure Indicators: Empty strings, English output, assertion errors
    Evidence: .sisyphus/evidence/task-13-nlg-quality.txt
  ```

  **Evidence to Capture:**
  - [ ] task-13-report-happy-path.txt — Full report output with all sections
  - [ ] task-13-report-degradation.txt — Graceful degradation with missing layers
  - [ ] task-13-nlg-quality.txt — NLG helper output verification

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(reports): auto pre-investigation report generator with IIA 2025 format and Bahasa Indonesia NLG`
  - Files: `backend/reports/generator.py`, `backend/reports/nlg.py`, `backend/reports/templates/*.j2`, `tests/test_report_generator.py`
  - Pre-commit: `pytest tests/test_report_generator.py -q`


### Task 14 — API Endpoints (Inference, XAI, Graph, Reports, Injection, Health)

  **Wave**: 3 (starts after T10-T13 complete; final task in Wave 3)
  **Depends on**: T4 (runtime config system), T10 (SHAP/Anchors), T11 (ONNX inference), T12 (DiCE), T13 (report generator)
  **Blocks**: T15-T19 (all frontend tasks consume these endpoints), T20 (offline bundle serves this API)

  **What to do**:
  - Create `backend/api/app.py` — FastAPI application factory:
    - `create_app() -> FastAPI` — initializes app with CORS, lifespan handler, error handlers
    - Lifespan handler: load ONNX models, initialize XAI explainers, build DiCE cache, load graph data on startup
    - Global exception handler: catch unhandled errors, return structured JSON error responses
    - CORS configured for localhost origins (React dev server + production)
    - Health check at root: `GET /` returns `{"status": "healthy", "version": str, "models_loaded": bool}`
  - Create `backend/api/routes.py` — all API route definitions:
    - **Prediction endpoint**: `GET /api/tender/{tender_id}/predict`
      - Load tender from SQLite, run ONNX inference, return `{"tender_id": str, "risk_level": str, "risk_score": float, "model": str, "ensemble_agreement": bool, "individual_scores": {...}}`
      - Apply runtime config filters (risk_threshold, institution_filter) from T4
    - **XAI endpoint**: `GET /api/tender/{tender_id}/explain`
      - Orchestrate all 5 Oracle Sandwich layers in parallel: SHAP, DiCE (async), Anchors, Leiden graph, Benford
      - Use `asyncio.gather()` with individual timeouts per layer
      - Return `{"tender_id": str, "layers": {"shap": {...}, "dice": {...}, "anchors": {...}, "graph": {...}, "benford": {...}}, "total_time_ms": float}`
      - If any layer fails/times out, return partial result with `"status": "timeout"` or `"error"` for that layer
    - **Graph endpoint**: `GET /api/graph/communities`
      - Return Leiden communities with risk scores: `{"communities": [{"id": int, "members": [...], "risk_score": float, "size": int}]}`
      - Support query params: `?min_size=3&min_risk=0.5` for filtering
    - **Report endpoint**: `GET /api/tender/{tender_id}/report?format=html|text`
      - Generate IIA report using T13 generator, return HTML or plain text
      - Default format: HTML
    - **Injection endpoint**: `PUT /api/config/inject` (delegates to T4 runtime config)
      - Accept JSON body with any combination of: `risk_threshold`, `institution_filter`, `sector_filter`, `date_range`, `benford_enabled`, `custom_params`
      - Pydantic validation → reject invalid, apply valid → return `{"applied": [...], "rejected": [...], "current_config": {...}}`
    - **Health endpoint**: `GET /api/health`
      - Return detailed health: models loaded, DB connected, XAI ready, memory usage, uptime
    - **Tender list endpoint**: `GET /api/tenders?page=1&per_page=50&risk_level=Risiko+Kritis&sort=risk_score`
      - Paginated tender list with filters and sorting
      - Return `{"items": [...], "total": int, "page": int, "per_page": int}`
  - Create `backend/api/dependencies.py` — FastAPI dependency injection:
    - `get_db()` — SQLite session dependency
    - `get_model()` — ONNX model singleton
    - `get_config()` — Runtime config singleton
    - `get_xai_orchestrator()` — XAI layer orchestrator
  - Create `backend/api/schemas.py` — API-specific Pydantic response models (if not already in T2):
    - `PredictionResponse`, `ExplanationResponse`, `CommunityResponse`, `InjectionRequest`, `InjectionResponse`, `HealthResponse`, `TenderListResponse`
  - Create `tests/test_api_routes.py`:
    - Use FastAPI TestClient (`httpx.AsyncClient` or `TestClient`)
    - Test each endpoint: correct status code, response structure, error handling
    - Test injection endpoint: valid params applied, invalid params rejected
    - Test XAI endpoint: partial failure returns partial result (not 500)
    - Test pagination: page bounds, empty results, sort order

  **Must NOT do**:
  - Do NOT use synchronous blocking calls for XAI layers — use `asyncio.gather()` with timeouts
  - Do NOT return 500 errors for XAI layer timeouts — return partial results with per-layer status
  - Do NOT hardcode port numbers — read from config or auto-detect
  - Do NOT skip Pydantic response models — all endpoints must have typed responses
  - Do NOT implement business logic in routes — routes are thin wrappers calling service modules
  - Do NOT add authentication/authorization — localhost-only app, not needed
  - Do NOT add rate limiting — single-user demo app

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: FastAPI route setup is well-understood but requires careful integration of 6+ backend modules with proper async orchestration
  - **Skills**: []
    - No specialized skills needed — pure FastAPI/Python async work
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction
    - `frontend-ui-ux`: This is backend API only

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on most Wave 3 tasks completing first)
  - **Parallel Group**: Wave 3 (final task, starts after T10-T13)
  - **Blocks**: T15-T19 (all frontend tasks), T20 (offline bundle)
  - **Blocked By**: T4 (config), T10 (SHAP/Anchors), T11 (ONNX), T12 (DiCE), T13 (reports)

  **References**:

  **Pattern References** (existing code to follow):
  - `backend/config/runtime_config.py` (T4) — Runtime config class that injection endpoint delegates to
  - `backend/models/onnx_inference.py` (T11) — ONNX model loading + inference functions called by predict endpoint
  - `backend/xai/shap_explainer.py` (T10) — XAI explainer interface; explain endpoint calls all explainers
  - `backend/xai/dice_explainer.py` (T12) — Async DiCE interface with timeout
  - `backend/reports/generator.py` (T13) — Report generation function called by report endpoint
  - `backend/graph/leiden.py` (T7) — Community detection results for graph endpoint

  **API/Type References** (contracts to implement against):
  - `backend/schemas/` (T2) — All Pydantic models: TenderRecord, RiskAssessment, XAIResult, etc.
  - `backend/config/settings.yaml` (T4) — `api.host`, `api.port`, `api.cors_origins` settings

  **External References** (libraries and frameworks):
  - FastAPI docs: https://fastapi.tiangolo.com/tutorial/ — Route definition, dependency injection, lifespan
  - FastAPI async: https://fastapi.tiangolo.com/async/ — async endpoint patterns
  - httpx AsyncClient: https://www.python-httpx.org/async/ — For testing async endpoints

  **Proposal References** (UPGRADE 3):
  - Lines 155-168: Tech stack specification — FastAPI as backend framework
  - Lines 170-179: Runtime injection specification — the injection endpoint must match this description exactly
  - Lines 137-148: Oracle Sandwich — the explain endpoint orchestrates all 5 layers

  **WHY Each Reference Matters**:
  - T4 runtime config: Injection endpoint is the COMPETITION REQUIREMENT — "aplikasi WAJIB mampu menerima variabel/logika dadakan"
  - T10-T13 modules: API is a thin wrapper — must call existing modules correctly, not reimplement logic
  - UPGRADE 3 lines 170-179: Judges will test injection endpoint live — must match proposal description exactly

  **Acceptance Criteria**:

  - [ ] `backend/api/app.py` exists with `create_app()` function
  - [ ] `backend/api/routes.py` exists with all 7 endpoint definitions
  - [ ] `backend/api/dependencies.py` exists with DI providers
  - [ ] `pytest tests/test_api_routes.py -q` → PASS (10+ tests, 0 failures)
  - [ ] `GET /api/tender/{id}/predict` returns prediction with risk_level and score
  - [ ] `GET /api/tender/{id}/explain` returns 5-layer XAI response (partial OK on timeout)
  - [ ] `GET /api/graph/communities` returns Leiden communities with filtering
  - [ ] `GET /api/tender/{id}/report` returns IIA-format HTML report
  - [ ] `PUT /api/config/inject` validates and applies runtime parameters
  - [ ] `GET /api/health` returns detailed system health
  - [ ] All endpoints return Pydantic-validated JSON responses

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Happy path — predict risk for a tender
    Tool: Bash (curl)
    Preconditions: Server running on localhost, at least one tender in DB
    Steps:
      1. curl -s http://localhost:{port}/api/health | python -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='healthy'; print('Health OK')"
      2. curl -s http://localhost:{port}/api/tender/TND-2023-001/predict | python -c "
         import sys,json
         d=json.load(sys.stdin)
         assert 'risk_level' in d
         assert d['risk_level'] in ['Aman','Perlu Pantauan','Risiko Tinggi','Risiko Kritis']
         assert 0 <= d['risk_score'] <= 1
         assert 'ensemble_agreement' in d
         print(f'PASS: {d["risk_level"]} (score={d["risk_score"]:.3f})')
         "
    Expected Result: Valid prediction response with Indonesian risk level and score 0-1
    Failure Indicators: 404 (tender not found), 500 (model error), missing fields, score out of range
    Evidence: .sisyphus/evidence/task-14-predict-happy.txt

  Scenario: XAI explain — all 5 layers return results
    Tool: Bash (curl)
    Preconditions: Server running, ONNX models loaded, XAI explainers initialized
    Steps:
      1. curl -s http://localhost:{port}/api/tender/TND-2023-001/explain | python -c "
         import sys,json
         d=json.load(sys.stdin)
         assert 'layers' in d
         expected_layers = ['shap','dice','anchors','graph','benford']
         for layer in expected_layers:
           assert layer in d['layers'], f'Missing layer: {layer}'
           status = d['layers'][layer].get('status', 'ok')
           assert status in ['ok','timeout','not_applicable','error'], f'Bad status for {layer}: {status}'
         assert d['total_time_ms'] > 0
         print(f'PASS: All 5 layers present, total={d["total_time_ms"]:.0f}ms')
         "
    Expected Result: All 5 XAI layers present in response with valid status per layer
    Failure Indicators: Missing layers, 500 error, total_time_ms=0
    Evidence: .sisyphus/evidence/task-14-explain-all-layers.txt

  Scenario: Runtime injection — apply and verify config change
    Tool: Bash (curl)
    Preconditions: Server running with default config
    Steps:
      1. curl -s -X PUT http://localhost:{port}/api/config/inject \
           -H 'Content-Type: application/json' \
           -d '{"risk_threshold": 0.8, "institution_filter": "Kemenkeu", "invalid_field_xyz": -999}' \
           | python -c "
         import sys,json
         d=json.load(sys.stdin)
         assert 'applied' in d
         assert 'risk_threshold' in d['applied']
         assert 'institution_filter' in d['applied']
         assert 'rejected' in d
         # invalid_field_xyz should be in custom_params or rejected
         print(f'PASS: Applied={d["applied"]}, Rejected={d["rejected"]}')
         "
      2. curl -s http://localhost:{port}/api/tender/TND-2023-001/predict | python -c "
         import sys,json; d=json.load(sys.stdin)
         # Verify injection took effect (filtered results)
         print(f'Post-injection prediction: {d["risk_level"]} (score={d["risk_score"]:.3f})')
         "
    Expected Result: Valid params applied, invalid captured in rejected/custom_params, subsequent predict uses new config
    Failure Indicators: 422 (validation error on valid params), 500, applied list empty
    Evidence: .sisyphus/evidence/task-14-injection-roundtrip.txt

  Scenario: XAI partial failure — one layer times out, others still return
    Tool: Bash (curl)
    Preconditions: Server running (DiCE may timeout on complex tender)
    Steps:
      1. curl -s http://localhost:{port}/api/tender/TND-2023-COMPLEX/explain | python -c "
         import sys,json
         d=json.load(sys.stdin)
         assert 'layers' in d
         # Even if one layer fails, response should be 200 with partial data
         statuses = {k: v.get('status','ok') for k,v in d['layers'].items()}
         print(f'Layer statuses: {statuses}')
         # At minimum, SHAP should always succeed (fastest)
         assert d['layers']['shap'].get('status','ok') == 'ok'
         print('PASS: Partial failure handled gracefully')
         "
    Expected Result: HTTP 200 with partial XAI results; failed layers marked with status
    Failure Indicators: HTTP 500, empty response, SHAP also failed
    Evidence: .sisyphus/evidence/task-14-explain-partial-failure.txt
  ```

  **Evidence to Capture:**
  - [ ] task-14-predict-happy.txt — Prediction endpoint response
  - [ ] task-14-explain-all-layers.txt — Full 5-layer XAI response
  - [ ] task-14-injection-roundtrip.txt — Injection apply + verify roundtrip
  - [ ] task-14-explain-partial-failure.txt — Partial failure handling

  **Commit**: YES (groups with Wave 3)
  - Message: `feat(api): FastAPI endpoints for inference, XAI, graph, reports, and runtime injection`
  - Files: `backend/api/app.py`, `backend/api/routes.py`, `backend/api/dependencies.py`, `backend/api/schemas.py`, `tests/test_api_routes.py`
  - Pre-commit: `pytest tests/test_api_routes.py -q`

---

### Task 15 — Dashboard Layout + Risk Overview + Tender Table

**Wave**: 4
**Depends on**: T5 (SQLite schema), T14 (API endpoints)
**Blocks**: T20 (offline bundle)

**What to do**:
- Create the main React dashboard page at `frontend/src/pages/Dashboard.tsx`.
- Implement a **Risk Distribution Chart** using Plotly: stacked bar or donut chart showing tender counts by risk level (Aman / Perlu Pantauan / Risiko Tinggi / Risiko Kritis) with Indonesian labels.
- Implement a **Summary Stats Panel**: total tenders analyzed, high-risk count, average risk score, injection config status (active filters displayed).
- Implement a **Tender Table** using a virtualized/paginated data table component:
  - Columns: Tender ID, Institution, HPS, Contract Value, Risk Level (color-coded badge), Risk Score, Ensemble Agreement.
  - Sortable by any column. Filterable by risk level, institution, year.
  - Row click navigates to Tender Detail page (route: `/tender/:id`).
- Implement a **Tender Detail Page** at `frontend/src/pages/TenderDetail.tsx`:
  - Shows prediction result (risk level, score, ensemble breakdown).
  - Tabs or sections for each XAI layer (placeholder containers — actual viz in T16-T18).
  - Link to generate/view report (placeholder — actual in T19).
- Set up React Router (`react-router-dom`) with routes: `/` (Dashboard), `/tender/:id` (Detail).
- Create shared layout component with sidebar navigation at `frontend/src/components/Layout.tsx`.
- Create API client module at `frontend/src/api/client.ts` using `fetch` (no axios — fewer deps for offline).
  - Functions: `fetchTenders()`, `fetchTenderPrediction(id)`, `fetchTenderExplanation(id)`, `fetchGraphCommunities()`, `fetchTenderReport(id)`, `applyInjection(params)`.
  - Base URL from environment variable `VITE_API_URL` defaulting to `http://localhost:8000`.
- Create React hooks at `frontend/src/hooks/`:
  - `useTenders()` — fetches tender list with pagination/filter state.
  - `usePrediction(id)` — fetches prediction for a tender.
  - `useExplanation(id)` — fetches XAI explanation.
- Style with Tailwind CSS or CSS modules — clean, professional look matching procurement/government aesthetic (blues, grays, clean typography).
- All components must handle loading, error, and empty states gracefully.

**Must NOT do**:
- Do NOT implement XAI visualizations (SHAP plots, DiCE table, graph viz) — those are T16-T18.
- Do NOT implement map/geographic features — that is T18.
- Do NOT install axios, lodash, or heavy UI frameworks (Material UI, Ant Design) — keep bundle small for offline.
- Do NOT hardcode any API URLs — must use env variable.
- Do NOT implement PDF export — that is T19.

**Recommended Agent Profile**:
- **Category**: `visual-engineering`
  - Reason: This is pure frontend UI work — React components, layout, styling, data table, Plotly chart.
- **Skills**: [`playwright`]
  - `playwright`: Required for browser-based QA verification — opening dashboard, clicking rows, checking elements.
- **Skills Evaluated but Omitted**:
  - `frontend-ui-ux`: Could help with design decisions, but the task has clear layout specs already.

**Parallelization**:
- **Can Run In Parallel**: YES — with T16, T17, T18, T19 (all Wave 4)
- **Parallel Group**: Wave 4
- **Blocks**: T20
- **Blocked By**: T5, T14

**References**:

**Pattern References** (existing code to follow):
- `frontend/src/api/client.ts` (to be created) — API client pattern: simple fetch wrappers, no external HTTP libraries
- `backend/api/routes.py` (T14 output) — All available API endpoints and their response shapes
- `backend/api/schemas.py` (T14 output) — Pydantic response schemas to mirror in TypeScript types

**API/Type References** (contracts to implement against):
- `frontend/src/types/` (T5 output) — TypeScript type definitions for Tender, Prediction, XAI layers
- `GET /api/tender/{id}/predict` response: `{risk_level: string, risk_score: float, ensemble_agreement: string}`
- `GET /api/tender/{id}/explain` response: `{layers: {shap: {...}, dice: {...}, anchors: {...}, graph: {...}, benford: {...}}, total_time_ms: float}`
- `PUT /api/config/inject` request: `{risk_threshold?: float, institution_filter?: string, ...}`

**External References** (libraries and frameworks):
- Plotly.js React: `react-plotly.js` — for Risk Distribution Chart (donut/bar)
- React Router: `react-router-dom` v6+ — routing setup
- UPGRADE 3 lines 104-124 — Feature descriptions for table column tooltips
- UPGRADE 3 lines 137-148 — Oracle Sandwich XAI layer names for Detail page tab labels

**WHY Each Reference Matters**:
- `backend/api/schemas.py` → TypeScript types MUST match Pydantic response schemas exactly for type safety
- UPGRADE 3 lines 137-148 → Tab labels and layer descriptions must match proposal language for judge alignment
- `backend/api/routes.py` → API client must call correct endpoints with correct HTTP methods

**Acceptance Criteria**:

- [ ] `frontend/src/pages/Dashboard.tsx` exists with risk chart + stats + tender table
- [ ] `frontend/src/pages/TenderDetail.tsx` exists with prediction display + XAI tab containers
- [ ] `frontend/src/components/Layout.tsx` exists with sidebar navigation
- [ ] `frontend/src/api/client.ts` exists with all 6 API functions
- [ ] `frontend/src/hooks/useTenders.ts` and `usePrediction.ts` exist
- [ ] React Router configured with `/` and `/tender/:id` routes
- [ ] Risk chart renders with Plotly (4 risk categories, Indonesian labels)
- [ ] Tender table is sortable, filterable, and row-clickable
- [ ] All components handle loading/error/empty states
- [ ] `npm run build` (or `bun run build`) completes with 0 errors

**QA Scenarios (MANDATORY):**

```
Scenario: Happy path — Dashboard loads with risk chart and tender table
  Tool: Playwright (playwright skill)
  Preconditions: FastAPI backend running on localhost:{port} with test data, React dev server on localhost:5173
  Steps:
    1. Navigate to http://localhost:5173/
    2. Wait for selector `.risk-chart` (Plotly container) to be visible, timeout 10s
    3. Assert `.risk-chart` contains SVG elements (Plotly renders SVG)
    4. Assert `.stats-panel` contains text matching /\d+ tender/i (total count)
    5. Assert `table.tender-table` or `[data-testid="tender-table"]` is visible
    6. Assert table has at least 1 row with cells containing Tender ID pattern /TND-\d{4}-\d{3}/
    7. Assert risk badges are color-coded: find `.badge-risiko-kritis` (red), `.badge-aman` (green)
    8. Take screenshot: .sisyphus/evidence/task-15-dashboard-happy.png
  Expected Result: Dashboard fully rendered with chart, stats, and populated tender table
  Failure Indicators: Blank page, missing chart, empty table, JavaScript console errors, 404 on API calls
  Evidence: .sisyphus/evidence/task-15-dashboard-happy.png

Scenario: Tender Detail — click row navigates to detail page with prediction
  Tool: Playwright (playwright skill)
  Preconditions: Dashboard loaded with tender data
  Steps:
    1. Navigate to http://localhost:5173/
    2. Wait for `[data-testid="tender-table"]` visible, timeout 10s
    3. Click first row in tender table
    4. Wait for URL to match /\/tender\/TND-.*/ (route changed)
    5. Assert `.prediction-result` is visible with text containing one of: Aman, Perlu Pantauan, Risiko Tinggi, Risiko Kritis
    6. Assert `.risk-score` displays a number between 0 and 1
    7. Assert XAI tabs/sections exist: find elements with text SHAP, DiCE, Anchors, Graph, Benford
    8. Take screenshot: .sisyphus/evidence/task-15-tender-detail.png
  Expected Result: Detail page shows prediction + risk score + XAI section headers
  Failure Indicators: Navigation doesn't work, 404 page, missing prediction data, XAI tabs absent
  Evidence: .sisyphus/evidence/task-15-tender-detail.png

Scenario: Error handling — API unavailable shows error state
  Tool: Playwright (playwright skill)
  Preconditions: React dev server running but backend NOT running
  Steps:
    1. Navigate to http://localhost:5173/
    2. Wait 5s for API calls to fail
    3. Assert an error indicator is visible: `.error-state` or text matching /gagal|error|tidak tersedia/i
    4. Assert page does NOT show a blank white screen (some UI structure still visible)
    5. Take screenshot: .sisyphus/evidence/task-15-error-state.png
  Expected Result: Graceful error UI shown, not a blank screen or unhandled exception
  Failure Indicators: White screen, JavaScript error in console with no user-facing message, infinite loading spinner
  Evidence: .sisyphus/evidence/task-15-error-state.png
```

**Evidence to Capture:**
- [ ] task-15-dashboard-happy.png — Full dashboard with chart, stats, table
- [ ] task-15-tender-detail.png — Tender detail page with prediction + XAI tabs
- [ ] task-15-error-state.png — Graceful error handling when API unavailable

**Commit**: YES (groups with Wave 4)
- Message: `feat(ui): React dashboard with risk chart, tender table, detail page, and API client`
- Files: `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/TenderDetail.tsx`, `frontend/src/components/Layout.tsx`, `frontend/src/api/client.ts`, `frontend/src/hooks/useTenders.ts`, `frontend/src/hooks/usePrediction.ts`
- Pre-commit: `cd frontend && npm run build`

---

### Task 16 — SHAP/XAI Visualization Components + DiCE Counterfactual Display

**Wave**: 4
**Depends on**: T5 (React scaffold), T10 (SHAP + Anchors backend), T12 (DiCE backend), T14 (API endpoints)
**Blocks**: T20 (offline bundle)

**What to do**:
- Create SHAP visualization components at `frontend/src/components/xai/`:
  - `ShapSummaryPlot.tsx` — Plotly horizontal bar chart showing global feature importance (top 15 features). Color-coded by impact direction (positive=red, negative=blue). Feature names in Indonesian where applicable.
  - `ShapWaterfallPlot.tsx` — Plotly waterfall chart for local (per-tender) SHAP explanation. Shows how each feature pushed the prediction from base value to final score.
- Create DiCE counterfactual display at `frontend/src/components/xai/DiceCounterfactual.tsx`:
  - Table showing the original values vs counterfactual values that would flip the prediction.
  - Highlight changed features with color coding (green = change needed, gray = unchanged).
  - Show "Apa yang harus berubah agar tender ini TIDAK ditandai?" as section header (matches proposal UPGRADE 3 line 144).
- Create Anchors rules display at `frontend/src/components/xai/AnchorRules.tsx`:
  - Display if-then rules from Anchors as readable cards/badges.
  - Show coverage and precision metadata when available.
  - Format: "JIKA [kondisi] MAKA [risiko tinggi]" — Indonesian rule labels.
- Create unified XAI panel component at `frontend/src/components/xai/XaiPanel.tsx`:
  - Tabs or accordion for each XAI layer: SHAP Global, SHAP Local, DiCE, Anchors.
  - Integrate into `TenderDetail.tsx` (T15) — replace placeholder containers.
  - Each layer tab shows loading/error/not_applicable states independently.
  - Display `total_time_ms` from API response as "Waktu analisis: X ms".
- Add `useExplanation(id)` hook enhancement (if not already in T15) to parse layer-specific data.
- All Plotly charts must be responsive (fill container width) and export-ready (Plotly config: `{displayModeBar: true, toImageButtonOptions: {format: 'png'}}`).

**Must NOT do**:
- Do NOT implement graph visualization — that is T17.
- Do NOT implement Benford visualization — include placeholder "Lihat analisis Benford" with the data from API but no custom chart (Benford data is statistical, not visual-heavy).
- Do NOT fetch data directly — use hooks from T15's API client.
- Do NOT install additional charting libraries beyond Plotly (already in T15).
- Do NOT use iframes or embed external URLs.

**Recommended Agent Profile**:
- **Category**: `visual-engineering`
  - Reason: Pure frontend React + Plotly visualization work. Requires understanding of chart design and data presentation.
- **Skills**: [`playwright`]
  - `playwright`: Required for browser-based QA — verifying charts render, tabs switch, data displays correctly.
- **Skills Evaluated but Omitted**:
  - `frontend-ui-ux`: Chart specs are detailed enough; no design ambiguity.

**Parallelization**:
- **Can Run In Parallel**: YES — with T15, T17, T18, T19 (all Wave 4)
- **Parallel Group**: Wave 4
- **Blocks**: T20
- **Blocked By**: T5, T10, T12, T14

**References**:

**Pattern References** (existing code to follow):
- `frontend/src/pages/TenderDetail.tsx` (T15 output) — XAI tab containers to fill with actual components
- `frontend/src/api/client.ts` (T15 output) — `fetchTenderExplanation(id)` function to use
- `frontend/src/hooks/useExplanation.ts` (T15 output) — Hook that provides XAI data per layer

**API/Type References** (contracts to implement against):
- `GET /api/tender/{id}/explain` response structure:
  - `layers.shap.global_summary: [{feature: str, importance: float, direction: str}]`
  - `layers.shap.local_waterfall: [{feature: str, base_value: float, contribution: float}]`
  - `layers.dice.counterfactuals: [{original: dict, counterfactual: dict, changed_features: list}]`
  - `layers.anchors.rules: [{rule: str, coverage: float, precision: float}]`
  - `layers.*.status: 'ok' | 'timeout' | 'not_applicable' | 'error'`

**External References** (libraries and frameworks):
- UPGRADE 3 line 143 — "SHAP summary plots" — Global layer
- UPGRADE 3 line 144 — "Apa yang harus berubah agar tender ini TIDAK ditandai?" — DiCE question
- UPGRADE 3 line 145 — "Aturan sederhana apa yang diikuti model?" — Anchors question
- DEEP_RESEARCH_SYNTHESIS.md lines 138-139 — DiCE-XGBoost (Microsoft) counterfactual explanations
- DEEP_RESEARCH_SYNTHESIS.md lines 141 — alibi (Seldon) Anchors explanations
- `react-plotly.js` docs: Bar chart, Waterfall chart configuration

**WHY Each Reference Matters**:
- UPGRADE 3 lines 143-145 → Section headers and questions MUST match proposal language exactly — judges will compare
- API response structure → Components MUST parse the exact JSON shape returned by T14 endpoints
- DiCE counterfactuals → Table must clearly show "what would need to change" — this is the XAI differentiator

**Acceptance Criteria**:

- [ ] `frontend/src/components/xai/ShapSummaryPlot.tsx` renders Plotly bar chart with top features
- [ ] `frontend/src/components/xai/ShapWaterfallPlot.tsx` renders Plotly waterfall for local explanation
- [ ] `frontend/src/components/xai/DiceCounterfactual.tsx` renders table with original vs counterfactual values
- [ ] `frontend/src/components/xai/AnchorRules.tsx` renders if-then rule cards
- [ ] `frontend/src/components/xai/XaiPanel.tsx` integrates all layers with tabs
- [ ] XaiPanel integrated into TenderDetail.tsx replacing placeholders
- [ ] Each tab handles loading/error/not_applicable states independently
- [ ] All Plotly charts are responsive and have export buttons
- [ ] `npm run build` completes with 0 errors

**QA Scenarios (MANDATORY):**

```
Scenario: Happy path — SHAP summary plot renders with feature bars
  Tool: Playwright (playwright skill)
  Preconditions: Backend running with XAI data for test tender, React dev server on localhost:5173
  Steps:
    1. Navigate to http://localhost:5173/tender/TND-2023-001
    2. Wait for `[data-testid="xai-panel"]` visible, timeout 15s
    3. Click tab/button with text "SHAP" or "Global"
    4. Wait for `.shap-summary-plot .plotly` to be visible, timeout 10s
    5. Assert SVG contains `<rect>` elements (Plotly bar chart rectangles)
    6. Assert at least 5 feature labels visible in the chart area
    7. Take screenshot: .sisyphus/evidence/task-16-shap-summary.png
  Expected Result: SHAP summary bar chart with ≥5 features, color-coded by direction
  Failure Indicators: Empty chart container, "No data" message, Plotly error, missing bars
  Evidence: .sisyphus/evidence/task-16-shap-summary.png

Scenario: DiCE counterfactual table displays changed features
  Tool: Playwright (playwright skill)
  Preconditions: Backend running with DiCE results for test tender
  Steps:
    1. Navigate to http://localhost:5173/tender/TND-2023-001
    2. Wait for `[data-testid="xai-panel"]` visible
    3. Click tab/button with text "DiCE" or "Counterfactual"
    4. Wait for `[data-testid="dice-table"]` or `.dice-counterfactual table` visible, timeout 10s
    5. Assert table header contains text matching /Original|Asli/i and /Counterfactual|Perubahan/i
    6. Assert at least 1 row has highlighted changed feature (CSS class `.changed-feature` or background-color not default)
    7. Assert section header contains "Apa yang harus berubah"
    8. Take screenshot: .sisyphus/evidence/task-16-dice-counterfactual.png
  Expected Result: Table showing original vs counterfactual values with changed features highlighted
  Failure Indicators: Empty table, all features shown as unchanged, missing header text
  Evidence: .sisyphus/evidence/task-16-dice-counterfactual.png

Scenario: XAI panel gracefully handles layer timeout/not_applicable
  Tool: Playwright (playwright skill)
  Preconditions: Backend running; DiCE layer configured to return status "timeout", Benford returns "not_applicable"
  Steps:
    1. Navigate to http://localhost:5173/tender/TND-2023-COMPLEX
    2. Wait for `[data-testid="xai-panel"]` visible
    3. Click DiCE tab — assert shows timeout message (text matching /timeout|waktu habis/i), NOT a crash
    4. Check Benford section — assert shows "not_applicable" or "Tidak berlaku" message
    5. Click SHAP tab — assert SHAP still renders correctly (not affected by other layer failures)
    6. Take screenshot: .sisyphus/evidence/task-16-xai-graceful-degrade.png
  Expected Result: Failed layers show informative messages; working layers unaffected
  Failure Indicators: Entire panel crashes, blank tabs, JavaScript error, SHAP affected by DiCE failure
  Evidence: .sisyphus/evidence/task-16-xai-graceful-degrade.png
```

**Evidence to Capture:**
- [ ] task-16-shap-summary.png — SHAP summary plot with feature importance bars
- [ ] task-16-dice-counterfactual.png — DiCE table with highlighted changes
- [ ] task-16-xai-graceful-degrade.png — Graceful degradation when layers fail

**Commit**: YES (groups with Wave 4)
- Message: `feat(ui): XAI visualization — SHAP plots, DiCE counterfactual table, Anchors rules display`
- Files: `frontend/src/components/xai/ShapSummaryPlot.tsx`, `frontend/src/components/xai/ShapWaterfallPlot.tsx`, `frontend/src/components/xai/DiceCounterfactual.tsx`, `frontend/src/components/xai/AnchorRules.tsx`, `frontend/src/components/xai/XaiPanel.tsx`
- Pre-commit: `cd frontend && npm run build`

---

### Task 17 — Cartel Graph Visualization (NetworkX → D3.js Force-Directed)

**Wave**: 4
**Depends on**: T5 (SQLite schema — community data stored), T7 (Leiden community detection — produces graph JSON), T14 (API endpoints — `/api/graph/communities` serves graph data)
**Blocks**: T20 (offline bundle)

**What to do**:
- Create a force-directed graph visualization component at `frontend/src/components/graph/CartelGraph.tsx` using **D3.js** (`d3-force`, `d3-selection`, `d3-zoom`).
- The component receives graph data from the backend endpoint `GET /api/graph/communities` which returns:
  ```json
  {
    "nodes": [{"id": "vendor_001", "name": "PT Maju Jaya", "community": 0, "degree": 5, "phantom_score": 0.8}],
    "edges": [{"source": "vendor_001", "target": "vendor_002", "weight": 3, "shared_tenders": ["TND-001", "TND-002"]}],
    "communities": [{"id": 0, "size": 4, "avg_risk": 0.85, "label": "Suspected Cartel A"}]
  }
  ```
- **Nodes** = vendor companies (bidders). Size proportional to `degree` (number of co-bidding relationships). Color by `community` assignment from Leiden algorithm — use a categorical color palette (d3.schemeTableau10 or similar, min 10 distinct colors).
- **Edges** = co-bidding relationships (two vendors bid on same tender). Width proportional to `weight` (number of shared tenders). Tooltip on hover shows shared tender IDs.
- **Community clusters**: Nodes in the same Leiden community should cluster visually via force simulation (use `d3.forceCluster` or custom centroid force). Draw a translucent convex hull or boundary around each community.
- **Interactivity**:
  - **Zoom & pan**: `d3.zoom()` with smooth transitions.
  - **Node hover**: Highlight all edges connected to hovered node; dim unrelated nodes (opacity 0.2). Show tooltip: vendor name, community, phantom bidder score, degree.
  - **Node click**: Select vendor — show detail sidebar/panel with: vendor name, community membership, all connected tenders (linked to Tender Detail page `/tender/:id`), phantom score, interlocking directorates if any.
  - **Community filter**: Dropdown or legend that lets user isolate a single community (fade others to 0.1 opacity).
  - **Risk coloring toggle**: Button to switch node coloring from community-based to risk-based (red=high, yellow=medium, green=low) using `phantom_score`.
- **Layout**: Force simulation parameters tuned for readability:
  - `forceLink().distance(d => 100 / d.weight)` — stronger links pull closer.
  - `forceManyBody().strength(-200)` — enough repulsion to prevent overlap.
  - `forceCollide().radius(d => nodeRadius(d) + 5)` — prevent node overlap.
  - `forceCenter()` — center the graph in the SVG viewport.
  - Simulation should stabilize within 300 ticks, then stop (not continuously drain CPU).
- **Legend**: Color-coded legend showing community labels and sizes. Include total node/edge counts.
- **Empty state**: When no graph data available, show informative message: "Tidak ada data graf komunitas. Jalankan analisis Leiden terlebih dahulu."
- **Performance**: For graphs with >500 nodes, implement canvas-based rendering (`d3-force` with canvas instead of SVG) to maintain 60fps. Add a toggle: SVG (interactive, <500 nodes) vs Canvas (performant, >500 nodes).
- Create wrapper component `frontend/src/components/graph/GraphPanel.tsx` that:
  - Fetches data via `useGraphCommunities()` hook (calls `GET /api/graph/communities`).
  - Handles loading spinner, error state, empty state.
  - Renders `CartelGraph` with fetched data.
  - Provides toolbar: zoom reset button, community filter dropdown, risk coloring toggle, SVG/Canvas toggle.
- Integrate `GraphPanel` into the Tender Detail page's "Graf" tab (T15 created placeholder containers for XAI layer tabs — this fills the Graph tab).
- Install D3 dependencies: `npm install d3 @types/d3` in frontend.

**Must NOT do**:
- Do NOT use a heavy graph library like Cytoscape.js or vis.js — D3.js is lighter for offline bundle and gives full control over rendering.
- Do NOT implement real-time graph updates or WebSocket connections — graph is static per analysis run.
- Do NOT add 3D visualization — 2D force-directed is sufficient for demo.
- Do NOT fetch graph data on every tab switch — cache in React state or use SWR/React Query stale-while-revalidate.
- Do NOT implement GAT attention weights visualization — that's beyond scope (mentioned in research but not in proposal).

**Recommended Agent Profile**:
> Select category + skills based on task domain. Justify each choice.
- **Category**: `visual-engineering`
  - Reason: This is a complex interactive data visualization task requiring D3.js force-directed graph rendering, SVG manipulation, zoom/pan interactions, and visual design decisions (color palettes, convex hulls, tooltips).
- **Skills**: [`playwright`]
  - `playwright`: Needed for QA scenarios — must open browser, interact with graph (zoom, hover, click nodes), take screenshots of rendered graph visualization.
- **Skills Evaluated but Omitted**:
  - `frontend-ui-ux`: Graph visualization is a specialized D3 task, not general UI/UX layout work. The visual-engineering category already covers this.

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 4 (with Tasks 15, 16, 18, 19)
- **Blocks**: T20 (offline bundle needs all frontend components)
- **Blocked By**: T5 (SQLite schema), T7 (Leiden community detection), T14 (API endpoints)

**References** (CRITICAL — Be Exhaustive):

**Pattern References** (existing code to follow):
- `frontend/src/components/xai/XaiPanel.tsx` (T16) — Tab-based panel pattern; GraphPanel integrates as one of the tabs.
- `frontend/src/hooks/useExplanation.ts` (T15) — Hook pattern for fetching backend data; copy for `useGraphCommunities()`.
- `frontend/src/api/client.ts` (T15) — `fetchGraphCommunities()` function already defined here; use it in the hook.
- `frontend/src/pages/TenderDetail.tsx` (T15) — Contains placeholder tab containers where GraphPanel slots in.

**API/Type References** (contracts to implement against):
- `backend/app/routers/graph.py` (T14) — `GET /api/graph/communities` endpoint; defines the response JSON schema (nodes, edges, communities arrays).
- `backend/app/models/schemas.py` (T3) — Pydantic response model `GraphCommunityResponse` defining exact field names and types.
- `backend/app/services/cartel_detection.py` (T7) — Leiden detection service; produces the graph JSON consumed by this component. Check `community` field type (int) and `weight` field semantics.

**External References** (libraries and frameworks):
- D3.js force simulation: https://d3js.org/d3-force — `forceSimulation`, `forceLink`, `forceManyBody`, `forceCenter`, `forceCollide` API.
- D3.js zoom: https://d3js.org/d3-zoom — `d3.zoom()` for pan/zoom behavior.
- D3.js color schemes: https://d3js.org/d3-scale-chromatic — `schemeTableau10` for 10-color categorical palette.
- Traag et al. (2019) — Leiden algorithm paper (DOI: 10.1038/s41598-019-41695-z) — understand community semantics.
- Imhof, Viklund & Huber (2025) — Graph Attention Networks for bid-rigging (arXiv:2507.12369) — context for what the graph represents (DEEP_RESEARCH_SYNTHESIS.md lines 27-35).

**WHY Each Reference Matters**:
- T16's XaiPanel.tsx: Shows the tab container pattern — GraphPanel must match the same interface (`activeTab`, `data` props) to integrate cleanly.
- T15's client.ts: Contains the already-defined `fetchGraphCommunities()` function — do NOT create a duplicate; import and use it.
- T7's cartel_detection.py: The Leiden service determines what `community` IDs mean — node coloring depends on understanding this output format.
- D3 force docs: Force simulation has many tunable params; wrong defaults cause unreadable graphs (nodes flying off-screen or collapsing into a ball).
- UPGRADE 3 lines 125-128: Proposal commits to "Graf bipartit Peserta–Tender menggunakan NetworkX" with "Leiden Community Detection" — the visualization must faithfully represent this.

**Acceptance Criteria**:

**QA Scenarios (MANDATORY — task is INCOMPLETE without these):**

```
Scenario: Graph renders with community-colored nodes (Happy Path)
  Tool: Playwright
  Preconditions: Backend running with test dataset loaded; Leiden analysis completed (at least 2 communities detected); frontend dev server running on port 5173
  Steps:
    1. Navigate to http://localhost:5173/tender/TND-2023-001
    2. Wait for `[data-testid="tender-detail"]` visible (timeout: 10s)
    3. Click the "Graf" tab — selector: `[data-testid="tab-graph"]`
    4. Wait for `[data-testid="graph-panel"]` visible (timeout: 15s — force simulation needs time)
    5. Assert SVG element exists inside graph-panel: `svg.cartel-graph` selector present
    6. Count circle elements (nodes): `svg.cartel-graph circle` — assert count >= 5 (test dataset has min 5 vendors)
    7. Count line elements (edges): `svg.cartel-graph line` — assert count >= 3
    8. Check node colors: select 2 circles with different `data-community` attributes — assert their `fill` CSS values differ
    9. Assert legend exists: `[data-testid="graph-legend"]` contains at least 2 community color entries
    10. Take screenshot: .sisyphus/evidence/task-17-graph-rendered.png
  Expected Result: Force-directed graph visible with colored nodes clustered by community, edges connecting co-bidders, legend showing community labels
  Failure Indicators: Empty SVG, all nodes same color, nodes piled at origin (0,0), no edges rendered, JavaScript console errors
  Evidence: .sisyphus/evidence/task-17-graph-rendered.png

Scenario: Node hover highlights connected edges and shows tooltip
  Tool: Playwright
  Preconditions: Graph already rendered (previous scenario passed)
  Steps:
    1. Navigate to http://localhost:5173/tender/TND-2023-001
    2. Click `[data-testid="tab-graph"]`, wait for `svg.cartel-graph` visible
    3. Hover over the first circle node: `svg.cartel-graph circle:first-of-type`
    4. Wait 500ms for tooltip animation
    5. Assert tooltip element visible: `[data-testid="graph-tooltip"]`
    6. Assert tooltip contains text matching vendor name pattern: /PT |CV |UD /
    7. Assert connected edges have increased opacity (filter `line` elements with matching source/target — opacity should be 1.0)
    8. Assert unconnected nodes have reduced opacity (< 0.3)
    9. Move mouse away from node — assert tooltip disappears within 300ms
    10. Take screenshot during hover: .sisyphus/evidence/task-17-node-hover.png
  Expected Result: Tooltip shows vendor info; connected subgraph highlighted; rest dimmed
  Failure Indicators: No tooltip appears, all nodes same opacity during hover, tooltip persists after mouse leaves
  Evidence: .sisyphus/evidence/task-17-node-hover.png

Scenario: Zoom and pan work correctly
  Tool: Playwright
  Preconditions: Graph rendered
  Steps:
    1. Navigate to graph tab as above
    2. Get initial transform of SVG group: evaluate `document.querySelector('svg.cartel-graph g.zoom-container').getAttribute('transform')`
    3. Perform scroll wheel zoom: `page.mouse.wheel(0, -300)` on the SVG element
    4. Wait 500ms
    5. Get new transform — assert scale value has increased (zoomed in)
    6. Click zoom reset button: `[data-testid="graph-zoom-reset"]`
    7. Wait 500ms
    8. Get transform again — assert scale is back to initial value
    9. Take screenshot after zoom-in: .sisyphus/evidence/task-17-zoom-pan.png
  Expected Result: Scroll zooms in/out smoothly; reset button returns to initial view
  Failure Indicators: No zoom response, zoom jumps erratically, reset button doesn't work
  Evidence: .sisyphus/evidence/task-17-zoom-pan.png

Scenario: Community filter isolates single community
  Tool: Playwright
  Preconditions: Graph rendered with at least 2 communities
  Steps:
    1. Navigate to graph tab as above
    2. Find community filter dropdown: `[data-testid="community-filter"]`
    3. Select the first community option (not "All")
    4. Wait 500ms for transition animation
    5. Count visible nodes (opacity > 0.5): assert count < total node count
    6. Assert all visible nodes have same `data-community` attribute value
    7. Assert filtered-out nodes have opacity <= 0.15
    8. Select "All" again — assert all nodes return to full opacity
    9. Take screenshot with filter active: .sisyphus/evidence/task-17-community-filter.png
  Expected Result: Only selected community's nodes and edges are prominent; others faded
  Failure Indicators: Filter has no visual effect, nodes disappear entirely instead of fading, all nodes remain visible
  Evidence: .sisyphus/evidence/task-17-community-filter.png

Scenario: Empty state when no graph data available
  Tool: Playwright
  Preconditions: Backend running but Leiden analysis has NOT been run (no communities in DB), or mock API to return empty graph
  Steps:
    1. Navigate to http://localhost:5173/tender/TND-EMPTY-001 (tender with no graph data)
    2. Click `[data-testid="tab-graph"]`
    3. Wait for `[data-testid="graph-panel"]` visible
    4. Assert NO SVG element inside graph-panel
    5. Assert empty state message visible: text matching /tidak ada data graf|no graph data/i
    6. Take screenshot: .sisyphus/evidence/task-17-empty-state.png
  Expected Result: Informative Indonesian-language empty state message, no broken SVG, no JS errors
  Failure Indicators: Blank panel, JavaScript error in console, SVG renders with 0 nodes (invisible)
  Evidence: .sisyphus/evidence/task-17-empty-state.png
```

**Evidence to Capture:**
- [ ] task-17-graph-rendered.png — Force-directed graph with community-colored nodes and edges
- [ ] task-17-node-hover.png — Tooltip and highlight on node hover
- [ ] task-17-zoom-pan.png — Graph after zoom interaction
- [ ] task-17-community-filter.png — Community filter active showing isolated cluster
- [ ] task-17-empty-state.png — Empty state when no graph data

**Commit**: YES (groups with Wave 4)
- Message: `feat(ui): cartel graph visualization — D3.js force-directed with Leiden community coloring`
- Files: `frontend/src/components/graph/CartelGraph.tsx`, `frontend/src/components/graph/GraphPanel.tsx`, `frontend/src/hooks/useGraphCommunities.ts`
- Pre-commit: `cd frontend && npm run build`

---

### Task 18 — Geographic Risk Heatmap (Folium Offline-Safe)

**Wave**: 4
**Depends on**: T5 (SQLite schema — tender institution locations), T14 (API endpoints — `/api/map/risk-heatmap` serves geo data)
**Blocks**: T20 (offline bundle)

**What to do**:
- Create a geographic risk heatmap component showing procurement fraud risk by Indonesian province/kabupaten.
- **Backend endpoint** `GET /api/map/risk-heatmap` (in T14's router) returns:
  ```json
  {
    "regions": [
      {"province": "DKI Jakarta", "kabupaten": "Jakarta Selatan", "lat": -6.2615, "lng": 106.8106, "avg_risk": 0.72, "tender_count": 450, "high_risk_count": 38},
      {"province": "Jawa Barat", "kabupaten": "Bandung", "lat": -6.9175, "lng": 107.6191, "avg_risk": 0.45, "tender_count": 312, "high_risk_count": 12}
    ],
    "summary": {"total_regions": 45, "highest_risk_region": "DKI Jakarta", "national_avg_risk": 0.52}
  }
  ```
- **Two implementation approaches** (choose based on offline constraint):
  - **Approach A (Preferred): React + Leaflet.js** — Use `react-leaflet` with **offline tile bundle**. Pre-download OpenStreetMap tiles for Indonesia (zoom 5-10) using `leaflet-offline` or bundle a minimal tile set as static assets in `frontend/public/tiles/`. This keeps everything in React and avoids Python-generated HTML.
  - **Approach B (Fallback): Folium server-side** — Generate Folium HTML on backend (`GET /api/map/risk-heatmap-html` returns full HTML page), embed in React via `<iframe>`. Use Folium's `tiles=None` + custom tile layer pointing to bundled local tiles. Less interactive but simpler.
- **Whichever approach**: Must work 100% offline (no tile server requests when Wi-Fi disabled).
- **Heatmap visualization**:
  - Circle markers at each province/kabupaten centroid.
  - Circle radius proportional to `tender_count` (more tenders = larger circle).
  - Circle color on a gradient: green (#22c55e, risk <0.3) → yellow (#eab308, risk 0.3-0.6) → orange (#f97316, risk 0.6-0.8) → red (#ef4444, risk >0.8) based on `avg_risk`.
  - Tooltip on hover: region name, avg risk score, tender count, high-risk count.
  - Click to zoom into region and show breakdown.
- **Legend**: Color gradient legend showing risk scale (0.0 = Aman → 1.0 = Risiko Kritis).
- **Summary stats panel** above or beside map: total regions analyzed, highest-risk region, national average risk.
- **Indonesia bounds**: Fit map bounds to Indonesia (lat: -11 to 6, lng: 95 to 141). Default zoom level 5.
- **Empty state**: When no geo data available, show placeholder message: "Data geografis belum tersedia. Jalankan analisis pada dataset dengan informasi lokasi LPSE."
- Create component at `frontend/src/components/map/RiskHeatmap.tsx` (the map itself).
- Create wrapper at `frontend/src/components/map/MapPanel.tsx` that:
  - Fetches data via `useRiskHeatmap()` hook (calls `GET /api/map/risk-heatmap`).
  - Handles loading, error, empty states.
  - Renders `RiskHeatmap` with data.
- Integrate `MapPanel` into the Dashboard page (T15) as a dedicated section/tab, and optionally into Tender Detail page if relevant.
- Install dependencies: `npm install react-leaflet leaflet @types/leaflet` (for Approach A).
- **Offline tile strategy**: Create a `scripts/download_indonesia_tiles.py` script that pre-downloads OSM tiles for Indonesia (zoom 5-10) to `frontend/public/tiles/{z}/{x}/{y}.png`. Include instructions in Task 23's sprint playbook. Alternatively, use a single static Indonesia SVG/GeoJSON map with D3.js choropleth (simpler offline, no tile dependency).

**Must NOT do**:
- Do NOT rely on online tile servers at demo time — must work with Wi-Fi disabled.
- Do NOT use Google Maps API or Mapbox — requires API keys and online access.
- Do NOT attempt real-time GPS or user location features.
- Do NOT over-engineer the map — it's a visualization aid, not a full GIS system.
- Do NOT create a separate backend route for Folium HTML if using Approach A (React Leaflet).
- Do NOT download tiles for the entire world — only Indonesia, zoom levels 5-10.

**Recommended Agent Profile**:
> Select category + skills based on task domain. Justify each choice.
- **Category**: `visual-engineering`
  - Reason: Geographic visualization with Leaflet/Folium, color gradient mapping, interactive map UI, responsive layout. Core visual design task.
- **Skills**: [`playwright`]
  - `playwright`: QA scenarios require navigating to map, checking rendered tiles/markers, taking screenshots.
- **Skills Evaluated but Omitted**:
  - `frontend-ui-ux`: Map implementation is specialized geo-viz, not general UI. visual-engineering covers it.

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 4 (with Tasks 15, 16, 17, 19)
- **Blocks**: T20 (offline bundle needs map component)
- **Blocked By**: T5 (SQLite schema), T14 (API endpoints)

**References** (CRITICAL — Be Exhaustive):

**Pattern References** (existing code to follow):
- `frontend/src/components/graph/GraphPanel.tsx` (T17) — Wrapper pattern: fetch hook + loading/error/empty states + render child. MapPanel follows identical structure.
- `frontend/src/pages/Dashboard.tsx` (T15) — Dashboard layout where MapPanel integrates as a section or tab.
- `frontend/src/api/client.ts` (T15) — Add `fetchRiskHeatmap()` function here; follow existing pattern.

**API/Type References** (contracts to implement against):
- `backend/app/routers/map.py` (T14) — `GET /api/map/risk-heatmap` endpoint; defines response schema.
- `backend/app/models/schemas.py` (T3) — Pydantic model `RiskHeatmapResponse` with regions array.

**External References** (libraries and frameworks):
- react-leaflet: https://react-leaflet.js.org — React wrapper for Leaflet.js maps.
- Leaflet.js: https://leafletjs.com — Core mapping library (lightweight, offline-capable with local tiles).
- UPGRADE 3 line 166 — Proposal specifies "Folium" for frontend maps (we upgrade to react-leaflet for better React integration but same visual output).
- Indonesia GeoJSON: https://github.com/superpikar/indonesia-geojson — Province/kabupaten boundary polygons for choropleth fallback.

**WHY Each Reference Matters**:
- T17's GraphPanel.tsx: Identical wrapper pattern ensures consistent component architecture across all visualization panels.
- T15's Dashboard.tsx: MapPanel must integrate into existing dashboard layout without breaking existing components.
- react-leaflet docs: Leaflet has specific React lifecycle requirements (map container must have fixed height, cleanup on unmount). Wrong setup causes memory leaks.
- UPGRADE 3 line 166: Proposal says "Folium" — we use Leaflet (Folium's JS engine) via react-leaflet. Same rendering, better React integration. Judges see the same map quality.
- Indonesia GeoJSON: Need province boundaries for choropleth shading if using fallback D3 approach.

**Acceptance Criteria**:

**QA Scenarios (MANDATORY — task is INCOMPLETE without these):**

```
Scenario: Map renders with risk-colored markers for Indonesian regions (Happy Path)
  Tool: Playwright
  Preconditions: Backend running with test dataset containing geo-located tenders across multiple provinces; frontend dev server on port 5173
  Steps:
    1. Navigate to http://localhost:5173/
    2. Wait for `[data-testid="dashboard"]` visible (timeout: 10s)
    3. Find map section/tab: click `[data-testid="tab-map"]` or scroll to `[data-testid="map-panel"]`
    4. Wait for map container visible: `[data-testid="risk-heatmap"]` (timeout: 10s)
    5. Assert map canvas/SVG is rendered (Leaflet creates `.leaflet-container` div)
    6. Count circle markers: `.leaflet-marker-icon` or `.circle-marker` — assert count >= 3 (test data has min 3 provinces)
    7. Check marker colors: select markers and verify they have different fill colors (not all same color)
    8. Assert legend exists: `[data-testid="map-legend"]` showing color gradient from green to red
    9. Assert summary stats visible: `[data-testid="map-summary"]` contains text matching /total.*region|wilayah/i
    10. Take screenshot: .sisyphus/evidence/task-18-map-rendered.png
  Expected Result: Indonesia map visible with colored circle markers at province locations, legend showing risk scale, summary stats panel
  Failure Indicators: Blank map (grey tiles), no markers rendered, all markers same color, map centered on wrong location (not Indonesia)
  Evidence: .sisyphus/evidence/task-18-map-rendered.png

Scenario: Map works offline (no tile requests when Wi-Fi disabled)
  Tool: Playwright
  Preconditions: Frontend and backend running; network request interception enabled
  Steps:
    1. Navigate to http://localhost:5173/
    2. Enable network request logging via Playwright: `page.on('request', ...)`
    3. Navigate to map section
    4. Wait for map to fully render (all markers visible)
    5. Collect all network requests made during map rendering
    6. Filter requests — assert ZERO requests to external tile servers (no requests to `tile.openstreetmap.org`, `api.mapbox.com`, `maps.googleapis.com`, etc.)
    7. Assert all tile requests (if any) go to localhost (e.g., `http://localhost:5173/tiles/`)
    8. Take screenshot: .sisyphus/evidence/task-18-offline-map.png
  Expected Result: Map renders using only local resources; zero external HTTP requests for tiles
  Failure Indicators: Requests to external tile servers, grey/missing tiles, network timeout errors in console
  Evidence: .sisyphus/evidence/task-18-offline-map.png

Scenario: Marker tooltip shows region info on hover
  Tool: Playwright
  Preconditions: Map rendered with markers
  Steps:
    1. Navigate to map, wait for markers
    2. Hover over the first circle marker (or click if using Leaflet popup instead of tooltip)
    3. Wait for tooltip/popup visible: `.leaflet-tooltip` or `.leaflet-popup`
    4. Assert tooltip contains province name (text matching Indonesian province: /Jakarta|Jawa|Sumatera|Kalimantan|Sulawesi/i)
    5. Assert tooltip contains risk score (text matching /risk|risiko|skor/i and a number between 0-1)
    6. Assert tooltip contains tender count (text matching /tender|jumlah/i)
    7. Take screenshot: .sisyphus/evidence/task-18-marker-tooltip.png
  Expected Result: Tooltip shows region name, risk score, and tender count
  Failure Indicators: No tooltip appears, tooltip shows raw JSON, tooltip missing key data fields
  Evidence: .sisyphus/evidence/task-18-marker-tooltip.png

Scenario: Empty state when no geographic data
  Tool: Playwright
  Preconditions: Backend returns empty regions array for map endpoint
  Steps:
    1. Navigate to map section
    2. Wait for `[data-testid="map-panel"]`
    3. Assert no map canvas rendered OR map shows with no markers
    4. Assert empty state message visible: text matching /data geografis belum|no geographic data/i
    5. Take screenshot: .sisyphus/evidence/task-18-empty-state.png
  Expected Result: Informative empty state message in Indonesian, no crash
  Failure Indicators: Map crashes, blank screen, JavaScript error
  Evidence: .sisyphus/evidence/task-18-empty-state.png
```

**Evidence to Capture:**
- [ ] task-18-map-rendered.png — Indonesia map with risk-colored markers and legend
- [ ] task-18-offline-map.png — Map rendering proof with no external tile requests
- [ ] task-18-marker-tooltip.png — Tooltip/popup showing region risk info
- [ ] task-18-empty-state.png — Empty state message

**Commit**: YES (groups with Wave 4)
- Message: `feat(ui): geographic risk heatmap — Leaflet markers with offline tiles for Indonesian procurement regions`
- Files: `frontend/src/components/map/RiskHeatmap.tsx`, `frontend/src/components/map/MapPanel.tsx`, `frontend/src/hooks/useRiskHeatmap.ts`, `scripts/download_indonesia_tiles.py`
- Pre-commit: `cd frontend && npm run build`

---

### Task 19 — Report Viewer + PDF Export Component

**Wave**: 4
**Depends on**: T5 (SQLite schema — report data), T13 (report generator — produces IIA-format HTML), T14 (API endpoints — `/api/tender/{id}/report` serves report HTML/data)
**Blocks**: T20 (offline bundle)

**What to do**:
- Create a report viewer component that displays pre-investigation reports generated by T13's NLG engine.
- **Backend endpoint** `GET /api/tender/{id}/report` (from T14) returns:
  ```json
  {
    "tender_id": "TND-2023-001",
    "report_html": "<div class='iia-report'>...<h1>Laporan Pra-Investigasi</h1>...",
    "report_metadata": {
      "generated_at": "2026-02-27T14:30:00",
      "risk_level": "Risiko Tinggi",
      "risk_score": 0.87,
      "institution": "Kementerian PUPR",
      "tender_value": 5200000000,
      "template_version": "IIA-2025-v1"
    }
  }
  ```
- **Report Viewer** at `frontend/src/components/reports/ReportViewer.tsx`:
  - Renders the `report_html` string safely inside a styled container (use `dangerouslySetInnerHTML` with DOMPurify sanitization for XSS protection).
  - Wraps HTML in a print-optimized container with proper margins, font sizes, page breaks.
  - Shows metadata header above report: generated date, risk level badge (color-coded), institution name, tender value (formatted as IDR currency).
  - Responsive layout: full-width on desktop, scrollable on mobile.
- **PDF Export** via `frontend/src/components/reports/PdfExportButton.tsx`:
  - Use `window.print()` CSS-based approach (simplest, zero dependency):
    - Create a `@media print` stylesheet that hides navigation/chrome, shows only the report container.
    - Trigger `window.print()` on button click — user's browser native print dialog handles PDF export.
  - **Alternative**: If higher fidelity needed, use `html2canvas` + `jspdf` (heavier but more control):
    - `html2canvas` captures the report container as canvas.
    - `jspdf` converts canvas to PDF with A4 page sizing.
    - Install: `npm install html2canvas jspdf` (only if window.print() quality is insufficient).
  - PDF filename: `LPSE-X_Report_{tender_id}_{date}.pdf`.
  - Button shows loading spinner during PDF generation.
- **Report List** at `frontend/src/components/reports/ReportList.tsx`:
  - Shows a table of all generated reports for the current analysis run.
  - Backend endpoint `GET /api/reports` returns list of available reports with metadata.
  - Columns: Tender ID, Institution, Risk Level (badge), Generated Date, Actions (View / Download PDF).
  - "View" opens the report in ReportViewer (inline or modal).
  - "Download PDF" triggers PDF export.
- Create wrapper `frontend/src/components/reports/ReportPanel.tsx` that:
  - Integrates ReportViewer and PdfExportButton.
  - Fetches report data via `useReport(tenderId)` hook.
  - Handles loading, error, and "report not generated yet" states.
  - If report not yet generated, shows a "Generate Report" button that calls `POST /api/tender/{id}/report/generate`.
- Integrate `ReportPanel` into the Tender Detail page (T15) as the "Laporan" tab.
- Add `ReportList` as a section in Dashboard (T15) or as a separate `/reports` route.
- Install DOMPurify: `npm install dompurify @types/dompurify`.

**Must NOT do**:
- Do NOT render raw HTML without sanitization — always use DOMPurify.
- Do NOT generate PDFs on the backend — use browser-side PDF export to avoid heavy Python PDF dependencies (wkhtmltopdf, weasyprint) that complicate offline bundling.
- Do NOT implement report editing or annotation features — reports are read-only.
- Do NOT add rich text editor functionality.
- Do NOT block report viewing while PDF is generating.

**Recommended Agent Profile**:
> Select category + skills based on task domain. Justify each choice.
- **Category**: `visual-engineering`
  - Reason: Report layout and styling, print media queries, PDF export UX, responsive design for report content. Core frontend visual task.
- **Skills**: [`playwright`]
  - `playwright`: QA scenarios require viewing reports in browser, triggering print dialog, verifying rendered HTML content, taking screenshots.
- **Skills Evaluated but Omitted**:
  - `frontend-ui-ux`: Report viewing is specialized document rendering, not general page layout. visual-engineering suffices.

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 4 (with Tasks 15, 16, 17, 18)
- **Blocks**: T20 (offline bundle)
- **Blocked By**: T5 (SQLite schema), T13 (report generator), T14 (API endpoints)

**References** (CRITICAL — Be Exhaustive):

**Pattern References** (existing code to follow):
- `frontend/src/components/graph/GraphPanel.tsx` (T17) — Wrapper pattern with fetch hook + loading/error/empty. ReportPanel follows same structure.
- `frontend/src/components/xai/XaiPanel.tsx` (T16) — Tab integration pattern; ReportPanel integrates as "Laporan" tab in TenderDetail.
- `frontend/src/pages/TenderDetail.tsx` (T15) — Contains placeholder tab for reports; this task fills it.
- `frontend/src/api/client.ts` (T15) — `fetchTenderReport(id)` function already defined here.

**API/Type References** (contracts to implement against):
- `backend/app/routers/reports.py` (T14) — `GET /api/tender/{id}/report` and `GET /api/reports` endpoints.
- `backend/app/services/report_generator.py` (T13) — Produces the IIA-format HTML; defines the report structure the viewer must render.
- `backend/app/models/schemas.py` (T3) — Pydantic model `ReportResponse` with `report_html` and `report_metadata`.

**External References** (libraries and frameworks):
- DOMPurify: https://github.com/cure53/DOMPurify — XSS-safe HTML sanitization for rendering `dangerouslySetInnerHTML`.
- UPGRADE 3 lines 151-153 — "Template-based NLG, IIA 2025 format" — defines what the report looks like.
- IIA Standards 2025 — Report format reference (structure: Executive Summary, Risk Findings, Evidence, Recommendations).

**WHY Each Reference Matters**:
- T13's report_generator.py: Viewer must understand the HTML structure produced by the generator — CSS classes, section IDs, heading hierarchy — to style it correctly.
- T15's TenderDetail.tsx: ReportPanel integrates as a tab; must match the tab API (`activeTab`, conditional rendering).
- DOMPurify: Rendering backend-generated HTML without sanitization is a critical XSS vulnerability. This is a security requirement, not optional.
- UPGRADE 3 lines 151-153: Proposal promises "legally defensible" format — the viewer must present reports professionally, not as raw HTML.

**Acceptance Criteria**:

**QA Scenarios (MANDATORY — task is INCOMPLETE without these):**

```
Scenario: Report viewer renders IIA-format report correctly (Happy Path)
  Tool: Playwright
  Preconditions: Backend running; T13 report generator has created a report for TND-2023-001; frontend dev server on port 5173
  Steps:
    1. Navigate to http://localhost:5173/tender/TND-2023-001
    2. Wait for `[data-testid="tender-detail"]` visible (timeout: 10s)
    3. Click the "Laporan" tab: `[data-testid="tab-report"]`
    4. Wait for `[data-testid="report-panel"]` visible (timeout: 10s)
    5. Assert report metadata header exists: `[data-testid="report-metadata"]`
    6. Assert risk level badge visible with text matching /Risiko Tinggi|Risiko Kritis|Perlu Pantauan|Aman/
    7. Assert report content container exists: `[data-testid="report-content"]`
    8. Assert report contains IIA sections: text matching /Laporan Pra-Investigasi|Ringkasan Eksekutif|Temuan Risiko|Rekomendasi/i
    9. Assert report content is NOT empty (innerHTML length > 100 characters)
    10. Take screenshot: .sisyphus/evidence/task-19-report-rendered.png
  Expected Result: Professional IIA-format report rendered with metadata header, risk badge, and full report content
  Failure Indicators: Blank report area, raw HTML tags visible, missing sections, report_html not sanitized (script tags visible)
  Evidence: .sisyphus/evidence/task-19-report-rendered.png

Scenario: PDF export button triggers browser print dialog
  Tool: Playwright
  Preconditions: Report rendered (previous scenario passed)
  Steps:
    1. Navigate to report tab for TND-2023-001
    2. Wait for report to render
    3. Find PDF export button: `[data-testid="pdf-export-btn"]`
    4. Assert button is visible and not disabled
    5. Note: Cannot fully test print dialog in Playwright, but can verify:
       a. Button click does not throw JavaScript error (check console)
       b. Print stylesheet exists: evaluate `document.querySelector('style[media="print"]')` or check computed styles
       c. In print mode, navigation elements should be hidden
    6. Take screenshot before clicking: .sisyphus/evidence/task-19-pdf-button.png
  Expected Result: PDF export button exists, is clickable, print stylesheet is configured
  Failure Indicators: Button missing, button disabled, JavaScript error on click, no print media styles defined
  Evidence: .sisyphus/evidence/task-19-pdf-button.png

Scenario: Report list shows all generated reports
  Tool: Playwright
  Preconditions: Backend has generated reports for at least 2 tenders; frontend running
  Steps:
    1. Navigate to http://localhost:5173/ (Dashboard)
    2. Navigate to reports section/tab: `[data-testid="tab-reports"]` or `/reports` route
    3. Wait for `[data-testid="report-list"]` visible
    4. Count table rows: `[data-testid="report-list"] tbody tr` — assert count >= 2
    5. Assert each row has columns: Tender ID, Institution, Risk Level, Date, Actions
    6. Assert "View" link exists in first row: `tr:first-child [data-testid="report-view-btn"]`
    7. Click "View" on first row — assert navigates to or opens report viewer
    8. Take screenshot: .sisyphus/evidence/task-19-report-list.png
  Expected Result: Table of reports with metadata and action buttons, View navigates to report viewer
  Failure Indicators: Empty table, missing columns, View button doesn't work
  Evidence: .sisyphus/evidence/task-19-report-list.png

Scenario: Report not yet generated shows generate button
  Tool: Playwright
  Preconditions: Navigate to a tender that has NOT had a report generated
  Steps:
    1. Navigate to http://localhost:5173/tender/TND-NO-REPORT
    2. Click "Laporan" tab
    3. Wait for `[data-testid="report-panel"]`
    4. Assert report content is NOT rendered (no `[data-testid="report-content"]`)
    5. Assert "Generate Report" button visible: `[data-testid="generate-report-btn"]`
    6. Take screenshot: .sisyphus/evidence/task-19-no-report-state.png
  Expected Result: Panel shows message that report hasn't been generated yet, with a button to generate it
  Failure Indicators: Panel crashes, shows loading forever, no generate button
  Evidence: .sisyphus/evidence/task-19-no-report-state.png
```

**Evidence to Capture:**
- [ ] task-19-report-rendered.png — IIA-format report with metadata header and content
- [ ] task-19-pdf-button.png — PDF export button visible on report
- [ ] task-19-report-list.png — Report list table with multiple reports
- [ ] task-19-no-report-state.png — Empty state with generate button

**Commit**: YES (groups with Wave 4)
- Message: `feat(ui): report viewer + PDF export — IIA-format report display with browser print/PDF`
- Files: `frontend/src/components/reports/ReportViewer.tsx`, `frontend/src/components/reports/PdfExportButton.tsx`, `frontend/src/components/reports/ReportList.tsx`, `frontend/src/components/reports/ReportPanel.tsx`, `frontend/src/hooks/useReport.ts`
- Pre-commit: `cd frontend && npm run build`

---

### Task 20 — Offline Portable Bundle + Auto Port Detection

> **Wave 5 — Integration + Packaging** | Depends: T14 (API layer), T15 (dashboard shell), T16-T19 (all UI components) | Blocks: T21, T22, T23

**What to do**:
- Create `lpse-x/main.py` as the **single entry point** for the entire application:
  - Auto-detect a free port using `socket.socket()` — bind to `127.0.0.1`, let OS assign port, read `sock.getsockname()[1]`, close socket, pass port to Uvicorn
  - Mount React production build as static files: `app.mount("/", StaticFiles(directory="static", html=True))` with fallback to `index.html` for SPA routing
  - On startup, print a clear banner: `LPSE-X running at http://127.0.0.1:{port}` and auto-open browser via `webbrowser.open()`
  - Graceful shutdown handler (SIGINT/SIGTERM) that closes DB connections and prints exit message
  - CLI flags: `--port` (override auto), `--no-browser` (headless mode for tests), `--data-dir` (custom data path)
- Create `scripts/build_bundle.sh` (cross-platform, also `scripts/build_bundle.bat` for Windows):
  - Step 1: `cd frontend && npm ci && npm run build` — produces `frontend/dist/`
  - Step 2: Copy `frontend/dist/*` → `lpse-x/static/`
  - Step 3: Copy backend modules → `lpse-x/backend/`
  - Step 4: Copy `runtime_config.yaml` + `models/*.onnx` + `data/sample/` → `lpse-x/`
  - Step 5: Generate `lpse-x/requirements.txt` from `pyproject.toml` (or copy lockfile)
  - Step 6: Validate bundle — check all critical files exist, print manifest
  - Output: self-contained `lpse-x/` folder ready to run with `python main.py`
- Configure FastAPI to serve static files with correct MIME types (JS, CSS, images, fonts)
- Add `lpse-x/README.md` with quick-start instructions (for judges): `pip install -r requirements.txt && python main.py`
- Ensure `runtime_config.yaml` is at `lpse-x/config/runtime_config.yaml` and `main.py` resolves paths relative to its own directory (`pathlib.Path(__file__).parent`)
- Add health check at `GET /api/health` returning `{"status": "ok", "port": N, "version": "1.0.0", "config_loaded": true}`

**Must NOT do**:
- Do NOT use Docker or containerization — judges run directly on laptops
- Do NOT create virtual environments at runtime — assume Python + Node are pre-installed
- Do NOT bundle `node_modules/` or `__pycache__/` in the output folder
- Do NOT hardcode any absolute paths — everything must be relative to `main.py`'s directory
- Do NOT use `pkg_resources` or `importlib.resources` — use simple `pathlib` relative paths
- Do NOT add a splash screen, loading animation, or unnecessary startup ceremony

**Recommended Agent Profile**:
> This task involves backend integration, file system operations, build scripting, and deployment packaging — requires careful path handling and cross-platform awareness.
- **Category**: `deep`
  - Reason: Integration task touching backend, frontend build output, and build scripts — requires careful coordination and understanding of how all pieces fit together
- **Skills**: [`playwright`]
  - `playwright`: Needed for QA scenario that opens browser to verify the bundled app serves the React frontend correctly
- **Skills Evaluated but Omitted**:
  - `frontend-ui-ux`: Not relevant — this task doesn't create UI components, just serves pre-built static files
  - `git-master`: No complex git operations needed

**Parallelization**:
- **Can Run In Parallel**: NO — depends on ALL Wave 4 outputs (frontend build, API routes, all UI components)
- **Parallel Group**: Wave 5 (first task — T21, T22, T23 depend on T20)
- **Blocks**: T21 (integration tests need running app), T22 (stress tests need running app), T23 (demo script references running app)
- **Blocked By**: T14 (FastAPI routes), T15 (dashboard shell), T16 (graph viz), T17 (map viz), T18 (dashboard panels), T19 (report viewer)

**References**:

**Pattern References** (existing code to follow):
- `backend/api/main.py` (from T14) — The existing FastAPI app definition with CORS, routers, and middleware. Task 20 wraps this into the entry point, mounting static files on top of the API routes.
- `backend/api/routes/config.py` (from T4) — The `PUT /api/config/inject` endpoint pattern. Task 20's health check endpoint follows the same router registration pattern.
- `runtime_config.yaml` (from T4) — The runtime configuration file. Task 20 must ensure this is correctly located in the bundle and that `main.py` resolves its path properly.

**API/Type References** (contracts to implement against):
- `backend/core/config.py:RuntimeConfig` (from T4) — Pydantic model for runtime configuration. `main.py` should load this on startup to verify config is valid before serving.
- FastAPI `StaticFiles` — Mount static files: `from starlette.staticfiles import StaticFiles`; `app.mount("/", StaticFiles(directory="static", html=True))`

**External References** (libraries and frameworks):
- FastAPI Static Files docs: https://fastapi.tiangolo.com/tutorial/static-files/ — How to serve static files and configure the mount point
- Uvicorn programmatic usage: https://www.uvicorn.org/deployment/#running-programmatically — `uvicorn.run(app, host=host, port=port)` for embedding in `main.py`
- Python `socket` auto-port: `sock = socket.socket(); sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]; sock.close()` — standard pattern for finding free ports

**WHY Each Reference Matters**:
- `backend/api/main.py` → This IS the FastAPI app. Task 20 imports it and wraps it with static file serving. Without reading this, you'd duplicate the app definition.
- `runtime_config.yaml` → Must be at the correct relative path inside the bundle. If path resolution is wrong, the app boots with default config and dynamic injection fails.
- FastAPI StaticFiles → The `html=True` flag is critical — it enables SPA fallback routing so React Router paths work correctly.
- Uvicorn programmatic → Must use `uvicorn.run()` not CLI `uvicorn` command, because we need to pass the dynamically-detected port.

**Acceptance Criteria**:

- [ ] `lpse-x/main.py` exists and is executable with `python lpse-x/main.py`
- [ ] Auto port detection works: running twice simultaneously uses different ports
- [ ] `scripts/build_bundle.sh` exists and produces a complete `lpse-x/` folder
- [ ] `scripts/build_bundle.bat` exists for Windows (mirrors .sh logic)
- [ ] Bundle contains: `main.py`, `static/index.html`, `backend/`, `config/runtime_config.yaml`, `models/*.onnx`, `requirements.txt`
- [ ] `GET /api/health` returns 200 with correct JSON shape
- [ ] `GET /` serves React app's `index.html`
- [ ] SPA routing works: `GET /dashboard` returns `index.html` (not 404)
- [ ] `--port 9999` flag overrides auto-detection
- [ ] `--no-browser` flag suppresses browser auto-open
- [ ] All paths are relative — moving `lpse-x/` to a different directory still works

**QA Scenarios:**

```
Scenario: Bundle build + app launch (happy path)
  Tool: Bash
  Preconditions: T14 (API) and T15-T19 (frontend) are complete. Node.js and Python available.
  Steps:
    1. Run `bash scripts/build_bundle.sh` (or `scripts\build_bundle.bat` on Windows)
    2. Assert exit code 0
    3. Assert `lpse-x/main.py` exists: `test -f lpse-x/main.py`
    4. Assert `lpse-x/static/index.html` exists: `test -f lpse-x/static/index.html`
    5. Assert `lpse-x/config/runtime_config.yaml` exists
    6. Assert `lpse-x/requirements.txt` exists
    7. Run `python lpse-x/main.py --no-browser &` and capture PID
    8. Wait 5 seconds for startup
    9. `curl -s http://127.0.0.1:<port>/api/health` — assert JSON contains `"status": "ok"`
    10. `curl -s http://127.0.0.1:<port>/` — assert response contains `<!DOCTYPE html>` or `<div id="root">`
    11. `curl -s http://127.0.0.1:<port>/dashboard` — assert response contains `index.html` content (SPA fallback)
    12. Kill PID, assert clean shutdown
  Expected Result: Bundle builds successfully, app starts on auto-detected port, serves both API and React frontend
  Failure Indicators: Build script fails, missing files in bundle, app crashes on startup, static files return 404
  Evidence: .sisyphus/evidence/task-20-bundle-build.txt, .sisyphus/evidence/task-20-health-check.json

Scenario: Auto port detection — dual instance
  Tool: Bash
  Preconditions: Bundle is built from previous scenario
  Steps:
    1. Run `python lpse-x/main.py --no-browser &` — capture output for PORT_A
    2. Wait 3 seconds
    3. Run `python lpse-x/main.py --no-browser &` — capture output for PORT_B
    4. Wait 3 seconds
    5. Assert PORT_A ≠ PORT_B (grep from stdout banner)
    6. `curl -s http://127.0.0.1:$PORT_A/api/health` — assert 200
    7. `curl -s http://127.0.0.1:$PORT_B/api/health` — assert 200
    8. Kill both processes
  Expected Result: Two instances run simultaneously on different auto-detected ports
  Failure Indicators: Second instance fails with "port already in use", same port detected twice
  Evidence: .sisyphus/evidence/task-20-dual-port.txt

Scenario: Manual port override
  Tool: Bash
  Preconditions: Bundle is built, port 9999 is free
  Steps:
    1. Run `python lpse-x/main.py --port 9999 --no-browser &`
    2. Wait 3 seconds
    3. `curl -s http://127.0.0.1:9999/api/health` — assert 200 and JSON contains `"port": 9999`
    4. Kill process
  Expected Result: App runs on explicitly specified port 9999
  Failure Indicators: App ignores --port flag and uses auto-detected port
  Evidence: .sisyphus/evidence/task-20-manual-port.txt

Scenario: Relocated bundle still works (no absolute paths)
  Tool: Bash
  Preconditions: Bundle built at `lpse-x/`
  Steps:
    1. `cp -r lpse-x/ /tmp/lpse-x-relocated/`
    2. `cd /tmp/lpse-x-relocated && python main.py --no-browser &`
    3. Wait 5 seconds
    4. `curl -s http://127.0.0.1:<port>/api/health` — assert 200
    5. `curl -s http://127.0.0.1:<port>/` — assert React app loads
    6. Kill process, `rm -rf /tmp/lpse-x-relocated/`
  Expected Result: Bundle works identically when moved to a different directory
  Failure Indicators: FileNotFoundError, config not found, static files 404
  Evidence: .sisyphus/evidence/task-20-relocated-bundle.txt
```

**Evidence to Capture:**
- [ ] task-20-bundle-build.txt — Build script output showing all steps passed + file manifest
- [ ] task-20-health-check.json — Health endpoint JSON response
- [ ] task-20-dual-port.txt — Two instances running on different ports
- [ ] task-20-manual-port.txt — Port override working correctly
- [ ] task-20-relocated-bundle.txt — Bundle works after relocation

**Commit**: YES (groups with Wave 5)
- Message: `feat(bundle): offline portable bundle — auto port, static serving, build scripts`
- Files: `lpse-x/main.py`, `scripts/build_bundle.sh`, `scripts/build_bundle.bat`, `lpse-x/README.md`
- Pre-commit: `python lpse-x/main.py --no-browser --port 18923 & sleep 3 && curl -sf http://127.0.0.1:18923/api/health && kill %1`

---

### Task 21 — End-to-End Integration Tests (Full Pipeline)

> **Wave 5 — Integration + Packaging** | Depends: T20 (bundle), T3-T14 (all backend modules) | Blocks: F1-F4 (Final Verification)

**What to do**:
- Create `tests/test_integration.py` with end-to-end tests covering the COMPLETE pipeline:
  - **Data ingestion → Features → Predict → Explain → Report** as a single flow
  - Use a **mini dataset** (50 tenders, not 1.1M) stored at `tests/fixtures/mini_tenders.json` — handcrafted subset with known risk profiles:
    - 10 high-risk tenders (single bidder, winner rotation, bid clustering)
    - 10 medium-risk tenders (some red flags but ambiguous)
    - 30 clean tenders (normal bidding patterns)
- Create `tests/fixtures/mini_tenders.json` with 50 OCDS-format tender records (minimal fields required by Cardinal + custom features)
- Create `tests/conftest.py` with shared fixtures:
  - `mini_db` — temporary SQLite DB loaded with mini dataset
  - `app_client` — FastAPI `TestClient` from `httpx` for API testing without starting server
  - `runtime_config` — default RuntimeConfig fixture
- **Test the full pipeline** in sequence:
  1. Load mini_tenders.json → ingest into SQLite → verify row count = 50
  2. Compute Cardinal red flags → verify 73 flags populated (some may be 0/null, but columns exist)
  3. Compute 12 custom features → verify feature matrix shape = (50, 85)
  4. Run Tri-Method AI predict → verify all 50 get risk_level in {aman, perlu_pantauan, risiko_tinggi, risiko_kritis}
  5. Pick a high-risk tender → call each XAI layer:
     - SHAP → verify returns global_summary + local_waterfall
     - DiCE → verify returns counterfactual_set (may be cached template)
     - Anchors → verify returns rules list
     - Leiden graph → verify returns community_id + connected entities
     - Benford → verify returns result (either analysis or not_applicable with reason)
  6. Generate report for high-risk tender → verify report string contains key sections (metadata, risk score, explanation)
- **Test API integration** (using TestClient, no real server):
  - `GET /api/health` → 200 + correct JSON
  - `GET /api/tender/{id}/predict` → 200 + risk_level field
  - `GET /api/tender/{id}/explain` → 200 + all 5 XAI layers present
  - `GET /api/graph/communities` → 200 + communities array
  - `GET /api/tender/{id}/report` → 200 + report text
  - `PUT /api/config/inject` with valid JSON → 200 + config updated
  - `PUT /api/config/inject` with invalid JSON → 422 + descriptive error
- **Test offline enforcement**:
  - Create `tests/test_offline_no_network.py` that patches `socket.socket.connect` to raise `ConnectionError`
  - Run full inference pipeline with mocked network → verify zero outbound connections attempted
  - Verify all map tiles (if any) are loaded from local cache, not fetched

**Must NOT do**:
- Do NOT use the full 1.1M dataset in integration tests — mini dataset only (50 records)
- Do NOT require a running server process — use FastAPI TestClient
- Do NOT skip any of the 5 XAI layers in the pipeline test — all 5 must produce output
- Do NOT mock the ML models in integration tests — use real (small) ONNX models trained on mini data
- Do NOT test individual functions (that's unit test territory) — test the pipeline as a whole
- Do NOT hardcode expected values that depend on model weights — test shapes, types, and ranges

**Recommended Agent Profile**:
> End-to-end integration tests require understanding of the entire system architecture, all module interfaces, and careful test fixture design. Deep reasoning is needed to ensure the mini dataset triggers all code paths.
- **Category**: `deep`
  - Reason: Integration tests span all backend modules (data, features, models, XAI, reports, API) and require careful fixture design + understanding of data flow through the entire pipeline
- **Skills**: []
- **Skills Evaluated but Omitted**:
  - `playwright`: Not needed — these are backend integration tests, not UI tests
  - `frontend-ui-ux`: Not relevant — purely backend pipeline

**Parallelization**:
- **Can Run In Parallel**: YES — with T22 (injection stress test) and T23 (docs), after T20 completes
- **Parallel Group**: Wave 5B (T21 + T22 + T23 run in parallel after T20)
- **Blocks**: F1-F4 (Final Verification Wave depends on all tests passing)
- **Blocked By**: T20 (needs the bundled app structure to test against)

**References**:

**Pattern References** (existing code to follow):
- `backend/api/main.py` (from T14) — The FastAPI app to mount as TestClient. Integration tests import this app directly.
- `backend/pipeline/ingest.py` (from T3) — Data ingestion module. Integration test calls this to load mini dataset into SQLite.
- `backend/features/cardinal_flags.py` (from T6) — Cardinal red flag computation. Test verifies 73 columns exist after running this.
- `backend/features/custom_features.py` (from T6) — Custom feature engineering. Test verifies 12 additional features computed.
- `backend/models/tri_method.py` (from T8) — Tri-Method AI prediction. Test verifies all 50 tenders get risk_level.
- `backend/xai/shap_explainer.py` (from T10), `backend/xai/dice_explainer.py` (from T12), `backend/xai/anchor_explainer.py` (from T10) — XAI layer modules. Test verifies each produces output.
- `backend/xai/benford_analyzer.py` (from T9) — Benford module. Test verifies it returns result or not_applicable.
- `backend/graph/leiden_detector.py` (from T7) — Graph module. Test verifies community detection runs.
- `backend/reports/generator.py` (from T13) — Report generator. Test verifies IIA-format report text.

**API/Type References** (contracts to implement against):
- `backend/core/types.py:TenderRecord` (from T2) — Shape of tender data in mini dataset
- `backend/core/types.py:RiskLevel` (from T2) — Enum: aman, perlu_pantauan, risiko_tinggi, risiko_kritis
- `backend/core/types.py:ExplanationResponse` (from T2) — Shape of full XAI response (5 layers)
- `backend/core/config.py:RuntimeConfig` (from T4) — Config shape for injection tests
- FastAPI `TestClient` from `httpx` — `from fastapi.testclient import TestClient`

**External References** (libraries and frameworks):
- FastAPI testing docs: https://fastapi.tiangolo.com/tutorial/testing/ — How to use TestClient for integration testing without running a server
- pytest fixtures: https://docs.pytest.org/en/stable/fixture.html — Shared fixtures in conftest.py
- OCDS format reference: https://standard.open-contracting.org/latest/en/ — Mini dataset must follow OCDS structure

**WHY Each Reference Matters**:
- `backend/api/main.py` → The app imported by TestClient. If API routes changed, tests must match.
- `backend/pipeline/ingest.py` → Data loading entry point. Mini dataset must be compatible with the ingestion format.
- All XAI modules → Integration test must call each one and verify it returns the expected type. If any module signature changed, tests break.
- `backend/core/types.py` → Response shapes define what the test asserts against. Wrong types = wrong assertions.
- OCDS format → Mini dataset must be valid OCDS for Cardinal to process it. Invalid format = Cardinal crashes = test fails for wrong reason.

**Acceptance Criteria**:

- [ ] `tests/fixtures/mini_tenders.json` exists with 50 OCDS-format tender records
- [ ] `tests/conftest.py` exists with `mini_db`, `app_client`, `runtime_config` fixtures
- [ ] `tests/test_integration.py` exists and passes: `pytest tests/test_integration.py -q`
- [ ] Pipeline test covers: ingest → features → predict → explain (all 5 layers) → report
- [ ] API test covers: health, predict, explain, graph, report, config inject (valid + invalid)
- [ ] `tests/test_offline_no_network.py` exists and passes: `pytest tests/test_offline_no_network.py -q`
- [ ] No test requires a running server process — all use TestClient
- [ ] All tests complete in < 60 seconds total
- [ ] `pytest tests/ -q` (all tests including unit + integration) passes with 0 failures

**QA Scenarios:**

```
Scenario: Full pipeline integration test (happy path)
  Tool: Bash
  Preconditions: T20 bundle built, all backend modules functional, ONNX models exported
  Steps:
    1. Run `pytest tests/test_integration.py -v --tb=short`
    2. Assert exit code 0
    3. Assert output contains "test_full_pipeline PASSED"
    4. Assert output contains "test_api_health PASSED"
    5. Assert output contains "test_api_predict PASSED"
    6. Assert output contains "test_api_explain PASSED"
    7. Assert output contains "test_api_graph PASSED"
    8. Assert output contains "test_api_report PASSED"
    9. Assert output contains "test_api_inject_valid PASSED"
    10. Assert output contains "test_api_inject_invalid PASSED"
    11. Capture full pytest output to evidence file
  Expected Result: All integration tests pass, covering the complete pipeline from ingestion to report generation
  Failure Indicators: Any test FAILED, import errors, fixture not found, timeout
  Evidence: .sisyphus/evidence/task-21-integration-tests.txt

Scenario: Offline enforcement test
  Tool: Bash
  Preconditions: Network mock configured in test_offline_no_network.py
  Steps:
    1. Run `pytest tests/test_offline_no_network.py -v --tb=short`
    2. Assert exit code 0
    3. Assert output contains "test_no_outbound_connections PASSED"
    4. Assert output contains "test_local_tiles_only PASSED" (if map tiles tested)
  Expected Result: Full inference pipeline works with zero network access
  Failure Indicators: ConnectionError not raised when expected, test FAILED
  Evidence: .sisyphus/evidence/task-21-offline-test.txt

Scenario: Mini dataset validity check
  Tool: Bash
  Preconditions: mini_tenders.json created
  Steps:
    1. Run `python -c "import json; d=json.load(open('tests/fixtures/mini_tenders.json')); print(len(d)); assert len(d)==50"`
    2. Assert exit code 0 and output is "50"
    3. Run `python -c "import json; d=json.load(open('tests/fixtures/mini_tenders.json')); assert all('ocid' in t for t in d); print('OCDS valid')"`
    4. Assert output contains "OCDS valid"
  Expected Result: Mini dataset has exactly 50 valid OCDS records
  Failure Indicators: Wrong count, missing OCDS fields, JSON parse error
  Evidence: .sisyphus/evidence/task-21-mini-dataset.txt

Scenario: All tests suite completes in < 60 seconds
  Tool: Bash
  Preconditions: All test files created
  Steps:
    1. Run `time pytest tests/ -q --tb=short` (or equivalent timing)
    2. Assert exit code 0
    3. Assert total elapsed time < 60 seconds
    4. Assert "0 failed" in output
  Expected Result: Entire test suite (unit + integration) passes quickly enough for CI and demo
  Failure Indicators: Total time > 60s, any failures
  Evidence: .sisyphus/evidence/task-21-test-suite-timing.txt
```

**Evidence to Capture:**
- [ ] task-21-integration-tests.txt — Full pytest verbose output for integration tests
- [ ] task-21-offline-test.txt — Offline enforcement test output
- [ ] task-21-mini-dataset.txt — Mini dataset validation output
- [ ] task-21-test-suite-timing.txt — Full test suite timing and results

**Commit**: YES (groups with Wave 5)
- Message: `test(integration): end-to-end pipeline tests + offline enforcement + mini dataset`
- Files: `tests/test_integration.py`, `tests/test_offline_no_network.py`, `tests/conftest.py`, `tests/fixtures/mini_tenders.json`
- Pre-commit: `pytest tests/test_integration.py -q`

---

### Task 22 — Runtime Injection Stress Test (All Parameter Combinations)

> **Wave 5 — Integration + Packaging** | Depends: T4 (runtime config), T14 (API), T20 (bundle) | Blocks: F1-F4 (Final Verification)

**What to do**:
- Create `tests/test_injection_stress.py` with comprehensive tests for ALL 7 injectable parameters + custom_params wildcard:
- **Test each parameter individually** (7 tests):
  1. `procurement_scope` → set to each valid value: `konstruksi`, `barang`, `jasa_konsultansi`, `jasa_lainnya`. Assert predictions change when scope changes.
  2. `institution_filter` → set to a specific K/L/Pemda name. Assert only matching tenders are processed.
  3. `risk_threshold` → sweep from 0.0 to 1.0 in 0.1 steps. Assert risk classifications shift appropriately (low threshold = more flagged).
  4. `year_range` → set `[2022, 2023]` then `[2023, 2024]`. Assert only tenders in range are included.
  5. `anomaly_method` → cycle through `isolation_forest`, `xgboost`, `ensemble`. Assert each method produces predictions without error.
  6. `output_format` → test `dashboard`, `api_json`, `audit_report`. Assert response format changes accordingly.
  7. `custom_params` → inject `{"new_flag": true, "special_weight": 0.5}`. Assert params are accepted and logged, system doesn't crash.
- **Test parameter combinations** (combinatorial):
  - Inject 2-3 params simultaneously via `PUT /api/config/inject`
  - Example: `{"risk_threshold": 0.3, "procurement_scope": "konstruksi", "anomaly_method": "xgboost"}`
  - Verify all injected params take effect simultaneously
- **Test invalid parameter rejection** (negative tests):
  - `risk_threshold: -0.5` → expect 422 with descriptive error mentioning valid range
  - `risk_threshold: 2.0` → expect 422 with descriptive error
  - `anomaly_method: "neural_network"` → expect 422 with valid options listed
  - `procurement_scope: 123` → expect 422 (wrong type)
  - `unknown_top_level_param: "foo"` → expect 422 (not in schema, not via custom_params)
  - Empty body `{}` → expect 200 (no changes, valid noop)
- **Test no-restart requirement**:
  - Inject param → verify change takes effect
  - Inject different param → verify new change takes effect, previous still active
  - Do NOT restart server between injections (verify via process PID or health check uptime)
- **Test config persistence across requests**:
  - Inject `risk_threshold: 0.3` → make prediction request → verify threshold applied
  - Make another prediction request WITHOUT re-injecting → verify threshold STILL 0.3 (not reset to default)
- **Test config reset/default**:
  - Inject override → verify applied
  - Inject original default value → verify back to baseline behavior

**Must NOT do**:
- Do NOT test with the full 1.1M dataset — use mini dataset from T21 fixtures
- Do NOT restart the server between injection tests — the entire point is hot-reload
- Do NOT mock the config system — use real Pydantic validation
- Do NOT test individual Pydantic validators in isolation — test through the API endpoint
- Do NOT generate random parameter combinations — use explicit, deterministic test cases
- Do NOT ignore the `custom_params` wildcard — this is specifically for unknown competition-time injections

**Recommended Agent Profile**:
> Runtime injection testing requires understanding of the config system architecture, API validation behavior, and how parameter changes propagate through the prediction pipeline. Needs systematic combinatorial thinking.
- **Category**: `deep`
  - Reason: Stress testing requires systematic parameter enumeration, understanding of Pydantic validation edge cases, and verification that config changes propagate correctly through the ML pipeline
- **Skills**: []
- **Skills Evaluated but Omitted**:
  - `playwright`: Not needed — these are API-level tests using curl/TestClient
  - `frontend-ui-ux`: Not relevant — purely backend config + API testing

**Parallelization**:
- **Can Run In Parallel**: YES — with T21 (integration tests) and T23 (docs), after T20 completes
- **Parallel Group**: Wave 5B (T21 + T22 + T23 run in parallel after T20)
- **Blocks**: F1-F4 (Final Verification Wave depends on all tests passing)
- **Blocked By**: T4 (runtime config system), T14 (API endpoints), T20 (bundle to test against)

**References**:

**Pattern References** (existing code to follow):
- `backend/core/config.py:RuntimeConfig` (from T4) — The Pydantic model defining all 7 injectable parameters + custom_params. This is the source of truth for valid values, types, and constraints.
- `backend/api/routes/config.py:inject_config()` (from T4) — The `PUT /api/config/inject` endpoint. Stress test calls this endpoint with various payloads.
- `tests/conftest.py:app_client` (from T21) — Reuse the TestClient fixture for API testing without a running server.

**API/Type References** (contracts to implement against):
- `backend/core/config.py:RuntimeConfig` (from T4) — Full parameter schema:
  - `procurement_scope: Literal["konstruksi", "barang", "jasa_konsultansi", "jasa_lainnya"]`
  - `institution_filter: Optional[str]`
  - `risk_threshold: float` (0.0-1.0)
  - `year_range: Tuple[int, int]`
  - `anomaly_method: Literal["isolation_forest", "xgboost", "ensemble"]`
  - `output_format: Literal["dashboard", "api_json", "audit_report"]`
  - `custom_params: Dict[str, Any]`
- UPGRADE 3 lines 170-179 — The exact list of injectable parameters as described in the proposal

**External References** (libraries and frameworks):
- Pydantic validation: https://docs.pydantic.dev/latest/concepts/validators/ — How Pydantic rejects invalid values and generates error messages
- FastAPI request validation: https://fastapi.tiangolo.com/tutorial/handling-errors/ — 422 Unprocessable Entity error format

**WHY Each Reference Matters**:
- `RuntimeConfig` → Defines EXACTLY what values are valid. Tests must match these constraints to test boundaries correctly.
- `inject_config()` → The actual endpoint being stress-tested. Tests must match its expected request body format.
- UPGRADE 3 lines 170-179 → The proposal promises these exact 7 parameters. Competition judges will test them. Missing any = points lost.
- Pydantic docs → Understanding how Pydantic formats error messages helps write correct assertions for rejection tests.

**Acceptance Criteria**:

- [ ] `tests/test_injection_stress.py` exists and passes: `pytest tests/test_injection_stress.py -q`
- [ ] All 7 parameters tested individually (7 test functions minimum)
- [ ] Multi-parameter combination test (at least 3 combinations)
- [ ] Invalid value rejection tests (at least 6 negative test cases)
- [ ] No-restart verification (config persists across requests)
- [ ] Config persistence test (injected values survive multiple requests)
- [ ] `custom_params` wildcard works for unknown parameters
- [ ] All tests use TestClient (no running server required)
- [ ] Tests complete in < 30 seconds total

**QA Scenarios:**

```
Scenario: Individual parameter injection — risk_threshold sweep
  Tool: Bash
  Preconditions: App client configured with mini dataset, default config loaded
  Steps:
    1. Run `pytest tests/test_injection_stress.py::test_risk_threshold_sweep -v --tb=short`
    2. Assert exit code 0
    3. Assert output shows test passing with all threshold values tested (0.0, 0.1, ..., 1.0)
  Expected Result: Risk threshold changes correctly affect classification distribution
  Failure Indicators: Same classification count regardless of threshold, validation error on valid values
  Evidence: .sisyphus/evidence/task-22-threshold-sweep.txt

Scenario: Invalid parameter rejection (negative tests)
  Tool: Bash
  Preconditions: App client configured
  Steps:
    1. Run `pytest tests/test_injection_stress.py::test_invalid_params -v --tb=short`
    2. Assert exit code 0
    3. Assert output shows all negative tests passing:
       - `test_invalid_threshold_negative` PASSED
       - `test_invalid_threshold_over_one` PASSED
       - `test_invalid_anomaly_method` PASSED
       - `test_invalid_scope_type` PASSED
       - `test_unknown_top_level_param` PASSED
       - `test_empty_body_noop` PASSED
  Expected Result: All invalid inputs are rejected with 422 + descriptive error; empty body is accepted as noop
  Failure Indicators: Invalid input accepted (200 instead of 422), valid empty body rejected, no error description
  Evidence: .sisyphus/evidence/task-22-invalid-params.txt

Scenario: Multi-parameter combo + no-restart persistence
  Tool: Bash
  Preconditions: App client configured with mini dataset
  Steps:
    1. Run `pytest tests/test_injection_stress.py::test_multi_param_combo -v --tb=short`
    2. Assert exit code 0
    3. Run `pytest tests/test_injection_stress.py::test_config_persistence -v --tb=short`
    4. Assert exit code 0
  Expected Result: Multiple params injected simultaneously take effect; config persists across subsequent requests without re-injection
  Failure Indicators: Only first param takes effect, config resets between requests
  Evidence: .sisyphus/evidence/task-22-combo-persistence.txt

Scenario: Custom params wildcard accepts unknown parameters
  Tool: Bash
  Preconditions: App client configured
  Steps:
    1. Run `pytest tests/test_injection_stress.py::test_custom_params_wildcard -v --tb=short`
    2. Assert exit code 0
    3. Assert custom_params values are stored and accessible
  Expected Result: Unknown parameters injected via custom_params dict are accepted, stored, and don't crash the system
  Failure Indicators: 422 rejection for custom_params, KeyError, system crash
  Evidence: .sisyphus/evidence/task-22-custom-params.txt

Scenario: Full stress test suite passes
  Tool: Bash
  Preconditions: All test functions written
  Steps:
    1. Run `pytest tests/test_injection_stress.py -v --tb=short`
    2. Assert exit code 0
    3. Assert total time < 30 seconds
    4. Assert "0 failed" in output
  Expected Result: All injection stress tests pass within time budget
  Failure Indicators: Any test FAILED, timeout
  Evidence: .sisyphus/evidence/task-22-full-stress-suite.txt
```

**Evidence to Capture:**
- [ ] task-22-threshold-sweep.txt — Risk threshold sweep test output
- [ ] task-22-invalid-params.txt — Invalid parameter rejection test output
- [ ] task-22-combo-persistence.txt — Multi-param combo + persistence test output
- [ ] task-22-custom-params.txt — Custom params wildcard test output
- [ ] task-22-full-stress-suite.txt — Complete stress test suite output with timing

**Commit**: YES (groups with Wave 5)
- Message: `test(injection): runtime injection stress tests — all 7 params + combos + negative cases`
- Files: `tests/test_injection_stress.py`
- Pre-commit: `pytest tests/test_injection_stress.py -q`

---

### Task 23 — Stage 3 Sprint Playbook, Demo Script & Architecture Documentation

**Wave**: 5B | **Depends on**: T20 (offline bundle — to reference actual app structure), T21 (integration tests — to list verified features) | **Blocks**: F1-F4 (Final Verification Wave)

**What to do**:

1. **`docs/SPRINT_PLAYBOOK.md`** — 24-hour Stage 3 sprint schedule:
   - **Phase 0 — Setup (0–2h):** Clone repo, install dependencies (`pip install -e ".[dev]"` + `cd frontend && npm ci`), verify SQLite DB path, run `pytest tests/ -q` to confirm green baseline, download opentender.net mini-dataset (10k tenders) if full dataset not pre-cached, verify ONNX model file present at `models/ensemble.onnx`
   - **Phase 1 — Core Features (2–8h):** Focus on data pipeline (T5/T6), feature engineering (T7/T8), model training + ONNX export (T9/T10/T11). Each sub-phase includes the exact command to run and expected output.
   - **Phase 2 — Integration (8–16h):** API endpoints (T14), XAI pipeline (T12/T13), report generation (T15). Wire frontend to backend. Test dynamic injection endpoint (`PUT /api/config/inject`).
   - **Phase 3 — Polish & UI (16–20h):** Dashboard polish (T16/T17), map visualization (T18), report viewer (T19). Offline bundle verification (T20).
   - **Phase 4 — Demo Prep (20–24h):** Run full integration tests (T21), injection stress tests (T22), rehearse demo script (this task), final offline bundle build.
   - **Team Role Assignments** (4-5 people):
     - **Lead ML Engineer**: Data pipeline + Feature Engineering + Model Training (T5–T11)
     - **XAI Specialist**: Oracle Sandwich XAI pipeline + Report Generation (T12–T13, T15)
     - **Backend Engineer**: FastAPI endpoints + Dynamic Injection + Database (T4, T14)
     - **Frontend Engineer**: React dashboard + Plotly charts + Folium maps (T16–T19)
     - **DevOps/QA** (optional 5th): Offline bundle + Testing + Demo rehearsal (T20–T23)
   - **Emergency Protocols**:
     - If `cardinal` fails to install → fall back to manual red flag computation using `backend/features/cardinal_fallback.py` (T7 includes this)
     - If ONNX export fails → serve raw sklearn/xgboost models directly (slower but functional)
     - If `leidenalg` fails (C++ compilation) → use `igraph` community detection as fallback
     - If opentender.net API is down → use pre-cached SQLite dataset
     - If DiCE is too slow → disable counterfactual layer, keep 4/5 XAI layers
     - If frontend build fails → serve React dev server (`npm start`) for demo
   - **Pre-built Script References**: List every `Makefile` / CLI command from T1 (`make setup`, `make test`, `make dev`, `make bundle`)

2. **`docs/DEMO_SCRIPT.md`** — Minute-by-minute demo narrative (10-15 min presentation):
   - **Opening (0–1 min):** Problem statement — "70%+ kasus korupsi KPK terkait pengadaan" [Ref: UPGRADE 3 line 262]. Show Transparency International score (34/100, rank 109) [UPGRADE 3 line 274]. Show ICW 2024 stats (364 cases, Rp 279.9T) [UPGRADE 3 line 270].
   - **Data (1–3 min):** Show opentender.net data (1.1M tenders, 55+ fields). Live API call demo: `curl https://opentender.net/api/tender/export/?limit=5`. Show raw vs processed data side by side.
   - **Feature Engineering (3–5 min):** Show Cardinal 73 red flags being computed. Show the 12 custom forensic features table. Highlight Phantom Bidder Score and Bid Clustering Score as novel signals.
   - **Model (5–7 min):** Show Tri-Method AI architecture diagram. Demonstrate Disagreement Protocol: when IF says safe but XGBoost says risky → "Manual Review Priority". Show ONNX inference speed (<200ms).
   - **Explainability — Oracle Sandwich (7–11 min):** THIS IS THE MONEY SHOT for Track C.
     - SHAP summary plot: "Which features matter most globally?"
     - DiCE counterfactual: "What would need to change for this tender to NOT be flagged?"
     - Anchors rule: "Simple rule the model follows"
     - Leiden graph visualization: "These 5 vendors form a cartel cluster"
     - Benford's Law chart: "Bid prices violate natural digit distribution"
   - **Dynamic Injection Demo (11–12 min):** Live `PUT /api/config/inject` call changing `risk_threshold` from 0.5 to 0.3. Show dashboard updating in real-time. Change `procurement_scope` to `konstruksi`. Show filtered results. Inject `custom_params` with unexpected key — show it's accepted and logged.
   - **Report (12–13 min):** Show auto-generated pre-investigation report in IIA 2025 format. Highlight NLG narrative quality.
   - **Impact & Closing (13–15 min):** Rp 279.9T potential savings. EU AI Act compliance. First system in Indonesia with 5-layer XAI.
   - **Prepared Judge Q&A Section**: At least 10 questions with prepared answers (see T23.4 below).

3. **`docs/ARCHITECTURE.md`** — System architecture documentation:
   - **Mermaid Diagram**: Full system data flow from opentender.net → data pipeline → feature engineering → model inference → XAI → report → frontend. Show each component as a box with library names.
   - **Component Descriptions**: One paragraph per module explaining what it does, why it exists, and which proposal section it implements.
   - **Technology Justification Table**: For each library (XGBoost, Isolation Forest, NetworkX, Leiden, Cardinal, SHAP, DiCE, Anchors/alibi, benford_py, ONNX Runtime, FastAPI, React, Plotly, Folium, SQLite, Pydantic), explain: why chosen, alternatives considered, trade-off made.
   - **Module Dependency Graph**: Which modules import from which. Show clean dependency direction (no circular deps).
   - **Runtime Config Flow**: How `runtime_config.yaml` → Pydantic → ConfigManager → all modules. Show dynamic injection path.

4. **`docs/TALKING_POINTS.md`** — Judge Q&A preparation:
   - **Expected Questions & Prepared Answers** (minimum 10):
     1. "How do you handle the cold-start/no-label problem?" → ICW weak labels + Isolation Forest unsupervised
     2. "Why not use deep learning / transformers?" → Explainability requirement (Track C), XGBoost is SHAP-native, ONNX keeps inference <200ms on CPU
     3. "How is this different from opentender.net?" → opentender has 7 rules, we have 85 signals + ML + graph + 5-layer XAI
     4. "Can this scale to all 1.1M tenders?" → Yes, ONNX Runtime + SQLite + batch processing
     5. "What about false positives?" → Disagreement Protocol flags uncertain cases for human review, Oracle Sandwich gives evidence for each flag
     6. "How do you handle dynamic injection?" → Pydantic-validated YAML config + live PUT endpoint + no restart
     7. "What if vendors change their fraud patterns?" → Isolation Forest detects novel anomalies, graph structure reveals hidden connections
     8. "Is this legally defensible?" → EU AI Act Pasal 86 compliance, IIA 2025 report format, human-in-the-loop design
     9. "What data privacy concerns exist?" → All data is public procurement data (government transparency), NPWP used only for network analysis
     10. "What's the deployment path to production?" → Localhost demo → LKPP pilot → integration with SPSE V5 roadmap
   - **Competitive Differentiation Points**: Table comparing LPSE-X vs ARACHNE vs BRIAS vs ALICE vs JAGA vs opentender.net (replicate UPGRADE 3 lines 86-94 with additional technical depth)
   - **Novelty Arguments**: 4 bullet points from UPGRADE 3 lines 183-189, expanded with technical evidence
   - **Weakness Acknowledgments with Mitigation**:
     - "No real fraud labels" → Mitigated by ICW weak labels + unsupervised IF + disagreement protocol
     - "Localhost only" → Competition constraint, architecture is cloud-ready
     - "DiCE can be slow" → Async/cached, not blocking inference
     - "Graph analysis needs connected data" → opentender.net provides NPWP linkages

**Must NOT do**:
- Do NOT write any code — this is purely documentation
- Do NOT make up performance metrics or benchmarks that haven't been verified
- Do NOT promise features that aren't in the plan (Tasks 1-22)
- Do NOT include implementation details that contradict the plan (e.g., don't mention Streamlit if we're using React)
- Do NOT create generic/vague playbook steps — every step must reference a specific Task number and specific command
- Do NOT write marketing fluff — keep tone technical and evidence-based

**Recommended Agent Profile**:
> Documentation task requiring deep understanding of the full system architecture, competition context, and proposal claims. Must synthesize information from proposal, plan, and research findings into actionable documents.
- **Category**: `writing`
  - Reason: Pure documentation task — no code writing, focused on clear technical prose, structured narratives, and judge-facing communication
- **Skills**: []
- **Skills Evaluated but Omitted**:
  - `playwright`: Not needed — no browser interaction, pure markdown writing
  - `frontend-ui-ux`: Not relevant — documentation only
  - `git-master`: Not needed — simple file creation, no complex git operations

**Parallelization**:
- **Can Run In Parallel**: YES — with T21 (integration tests) and T22 (injection stress tests)
- **Parallel Group**: Wave 5B (T21 + T22 + T23 run in parallel after T20)
- **Blocks**: F1-F4 (Final Verification Wave — F1 needs architecture docs to verify compliance, F3 needs demo script to execute)
- **Blocked By**: T20 (offline bundle — to reference actual build commands), T21 (integration tests — to list verified features in demo)

**References**:

**Pattern References** (existing code to follow):
- `.sisyphus/plans/lpse-x-build.md` (this plan) — Tasks 1-22 contain the complete implementation spec. The SPRINT_PLAYBOOK must reference specific task numbers and their outputs. The ARCHITECTURE.md must mirror the module structure defined in T1-T3.
- `backend/core/config.py:RuntimeConfig` (from T4) — The dynamic injection config that must be prominently featured in the demo script
- `Makefile` (from T1) — All build/test/run commands that the sprint playbook must reference

**API/Type References** (contracts to implement against):
- `backend/api/routes/*.py` (from T14) — All API endpoint signatures needed for the demo script's live API calls
- `backend/xai/oracle_sandwich.py` (from T12) — The 5-layer XAI output structure that must be accurately described in architecture docs
- `backend/reports/generator.py` (from T15) — Report template and NLG output format for demo script

**External References** (libraries and frameworks):
- UPGRADE 3 (full file) — The competition proposal. Lines 86-94 (competitive comparison), 102-179 (architecture + tech), 181-189 (novelty), 262-275 (impact statistics). DEMO_SCRIPT and TALKING_POINTS must align exactly with proposal claims.
- `C:\Hackthon\DEEP_RESEARCH_SYNTHESIS.md` — Research findings (474 lines). Lines 27-60 (graph research), 86-127 (XAI papers), 130-168 (tools), 171-193 (opentender), 210-230 (Oracle Sandwich). Use as evidence base for talking points.
- Find IT! 2026 competition rules — Dynamic injection requirement, scoring criteria, Track C (XAI) emphasis. The demo script must explicitly address scoring rubric dimensions.
- Mermaid diagram syntax: https://mermaid.js.org/syntax/flowchart.html — For architecture diagrams in markdown

**WHY Each Reference Matters**:
- This plan (Tasks 1-22) → The playbook MUST reference exact task numbers and commands. Vague instructions like "set up the backend" are useless — the playbook must say "Run Task 14 commands: `uvicorn backend.api.main:app`".
- UPGRADE 3 → Every claim in the demo script and talking points MUST trace back to a specific line in the proposal. Judges will compare your demo against your abstract.
- DEEP_RESEARCH_SYNTHESIS → Provides academic citations and evidence that strengthen talking points. E.g., "Imhof et al. 2025: 91% accuracy with graph methods" adds credibility.
- Competition rules → The demo must explicitly demonstrate dynamic injection (disqualification risk if missing) and XAI (Track C scoring focus).

**Acceptance Criteria**:

- [ ] `docs/SPRINT_PLAYBOOK.md` exists and contains all 5 phases with time allocations
- [ ] Every phase references specific Task numbers (T1-T22) and exact commands
- [ ] Team role assignments cover 4-5 people with clear ownership per task
- [ ] Emergency protocols cover at least 6 failure scenarios with concrete fallbacks
- [ ] `docs/DEMO_SCRIPT.md` exists with minute-by-minute breakdown (10-15 min)
- [ ] Demo script includes live dynamic injection demo with specific `curl` commands
- [ ] Demo script covers all 5 Oracle Sandwich XAI layers with specific click/show actions
- [ ] `docs/ARCHITECTURE.md` exists with Mermaid diagram and component descriptions
- [ ] Architecture diagram covers all 5 core mechanisms from proposal
- [ ] Technology justification table covers all 16+ libraries with alternatives considered
- [ ] `docs/TALKING_POINTS.md` exists with ≥10 prepared judge Q&A pairs
- [ ] Competitive differentiation table present (LPSE-X vs 6 competitors)
- [ ] Weakness acknowledgments present with mitigations
- [ ] All statistics cited in docs match UPGRADE 3 exactly (70% KPK, 34/100 TI, 364 cases ICW, Rp 279.9T)
- [ ] No reference to Streamlit — frontend is React throughout
- [ ] All 4 files are valid Markdown with no broken links or formatting issues

**QA Scenarios:**

```
Scenario: Sprint playbook completeness — all tasks referenced
  Tool: Bash (grep)
  Preconditions: docs/SPRINT_PLAYBOOK.md exists
  Steps:
    1. Run `grep -c "T[0-9]\+" docs/SPRINT_PLAYBOOK.md` — count task references
    2. Assert count ≥ 22 (every task T1-T22 referenced at least once)
    3. Run `grep -c "make \|pytest \|uvicorn \|npm " docs/SPRINT_PLAYBOOK.md` — count command references
    4. Assert count ≥ 10 (concrete commands, not vague instructions)
    5. Run `grep -c "Phase [0-4]" docs/SPRINT_PLAYBOOK.md`
    6. Assert count ≥ 5 (all 5 phases present)
  Expected Result: All 22 tasks referenced, ≥10 concrete commands, 5 phases present
  Failure Indicators: Tasks missing from playbook, generic instructions without commands, missing phases
  Evidence: .sisyphus/evidence/task-23-playbook-completeness.txt

Scenario: Demo script — dynamic injection demo present and accurate
  Tool: Bash (grep)
  Preconditions: docs/DEMO_SCRIPT.md exists
  Steps:
    1. Run `grep -c "PUT /api/config/inject\|curl.*inject" docs/DEMO_SCRIPT.md`
    2. Assert count ≥ 2 (at least 2 injection demo commands)
    3. Run `grep -c "risk_threshold\|procurement_scope\|custom_params" docs/DEMO_SCRIPT.md`
    4. Assert count ≥ 3 (all key injectable params mentioned in demo)
    5. Run `grep -c "SHAP\|DiCE\|Anchors\|Leiden\|Benford" docs/DEMO_SCRIPT.md`
    6. Assert count ≥ 5 (all 5 Oracle Sandwich layers in demo)
    7. Run `grep -c "min\b" docs/DEMO_SCRIPT.md` to verify minute-by-minute structure
    8. Assert count ≥ 5 (time markers present)
  Expected Result: Dynamic injection demo with concrete curl commands, all 5 XAI layers, time-structured
  Failure Indicators: Missing injection demo, fewer than 5 XAI layers, no time structure
  Evidence: .sisyphus/evidence/task-23-demo-injection.txt

Scenario: Architecture doc — Mermaid diagram renders and covers all modules
  Tool: Bash (grep)
  Preconditions: docs/ARCHITECTURE.md exists
  Steps:
    1. Run `grep -c "\`\`\`mermaid" docs/ARCHITECTURE.md`
    2. Assert count ≥ 1 (at least one Mermaid code block)
    3. Run `grep -c "Cardinal\|NetworkX\|Leiden\|XGBoost\|SHAP\|DiCE\|Anchors\|benford_py\|ONNX\|FastAPI\|React\|Plotly\|Folium\|SQLite\|Pydantic" docs/ARCHITECTURE.md`
    4. Assert count ≥ 15 (all major libraries mentioned)
    5. Run `grep -c "Alternatives\|Trade-off\|Why chosen" docs/ARCHITECTURE.md`
    6. Assert count ≥ 3 (technology justification present)
  Expected Result: Valid Mermaid diagram, all 16+ libraries documented, justifications present
  Failure Indicators: No Mermaid block, missing libraries, no justification column
  Evidence: .sisyphus/evidence/task-23-architecture-mermaid.txt

Scenario: Talking points — judge Q&A completeness
  Tool: Bash (grep)
  Preconditions: docs/TALKING_POINTS.md exists
  Steps:
    1. Run `grep -c "^[0-9]\+\.\|^- \*\*Q" docs/TALKING_POINTS.md` to count Q&A pairs
    2. Assert count ≥ 10 (at least 10 prepared questions)
    3. Run `grep -c "ARACHNE\|BRIAS\|ALICE\|JAGA\|opentender" docs/TALKING_POINTS.md`
    4. Assert count ≥ 5 (competitive comparison present)
    5. Run `grep -c "Weakness\|Limitation\|Mitigation" docs/TALKING_POINTS.md`
    6. Assert count ≥ 3 (weakness acknowledgments present)
    7. Run `grep -c "70%\|34/100\|364 kasus\|279.9\|279,9" docs/TALKING_POINTS.md`
    8. Assert count ≥ 2 (key statistics cited)
  Expected Result: ≥10 Q&A pairs, competitive table, weaknesses acknowledged, statistics accurate
  Failure Indicators: Fewer than 10 Q&A, missing competitors, no weakness section, wrong statistics
  Evidence: .sisyphus/evidence/task-23-talking-points.txt

Scenario: Cross-document consistency — no Streamlit references, React throughout
  Tool: Bash (grep)
  Preconditions: All 4 docs exist
  Steps:
    1. Run `grep -ri "streamlit" docs/SPRINT_PLAYBOOK.md docs/DEMO_SCRIPT.md docs/ARCHITECTURE.md docs/TALKING_POINTS.md`
    2. Assert output is empty (zero Streamlit references)
    3. Run `grep -c "React" docs/ARCHITECTURE.md`
    4. Assert count ≥ 1 (React mentioned as frontend)
    5. Run `grep -ri "cloud\|aws\|gcp\|azure\|heroku" docs/` — check no cloud references
    6. Assert output is empty or only in context of "cloud-ready architecture" future plans
  Expected Result: Zero Streamlit mentions, React present, no cloud deployment claims
  Failure Indicators: Streamlit found anywhere, React missing from architecture, cloud deployment promised
  Evidence: .sisyphus/evidence/task-23-consistency.txt
```

**Evidence to Capture:**
- [ ] task-23-playbook-completeness.txt — Sprint playbook grep results showing task/command coverage
- [ ] task-23-demo-injection.txt — Demo script grep results showing injection demo and XAI layers
- [ ] task-23-architecture-mermaid.txt — Architecture doc grep results showing Mermaid + libraries
- [ ] task-23-talking-points.txt — Talking points grep results showing Q&A count and completeness
- [ ] task-23-consistency.txt — Cross-document consistency check (no Streamlit, React present)

**Commit**: YES (groups with Wave 5)
- Message: `docs(sprint): sprint playbook, demo script, architecture docs, and judge Q&A talking points`
- Files: `docs/SPRINT_PLAYBOOK.md`, `docs/DEMO_SCRIPT.md`, `docs/ARCHITECTURE.md`, `docs/TALKING_POINTS.md`
- Pre-commit: `test -f docs/SPRINT_PLAYBOOK.md && test -f docs/DEMO_SCRIPT.md && test -f docs/ARCHITECTURE.md && test -f docs/TALKING_POINTS.md`


## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run linter + `pytest tests/ -q`. Review all changed files for: `as any`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp). Verify structured logging, type annotations, docstrings.
  Output: `Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill for UI)
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (features working together). Test edge cases: empty state, invalid input, rapid actions. Test offline mode (Wi-Fi disabled). Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | Offline [PASS/FAIL] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination. Verify proposal alignment: does the app match what UPGRADE 3 describes?
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Proposal Alignment [YES/NO] | VERDICT`

---

## Commit Strategy

| Wave | Commit Message | Key Files |
|------|---------------|-----------|
| 1 | `feat(scaffold): project structure, types, config, data pipeline` | `lpse-x/`, `pyproject.toml`, `package.json` |
| 2 | `feat(engine): feature engineering, graph detection, tri-method AI` | `backend/features/`, `backend/graph/`, `backend/models/` |
| 3 | `feat(xai): oracle sandwich XAI, ONNX export, reports, API` | `backend/xai/`, `backend/api/`, `backend/reports/` |
| 4 | `feat(ui): React dashboard, visualizations, maps, reports` | `frontend/src/` |
| 5 | `feat(bundle): offline packaging, integration tests, sprint playbook` | `bundle/`, `tests/`, `docs/` |
| FINAL | `chore(qa): final verification evidence` | `.sisyphus/evidence/` |

---

## Success Criteria

### Verification Commands
```bash
# Start server (offline mode)
python -m lpse_x.main                    # Expected: Server running on auto-detected port

# Runtime injection
curl -X PUT http://localhost:{port}/api/config/inject \
  -H 'Content-Type: application/json' \
  -d '{"risk_threshold": 0.8, "institution_filter": "Kemenkeu"}' # Expected: 200 OK

# Inference
curl http://localhost:{port}/api/tender/{id}/predict  # Expected: JSON with risk_level + score

# XAI
curl http://localhost:{port}/api/tender/{id}/explain   # Expected: 5-layer XAI response

# Graph
curl http://localhost:{port}/api/graph/communities      # Expected: Leiden communities JSON

# Report
curl http://localhost:{port}/api/tender/{id}/report     # Expected: IIA-format report

# Tests
pytest tests/ -q                           # Expected: ALL PASS
pytest tests/test_onnx_parity.py -q       # Expected: native vs ONNX allclose
pytest tests/test_leiden_seed_repro.py -q  # Expected: deterministic communities
pytest tests/test_xai_sla.py -q           # Expected: each layer under time budget
pytest tests/test_benford_gating.py -q    # Expected: not_applicable when pre-check fails
pytest tests/test_offline_no_network.py -q # Expected: zero outbound network calls
```

### Final Checklist
- [ ] All "Must Have" present and verified
- [ ] All "Must NOT Have" absent (codebase search)
- [ ] All tests pass
- [ ] App runs offline from single folder
- [ ] Runtime injection works for all documented parameters
- [ ] XAI layers produce output within latency SLA
- [ ] Pre-investigation report generates in Bahasa Indonesia
- [ ] Competition scoring criteria alignment verified per stage

### Competition Scoring Alignment

**Stage 2 AI (30% Model + 25% Data + 20% Method + 15% Robust + 10% Docs)**:
- Model Performance → Tasks 8, 11 (Tri-Method AI + ONNX <200ms)
- Data Engineering → Tasks 3, 6 (1.1M tenders, 85 features)
- Methodology → Tasks 7, 8, 9 (graph + ensemble + Benford)
- Robustness → Tasks 21, 22 (integration + injection tests)
- Documentation → Task 23 (sprint playbook + technical docs)

**Stage 2 SE (35% Inference + 25% Deps + 20% Spec + 20% Scale)**:
- Inference Readiness → Task 11 (ONNX <200ms, parity verified)
- Dependency Management → Task 1, 20 (pinned versions, offline bundle)
- Tech Spec → Task 2 (types, schemas, API contracts)
- Scalability → Task 14 (async FastAPI, connection pooling)

**Stage 2 Product (40% Arch + 30% Ethics + 30% Feasible)**:
- System Architecture → Tasks 1, 4, 14, 20 (modular, injectable, portable)
- Data Ethics/Privacy → Task 3 (NPWP anonymization, data handling policy)
- Implementation Feasibility → Task 20, 21 (offline demo, integration tests)

**Stage 3 AI (30% Live + 25% Integrity + 25% Integration + 20% Defense)**:
- Live Inference Quality → Task 11 (ONNX runtime, verified parity)
- Integrity/Consistency → Task 22 (injection doesn't break predictions)
- Integration Optimization → Task 21 (end-to-end pipeline)
- Technical Defense → Task 23 (demo script with talking points)

**Stage 3 SE (30% Flow + 30% Dynamic + 20% Execution + 20% Arch)**:
- System Integration Flow → Tasks 14, 20 (API → frontend seamless)
- Dynamic Adaptability → Tasks 4, 22 (runtime injection + stress test)
- Tech Execution → Task 20 (portable, auto-port, clean launch)
- Architecture Clarity → Task 23 (architecture diagram + defense)

**Stage 3 Product (30% Augment + 25% UX + 25% Story + 20% Viable)**:
- Augmenting Essence → Tasks 15-19 (dashboard augments auditor workflow)
- User Experience → Tasks 15-19 (React UI, interactive viz)
- Storytelling → Task 23 (demo narrative, problem→solution→impact)
- Solution Viability → Task 20, 21 (works offline, tested end-to-end)
