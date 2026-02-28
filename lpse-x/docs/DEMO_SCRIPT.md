# LPSE-X Demo Script — Stage 3 (10 Menit)

## Konteks

**Platform**: LPSE-X — Forensik Pengadaan Pemerintah Berbasis XAI  
**Hackathon**: Find IT! 2026 UGM — Track C: "The Explainable Oracle"  
**Durasi demo**: 10 menit  
**Audience**: Juri teknis + evaluator bisnis  

---

## Persiapan Sebelum Demo (T-15 menit)

```bash
# 1. Start server
cd C:\Hackthon\lpse-x
.venv\Scripts\python -m backend.main

# 2. Buka browser ke http://localhost:<port>
# 3. Pastikan dashboard menampilkan tender dengan risk score
# 4. Siapkan terminal untuk live injection demo
```

---

## Alur Demo (10 Menit)

### Menit 1–2: Pembukaan & Dashboard Overview

**Yang dikatakan:**
> "LPSE-X adalah platform forensik pengadaan pemerintah pertama di Indonesia yang menggunakan Explainable AI. Tidak cukup hanya mendeteksi fraud — sistem kami **menjelaskan mengapa** sebuah tender dicurigai, sehingga auditor bisa mengambil keputusan berdasarkan bukti, bukan kotak hitam."

**Yang ditunjukkan:**
- Dashboard utama → tabel tender dengan kolom `Risk Score`, `Risk Level`, `Method`
- Filter aktif: `scope=konstruksi`, `year_range=2022-2024`, `threshold=0.7`
- Highlight: 3–5 tender dengan warna merah (Risiko Kritis/Tinggi)

---

### Menit 3–4: Drill-Down Tender Berisiko Tinggi

**Yang ditunjukkan:**
- Klik tender berisiko tinggi (risk score ≥ 0.85)
- Halaman detail → tampilkan **Oracle Sandwich XAI** (5 layer)

**Poin utama per layer:**

| Layer | Yang ditunjukkan | Pesan utama |
|-------|-----------------|-------------|
| **SHAP** | Bar chart feature importance | "n_bidders=1 berkontribusi +0.42 ke skor risiko" |
| **Anchors** | Rule cards | "JIKA n_bidders ≤ 1 DAN price_ratio > 0.98 → Risiko Tinggi (presisi 91%)" |
| **Benford's Law** | Digit frequency chart | "Distribusi digit pertama menyimpang dari hukum Benford (p=0.001)" |
| **Leiden Graph** | Community graph | "Vendor ini tergabung dalam komunitas 7 anggota dengan win-rotation terdeteksi" |
| **DiCE** | Counterfactual cards | "Jika jumlah peserta ≥ 3, risiko turun ke 0.31 (Aman)" |

---

### Menit 5: Deteksi Kartel via Graph Analysis

**Yang ditunjukkan:**
- Navigasi ke halaman `/graph`
- Visualisasi graph kartel Leiden → node = vendor, edge = co-bid
- Highlight komunitas dengan warna merah (suspicion score tinggi)
- Klik node vendor → tampilkan `win_rotation_pattern`, `repeat_pairing_index`

**Yang dikatakan:**
> "Leiden community detection menemukan 12 komunitas vendor yang co-bid secara berulang. Komunitas ini menunjukkan pola rotasi kemenangan — anggotanya bergantian menang secara mencurigakan."

---

### Menit 6: Laporan Pra-Investigasi (IIA 2025 Format)

**Yang ditunjukkan:**
- Navigasi ke `/reports` → klik "Generate Report" untuk tender yang sama
- Laporan auto-generate dalam Bahasa Indonesia
- Sections: Temuan Utama, Analisis Risiko, Rekomendasi, Lampiran Bukti

**Yang dikatakan:**
> "Laporan ini mengikuti format IIA 2025 — siap dikirim ke aparat pengawas tanpa editing manual."

---

### Menit 7–8: DEMO KRITIS — Dynamic Injection (Competition Requirement)

