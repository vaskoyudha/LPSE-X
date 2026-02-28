# LPSE-X Architecture — Technical Reference

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    LPSE-X Platform                          │
│                                                             │
│  ┌──────────────┐    ┌──────────────────────────────────┐   │
│  │   React SPA  │    │         FastAPI Backend           │   │
│  │  (TypeScript)│◄──►│   /api/predict   /api/xai        │   │
│  │  Plotly.js   │    │   /api/graph     /api/reports     │   │
│  │  D3 Graph    │    │   /api/config    /api/health      │   │
│  └──────────────┘    └──────────────┬───────────────────┘   │
│                                     │                       │
│  ┌──────────────────────────────────▼───────────────────┐   │
│  │                  Core Engine                          │   │
│  │                                                       │   │
│  │  ┌─────────────┐  ┌────────────┐  ┌───────────────┐  │   │
│  │  │  Tri-Method │  │   Oracle   │  │   Report      │  │   │
│  │  │  AI Engine  │  │  Sandwich  │  │  Generator    │  │   │
│  │  │  IF+XGB+ICW │  │  XAI (5L) │  │  IIA 2025     │  │   │
│  │  └──────┬──────┘  └─────┬──────┘  └───────────────┘  │   │
│  │         │               │                             │   │
│  │  ┌──────▼──────────────▼──────────────────────────┐  │   │
│  │  │           Feature Pipeline (85 features)        │  │   │
│  │  │   73 Cardinal OCP Red Flags + 12 Custom ML     │  │   │
│  │  └──────────────────────┬─────────────────────────┘  │   │
│  │                         │                             │   │
│  │  ┌──────────────────────▼─────────────────────────┐  │   │
│  │  │        SQLite Database (lpse_x.db)              │  │   │
│  │  │  tenders | features | predictions | reports     │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Runtime Config (runtime_config.yaml)          │   │
│  │   risk_threshold | procurement_scope | year_range    │   │
│  │   institution_filter | anomaly_method | custom_params│   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Tri-Method AI Engine (`backend/ml/`)

**Purpose**: 4-level risk classification with ensemble disagreement protocol

| Method | Algorithm | Role |
|--------|-----------|------|
| Isolation Forest | Unsupervised anomaly detection | Novelty signal |
| XGBoost (ONNX) | Gradient boosting classifier | Primary risk scorer |
| ICW Weak Labels | `total_score` from opentender.net | External validation |

**Disagreement Protocol**:
- If all 3 agree → high confidence
- If 2/3 agree → moderate confidence, flag for review
- If all disagree → `manual_review_priority=True`

**Risk Levels**:
- `Aman` (0.0–0.4)
- `Perlu Pantauan` (0.4–0.6)  
- `Risiko Tinggi` (0.6–0.85)
- `Risiko Kritis` (0.85–1.0)

**ONNX Export**: All models exported to ONNX for <200ms inference on CPU without retraining.

---

### 2. Oracle Sandwich XAI (`backend/xai/`)

**Purpose**: 5-layer explainability stack — no black box

| Layer | Library | Output | Latency SLA |
|-------|---------|--------|-------------|
| **SHAP** | shap (TreeExplainer) | Feature importance + waterfall | <2s |
| **DiCE** | dice-ml | Counterfactual "what-if" scenarios | cached/async |
| **Anchors** | alibi | IF-THEN rules with precision/coverage | <5s |
| **Leiden Graph** | leidenalg | Community membership + cartel score | <1s |
| **Benford's Law** | benford_py | Digit distribution chi-sq test | <0.5s |

**Fault Tolerance**: Every layer runs independently. If one fails, others continue. `layers_ok` + `layers_failed` counters in response.

**Benford Applicability Gate**: Returns `"not_applicable"` if bid amounts don't span orders of magnitude — prevents misleading results on uniform data.

---

### 3. Graph Cartel Detection (`backend/graph/`)

**Purpose**: Network-based bid-rigging detection

**Algorithm**: Leiden community detection (Traag et al., 2019)
- Superior to Louvain: guaranteed optimal modularity
- Fixed seed=42 for reproducibility
- Version logged in every run

**Graph Construction**:
```
Bipartite: Vendors ←→ Tenders (edge = participated)
Projection: Vendors ←→ Vendors (edge = shared tender participation)
```

**Cartel Suspicion Score** (0–1):
- `intra_bid_frequency` × 0.3
- `win_rotation` × 0.3  
- `price_similarity` × 0.2
- `geographic_overlap` × 0.2

---

### 4. Runtime Config System (`backend/config/`)

**Purpose**: Zero-restart parameter injection — competition-critical requirement

**Mechanism**:
1. `runtime_config.yaml` → loaded at startup via Pydantic
2. `GET /api/config` → returns current active config
3. `PUT /api/config/inject` → validates via Pydantic, applies instantly
4. Thread-safe singleton: `_config_lock` (RLock) prevents race conditions

