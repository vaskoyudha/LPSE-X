# LPSE-X Architecture Diagram — Work Plan

## TL;DR

> **Quick Summary**: Create a comprehensive Mermaid architecture diagram file (`LPSE-X_Architecture.md`) that visualizes all 10 major subsystems of the LPSE-X procurement fraud detection platform, using multiple modular Mermaid diagrams with correct GitHub rendering.
>
> **Deliverables**:
> - `C:\Hackthon\LPSE-X_Architecture.md` — Single file with 10+ Mermaid diagrams covering the complete system
>
> **Estimated Effort**: Short (1 task, ~30 min agent work)
> **Parallel Execution**: NO — single sequential task
> **Critical Path**: Task 1 (write entire file)

---

## Context

### Original Request
User requested a detailed Mermaid (.md) architecture diagram showing how the entire LPSE-X system works — covering data ingestion, feature engineering, graph analysis, AI models, XAI layers, report generation, backend, frontend, and runtime configuration.

### Interview Summary
**Key Discussions**:
- All content is fully specified in UPGRADE 3 proposal (340 lines) and DEEP_RESEARCH_SYNTHESIS.md (474 lines)
- User chose Mermaid format in a previous session
- Diagram must be comprehensive and detailed — not simplified
- Competition rules in AGENTS.md constrain the architecture (no external APIs, localhost only, dynamic injection mandatory)

**Research Findings**:
- Full tech stack is locked and non-negotiable (see AGENTS.md §8)
- 7 injectable parameters + custom_params wildcard are contractual
- 4 risk levels with exact Indonesian labels are contractual
- Performance SLAs are defined (<200ms inference, <2s SHAP, etc.)

### Metis Review
**Identified Gaps** (addressed):
- Mermaid rendering: Use modular small diagrams, quote labels, alphanumeric IDs → incorporated as guardrail
- Scope creep: Locked to "architecture visualization only" — no code, no wireframes, no API schemas
- Contract drift: All 7 injectable params, risk labels, and tech stack must appear verbatim → added as acceptance criteria
- Diagram diversity: Must use at least flowchart + sequenceDiagram; classDiagram/erDiagram/stateDiagram recommended
- Language policy: English headings + Indonesian terms where contractually required (risk labels, report language)

---

## Work Objectives

### Core Objective
Create a single Markdown file with 10+ Mermaid diagrams that fully visualize the LPSE-X system architecture for competition documentation and team reference.

### Concrete Deliverables
- `C:\Hackthon\LPSE-X_Architecture.md` — Complete architecture document

### Definition of Done
- [ ] File exists at `C:\Hackthon\LPSE-X_Architecture.md`
- [ ] Contains all 10 required sections with correct headings
- [ ] Contains ≥10 Mermaid diagram blocks
- [ ] Uses at least 2 diagram types (flowchart + sequenceDiagram minimum)
- [ ] All contractual terms present (7 params, risk labels, tech stack components)
- [ ] No references to disqualifying patterns (external APIs, cloud, Streamlit, hardcoded values)

### Must Have
- All 10 sections in exact order
- Verbatim: `procurement_scope`, `institution_filter`, `risk_threshold`, `year_range`, `anomaly_method`, `output_format`, `custom_params`
- Verbatim: `PUT /api/config/inject`
- Verbatim: `Aman → Perlu Pantauan → Risiko Tinggi → Risiko Kritis`
- All tech stack components named: Cardinal, OCP, NetworkX, leidenalg, XGBoost, Isolation Forest, ONNX Runtime, SHAP, DiCE, Anchors, benford_py, Jinja2, FastAPI, React, SQLite
- Performance annotations: <200ms inference, <2s SHAP, <5s Anchors, DiCE cached/async, Benford ≥100 records

### Must NOT Have (Guardrails)
- No implementation code (only architecture diagrams)
- No external API references (OpenAI, Google AI, cloud services)
- No Streamlit references (React is mandated)
- No hardcoded port numbers
- No Mermaid `click` callbacks (render issues)
- No single mega-diagram (must be modular, split by section)
- No components not in the proposal (no Kafka, Postgres, Redis, etc.)

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: N/A (documentation file)
- **Automated tests**: None (documentation)
- **Framework**: N/A

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Documentation**: Use Bash (Python one-liners) to verify file content, headings, required terms

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Single Task):
└── Task 1: Write complete LPSE-X_Architecture.md [writing]

