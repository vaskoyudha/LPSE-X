# LPSE-X — Sprint Playbook (24-Hour Stage 3)

> **Find IT! 2026 at UGM — Track C: XAI — "The Explainable Oracle"**
> This playbook covers the full 24-hour execution sprint for Stage 3.
> Every step references a specific Task number (T1–T22) and the exact command to run.

---

## Team Role Assignments

| Role | Person(s) | Task Ownership |
|------|-----------|---------------|
| **Lead ML Engineer** | 1 person | T5, T6, T7, T8, T9, T10, T11 — data pipeline + feature engineering + model training + ONNX export |
| **XAI Specialist** | 1 person | T12, T13, T15 — Oracle Sandwich XAI + DiCE + report generation |
| **Backend Engineer** | 1 person | T4, T14 — runtime config + FastAPI endpoints + dynamic injection |
| **Frontend Engineer** | 1 person | T15, T16, T17, T18, T19 — React dashboard + Plotly charts + Folium maps |
| **DevOps / QA** | 1 person (optional 5th) | T20, T21, T22, T23 — offline bundle + testing + demo rehearsal |

---

## Phase 0 — Setup (0–2h)

**Goal**: Green baseline confirmed, all dependencies installed.

### Steps

1. **Clone repo and verify structure** (T1)
   ```bash
   git clone <repo-url> lpse-x && cd lpse-x
   ls backend/ frontend/ config/ tests/ docs/ models/ data/
   # Expected: all directories present
   ```

2. **Install Python dependencies** (T1)
   ```bash
   make install
   # OR: python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"
   # Expected: pip install completes, no errors
   .venv/Scripts/python --version
   # Expected: Python 3.11.x (NOT 3.14)
   ```

3. **Install frontend dependencies** (T1)
   ```bash
   make install-frontend
   # OR: cd frontend && npm install
   # Expected: node_modules/ created
   ```

4. **Run baseline tests** (T21)
   ```bash
   make test
   # OR: .venv/Scripts/python -m pytest tests/ -q
   # Expected: 449 passed, 0 failed
   ```

5. **Verify SQLite database** (T3)
   ```bash
   ls data/lpse_x.db
   # Expected: file exists
   .venv/Scripts/python -c "import sqlite3; conn=sqlite3.connect('data/lpse_x.db'); print(conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall())"
   # Expected: list of tables including tenders, features, communities
   ```

6. **Verify ONNX model** (T11)
   ```bash
   ls models/ensemble.onnx 2>/dev/null || echo "ONNX not yet generated — will be created in Phase 1"
   # Note: if missing, run T11 ONNX export (see Phase 1)
   ```

7. **Download mini-dataset** (T3, T5) — if full dataset not pre-cached
   ```bash
   .venv/Scripts/python -m backend.data.ingestion --limit 10000
   # Expected: ~10k tenders loaded into data/lpse_x.db
   # Fallback: use pre-cached SQLite dataset already in data/
   ```

**Phase 0 Exit Criteria**: `pytest tests/ -q` → 449 passed, SQLite DB exists.

---

## Phase 1 — Core Features (2–8h)

**Goal**: Full data pipeline + feature engineering + trained models + ONNX export working.

### T5/T6 — Data Pipeline + Feature Engineering (2–4h)

1. **Ingest LKPP XLSX data** (T5)
   ```bash
   .venv/Scripts/python -m backend.data.lkpp_loader
   # Expected: CSV/XLSX loaded, records inserted into tenders table
   ```

2. **Run feature pipeline** (T6)
   ```bash
   .venv/Scripts/python -c "
   from backend.features.pipeline import run_feature_pipeline
   result = run_feature_pipeline()
   print(f'Features computed: {result}')
   "
   # Expected: cardinal_flags + custom_features computed for all tenders
   ```

3. **Verify Cardinal 73 OCP flags** (T6)
   ```bash
   .venv/Scripts/python -c "
   from backend.features.cardinal_flags import compute_cardinal_flags
   flags = compute_cardinal_flags({'n_bidders': 1, 'price_ratio': 0.99})
   print(f'Cardinal flags: {len(flags)} features computed')
   "
   # Expected: 73 features returned
   ```

4. **Verify custom forensic features** (T6)
   ```bash
   .venv/Scripts/python -m pytest tests/test_features.py -q
   # Expected: all feature tests pass
   ```

