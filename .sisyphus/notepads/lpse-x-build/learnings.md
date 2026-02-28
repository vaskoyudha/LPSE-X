## [2026-02-28] Task 1: Scaffolding Complete
- Python venv: lpse-x/.venv
- Python version: 3.11.9
- Node version: v25.2.1
- Core Python deps status: OK
- leidenalg/igraph status: OK (Communities: 2)
- alibi status: Installed (no-deps due to numpy<2 constraint)
- dice-ml status: Installed (no-deps due to pandas<2 constraint)
- benford-py import name: import benford (confirmed)
- React build: OK
- frontend/dist/index.html exists: YES


## [2026-02-28] Task 1: Full Dependency Resolution (Orchestrator verification)
 alibi requires spacy, dill, scikit-image — all installed successfully
 dice-ml requires raiutils, jsonschema — installed successfully (has pandas<2 warning but works)
 alibi has numpy<2 conflict warning but imports and runs fine
 benford import name: `import benford` (confirmed OK)
 cardinal: NOT on PyPI as cardinal — not installed — Task 6 must implement red flags manually OR clone from GitHub
 All 16 core packages verified: fastapi 0.115.6, xgboost 2.1.3, shap 0.46.0, networkx 3.4.2, onnxruntime 1.20.1, pandas 2.2.3, numpy 2.2.1, leidenalg 0.10.2, igraph 0.11.8, folium 0.18.0, plotly 5.24.1, jinja2 3.1.5, alibi 0.9.6, benford OK, dice_ml OK, skl2onnx 1.17.0
 leidenalg Windows test: Communities=2 (Petersen graph), no DLL errors — CONFIRMED WORKING
 React frontend: dist/ built, index.html exists — CONFIRMED WORKING
 Venv uses Python 3.11.9 (not system 3.14) — all .pyc compiled for cp311
 pyproject.toml has all pinned versions — no floating ranges
## [2026-02-28] Task 2: Pydantic Models & TypeScript Types Complete

### What was created:

1. **backend/schemas/models.py** (12 KB, 315 lines)
   - 4 Enums: RiskLevel, ProcurementScope, AnomalyMethod, OutputFormat
   - 8 Data Models: TenderRecord, RiskPrediction, XAIExplanation, GraphCommunity, RuntimeConfig, InvestigationReport, InjectionRequest, InjectionResponse
   - All 7 injectable parameters present in RuntimeConfig with proper validation
   - RiskLevel enum uses EXACT competition values: "Aman", "Perlu Pantauan", "Risiko Tinggi", "Risiko Kritis"

2. **backend/schemas/__init__.py** (593 bytes)
   - Barrel export of all 12 models/types for clean imports

3. **frontend/src/types/models.ts** (4.1 KB)
   - TypeScript mirrors of all Pydantic models
   - String literal unions for enums
   - Exact schema correspondence with Python side

4. **frontend/src/types/api.ts** (1.8 KB)
   - Standard API response wrappers: ApiResponse<T>, ApiError, PaginatedResponse<T>
   - Domain-specific responses: TenderWithPrediction, RiskSummary, CartelDetectionResponse, etc.

5. **frontend/src/types/index.ts** (updated)
   - Central re-export point using `export type` for isolatedModules compatibility

### Key Features:

- **Competition Compliance**: All 7 injectable parameters hardcoded in RuntimeConfig with correct names
- **Risk Threshold Validation**: Enforced 0.0-1.0 range (tested rejection of 2.0)
- **Custom Params Wildcard**: dict[str, Any] for unknown judge-injected params
- **Oracle Sandwich XAI**: All 5 layers (SHAP, DiCE, Anchors, Leiden, Benford) modeled as optional fields
- **Pydantic v2 Validation**: Automatic validation via Field(ge=..., le=...)
- **TypeScript Safety**: No `Any` usage; proper generics and `unknown` types

### QA Results (All Passed):

1. Pydantic instantiation + validation: PASS
2. Runtime config custom_params wildcard: PASS
3. TypeScript compilation (npx tsc --noEmit): PASS (zero errors)

### Evidence Files Created:

- `.sisyphus/evidence/task-2-pydantic-validation.txt`: Model instantiation test
- `.sisyphus/evidence/task-2-custom-params.txt`: Wildcard parameter test
- `.sisyphus/evidence/task-2-ts-compile.txt`: TS compilation (empty = success)

### Notes:

