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

Model temporal memakai 32 provinsi dengan batas stabil. Provinsi baru di Papua tetap tersedia pada data 2025 dan peringkat dashboard, tetapi tidak dipaksakan ke geometri 34 provinsi historis.
