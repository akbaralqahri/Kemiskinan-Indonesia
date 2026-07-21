# Pipeline Analisis

Semua perintah dijalankan dari root repository.

## 1. Ekstraksi dan harmonisasi

```bash
python work/extract_bps_panel.py
```

Input:

- `data/raw/poverty/*.csv`
- `data/raw/bps_publications/*.pdf`

Output: `data/processed/extracted_panel.json`.

## 2. Analisis dan forecasting

```bash
python work/analyze_poverty_panel.py
```

Output: `data/processed/poverty_analysis.json`.

Tahap ini membuat panel lag t-1, EDA, korelasi pooled/within, Ridge, baseline, walk-forward validation 2022-2025, ensemble, serta proyeksi 2026.

## 3. Data siap tayang

```bash
python work/prepare_site_data.py
```

Output: `dashboard-web/app/data/dashboard-data.json`.

## 4. Laporan PDF

```bash
python work/create_analysis_report.py
```

Output: `output/pdf/laporan_analisis_kemiskinan_indonesia_2015_2026.pdf`.

## 5. Workbook analisis

`build_foundation_workbook.mjs` menghasilkan workbook dan preview di `output/spreadsheets`. Script ini memakai runtime spreadsheet Codex (`@oai/artifact-tool`) dan bersifat opsional untuk pengguna di luar lingkungan tersebut.

## Script diagnostik

- `diagnose_bps.mjs`: membantu memeriksa response halaman BPS.
- `verify_foundation_workbook.mjs`: memeriksa sheet dan formula workbook hasil analisis.