Wave FINAL (After Task 1):
├── Task F1: Content verification [quick]
└── Task F2: Contract compliance check [quick]
```

### Dependency Matrix
- **1**: None → F1, F2
- **F1**: 1 → done
- **F2**: 1 → done

### Agent Dispatch Summary
- **Wave 1**: 1 task — T1 → `writing`
- **FINAL**: 2 tasks — F1 → `quick`, F2 → `quick`

---

## TODOs

 [x] 1. Write Complete LPSE-X Architecture Diagram File

  **What to do**:

  Create `C:\Hackthon\LPSE-X_Architecture.md` with a title header, introductory metadata block, and exactly 10 sections, each containing one or more Mermaid diagrams. The content MUST be sourced from three reference files. Use multiple Mermaid diagram types for variety.

  **Section-by-section specification:**

  **Section 1: System Overview — High-Level Architecture**
  - Diagram type: `flowchart TB`
  - Show all major subsystems as subgraph blocks: Data Sources (4), Ingestion Pipeline, SQLite Storage, Feature Engineering, Graph Engine, Tri-Method AI, Oracle Sandwich XAI (5 layers), Report Generation, FastAPI Backend (with Dynamic Injection endpoint), React Frontend (with 5 outputs), Runtime Config (YAML → Pydantic → ConfigManager)
  - Show data flow arrows between all subsystems
  - Show config flow (dotted arrows) from ConfigManager to ALL processing modules
  - Use color-coded classes: green=sources, blue=processing, orange=storage, purple=AI, pink=XAI, cyan=API, indigo=frontend, yellow=config

  **Section 2: Data Ingestion Pipeline — Detailed Flow**
  - Diagram type: `flowchart LR`
  - Left: 4 data sources with details (opentender.net: REST API endpoints `/api/tender/export/`, `/api/tender/export_hhi/`, `/api/tender/export-ocds-batch/`, 1,106,096 tenders, 55+ fields, OCDS; pyproc: Python wrapper, rate 1req/2s, exponential backoff; LKPP: CKAN API, 26 datasets, 631+ K/L/PD, XLSX/JSON; Corruption cases: KPK+MA+ICW, 200+ curated)
  - Middle: Pipeline stages (Async Fetcher httpx+aiofiles → OCDS Schema Validation Pydantic → Data Cleaning: median imputation, drop missing HPS/kontrak, IQR outlier detection, normalize → OCDS → Privacy: NPWP SHA-256 hash, store hash + last 4 digits → SQLite Bulk Insert aiosqlite raw SQL batch 5000/tx)
  - Right: SQLite tables (tenders, vendors, awards, corruption_cases, vendor_network_edges)

  **Section 3: Feature Engineering — 85 Forensic Signals**
  - Diagram type: `flowchart TB`
  - Show two parallel branches: Cardinal Library (OCP) → 73 Red Flags (subdivided into Planning/Tender/Award/Implementation phase flags) AND Custom ML Features → 12 features (list all 12 by name: Bid Clustering Score, Vendor Win Concentration, HPS Deviation Ratio, Participant Count Anomaly, Geographic Concentration, Repeat Pairing Index, Temporal Submission Pattern, Historical Win Rate, Phantom Bidder Score, Benford's Law Anomaly, Interlocking Directorates, Bid Rotation Pattern)
  - Both branches converge into: 85-Dimensional Feature Vector per Tender → Fed to Tri-Method AI

  **Section 4: Graph-Based Cartel Detection**
  - Diagram type: `flowchart LR` + second diagram `classDiagram` showing graph structure
  - Flowchart: SQLite vendor/award data → NetworkX Bipartite Graph (Vendor ↔ Tender) → Leiden Community Detection (leidenalg) → Cartel Clusters Identified → Graph Metrics (Degree, Betweenness, Community Membership) → Fed to Oracle Sandwich Layer 4
  - Class diagram: Show Vendor and Tender as classes linked by Bid relationship, with Community grouping

  **Section 5: Tri-Method AI Engine**
  - Diagram type: `flowchart TB` + second diagram `stateDiagram-v2` for risk classification
  - Flowchart: 85-dim Feature Vector fans out to 3 parallel paths: Isolation Forest (unsupervised, anomaly score) + XGBoost (supervised, 4-level classification) + ICW Weak Labels (weakly supervised, total_score from 1.1M tenders) → all three feed into Disagreement Protocol (weighted ensemble) → when models agree: weighted average risk score → when models disagree: flag as "Manual Review Priority" → ONNX Runtime (<200ms/prediction CPU)
  - State diagram: Show 4 risk states: Aman → Perlu Pantauan → Risiko Tinggi → Risiko Kritis with threshold transitions (risk_threshold from config)

  **Section 6: Oracle Sandwich XAI — 5 Layers**
  - Diagram type: `flowchart TB` showing the 5-layer sandwich architecture
  - Layer 1 GLOBAL: SHAP TreeExplainer → Summary Plots → "Which features matter most overall?" (<2s SLA)
  - Layer 2 LOCAL: DiCE Counterfactuals (Microsoft, dice-ml) → "What must change to NOT be flagged?" (Cached/Async, NOT blocking)
  - Layer 3 RULES: Anchors (alibi library) → If-Then Rules → "What simple rule does the model follow?" (<5s SLA)
  - Layer 4 GRAPH: Leiden Community Visualization → "Which companies form a cartel?" (<3s SLA)
  - Layer 5 STATISTICAL: Benford's Law (benford_py) → χ² Digit Distribution → "Are bid prices statistically natural?" (<1s SLA, requires ≥100 records pre-check)
  - Show all 5 layers feeding into the Report Generation module

  **Section 7: Auto Report Generation**
  - Diagram type: `sequenceDiagram`
  - Participants: User, FastAPI, ReportEngine, Jinja2, OracleSandwich, SQLite
  - Flow: User requests report for tender ID → FastAPI calls ReportEngine → ReportEngine queries SQLite for tender data → ReportEngine requests all 5 XAI layers from OracleSandwich → OracleSandwich returns structured explanations → Jinja2 renders Bahasa Indonesia template (IIA 2025 format) → ReportEngine returns PDF/HTML → FastAPI serves to User
  - Note: Template-based NLG for consistency and legal defensibility

  **Section 8: FastAPI Backend Architecture with Dynamic Injection**
  - Diagram type: `flowchart LR` + second diagram `sequenceDiagram` for injection flow
  - Flowchart: Show all API endpoints grouped: Config (PUT /api/config/inject), Tenders (GET /api/tenders), Risk (GET /api/risk/{id}), Explain (GET /api/explain/{id}), Network (GET /api/network), Report (GET /api/report/{id}), Heatmap (GET /api/heatmap) → each connects to relevant backend module
  - Sequence diagram for Dynamic Injection: Judge → PUT /api/config/inject with JSON body → Pydantic validates → if invalid: 422 + descriptive error → if valid: ConfigManager applies instantly (no restart, no retraining) → Audit log entry with timestamp → All modules read new config → Response 200 OK with applied config
  - Show all 7 parameters + custom_params in the validation step

  **Section 9: React Frontend with 5 Outputs**
  - Diagram type: `flowchart TB`
  - Show React SPA (Vite build) connecting to FastAPI backend
  - 5 output components: (1) Risk Score Dashboard — Plotly bar/pie charts, 4-level color coding, (2) Oracle Sandwich Explanation Panel — SHAP waterfall + DiCE table + Anchors rules + Benford chart, (3) Geographic Risk Heatmap — Folium/Leaflet, offline tile fallback, per-institution/region, (4) Cartel Network Graph — interactive vendor cluster visualization, Leiden communities highlighted, (5) Pre-Investigation Report Viewer — rendered Bahasa Indonesia report, download PDF
  - Show data flow from each output component back to relevant API endpoints

  **Section 10: Runtime Config Flow**
  - Diagram type: `sequenceDiagram`
  - Participants: YAML_File, Pydantic, ConfigManager, FeatureEng, GraphEngine, TriMethodAI, OracleSandwich, ReportGen, FastAPI
  - Flow: On startup: YAML_File loaded → Pydantic validates all 7 params + custom_params → ConfigManager singleton initialized → All modules receive config reference
  - On injection: FastAPI receives PUT → Pydantic re-validates → ConfigManager updates in-place → Audit log → All modules see new values immediately (no restart)
  - Show the 7 specific parameters flowing to their relevant modules (e.g., procurement_scope → FeatureEng filter, risk_threshold → TriMethodAI classification, anomaly_method → TriMethodAI model selection, institution_filter → data queries, year_range → data queries, output_format → ReportGen/API response, custom_params → wildcard handler)

  **Must NOT do**:
  - Do NOT include implementation code — only Mermaid diagrams and descriptive text
  - Do NOT reference external APIs, cloud services, or Streamlit
  - Do NOT use Mermaid `click` callbacks
  - Do NOT create one mega-diagram — each section gets its own diagram(s)
  - Do NOT use special characters in Mermaid node IDs (alphanumeric + underscore only)
  - Do NOT hardcode port numbers

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: This is a documentation/technical writing task — creating a detailed Markdown file with Mermaid diagrams. No code execution needed.
  - **Skills**: []
    - No skills needed — pure Markdown/Mermaid writing from reference documents
  - **Skills Evaluated but Omitted**:
    - `react:components`: Not applicable — we're documenting React architecture, not building components
    - `playwright`: Not applicable — no browser verification needed for a Markdown file
    - `frontend-ui-ux`: Not applicable — diagrams, not UI implementation

  **Parallelization**:
  - **Can Run In Parallel**: NO (single task)
  - **Parallel Group**: Wave 1 (solo)
  - **Blocks**: F1, F2
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing files to match style):
  - `C:\Hackthon\AGENTS.md` — Markdown style conventions (headings, tables, separators). Match this style for section headers and tables.
  - `C:\Hackthon\DEEP_RESEARCH_SYNTHESIS.md` — Example of detailed technical documentation in this project. Shows how to structure technical content with tables and code blocks.

  **Content References** (source of truth for ALL diagram content):
  - `C:\Users\vasco\Downloads\UPGRADE 3` (lines 62-179) — **PRIMARY SOURCE**: All 5 core mechanisms, tech stack table, dynamic injection parameters, output descriptions. Copy terms VERBATIM from this file.
  - `C:\Users\vasco\Downloads\UPGRADE 3` (lines 102-153) — 5 core mechanisms in detail: Feature Engineering (73+12), Graph Detection (Leiden), Tri-Method AI (IF+XGB+ICW), Oracle Sandwich XAI (5 layers), Auto Report (Jinja2 IIA 2025)
  - `C:\Users\vasco\Downloads\UPGRADE 3` (lines 155-168) — Technology table: exact component→technology mapping
  - `C:\Users\vasco\Downloads\UPGRADE 3` (lines 170-179) — Dynamic injection: 7 parameters + custom_params + PUT endpoint
  - `C:\Users\vasco\Downloads\UPGRADE 3` (lines 194-228) — Data sources table (4 sources with volumes) + data preparation pipeline
  - `C:\Users\vasco\Downloads\UPGRADE 3` (lines 108-123) — 12 custom forensic ML features (exact names and descriptions)
  - `C:\Hackthon\DEEP_RESEARCH_SYNTHESIS.md` (lines 130-167) — Tools & libraries with install commands and descriptions
  - `C:\Hackthon\DEEP_RESEARCH_SYNTHESIS.md` (lines 210-258) — Enhanced Oracle Sandwich architecture (4 layers with sub-components)
  - `C:\Hackthon\DEEP_RESEARCH_SYNTHESIS.md` (lines 284-310) — Benford's Law implementation details and forensic value

  **Constraint References** (rules that MUST NOT be violated):
  - `C:\Hackthon\AGENTS.md` (lines 9-51) — Disqualification rules: dynamic injection mandatory, modular architecture, no external APIs
  - `C:\Hackthon\AGENTS.md` (lines 54-72) — Execution rules: no retraining during demo, localhost only, auto-detect port
  - `C:\Hackthon\AGENTS.md` (lines 80-101) — Exact tech stack table (DO NOT substitute any component)
  - `C:\Hackthon\AGENTS.md` (lines 103-107) — 4 risk levels with exact Indonesian labels
  - `C:\Hackthon\AGENTS.md` (lines 166-176) — Performance requirements table (inference, SHAP, Anchors, DiCE, Leiden, Benford SLAs)

  **WHY Each Reference Matters**:
  - UPGRADE 3 is the CONTRACT with judges — every term must match exactly
  - AGENTS.md contains disqualification rules — diagram must not imply forbidden patterns
  - DEEP_RESEARCH_SYNTHESIS.md has enhanced technical details beyond the proposal

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: File exists with all 10 section headings
    Tool: Bash (python one-liner)
    Preconditions: Task 1 completed
    Steps:
      1. Run: python -c "from pathlib import Path; p=Path(r'C:\Hackthon\LPSE-X_Architecture.md'); assert p.exists(), 'missing file'; s=p.read_text(encoding='utf-8'); req=['System Overview','Data Ingestion Pipeline','Feature Engineering','Graph-Based Cartel Detection','Tri-Method AI Engine','Oracle Sandwich XAI','Auto Report Generation','FastAPI Backend','React Frontend','Runtime Config Flow']; miss=[h for h in req if h not in s]; assert not miss, f'missing: {miss}'; print('ALL 10 SECTIONS PRESENT')"
    Expected Result: Prints "ALL 10 SECTIONS PRESENT"
    Failure Indicators: AssertionError with list of missing headings
    Evidence: .sisyphus/evidence/task-1-headings-check.txt

  Scenario: At least 10 Mermaid blocks with diagram type diversity
    Tool: Bash (python one-liner)
    Preconditions: File exists
    Steps:
      1. Run: python -c "import re; from pathlib import Path; s=Path(r'C:\Hackthon\LPSE-X_Architecture.md').read_text(encoding='utf-8'); blocks=re.findall(r'```mermaid(.*?)```', s, re.S); n=len(blocks); assert n>=10, f'need >=10 mermaid blocks, got {n}'; types=set(); [types.add(t) for b in blocks for t in ['flowchart','sequenceDiagram','classDiagram','erDiagram','stateDiagram-v2'] if t in b]; assert len(types)>=2, f'need >=2 diagram types, got {types}'; print(f'OK: {n} blocks, types: {sorted(types)}')"
    Expected Result: OK: N blocks (N≥10), types includes at least flowchart + sequenceDiagram
    Failure Indicators: AssertionError with count or missing types
    Evidence: .sisyphus/evidence/task-1-mermaid-diversity.txt

  Scenario: All contractual terms present verbatim
    Tool: Bash (python one-liner)
    Preconditions: File exists
    Steps:
      1. Run: python -c "from pathlib import Path; s=Path(r'C:\Hackthon\LPSE-X_Architecture.md').read_text(encoding='utf-8'); must=['PUT /api/config/inject','procurement_scope','institution_filter','risk_threshold','year_range','anomaly_method','output_format','custom_params','Aman','Perlu Pantauan','Risiko Tinggi','Risiko Kritis','Cardinal','NetworkX','leidenalg','XGBoost','Isolation Forest','ONNX Runtime','SHAP','DiCE','Anchors','benford_py','Jinja2','FastAPI','React','SQLite','IIA 2025']; miss=[m for m in must if m not in s]; assert not miss, f'missing: {miss}'; print(f'ALL {len(must)} TERMS PRESENT')"
    Expected Result: Prints "ALL 27 TERMS PRESENT"
    Failure Indicators: AssertionError with list of missing terms
    Evidence: .sisyphus/evidence/task-1-contract-terms.txt

  Scenario: No disqualifying content present
    Tool: Bash (python one-liner)
    Preconditions: File exists
    Steps:
      1. Run: python -c "from pathlib import Path; s=Path(r'C:\Hackthon\LPSE-X_Architecture.md').read_text(encoding='utf-8').lower(); forbidden=['openai','anthropic','google ai','cloud server','streamlit','kafka','postgres','redis','mongodb']; found=[f for f in forbidden if f in s]; assert not found, f'FORBIDDEN terms found: {found}'; print('CLEAN — no forbidden terms')"
    Expected Result: Prints "CLEAN — no forbidden terms"
    Failure Indicators: AssertionError with list of forbidden terms found
    Evidence: .sisyphus/evidence/task-1-no-forbidden.txt
  ```

  **Evidence to Capture:**
  - [ ] task-1-headings-check.txt — 10 sections verified
  - [ ] task-1-mermaid-diversity.txt — ≥10 blocks, ≥2 types
  - [ ] task-1-contract-terms.txt — 27 contractual terms verified
  - [ ] task-1-no-forbidden.txt — zero disqualifying content

  **Commit**: YES
  - Message: `docs: add comprehensive Mermaid architecture diagram for LPSE-X`
  - Files: `LPSE-X_Architecture.md`
  - Pre-commit: Run all 4 QA scenarios above

