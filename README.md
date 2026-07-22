# Analisis Kemiskinan Indonesia 2015-2026

Repository ini memuat seluruh siklus project data science: sumber BPS, harmonisasi panel provinsi, analisis multivariat, evaluasi model, proyeksi 2026, laporan, dan dashboard web.

Dashboard aktif: [Peta Kemiskinan Indonesia](https://peta-kemiskinan-indonesia.pruductnumberone19.chatgpt.site/)

## Struktur repository

```text
KemiskinanIndo/
|-- data/
|   |-- raw/
|   |   |-- poverty/             # 11 CSV kemiskinan BPS, 2015-2025
|   |   `-- bps_publications/    # Publikasi Statistik Indonesia
|   `-- processed/               # Panel harmonis dan hasil model berbentuk JSON
|-- work/                        # Script ekstraksi, analisis, ekspor, dan laporan
|-- dashboard-web/               # Aplikasi Next.js/Vinext yang dideploy
|-- output/
|   |-- pdf/                     # Laporan analisis
|   `-- spreadsheets/            # Workbook dan preview hasil analisis
|-- docs/                        # Dokumentasi arsitektur dan reproduksi
|-- scripts/                     # Perintah bantu lintas tahap
|-- tmp/                         # Artefak sementara; tidak masuk Git
|-- requirements.txt
`-- .gitignore
```

## Menjalankan dashboard

Prasyarat: Node.js 22.13 atau lebih baru.

```bash
cd dashboard-web
npm install
npm run dev
```

Buka `http://localhost:3000`.

Dashboard dapat langsung berjalan setelah repository di-clone karena data siap tayang sudah tersedia di `dashboard-web/app/data/dashboard-data.json`.

## Mereproduksi analisis

Siapkan Python virtual environment dan dependency:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Jalankan tahap berikut dari root repository:

```bash
python work/fetch_current_province_geojson.py  # opsional: perbarui batas BIG
python work/extract_bps_panel.py
python work/analyze_poverty_panel.py
python work/prepare_site_data.py
python work/create_analysis_report.py
```

Pada Windows, seluruh rangkaian dapat dijalankan dengan:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/reproduce.ps1
```

Gunakan `-SkipExtract` bila ingin memakai `data/processed/extracted_panel.json` yang sudah tersedia.
Gunakan `-RefreshMap` hanya ketika ingin mengambil ulang batas 38 provinsi dari layanan BIG; GeoJSON siap tayang sudah disertakan di repository.

## Hasil utama

- Kemiskinan nasional turun dari 11,22% pada Maret 2015 menjadi 8,47% pada Maret 2025.
- Model utama memakai 32 provinsi dengan batas konsisten sepanjang 2015-2025.
- Model terpilih adalah ensemble 50% naive lag-1 dan 50% Ridge.
- Walk-forward validation 2022-2025 menghasilkan MAE sekitar 0,353 poin persen.
- MAE ensemble sekitar 19,6% lebih rendah daripada baseline naive lag-1.
- Dispersi kemiskinan pada 32 provinsi stabil menyempit sekitar 28,6% sejak 2015.
- Global Moran's I 2025 sebesar 0,663 (pseudo-p 0,001), menandakan pola kemiskinan mengelompok secara geografis pada definisi KNN-4.
- Proyeksi 2026 bersifat eksperimental dan bukan angka resmi BPS.

Dashboard kini memuat tab temuan, peta 38 provinsi terkini, penjelasan semesta 38/34/32, matriks risiko forecast, diagnostik error per provinsi, serta unduhan laporan PDF dan data JSON.

## Deployment

Repository Git dimulai dari folder ini, tetapi root aplikasi deployment adalah `dashboard-web`.

- Vercel: set **Root Directory** ke `dashboard-web` dan gunakan `npm run build:vercel`.
- Cloudflare Workers: set root ke `dashboard-web` dan gunakan alur Vinext/Wrangler.

Panduan lengkap terdapat di [dashboard-web/docs/DEPLOYMENT.md](dashboard-web/docs/DEPLOYMENT.md).

## Menghubungkan ke GitHub

Buat repository kosong di GitHub, lalu jalankan dari folder `KemiskinanIndo`:

```bash
git remote add origin https://github.com/USERNAME/NAMA-REPOSITORY.git
git push -u origin main
```

Periksa remote dengan `git remote -v`. Repository menyertakan lima PDF publikasi BPS, sehingga push pertama lebih besar daripada push dashboard biasa. Jika repository nantinya bertambah besar, pertimbangkan Git LFS atau penyimpanan sumber eksternal tanpa mengubah struktur folder lokal.

## Dokumentasi

- [Arsitektur dan aliran data](docs/ARCHITECTURE.md)
- [Katalog dataset](data/README.md)
- [Urutan script analisis](work/README.md)
- [Daftar keluaran](output/README.md)
- [Panduan deployment](dashboard-web/docs/DEPLOYMENT.md)

## Catatan interpretasi

Korelasi dan koefisien model merupakan hubungan statistik, bukan bukti sebab-akibat. Peringkat provinsi perlu dibaca bersama ukuran populasi, kedalaman kemiskinan, ketimpangan, dan konteks wilayah.