- LSP diagnostics show expected Pydantic warnings (Optional deprecation in Python 3.10+, but these don't block functionality)
- All imports verified end-to-end
- Schema ready for FastAPI endpoint generation (model_json_schema() works)

# Task 3 Learnings — Data Pipeline Layer

## Date: 2026-02-28

### Key Findings

1. **basedpyright strict mode**: Using `dict[str, object]` as return/param types causes cascading LSP errors when downstream code calls `.get()`, uses operators (`<`, `>`), or calls string methods (`.lower()`). Fix: use `dict[str, Any]` from `typing` instead.

2. **pyproc not installed**: Despite being in the tech stack, pyproc is NOT in the venv. `pyproc_loader.py` handles this gracefully with `try/except ImportError` and a module-level `_pyproc_available` flag. The `reportMissingImports` LSP error is acceptable — it's a runtime-optional dependency.

3. **UPPERCASE constant redefinition**: basedpyright treats UPPERCASE variables as constants. Reassigning `_PYPROC_AVAILABLE = True` inside a `try` block triggers `reportConstantRedefinition`. Fix: use lowercase naming (`_pyproc_available`) for mutable module-level flags.

4. **Optional callable types**: When a module-level variable like `Lpse = None` is conditionally imported, calling it triggers `reportOptionalCall` since pyright infers type `None`. Fix: use `_LpseClass: Any = None` to bypass strict callable checking.

5. **aiosqlite works well**: `init_db()` with raw SQL DDL and `aiosqlite.connect()` is clean and fast. 5 tables created with proper indexes in <100ms.

6. **LKPP column mapping**: LKPP datasets have inconsistent column names (e.g., `nama_satker` vs `instansi` vs `kementerian_lembaga` all mean buyer_name). A priority-based mapping dict handles all variants.

### Files Created
- `backend/data/__init__.py` — barrel exports (4 symbols)
- `backend/data/storage.py` — async SQLite, 5 tables, init_db, get_connection, upsert_tender, count_tenders
- `backend/data/ingestion.py` — opentender.net paginated download, NPWP SHA-256 hashing, OCDS parsing
- `backend/data/lkpp_loader.py` — LKPP XLSX column normalization and loading
 `backend/data/pyproc_loader.py` — optional pyproc wrapper with Cloudflare fallback

## [2026-02-28] Task 6: Feature Engineering — COMPLETE
 73 Cardinal OCP flags: R001..R073 (Planning/Tender/Award/Implementation phases)
 12 Custom forensic features: bid_clustering_score, vendor_win_concentration, hps_deviation_ratio,
  participant_count_anomaly, geographic_concentration, repeat_pairing_index, temporal_submission_pattern,
  historical_win_rate, phantom_bidder_score, benford_anomaly (placeholder), interlocking_directorates,
  bid_rotation_pattern (placeholder)
 Pipeline: 87-column DataFrame (73+12+2 metadata). Returns pd.DataFrame(merged) for type safety.
 LSP FIX: wrap `df[LIST_COLS].copy()` return as `pd.DataFrame(df[LIST_COLS].copy())` - basedpyright strict
 LSP FIX: wrap `.value_counts()` call as `pd.Series(merged['col']).value_counts()` - ndarray workaround
 LSP FIX: assert `bool(series.isna().all())` not `assert series.isna().all()` - Series.__bool__ returns NoReturn
 Tests: 24/24 pass (`pytest tests/test_features.py -q` 1.44s)
 benford_anomaly and bid_rotation_pattern are NaN placeholders - backfilled by T9 and T7 respectively
 Cardinal NOT on PyPI - full manual implementation from OCP Dec 2024 PDF (73 flags)

## [2026-02-28] Task 7: Graph + Leiden Cartel Detection
- NetworkX no type stubs → reportMissingTypeArgument for Graph generics is expected/acceptable (not blocking)
- leidenalg.__version__ not recognized by pyright → use getattr(leidenalg, '__version__', 'unknown')
- igraph type stubs incomplete → type: ignore comments acceptable on leidenalg/igraph calls
- Windows SQLite WAL teardown: os.unlink() on temp DB raises PermissionError → wrap in try/except PermissionError: pass
- Vendor nodes: "vendor:{npwp_hash}", tender nodes: "tender:{tender_id}" — strip prefix in output
- Leiden call: leidenalg.find_partition(ig_graph, leidenalg.ModularityVertexPartition, weights="weight", seed=42)
- 4-signal cartel scorer: IBF (isolated_bid_fraction), WR (win_rate), PS (price_spread), GO (geographic_overlap)
- All scorer weights from get_config().custom_params — never hardcoded
