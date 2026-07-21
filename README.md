# Peta Kemiskinan Indonesia

Dashboard web interaktif untuk mengeksplorasi kemiskinan Indonesia pada 2015-2025 dan proyeksi indikatif 2026. Aplikasi memuat tren nasional, peta koroplet provinsi, perbandingan indikator, penjelasan faktor terkait, evaluasi model, dan rentang ketidakpastian prediksi.

## Menjalankan secara lokal

Prasyarat: Node.js `>=22.13.0`.

```bash
npm install
npm run dev
```

Buka `http://localhost:3000`.

## Pemeriksaan build

```bash
# Target Cloudflare Workers / OpenAI Sites
npm run build

# Target Vercel
npm run build:vercel
```

## Deploy

Panduan lengkap tersedia di [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), termasuk:

- deploy melalui dashboard atau CLI Vercel;
- deploy ke Cloudflare Workers dengan Wrangler;
- pengaturan root directory, custom domain, dan pemecahan masalah.

## Struktur penting

- `app/page.tsx`: tampilan dan interaksi dashboard;
- `app/data/dashboard-data.json`: data siap tayang dan hasil model;
- `public/data/indonesia-adm1-legacy.geojson`: geometri 34 provinsi historis;
- `vercel.json`: konfigurasi build Vercel;
- `docs/DEPLOYMENT.md`: dokumentasi deployment.

## Catatan analitis

Prediksi 2026 adalah hasil model analitis, bukan angka resmi BPS. Hubungan antarfaktor di dashboard adalah asosiasi statistik dan tidak boleh langsung dibaca sebagai sebab-akibat.