---

## Final Verification Wave (MANDATORY — after Task 1)

> 2 review agents run in PARALLEL. Both must APPROVE. Rejection → fix → re-run.

 [x] F1. **Content Completeness Audit** — `quick`
  Read `LPSE-X_Architecture.md` end-to-end. Verify all 10 sections have substantive Mermaid diagrams (not placeholders). Check that each of the 5 core mechanisms (Feature Engineering, Graph Detection, Tri-Method AI, Oracle Sandwich, Auto Report) has its own dedicated diagram. Verify performance SLAs are annotated (<200ms, <2s, <5s, cached/async, ≥100). Verify all 12 custom features are named. Verify all 73 OCP flags are referenced via Cardinal.
  Output: `Sections [10/10] | Mechanisms [5/5] | SLAs [6/6] | Custom Features [12/12] | VERDICT: APPROVE/REJECT`

 [x] F2. **Contract Compliance Check** — `quick`
  Run all 4 QA scenarios from Task 1. Additionally: verify the 7 injectable parameters appear in Section 8 AND Section 10. Verify `PUT /api/config/inject` appears with "no restart" and "no retraining" context. Verify risk labels appear in exact order. Verify "Bahasa Indonesia" and "IIA 2025" appear in Section 7.
  Output: `QA [4/4 pass] | Injection Params [7/7 in §8+§10] | Risk Labels [correct order] | Report Format [Bahasa+IIA] | VERDICT: APPROVE/REJECT`

