# Issues — lpse-x-build

## Known Risks
- leidenalg on Windows may need C library (igraph) — must verify in Task 1 before proceeding
- pyproc real-time scraping: MA Cloudflare protection may block — have fallback (opentender bulk data)
- DiCE is slow — must be async/cached, never blocking main inference endpoint
- Benford's Law only valid with >=100 records spanning orders of magnitude — pre-check required
- All stochastic processes (Leiden, XGBoost) need seed logging for reproducibility
- SHAP must be computed on standardized/encoded features (Hwang et al. 2025 sensitivity finding)

## Resolved Issues (from Architecture Plan)
- Port conflict on demo laptop → auto-detect free port
- Offline map tiles → Folium in offline-safe mode
- ONNX parity → native vs ONNX parity test in Task 11 acceptance criteria
- Leiden reproducibility → seed + version logging requirement

## Task 1 Watch Items
- Verify leidenalg+igraph compile on Windows without DLL errors
- cardinal PyPI package: verify correct package name (may be `cardinal-pythons` or similar)
- benford_py: verify correct import name (`import benford` vs `import benford_py`)
