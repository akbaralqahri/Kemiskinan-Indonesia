# Katalog Data

Folder `data` memisahkan sumber asli dari data hasil pemrosesan. Script tidak menimpa file di `raw`.

## `raw/poverty`

Berisi 11 CSV tabel **Jumlah dan Persentase Penduduk Miskin Menurut Provinsi** untuk 2015-2025. Sumber utama adalah tabel statistik BPS.

Setiap file dipertahankan dalam bentuk asal agar proses parsing dan audit dapat diulang.

## `raw/bps_publications`

Berisi lima publikasi Statistik Indonesia yang digunakan untuk melengkapi indikator:

- Statistik Indonesia 2016;
- Statistik Indonesia 2019;
- Statistik Indonesia 2021;
- Statistik Indonesia 2024;
- Statistik Indonesia 2026.

Variabel yang diekstrak mencakup TPT, TPAK, IPM, PDRB per kapita, pertumbuhan PDRB, sanitasi, air minum, dan struktur pengeluaran.

## `processed`

- `extracted_panel.json`: data panjang, panel provinsi-tahun, cakupan, dan audit ekstraksi.
- `poverty_analysis.json`: EDA, korelasi, koefisien, validasi model, dan proyeksi 2026.

Kedua file dapat dibuat ulang menggunakan script dalam folder `work`.

## Keterangan simbol BPS

| Simbol | Makna | Perlakuan utama |
|---|---|---|
| `...` | Data tidak tersedia | `NULL`, bukan nol |
| `-` | Tidak ada atau nol | Ditentukan berdasarkan konteks |
| `NA` | Data tidak dapat ditampilkan | `NULL` |
| `e` | Angka estimasi | Nilai dipertahankan dengan flag |
| `r` | Angka diperbaiki | Versi revisi digunakan |
| `~0` | Data dapat diabaikan | Nol dengan flag |
| `*`, `**`, `***` | Tingkat kesementaraan angka | Nilai dipertahankan dengan peringatan |
| `a`, `b` | Penanda RSE | Digunakan secara hati-hati dan diverifikasi |
| `c` | Agregat tidak sama dengan wilayah di atasnya | Tidak dijumlahkan tanpa rekonsiliasi |

## Batas wilayah

Project memakai tiga semesta wilayah yang tidak boleh dicampur:

- **38 provinsi (2024-2025):** peta dan peringkat terbaru menggunakan batas BIG;
- **34 provinsi (2015-2023):** peta historis menggunakan geoBoundaries dengan konfigurasi lama;
- **32 provinsi stabil:** korelasi panel, validasi, dan forecast mengecualikan Papua, Papua Barat, serta provinsi pecahannya agar unit wilayah konsisten.

`dashboard-web/public/data/indonesia-adm1-current.geojson` berasal dari layer **Area Batas Wilayah Administrasi Provinsi** BIG dan disederhanakan untuk visualisasi, bukan penetapan batas hukum. File dapat diperbarui dengan `python work/fetch_current_province_geojson.py`.