---

## Commit Strategy

- **Task 1**: `docs: add comprehensive Mermaid architecture diagram for LPSE-X` — `LPSE-X_Architecture.md`

---

## Success Criteria

### Verification Commands
```bash
# File exists
python -c "from pathlib import Path; assert Path(r'C:\Hackthon\LPSE-X_Architecture.md').exists(); print('EXISTS')"

# All 10 sections present
python -c "from pathlib import Path; s=Path(r'C:\Hackthon\LPSE-X_Architecture.md').read_text(encoding='utf-8'); req=['System Overview','Data Ingestion','Feature Engineering','Cartel Detection','Tri-Method','Oracle Sandwich','Report Generation','FastAPI','React Frontend','Runtime Config']; miss=[h for h in req if h not in s]; print('PASS' if not miss else f'FAIL: {miss}')"

# ≥10 Mermaid blocks
python -c "import re; from pathlib import Path; s=Path(r'C:\Hackthon\LPSE-X_Architecture.md').read_text(encoding='utf-8'); n=len(re.findall(r'```mermaid', s)); print(f'PASS: {n} blocks' if n>=10 else f'FAIL: {n} blocks')"

# All contractual terms
python -c "from pathlib import Path; s=Path(r'C:\Hackthon\LPSE-X_Architecture.md').read_text(encoding='utf-8'); must=['PUT /api/config/inject','procurement_scope','custom_params','Aman','Risiko Kritis','Cardinal','ONNX Runtime','SHAP','DiCE','Anchors','benford_py','FastAPI','React','SQLite']; miss=[m for m in must if m not in s]; print('PASS' if not miss else f'FAIL: {miss}')"
```

### Final Checklist
- [ ] File exists at `C:\Hackthon\LPSE-X_Architecture.md`
- [ ] All 10 sections with substantive Mermaid diagrams
- [ ] ≥10 Mermaid blocks using ≥2 diagram types
- [ ] All 27 contractual terms present verbatim
- [ ] Zero disqualifying content (no external APIs, no Streamlit, no cloud)
- [ ] Performance SLAs annotated in relevant diagrams
- [ ] All 12 custom forensic features named
- [ ] Dynamic injection flow shown in Sections 8 and 10
- [ ] Risk levels in correct order: Aman → Perlu Pantauan → Risiko Tinggi → Risiko Kritis
- [ ] Report generation shows Bahasa Indonesia + IIA 2025 standard
