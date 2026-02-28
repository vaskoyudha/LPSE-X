# LPSE-X Talking Points — Scoring Criteria

## Penilaian Find IT! 2026 Track C

| Kriteria | Bobot | Target LPSE-X |
|---------|-------|---------------|
| XAI Quality | 40% | Oracle Sandwich 5-layer, setiap keputusan dapat dijelaskan |
| Completeness | 30% | End-to-end pipeline, semua 5 mekanisme inti terimplementasi |
| Offline Capability | 20% | 100% offline, zero cloud, portable bundle |
| Code Quality | 10% | 449 tests, no hardcoded params, clean architecture |

---

## 1. XAI Quality (40%) — Talking Points

### Apa yang harus disampaikan
> "Sistem kami mengimplementasikan **Oracle Sandwich** — 5 layer XAI yang saling melengkapi. Setiap layer menjawab pertanyaan yang berbeda dari seorang auditor."

### Argumen per layer

| Layer | Pertanyaan yang dijawab | Nilai bagi auditor |
|-------|------------------------|-------------------|
| **SHAP** | "Fitur mana yang paling mendorong risiko ini?" | Dapat menunjuk ke data spesifik dalam rekaman tender |
| **Anchors** | "Aturan apa yang selalu berlaku?" | Rule IF-THEN yang dapat dijelaskan ke pengadilan |
| **DiCE** | "Apa yang perlu berubah agar tender ini menjadi aman?" | Rekomendasi korektif, bukan hanya diagnosis |
| **Leiden Graph** | "Vendor mana yang berkolusi bersama?" | Visualisasi jaringan kartel yang dapat diaudit |
| **Benford's Law** | "Apakah angka-angka ini terlihat dimanipulasi?" | Bukti statistik manipulasi data berbasis hukum matematika |

### Fault Tolerance
- Setiap layer berjalan independen
- Satu layer gagal ≠ sistem crash
- `layers_ok` + `layers_failed` dicatat di setiap response
- Benford mengembalikan `"not_applicable"` jika data tidak applicable — tidak ada false alarm

---

## 2. Completeness (30%) — Talking Points

### 5 Mekanisme Inti (semua terimplementasi)

| Mekanisme | Status | Bukti |
|-----------|--------|-------|
| 85 feature engineering (73 Cardinal + 12 custom) | ✅ | `backend/features/` |
| Leiden cartel detection + graph analysis | ✅ | `backend/graph/` |
| Tri-Method AI (IF + XGBoost + ICW) | ✅ | `backend/ml/` |
| Oracle Sandwich 5-layer XAI | ✅ | `backend/xai/` |
| Auto pre-investigation report (IIA 2025) | ✅ | `backend/reports/` |

### Data Pipeline
- Sumber: opentender.net (1.1M tender OCDS) + LKPP XLSX + pyproc
- Storage: SQLite (zero-config, portable)
- Privacy: NPWP di-hash SHA-256 (tidak ada data mentah)

### End-to-End Flow
```
Data Ingestion → Feature Engineering → ML Training (offline) 
→ ONNX Export → Runtime Inference → XAI → Report → Dashboard
```

---

## 3. Offline Capability (20%) — Talking Points

### Cara membuktikan saat demo
1. Matikan Wi-Fi / aktifkan airplane mode
2. Refresh dashboard → tetap berjalan
3. Jalankan `POST /api/predict` → berhasil
4. Generate laporan → berhasil

### Arsitektur offline
- **Zero external API calls**: Tidak ada OpenAI, tidak ada Google, tidak ada cloud
- **ONNX Runtime**: Inference CPU-only, tidak perlu GPU, tidak perlu internet
- **SQLite**: Database lokal, tidak ada PostgreSQL/MongoDB cloud
- **Bundled tiles**: Folium di-set ke offline-safe mode
- **Auto port-detection**: Tidak konflik dengan aplikasi lain di laptop juri

### Kalau juri tanya: "Tapi datanya darimana?"
> "Data diunduh satu kali di Stage 2 dari opentender.net. Di Stage 3, semua query dilayani dari SQLite lokal. Tidak ada network call setelah ingestion."

---

## 4. Code Quality (10%) — Talking Points

### Metrics yang bisa ditunjukkan

| Metric | Nilai |
|--------|-------|
| Total test count | 449 tests |
| Test pass rate | 100% (0 failures) |
| Hardcoded parameters | 0 (semua via runtime_config.yaml) |
| External API dependencies | 0 |
| Random seeds documented | seed=42, logged di setiap run |

### Arsitektur bersih
- **No ORM**: Raw SQL + aiosqlite (performa + portabilitas)
- **Pydantic validation**: Semua input divalidasi sebelum diproses
- **Thread-safe config**: `_config_lock` (RLock) untuk injection concurrent-safe
- **Structured logging**: Tidak ada `print()` di production — semua via Python logging
- **Audit trail**: Setiap config injection dicatat dengan timestamp

### Dynamic Injection — argumen utama
> "Semua parameter dapat diubah tanpa restart server. Sistem menerima `custom_params` — dictionary arbitrer untuk parameter yang tidak terduga dari juri. Ini bukan afterthought; ini adalah arsitektur inti sejak awal."

---

## Pesan Kunci Keseluruhan (30 detik pitch)

> "LPSE-X bukan hanya anomaly detector — itu adalah **Oracle Forensik** yang menjelaskan setiap keputusannya dalam bahasa yang bisa dipahami auditor, jaksa, dan hakim. Kami mengambil 1.1 juta data tender pemerintah, mengekstrak 85 sinyal kecurangan, mendeteksi kartel lewat graph analysis, dan menghasilkan laporan pra-investigasi format IIA — semuanya offline, semuanya dapat dijelaskan, dan semuanya bisa diubah parameternya secara real-time tanpa restart."

---

## Antisipasi Kritik

| Kritik | Respons |
|--------|---------|
| "Model kamu black box" | "Tidak — kami punya SHAP (nilai kontribusi per fitur), Anchors (aturan IF-THEN), dan DiCE (skenario counterfactual). Tiga lapisan yang berbeda untuk menjelaskan keputusan yang sama." |
| "Data 1.1M tender itu valid?" | "Data dari opentender.net, sumber resmi yang didukung Open Contracting Partnership. ICW Indonesia menggunakannya untuk PFA scoring." |
| "Kenapa tidak pakai Streamlit?" | "Streamlit untuk prototyping. React untuk produksi. Juri akan melihat aplikasi yang siap dipakai oleh BPK atau KPK, bukan Jupyter notebook." |
| "Offline bisa? Sungguh?" | "Matikan Wi-Fi sekarang, saya demonstrasikan." |
| "Dynamic injection itu apa?" | "Juri bisa inject parameter apapun ke sistem kami saat demo — risk threshold, scope, bahkan parameter tak terduga via custom_params — tanpa restart server. Perubahan aktif dalam milidetik." |
