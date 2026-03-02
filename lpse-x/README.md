# LPSE-X — Platform Forensik Pengadaan Berbasis XAI

> **Find IT! 2026 UGM — Track C: "The Explainable Oracle"**  
> Sistem deteksi anomali pengadaan pemerintah yang **dapat menjelaskan keputusannya** menggunakan Oracle Sandwich XAI.

---

## Daftar Isi

- [Ringkasan](#ringkasan)
- [Arsitektur](#arsitektur)
- [Persyaratan Sistem](#persyaratan-sistem)
- [Instalasi & Setup](#instalasi--setup)
- [Menjalankan Sistem](#menjalankan-sistem)
- [Struktur Proyek](#struktur-proyek)
- [Data & Model](#data--model)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Konteks Hackathon](#konteks-hackathon)

---

## Ringkasan

LPSE-X adalah platform forensik pengadaan pemerintah yang menggunakan **Explainable AI (XAI)** untuk mendeteksi potensi kecurangan dalam proses tender. Tidak seperti sistem blackbox biasa, LPSE-X menjelaskan *mengapa* sebuah tender dicurigai melalui 5 lapisan analisis independen:

| Layer | Metode | Output |
|-------|--------|--------|
| **SHAP** | Feature importance | Fitur mana yang mendorong risiko |
| **Anchors** | Rule extraction | Aturan if-then yang dapat dipertanggungjawabkan |
| **Benford's Law** | Digit distribution | Deteksi manipulasi angka |
| **Leiden Graph** | Community detection | Jaringan kartel vendor |
| **DiCE** | Counterfactual | "Jika X berubah, risiko turun ke Y" |

### Fitur Utama

- **1.050 tender** dianalisis dengan skor risiko real-time
- **8 komunitas kartel** vendor terdeteksi via Leiden algorithm
- **5 laporan pra-investigasi** format IIA 2025 pre-generated
- **100% offline** — tidak ada API eksternal, berjalan dari folder tunggal
- **Dynamic Injection** — parameter bisa diubah tanpa restart server
- **Auto port detection** — tidak ada port hardcoded

---

## Arsitektur

```
lpse-x/
├── backend/          # FastAPI + Python ML
│   ├── api/          # REST endpoints
│   ├── ml/           # XGBoost + IForest prediction
│   ├── reports/      # IIA 2025 report generator (Jinja2)
│   └── config/       # Runtime config + Dynamic Injection
├── frontend/         # React + TypeScript + Vite
│   └── src/pages/    # Dashboard, TenderDetail, CartelGraph, RiskMap, Reports
├── data/
│   └── lpse_x.db     # SQLite: tenders(1050), predictions(1050), communities(8)
├── models/
│   ├── xgboost.ubj   # XGBoost model (pre-trained, seed=42)
│   └── iforest.pkl   # Isolation Forest model
└── scripts/          # batch_predict, seed_cobidding, generate_reports
```

**Tech Stack:**
- Backend: Python 3.11, FastAPI, aiosqlite, XGBoost, SHAP, Jinja2
- Frontend: React 18, TypeScript, Vite, Recharts, Cytoscape.js, Leaflet
- Database: SQLite (via aiosqlite, no ORM)
- ML: XGBoost + Isolation Forest ensemble, seed=42

---

## Persyaratan Sistem

- Python 3.11+
- Node.js 18+ (untuk build frontend)
- Windows / Linux / macOS
- Tidak membutuhkan koneksi internet

---

## Instalasi & Setup

### 1. Clone & Setup Python Environment

```bash
git clone <repo-url>
cd lpse-x

# Buat virtual environment
python -m venv .venv

# Aktifkan (Windows)
.venv\Scripts\activate
# Aktifkan (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 3. Jalankan Scripts Seeding (opsional — data sudah ada di DB)

```bash
# Pre-compute prediksi untuk semua tender
.venv/Scripts/python.exe scripts/batch_predict.py

# Seed komunitas co-bidding
.venv/Scripts/python.exe scripts/seed_cobidding.py

# Generate laporan pra-investigasi top-5
.venv/Scripts/python.exe scripts/generate_reports.py
```

---

## Menjalankan Sistem

```bash
# Start backend + serve frontend (auto port detection 8000-8099)
.venv\Scripts\python.exe start_lpse_x.py
```

Buka browser ke `http://localhost:<port>` (port ditampilkan di terminal).

Atau jalankan backend saja:

```bash
.venv\Scripts\python.exe -m backend.main
```

---

## Struktur Proyek

```
lpse-x/
├── backend/
│   ├── api/
│   │   └── routes/
│   │       ├── tenders.py        # GET /api/tenders, GET /api/tenders/{id}
│   │       ├── reports.py        # GET/POST /api/reports/{tender_id}
│   │       ├── graph.py          # GET /api/graph/communities
│   │       ├── config.py         # GET/PUT /api/config, PUT /api/config/inject
│   │       └── oracle.py         # POST /api/oracle/explain
│   ├── ml/
│   │   ├── predict.py            # XGBoost + IForest ensemble
│   │   └── features.py           # 82-feature extractor
│   ├── reports/
│   │   ├── generator.py          # ReportGenerator (IIA 2025 format)
│   │   └── templates/            # Jinja2 templates
│   ├── config/
│   │   └── runtime.py            # Dynamic Injection config
│   └── main.py                   # FastAPI app entrypoint
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.tsx     # Tabel tender + risk scores
│       │   ├── TenderDetail.tsx  # Detail XAI per tender
│       │   ├── CartelGraph.tsx   # Visualisasi komunitas kartel
│       │   ├── RiskMap.tsx       # Peta risiko per wilayah
│       │   └── Reports.tsx       # Laporan pra-investigasi
│       ├── api/client.ts         # API client (listTenders, getTender)
│       └── types/models.ts       # TypeScript type definitions
├── data/
│   └── lpse_x.db                 # SQLite database
├── models/
│   ├── xgboost.ubj               # XGBoost model binary
│   ├── iforest.pkl               # Isolation Forest model
│   └── iforest.json              # Feature names (21 features)
├── scripts/
│   ├── batch_predict.py          # Batch prediction untuk semua tender
│   ├── seed_cobidding.py         # Seed komunitas co-bidding
│   └── generate_reports.py       # Pre-generate laporan pra-investigasi
├── tests/                        # Pytest test suite
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEMO_SCRIPT.md            # Script demo 10 menit
│   └── TALKING_POINTS.md
└── pyproject.toml
```

---

## Data & Model

### Database (data/lpse_x.db)

| Tabel | Rows | Deskripsi |
|-------|------|-----------|
| `tenders` | 1.050 | Data tender LPSE (SYN-* + LP-2021-*) |
| `features` | 1.050 | 82 fitur per tender (ICW scoring) |
| `predictions` | 1.050 | Skor risiko XGBoost+IForest |
| `communities` | 8 | Komunitas vendor co-bidding |
| `reports` | 5 | Laporan pra-investigasi top-5 |

### Distribusi Risiko

| Level | Count | % |
|-------|-------|---|
| High | 196 | 18.7% |
| Medium | 408 | 38.9% |
| Low | 446 | 42.5% |

### Top-5 Tender Risiko Tertinggi

| Tender ID | Risk Score | Buyer |
|-----------|-----------|-------|
| SYN-2018-00627 | 0.864 | Kota Pematang Siantar |
| SYN-2024-00563 | 0.852 | Kabupaten Sumba Timur |
| SYN-2018-00445 | 0.847 | Kabupaten Bone Bolango |
| SYN-2022-00432 | 0.823 | Kabupaten Ogan Komering Ulu Timur |
| SYN-2023-00074 | 0.819 | Kementerian Pekerjaan Umum |

---

## API Endpoints

| Method | Path | Deskripsi |
|--------|------|-----------|
| `GET` | `/api/tenders` | List tender dengan pagination + filter |
| `GET` | `/api/tenders/{id}` | Detail tender + features + prediction |
| `GET` | `/api/graph/communities` | Komunitas kartel vendor |
| `GET` | `/api/reports/{tender_id}` | Generate laporan pra-investigasi |
| `POST` | `/api/reports/{tender_id}` | Generate laporan dari oracle result |
| `GET` | `/api/config` | Lihat config runtime |
| `PUT` | `/api/config/inject` | Dynamic Injection parameter |
| `POST` | `/api/oracle/explain` | XAI explanation per tender |

### Contoh: List Tender

```bash
curl "http://localhost:8000/api/tenders?page=1&page_size=10&risk_level=high"
```

Response:
```json
{
  "items": [...],
  "total": 196,
  "page": 1,
  "page_size": 10,
  "timestamp": "2026-03-02T..."
}
```

### Contoh: Dynamic Injection

```bash
curl -X PUT http://localhost:8000/api/config/inject \
  -H "Content-Type: application/json" \
  -d '{"risk_threshold": 0.5, "custom_params": {"judge_note": "review"}}'
```

---

## Testing

```bash
# Jalankan semua tests
.venv\Scripts\python.exe -m pytest tests/ -v

# Tests spesifik untuk tenders API
.venv\Scripts\python.exe -m pytest tests/test_tenders_api.py -v
```

---

## Konteks Hackathon

**Event**: Find IT! 2026 — Gadjah Mada University  
**Track**: Track C — "The Explainable Oracle"  
**Tim**: LPSE-X  

### Kriteria Penilaian

| Kriteria | Bobot | Implementasi |
|---------|-------|-------------|
| XAI Quality | 40% | 5-layer Oracle Sandwich (SHAP, Anchors, DiCE, Leiden, Benford) |
| Completeness | 30% | Data pipeline → ML → XAI → Laporan, end-to-end |
| Offline Capability | 20% | Zero cloud, portable bundle, auto port-detection |
| Code Quality | 10% | Pytest suite, seed=42, no hardcoded params, audit trail |

### Privacy by Design

- NPWP tidak disimpan mentah — hanya SHA-256 hash + 4 digit terakhir
- Semua data di SQLite lokal — tidak ada cloud storage
- Tidak ada API key atau credential eksternal

---

*Dikembangkan untuk Find IT! 2026 — Gadjah Mada University*
