# Arsitektur Project

## Aliran data

```text
CSV kemiskinan + PDF Statistik Indonesia
                  |
                  v
       work/extract_bps_panel.py
                  |
                  v
 data/processed/extracted_panel.json
                  |
                  v
     work/analyze_poverty_panel.py
                  |
                  v
 data/processed/poverty_analysis.json
          |                       |
          v                       v
work/prepare_site_data.py   work/create_analysis_report.py
          |                       |
          v                       v
dashboard-data.json          output/pdf/*.pdf
          |
          v
dashboard-web -> Vercel / Cloudflare Workers / Sites
```

Sumber geometri berjalan paralel: layer provinsi BIG diproses oleh `work/fetch_current_province_geojson.py` menjadi GeoJSON 38 provinsi. File ini dipakai pada peta 2024-2025 dan analisis spasial 2025.

## Prinsip desain

1. **Raw immutable**: sumber asli tidak dimodifikasi oleh pipeline.
2. **Processed reproducible**: JSON hasil olahan selalu dapat dibuat ulang dari `data/raw`.
3. **Timing aman**: target Maret tahun t diprediksi memakai indikator t-1.
4. **Validasi temporal**: tahun uji tidak boleh ikut dalam data pelatihan.
5. **Pemisahan deployment**: platform web hanya membutuhkan `dashboard-web`, tetapi repository tetap menyimpan keseluruhan penelitian.
6. **Audit mutu**: simbol BPS dan status angka sementara dipertahankan.

## Cakupan model

Model memakai 32 provinsi dengan batas konsisten pada 2015-2025. Peta memilih geometri berdasarkan tahun: 34 batas historis untuk 2015-2023 dan 38 batas BIG untuk 2024-2025. Pemisahan ini mencegah perubahan geometri terbaca sebagai perubahan statistik.

## Forecast

Model rekomendasi adalah ensemble antara naive lag-1 dan Ridge dengan penggerak sosial-ekonomi. Interval 80% dibangun dari residual out-of-sample. Hasil 2026 adalah eksperimen analitis, bukan publikasi resmi BPS.

Output analisis juga menyimpan konvergensi, Global Moran's I eksploratif, error validasi per provinsi, selisih antarmodel, serta kelas prioritas pemantauan. JSON dan PDF final disalin ke `dashboard-web/public/downloads` agar tersedia setelah deployment.