### T7 — Graph Detection (4–5h)

1. **Build vendor-tender bipartite graph** (T7)
   ```bash
   .venv/Scripts/python -c "
   from backend.graph.builder import build_bipartite_graph
   import aiosqlite, asyncio
   async def run():
       async with aiosqlite.connect('data/lpse_x.db') as db:
           G = await build_bipartite_graph(db)
           print(f'Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges')
   asyncio.run(run())
   "
   ```

2. **Run Leiden community detection** (T7)
   ```bash
   .venv/Scripts/python -c "
   from backend.graph.leiden import detect_communities
   import sqlite3
   conn = sqlite3.connect('data/lpse_x.db')
   result = detect_communities(conn=conn)
   print(f'Communities detected: {result}')
   "
   # Expected: communities saved to SQLite communities table
   ```

3. **Verify graph tests** (T7)
   ```bash
   .venv/Scripts/python -m pytest tests/test_graph.py -q
   ```

### T8/T9 — Tri-Method AI + Benford (5–7h)

1. **Train Isolation Forest** (T8)
   ```bash
   .venv/Scripts/python -c "
   from backend.ml.isolation_forest import train_isolation_forest
   model = train_isolation_forest()
   print(f'IsolationForest trained, saved to models/iforest.pkl')
   "
   ```

2. **Train XGBoost** (T8)
   ```bash
   .venv/Scripts/python -c "
   from backend.ml.xgboost_model import train_xgboost
   model = train_xgboost()
   print(f'XGBoost trained, saved to models/xgboost.ubj')
   "
   ```

3. **Full training pipeline** (T8)
   ```bash
   .venv/Scripts/python -m backend.ml.train
   # Expected: JSON summary of training results printed
   ```

4. **Verify Benford analysis** (T9)
   ```bash
   .venv/Scripts/python -m pytest tests/test_benford.py -q
   # Expected: benford tests pass
   ```

### T10/T11 — XAI Pipeline + ONNX Export (7–8h)

1. **Export ONNX model** (T11)
   ```bash
   .venv/Scripts/python -c "
   from backend.ml.onnx_export import export_ensemble_to_onnx
   path = export_ensemble_to_onnx()
   print(f'ONNX exported to: {path}')
   "
   # Expected: models/ensemble.onnx created
   ```

2. **Verify ONNX parity** (T11)
   ```bash
   .venv/Scripts/python -m pytest tests/test_onnx.py -q
   # Expected: native vs ONNX predictions allclose (tolerance 1e-5)
   ```

3. **Test XAI pipeline** (T10)
   ```bash
   .venv/Scripts/python -m pytest tests/test_xai.py -q
   ```

**Phase 1 Exit Criteria**: `models/iforest.pkl`, `models/xgboost.ubj` exist. `pytest tests/test_features.py tests/test_graph.py tests/test_models.py tests/test_benford.py tests/test_xai.py tests/test_onnx.py -q` → all pass.

---

## Phase 2 — Integration (8–16h)

**Goal**: Full API working end-to-end. Dynamic injection verified. Frontend connected.

### T4 — Runtime Config (8–9h)

1. **Verify runtime config loads** (T4)
   ```bash
   .venv/Scripts/python -c "
   from backend.config.runtime import get_config
   cfg = get_config()
   print(f'Config loaded: risk_threshold={cfg.risk_threshold}')
   "
   # Expected: config loaded from config/runtime_config.yaml
   ```

2. **Test injection endpoint** (T4, T22)
   ```bash
   # Start server first (see below), then:
   curl -X PUT http://localhost:8000/api/config/inject \
     -H 'Content-Type: application/json' \
     -d '{"risk_threshold": 0.5, "custom_params": {"judge_key": "judge_value"}}'
   # Expected: 200 OK with old_values + new_values
   ```

### T14 — FastAPI Endpoints (9–12h)

1. **Start server** (T14, T20)
   ```bash
   .venv/Scripts/python -m backend.main
   # Expected: "LPSE-X starting on http://localhost:8000"
   # Note: port auto-detected, no hardcoding
   ```

