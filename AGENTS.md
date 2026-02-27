# LPSE-X Project Rules

## Competition: Find IT! 2026 — Universitas Gadjah Mada
## Track: C — "The Explainable Oracle" (Predictive Analytics)
## Product: LPSE-X (Explainable AI for Procurement Fraud Detection)

---

## DISQUALIFICATION RULES (ZERO TOLERANCE)

These rules result in **immediate disqualification** if violated. Every agent MUST internalize these.

### 1. Dynamic Injection is MANDATORY

> "Aplikasi Anda WAJIB mampu menerima dan memproses variabel/logika dadakan ini agar sistem dianggap valid."
> "Kegagalan dalam mengimplementasikan Dynamic Injection ini akan dianggap sebagai indikasi ketidaksiapan sistem atau kecurangan, yang dapat berdampak pada diskualifikasi."

**What this means:**
- ALL operational parameters MUST be configurable via `runtime_config.yaml`
- A `PUT /api/config/inject` endpoint MUST exist that changes behavior WITHOUT server restart and WITHOUT model retraining
- Pydantic validates injected params — invalid params rejected with descriptive error, valid params applied instantly
- HARDCODED parameters = DISQUALIFICATION

**The 7 injectable parameters (ALL mandatory):**

| Parameter | What It Controls |
|-----------|-----------------|
| `procurement_scope` | Procurement category (konstruksi / barang / jasa konsultansi / jasa lainnya) |
| `institution_filter` | Specific K/L/Pemda institutions |
| `risk_threshold` | Risk score threshold (0.0–1.0) |
| `year_range` | Analysis year range |
| `anomaly_method` | Detection method (Isolation Forest / XGBoost / ensemble) |
| `output_format` | Output format (dashboard / API JSON / audit report) |
| `custom_params` | **Wildcard dictionary** for unexpected judge-injected parameters |

`custom_params` is critical — judges WILL inject unknown parameters at competition time.

### 2. Architecture Must Be Flexible and Modular

> "Peserta dituntut untuk membuat arsitektur aplikasi yang fleksibel dan modular."

- NO monolithic code — separate modules for data, features, models, XAI, API, frontend
- Each component must be independently testable and replaceable

### 3. No External API Calls (Track B Constraint Applied)

- ZERO calls to external AI APIs (OpenAI, Google AI, Anthropic, etc.) — fully sovereign
- ZERO cloud server dependencies — localhost ONLY
- After initial data ingestion, ALL queries served from local SQLite
- The application runs 100% on the participant's laptop during demo

---

## EXECUTION RULES (24-HOUR HACKATHON)

### 4. No Model Retraining During Stage 3 (Demo Sprint)

- Models MUST be production-ready BEFORE the 24-hour sprint
- Stage 3 is inference-only — load pre-trained ONNX models, no training code runs
- ONNX Runtime for inference: <200ms per prediction on standard CPU

### 5. Localhost Only — No Cloud

- No cloud server is provided by organizers
- Demo runs entirely on participant's laptop
- Auto-detect free port (no hardcoded port numbers)
- All file paths relative to AppDir (no temp/user-profile paths)

### 6. Team Size: 4-5 People

- Maximize parallel task execution across team members
- Plan is structured in waves to enable this

---

## TECHNICAL COMMITMENTS (FROM PROPOSAL — THESE ARE CONTRACTUAL)

Every item below was PROMISED in the accepted proposal. Failure to deliver = broken contract with judges.

### 7. Five Core Mechanisms (ALL required)

1. **Feature Engineering** — 73 OCP red flags (Cardinal library, OCDS format) + 12 custom forensic ML features
2. **Graph-Based Cartel Detection** — NetworkX bipartite graph + Leiden community detection (`leidenalg`)
3. **Tri-Method AI** — Isolation Forest (unsupervised) + XGBoost (supervised) + ICW weak labels (weakly supervised) + Disagreement Protocol
4. **Oracle Sandwich XAI (5 layers)** — SHAP (Global) + DiCE (Local) + Anchors (Rules) + Leiden (Graph) + Benford (Statistical)
5. **Auto Pre-Investigation Report** — Jinja2 NLG, IIA 2025 standards, Bahasa Indonesia

### 8. Exact Tech Stack (DO NOT substitute)