**Deadlock Prevention**: `get_config()` is called BEFORE acquiring lock in `inject_config()` — ensures `_config` is initialized before lock acquisition.

**Injectable Parameters**:
```yaml
risk_threshold: 0.7           # float [0.0, 1.0]
procurement_scope: konstruksi  # enum
institution_filter: [...]      # list[str]
year_range: [2022, 2024]       # tuple[int, int]
anomaly_method: ensemble       # enum
output_format: dashboard       # enum
custom_params: {}              # dict[str, Any] — wildcard
```

---

### 5. Data Pipeline (`backend/data/`)

**Sources**:
- opentender.net (1.1M tenders, OCDS format)
- LKPP XLSX (4 files, pre-downloaded to `C:\Hackthon\`)
- pyproc (real-time LPSE, with offline fallback)

**Privacy**: NPWP hashed via SHA-256 — only hash + last 4 digits stored.

**Schema**: Raw SQL + aiosqlite (no ORM). Tables:
- `tenders` — raw OCDS data (55+ fields)
- `features` — 85-column feature matrix
- `predictions` — model outputs with timestamps
- `communities` — Leiden cartel detection results
- `reports` — generated IIA-format reports

---

### 6. Feature Engineering (`backend/features/`)

**73 Cardinal Red Flags** (OCP library, Dec 2024):
- Planning phase (1–18): Sole-source justification, insufficient notice periods
- Tender phase (19–41): Restrictive requirements, short bid windows
- Award phase (42–58): Winner pre-announcement, evaluation score anomalies
- Implementation phase (59–73): Contract modification patterns

**12 Custom Forensic ML Features**:

| Feature | Formula | Detection |
|---------|---------|-----------|
| `bid_clustering_score` | std(bids) / HPS | Low spread = suspicious |
| `vendor_win_concentration` | vendor_wins / total_tenders | Market domination |
| `hps_deviation_ratio` | (contract - HPS) / HPS | HPS leakage |
| `participant_count_anomaly` | z-score vs category mean | Artificially low bidders |
| `geographic_concentration` | distinct_regions / bidders | Regional cartel |
| `repeat_pairing_index` | co-bid frequency SQL join | Collusion pairs |
| `temporal_submission_pattern` | time variance of submissions | Coordinated timing |
| `historical_win_rate` | wins / participations | Track record |
| `phantom_bidder_score` | zero-win participations rate | Cover bidding |
| `benford_anomaly` | chi-sq p-value | Amount manipulation |
| `interlocking_directorates` | NPWP hash prefix overlap | Shell company detection |
| `bid_rotation_pattern` | sequential wins in community | Cartel rotation |

---

## API Reference

### Inference
```
POST /api/predict
Body: {tender_id, features: dict, icw_raw_score?, tender_metadata?}
Returns: {status, tender_id, risk_level, final_score, individual_scores, disagreement_flag, ...}
```

### XAI
```
POST /api/xai/{tender_id}
Body: {features: dict, amount_values?: list[float]}
Returns: {status, tender_id, data: {shap, anchors, leiden, benford, dice, layers_ok, layers_failed}}

POST /api/xai/dice/precompute
GET  /api/xai/dice/status/{tender_id}
```

### Config (Dynamic Injection)
```
GET  /api/config          → current config
PUT  /api/config/inject   → inject parameters (partial update)
GET  /api/config/log      → injection audit trail
```

### Graph
```
GET /api/graph                    → all communities
GET /api/graph/vendor/{vendor_id} → vendor community membership
```

### Reports
```
GET  /api/reports/{tender_id}     → auto-generate report
POST /api/reports/{tender_id}     → generate with oracle result
Body: {oracle_result?, tender_data?}
```

### Health
```
GET /api/health → {status, version, uptime, models, config_hash, config}
```

---

## Security & Privacy

- **NPWP Anonymization**: SHA-256 hash only, no raw NPWP stored
- **No External Calls**: Zero outbound network after initial data ingestion
- **Audit Trail**: Every config injection logged with timestamp
- **Seed Logging**: All stochastic operations log seed=42 + library versions
- **No Raw Credentials**: No API keys, no cloud tokens required

---

## Offline Packaging

The entire platform ships as a portable folder:
```
lpse-x/
  .venv/              Python virtual environment
  frontend/dist/      Built React SPA (served by FastAPI)
  models/             ONNX-exported ML models
  data/lpse_x.db      SQLite database (pre-loaded)
  config/             runtime_config.yaml
  backend/main.py     Entry point (auto port-detection)
```

**Start command**: `python -m backend.main`  
**Port**: Auto-detected (avoids conflicts)  
**Offline**: Works with Wi-Fi disabled  
**No install needed**: Dependencies bundled in `.venv/`