2. **Verify all 7 routes** (T14)
   ```bash
   curl http://localhost:8000/api/health
   curl http://localhost:8000/api/config
   curl -X PUT http://localhost:8000/api/config/inject \
     -H 'Content-Type: application/json' \
     -d '{"risk_threshold": 0.4}'
   curl -X POST http://localhost:8000/api/predict \
     -H 'Content-Type: application/json' \
     -d '{"tender_id": "TEST-001", "features": {"n_bidders": 2, "price_ratio": 0.95}}'
   curl -X POST http://localhost:8000/api/xai/TEST-001 \
     -H 'Content-Type: application/json' \
     -d '{"features": {"n_bidders": 2, "price_ratio": 0.95}}'
   curl http://localhost:8000/api/graph
   curl http://localhost:8000/api/reports/TEST-001
   ```

3. **Run API tests** (T14)
   ```bash
   .venv/Scripts/python -m pytest tests/test_api.py -q
   # Expected: 40 passed
   ```

### T12/T13 — DiCE + Reports (12–15h)

1. **Test DiCE counterfactuals** (T12)
   ```bash
   .venv/Scripts/python -m pytest tests/test_dice_explainer.py -q
   ```

2. **Trigger DiCE precompute** (T12)
   ```bash
   curl -X POST "http://localhost:8000/api/xai/dice/precompute?n_cfs=3" \
     -H 'Content-Type: application/json' \
     -d '{"tender_id": "TEST-001", "features": {"n_bidders": 1, "price_ratio": 0.99}}'
   # Expected: {"status": "accepted", ...}
   ```

3. **Test report generation** (T13)
   ```bash
   .venv/Scripts/python -m pytest tests/test_reports.py -q
   curl http://localhost:8000/api/reports/TEST-001
   # Expected: IIA 2025 format report in Bahasa Indonesia
   ```

### T15 — Wire Frontend to Backend (15–16h)

1. **Build frontend** (T15)
   ```bash
   make build-frontend
   # OR: cd frontend && npm run build
   # Expected: frontend/dist/ created
   ```

2. **Verify SPA served** (T15)
   ```bash
   curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
   # Expected: 200
   ```

**Phase 2 Exit Criteria**: All 7 API routes return 200. Frontend served. Dynamic injection works.

---

## Phase 3 — Polish & UI (16–20h)

**Goal**: Dashboard polished, maps working, report viewer functional, offline verified.

### T16/T17 — Dashboard + Visualizations (16–18h)

1. **Verify dashboard page loads** (T16)
   ```bash
   # Open http://localhost:8000/ in browser
   # Expected: Dashboard with risk score distribution chart
   ```

2. **Verify Plotly charts render** (T17)
   ```bash
   # Navigate to CartelGraph page
   # Expected: vendor network graph displayed (if graph data present)
   ```

### T18/T19 — Map + Reports Viewer (18–19h)

1. **Verify RiskMap page** (T18)
   ```bash
   # Navigate to /risk-map
   # Expected: Folium/Leaflet map with regional risk choropleth
   ```

2. **Verify Reports page** (T19)
   ```bash
   # Navigate to /reports
   # Expected: IIA 2025 report rendered with all 6 sections
   ```

### T20 — Offline Bundle Verification (19–20h)

1. **Kill Wi-Fi / disconnect network**

2. **Verify app still runs** (T20)
   ```bash
   .venv/Scripts/python -m backend.main
   # Expected: starts, no network errors
   curl http://localhost:8000/api/health
   # Expected: 200 OK
   ```

3. **Run offline enforcement tests** (T21)
   ```bash
   .venv/Scripts/python -m pytest tests/test_offline_no_network.py -q
   # Expected: 7 passed — zero outbound network calls
   ```

4. **Verify start_lpse_x.py launcher** (T20)
   ```bash
   .venv/Scripts/python start_lpse_x.py
   # Expected: server starts with auto-port detection
   ```

**Phase 3 Exit Criteria**: Frontend loads in browser, offline mode works, no external calls.

---

## Phase 4 — Demo Prep (20–24h)

**Goal**: All tests green, demo script rehearsed, injection stress tested.

### T21 — Integration Tests (20–21h)

1. **Run full integration suite** (T21)
   ```bash
   .venv/Scripts/python -m pytest tests/test_integration.py -v
   # Expected: 36 passed
   ```