| Component | Technology | Non-negotiable |
|-----------|-----------|---------------|
| ML Models | XGBoost + Isolation Forest | YES |
| Graph Analysis | NetworkX + Leiden (`leidenalg`) | YES |
| Red Flags | Cardinal (OCP, OCDS) | YES |
| Explainability | SHAP + DiCE + Anchors (`alibi`) | YES |
| Statistical Forensics | `benford_py` | YES |
| Inference | ONNX Runtime | YES |
| Backend | Python 3.11, FastAPI + Uvicorn | YES |
| Frontend | React + Plotly + Folium | YES (NOT Streamlit) |
| Database | SQLite | YES |
| Config | YAML + Pydantic | YES |

### 9. Four Risk Levels (exact labels, exact order)

```
Aman → Perlu Pantauan → Risiko Tinggi → Risiko Kritis
```

### 10. Five Required Outputs

1. Risk score per tender (4-level classification)
2. Transparent forensic explanation (5-layer Oracle Sandwich)
3. Interactive risk heatmap (geographic, per institution/region)
4. Cartel network graph (vendor cluster visualization)
5. Auto pre-investigation report (Bahasa Indonesia, IIA 2025)

### 11. MVP Scope

- Sector: Construction (Pekerjaan Konstruksi)
- Institutions: 5 LPSE (Kemenkeu, Kemen-PUPR, Pemprov DKI Jakarta, Kemenkes, Pemprov Sumbar)
- Period: 2022–2024

### 12. Data Sources

| Source | Method | Volume |
|--------|--------|--------|
| opentender.net (ICW) | REST API + bulk export | 1,106,096 tenders |
| pyproc (LPSE real-time) | Python wrapper, PyPI | Hundreds of thousands/year |
| LKPP Open Data (SiRUP) | CKAN API — XLSX/JSON | 26 datasets |
| Corruption cases | KPK + MA + ICW aggregation | 200+ curated cases |

---

## CODING GUARDRAILS (FOR ALL AGENTS)

### NEVER do these:

- ❌ `as any`, `@ts-ignore`, `@ts-expect-error` — fix the types properly
- ❌ Empty catch blocks `catch(e) {}` — always handle errors
- ❌ `console.log` in production — use structured logging
- ❌ Hardcoded thresholds, ports, file paths, or parameters
- ❌ ORM usage — use raw SQL + aiosqlite for speed
- ❌ Floating dependency versions — pin ALL versions exactly
- ❌ Store raw NPWP values — hash with SHA-256 (store hash + last 4 digits only)
- ❌ Block main inference with slow XAI (DiCE must be cached/async)
- ❌ Run Benford analysis without applicability pre-check (need ≥100 records)
- ❌ Use random seeds without logging them — all stochastic processes must be reproducible
- ❌ Compute SHAP on unstandardized categorical encodings (Hwang et al. 2025 sensitivity finding)
- ❌ Use online map tiles without offline fallback
- ❌ Delete failing tests to make them pass

### ALWAYS do these:

- ✅ Read ALL parameters from `runtime_config.yaml` — never hardcode
- ✅ Pin every dependency version in pyproject.toml and package.json
- ✅ Run `lsp_diagnostics` on changed files before marking task complete
- ✅ Include QA scenarios with every task
- ✅ Log every dynamic injection with timestamp for audit trail
- ✅ Validate all data against OCDS schema before storage
- ✅ Use Pydantic `model_json_schema()` for OpenAPI generation
- ✅ Keep modules independently testable
- ✅ Use temporal split for train/validation/test (2018-2021 / 2022 / 2023-2024)

---

## PERFORMANCE REQUIREMENTS

| Metric | Target | Source |
|--------|--------|--------|
| Inference latency | <200ms per prediction | ONNX Runtime on CPU |
| SHAP explanation | <2s per prediction | XAI SLA |
| Anchors explanation | <5s per prediction | XAI SLA |
| DiCE counterfactuals | Cached/async, not blocking | Metis gap analysis |
| Leiden detection | <3s per community run | XAI SLA |
| Benford analysis | <1s per dataset | XAI SLA |
| Target F1-Score | 0.85–0.92 | Westerski et al. 2021 benchmark |

---

## KEY REFERENCE FILES

| File | What It Contains |
|------|-----------------|
| `C:\Users\vasco\Downloads\UPGRADE 3` | FINAL proposal (340 lines) — the CONTRACT with judges |
| `C:\Hackthon\DEEP_RESEARCH_SYNTHESIS.md` | Research synthesis (474 lines) — academic backing |
| `C:\Hackthon\lkpp_*.xlsx` | 4 downloaded LKPP datasets |
| `C:\Hackthon\test_pyproc_local.py` | pyproc verification script |

---

*Last updated: 2026-02-27. These rules are non-negotiable for the entire project lifecycle.*