> ⚠️ **INI YANG PALING PENTING** — kegagalan di sini = diskualifikasi

**Script terminal:**

```bash
# Step 1: Lihat config saat ini
curl http://localhost:<port>/api/config

# Step 2: Inject parameter baru dari juri
curl -X PUT http://localhost:<port>/api/config/inject \
  -H "Content-Type: application/json" \
  -d '{
    "risk_threshold": 0.5,
    "procurement_scope": "konstruksi",
    "institution_filter": ["Kemenkeu", "Kemen-PUPR"],
    "year_range": [2022, 2024],
    "anomaly_method": "ensemble",
    "custom_params": {
      "judge_province": "Jawa Barat",
      "extra_weight": 1.5,
      "enable_benford_strict": true
    }
  }'

# Step 3: Lihat perubahan
curl http://localhost:<port>/api/config
```

**Yang ditunjukkan:**
- Response injection: `{"success": true, "old_values": {...}, "new_values": {...}}`
- **Refresh dashboard** → lebih banyak tender masuk threshold (karena threshold turun ke 0.5)
- GET config → semua parameter termasuk `custom_params` tersimpan

**Yang dikatakan:**
> "Tidak perlu restart server. Config berubah instan. Sistem menerima parameter tak terduga apapun via `custom_params` — ini memenuhi requirement Dynamic Injection secara penuh."

---

### Menit 9: Offline Capability

**Yang ditunjukkan:**
- Matikan Wi-Fi (atau aktifkan airplane mode)
- Refresh dashboard → **tetap berjalan normal**
- Jalankan prediksi baru → berhasil

**Yang dikatakan:**
> "LPSE-X berjalan 100% offline dari folder tunggal. Tidak ada dependency ke cloud, tidak ada API key eksternal. Siap dijalankan dari USB di laptop apapun."

---

### Menit 10: Penutup & Poin Scoring

**Yang dikatakan:**
> "LPSE-X memenuhi semua kriteria penilaian:
> - **XAI Quality (40%)**: 5 layer Oracle Sandwich — SHAP, Anchors, DiCE, Leiden, Benford
> - **Completeness (30%)**: Data pipeline → ML → XAI → Laporan, end-to-end
> - **Offline Capability (20%)**: Zero cloud, portable bundle, auto port-detection
> - **Code Quality (10%)**: 449 tests lulus, no hardcoded params, seed=42 logged, audit trail lengkap"

---

## Antisipasi Pertanyaan Juri

| Pertanyaan | Jawaban |
|-----------|---------|
| "Apa bedanya dengan dashboard LKPP biasa?" | "LKPP menampilkan data. LPSE-X **menjelaskan** mengapa sebuah tender berisiko, dengan bukti yang bisa dipertanggungjawabkan secara hukum." |
| "Apakah model bisa salah?" | "Ya — itulah mengapa kami pakai XAI. SHAP dan Anchors menunjukkan reasoning, sehingga auditor bisa override jika ada konteks yang model tidak tahu." |
| "Bagaimana dengan GDPR/privasi?" | "NPWP tidak disimpan mentah — hanya SHA-256 hash + 4 digit terakhir. Seluruh data di local SQLite." |
| "Bisa inject parameter apapun?" | "Ya, via `custom_params` dict. Sistem menerima key-value arbitrary tanpa schema error." |
| "Berapa lama model dilatih?" | "Model dilatih di Stage 2 (pre-hackathon). Stage 3 adalah inference only — tidak ada retraining." |

---

## Checklist Teknis Sebelum Naik Panggung

- [ ] Server berjalan di port auto-detected
- [ ] Dashboard menampilkan data (≥10 tender dengan risk scores)
- [ ] Injection endpoint responsif (`curl /api/config/inject`)
- [ ] Graph page menampilkan komunitas
- [ ] Reports page menghasilkan laporan
- [ ] Wi-Fi test: matikan → sistem tetap jalan
- [ ] Terminal siap untuk live injection demo