2. **Run offline tests** (T21)
   ```bash
   .venv/Scripts/python -m pytest tests/test_offline_no_network.py -v
   # Expected: 7 passed
   ```

### T22 — Injection Stress Tests (21–22h)

1. **Run injection stress suite** (T22)
   ```bash
   .venv/Scripts/python -m pytest tests/test_injection_stress.py -v
   # Expected: 60 passed
   ```

2. **Manual injection demo rehearsal** (T22)
   ```bash
   # Rehearse the live demo injection sequence:
   curl -X PUT http://localhost:8000/api/config/inject \
     -H 'Content-Type: application/json' \
     -d '{"risk_threshold": 0.3}'
   curl http://localhost:8000/api/config  # verify change applied
   curl -X PUT http://localhost:8000/api/config/inject \
     -H 'Content-Type: application/json' \
     -d '{"custom_params": {"juri_inject": "nilai_dadakan", "skenario": 42}}'
   # Expected: system accepts unknown params, no 422 error
   ```

### Full Test Suite (22–23h)

```bash
.venv/Scripts/python -m pytest tests/ -q
# Expected: 449 passed, 0 failed
# If any fail: fix before demo
```

### Demo Rehearsal (23–24h)

Follow `docs/DEMO_SCRIPT.md` minute-by-minute. Each presenter rehearses:
1. Opening stats (Rp 279.9T, 364 kasus ICW, 34/100 TI score)
2. Live data flow walkthrough
3. Feature engineering + Cardinal flags
4. Tri-Method AI prediction
5. Oracle Sandwich XAI — 5 layers
6. **CRITICAL**: Live injection demo (`PUT /api/config/inject`)
7. IIA 2025 report display
8. Impact closing

---

## Emergency Protocols

| Scenario | Detection | Fallback |
|----------|-----------|---------|
| `cardinal` package fails to install | `pip install cardinal` fails | Use `backend/features/cardinal_flags.py` manual computation — T6 includes this fallback |
| ONNX export fails | `models/ensemble.onnx` missing | Set `USE_ONNX=false` in config; serve raw sklearn/xgboost directly (slower but functional) |
| `leidenalg` fails (C++ compilation) | `import leidenalg` raises ImportError | Use `igraph.community_fastgreedy()` as fallback in `backend/graph/leiden.py` |
| opentender.net API is down | `backend/data/ingestion.py` times out | Use pre-cached SQLite dataset in `data/lpse_x.db` — system is fully offline-capable |
| DiCE is too slow (>10s) | `/api/xai/dice/precompute` timeout | Disable DiCE layer via `custom_params: {"disable_dice": true}` — 4/5 XAI layers remain |
| Frontend build fails | `npm run build` error | Serve React dev server: `cd frontend && npm start` (port 3000), CORS already configured |
| Port 8000 in use | `find_free_port()` logs next port | Note the new port (printed on startup), use it for all curl commands |
| Database locked | SQLite "database is locked" error | `rm data/test.db` (test artifact), restart server |

---

## Pre-Built Script References

All commands available via `Makefile`:

```bash
make install          # Python venv + pip install -e ".[dev]"
make install-frontend # cd frontend && npm install
make start            # uvicorn backend.main:app --reload
make test             # pytest tests/ -q
make build-frontend   # cd frontend && npm run build
```

Single-command launch (offline bundle):
```bash
.venv/Scripts/python start_lpse_x.py
```

---

## Scoring Criteria Checklist

Before stepping on stage, verify:

| Stage 3 Criterion | Verified By | Status |
|-------------------|-------------|--------|
| Live Inference <200ms | `pytest tests/test_onnx.py -q` | [ ] |
| Dynamic Injection works | `curl PUT /api/config/inject` returns 200 | [ ] |
| custom_params wildcard accepted | Inject `{"custom_params": {"x": 1}}` → 200 | [ ] |
| XAI layers produce output | `curl POST /api/xai/{id}` → layers_ok >= 1 | [ ] |
| Offline mode works | Disconnect Wi-Fi, curl /api/health → 200 | [ ] |
| 449 tests pass | `pytest tests/ -q` → 449 passed | [ ] |
| Report in Bahasa Indonesia | `curl /api/reports/{id}` → Bahasa text | [ ] |
| Frontend serves | `curl / → 200` | [ ] |
