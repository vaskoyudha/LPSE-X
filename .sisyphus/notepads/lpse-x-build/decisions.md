# Decisions — lpse-x-build

## Architecture Decisions
- Monorepo under `lpse-x/` with backend/, frontend/, models/, data/, config/, reports/, tests/
- FastAPI serves both API and React static files (single server, no separate nginx)
- SQLite for zero-config localhost deployment
- ONNX Runtime for model inference (trained once pre-hackathon, no retraining at Stage 3)
- Temporal split: 2018-2021 train / 2022 validate / 2023-2024 test
- ICW total_score on opentender.net tenders used as weak labels (no manual annotation needed)
- DiCE counterfactuals: CACHED/ASYNC only — NOT blocking main inference
- Benford analysis: pre-check gating — return "not_applicable" when <100 records
- Map tiles: Folium in offline-safe mode (bundled or disabled)

## Data Sources (Verified)
- opentender.net: 1,106,096 tenders, OCDS format, REST API bulk export ✅
- LKPP CKAN: 4 XLSX files already at C:\Hackthon\lkpp_*.xlsx ✅
- pyproc: Python wrapper for real-time LPSE scraping (needs testing via test_pyproc_local.py)
- Cardinal (OCP): Auto-computes 73 red flags from OCDS data

## MVP Scope
- Sector: Pekerjaan Konstruksi (construction)
- Institutions: 5 LPSE (Kemenkeu, Kemen-PUPR, Pemprov DKI Jakarta, Kemenkes, Pemprov Sumbar)
- Period: 2022-2024
