# Panduan Deployment Dashboard Kemiskinan Indonesia

Dokumen ini menjelaskan cara menayangkan subproject `dashboard-web` dari repository monorepo `KemiskinanIndo` melalui Vercel atau Cloudflare Workers. Keduanya dapat memakai custom domain dan deploy otomatis dari Git.

## 1. Prasyarat

- Node.js `22.13.0` atau lebih baru;
- Git;
- akun Vercel atau Cloudflare;
- repository GitHub, GitLab, atau Bitbucket jika ingin continuous deployment.

Siapkan project dan pastikan kedua build lulus sebelum deploy:

```bash
npm install
npm run build:vercel
npm run build
```

Dashboard saat ini tidak membutuhkan database, secret, atau environment variable. Jangan memasukkan token Vercel, Cloudflare, maupun Git ke repository.

## 2. Deployment ke Vercel

### Pilihan A - melalui dashboard Vercel

1. Push folder project ke GitHub, GitLab, atau Bitbucket.
2. Masuk ke Vercel, pilih **Add New > Project**, lalu impor repository.
3. Isi **Root Directory** dengan `dashboard-web`.
4. Pastikan **Framework Preset** terbaca sebagai **Next.js**.
5. Konfigurasi build yang digunakan:
   - Install Command: `npm install`
   - Build Command: `npm run build:vercel`
   - Output Directory: biarkan default Next.js, jangan diisi manual.
6. Klik **Deploy**.

File `vercel.json` dalam project sudah menetapkan framework Next.js dan build command yang benar. Setelah Git terhubung, setiap push ke branch produksi akan menghasilkan production deployment; branch lain mendapat preview deployment.

### Pilihan B - melalui Vercel CLI

Dari folder `dashboard-web`:

```bash
npx vercel
```

Ikuti proses login dan pemilihan project. Untuk deployment produksi:

```bash
npx vercel --prod
```

Uji hasil build Vercel secara lokal bila diperlukan:

```bash
npm run build:vercel
npm run start:vercel
```

### Custom domain di Vercel

1. Buka project di Vercel.
2. Masuk ke **Settings > Domains**.
3. Tambahkan domain atau subdomain.
4. Ikuti instruksi DNS yang ditampilkan Vercel.
5. Tunggu status domain menjadi valid; HTTPS diterbitkan otomatis.

Dokumentasi resmi: [Next.js on Vercel](https://vercel.com/frameworks/nextjs) dan [Git deployments](https://vercel.com/docs/git).

## 3. Deployment ke Cloudflare Workers

Project menggunakan Vinext untuk menghasilkan Worker beserta static assets. Target yang sesuai adalah **Cloudflare Workers**, bukan export HTML statis.

### Deployment manual dengan Wrangler

Login sekali pada perangkat yang digunakan:

```bash
npx wrangler login
```

Kemudian jalankan:

```bash
npm run deploy:cloudflare
```

Perintah tersebut melakukan dua langkah:

1. `vinext build` menghasilkan bundle di folder `dist`;
2. `wrangler deploy --config dist/server/wrangler.json` mengunggah Worker dan aset statis.

Alternatifnya, jalankan kedua perintah secara terpisah:

```bash
npm run build
npx wrangler deploy --config dist/server/wrangler.json
```

Wrangler akan menampilkan URL `workers.dev` setelah deployment selesai. File konfigurasi di `dist/server/wrangler.json` dibuat ulang saat build, sehingga jangan mengeditnya sebagai konfigurasi sumber permanen.

### Continuous deployment di Cloudflare

Untuk deployment otomatis dari repository:

1. Buka **Workers & Pages** di Cloudflare Dashboard.
2. Pilih pembuatan aplikasi dari repository Git.
3. Pilih repository dan branch produksi.
4. Jika monorepo, set root directory ke `dashboard-web`.
5. Gunakan build command `npm run build`.
6. Gunakan deploy command `npx wrangler deploy --config dist/server/wrangler.json` bila form meminta perintah deploy terpisah.
7. Tidak ada environment variable yang perlu ditambahkan untuk versi dashboard saat ini.

Nama menu dapat berubah mengikuti pembaruan Cloudflare. Intinya, build harus selesai lebih dahulu dan Wrangler harus menggunakan konfigurasi hasil Vinext di `dist/server/wrangler.json`.

### Custom domain di Cloudflare

1. Buka Worker yang sudah aktif.
2. Masuk ke **Settings > Domains & Routes**.
3. Tambahkan custom domain.
4. Pilih zone/domain yang sudah dikelola Cloudflare.
5. Verifikasi URL, peta, GeoJSON, dan social preview setelah DNS aktif.

Dokumentasi resmi: [Next.js on Cloudflare Workers](https://developers.cloudflare.com/workers/framework-guides/web-apps/nextjs/), [Wrangler](https://developers.cloudflare.com/workers/wrangler/), dan [Wrangler configuration](https://developers.cloudflare.com/workers/wrangler/configuration/).

## 4. Checklist setelah deployment

- Halaman utama dapat dibuka tanpa error 500.
- Peta menampilkan bentuk kepulauan Indonesia, bukan kotak.
- Filter tahun dan provinsi mengubah visual yang relevan.
- Tooltip peta muncul saat provinsi diarahkan atau dipilih.
- Grafik tren nasional dan peringkat provinsi tampil.
- Bagian prediksi menampilkan label **Proyeksi 2026** dan interval ketidakpastian.
- File `/data/indonesia-adm1-legacy.geojson` dan `/data/indonesia-adm1-current.geojson` mengembalikan status 200.
- Tab **Temuan**, matriks risiko, dan diagnostik provinsi dapat dibuka.
- Tautan `/downloads/laporan_analisis_kemiskinan_indonesia_2015_2026.pdf` dan `/downloads/dashboard-data.json` dapat diunduh.
- Tampilan diuji pada desktop dan ponsel.
- Judul, description, favicon, dan gambar social preview terbaca.

## 5. Pemecahan masalah

### Peta kosong atau berbentuk kotak

- Pastikan kedua file GeoJSON dalam `public/data` ikut terdeploy.
- Hapus cache browser atau buka deployment terbaru dalam mode privat.
- Periksa Console dan Network browser untuk request GeoJSON yang gagal.
- Pastikan source terbaru memuat fungsi normalisasi arah polygon sebelum geometri diberikan ke D3.

### Build gagal karena versi Node.js

Pilih Node.js 22 pada pengaturan platform. Project mensyaratkan `>=22.13.0` pada `package.json`.

### Vercel mencoba mengompilasi modul Cloudflare

Gunakan `npm run build:vercel`, bukan `npm run build`. Konfigurasi `tsconfig.json` sudah mengecualikan folder Worker, D1, dan Drizzle dari build Next.js.

### Cloudflare tidak menemukan konfigurasi

Jalankan `npm run build` terlebih dahulu. File `dist/server/wrangler.json` baru tersedia setelah proses Vinext selesai.

### Aset lama masih tampil

Pastikan deployment terakhir berhasil, lalu lakukan hard refresh. Pada custom domain, periksa aturan cache Cloudflare jika ada.

## 6. Rekomendasi alur produksi

1. Kerjakan perubahan pada branch terpisah.
2. Jalankan `npm run build:vercel` dan `npm run build`.
3. Tinjau preview deployment.
4. Merge ke branch produksi setelah peta, filter, dan prediksi lolos checklist.
5. Simpan dataset sumber dan artefak model secara terpisah agar hasil analisis dapat direproduksi.

Untuk project ini, Vercel adalah jalur paling sederhana bila menginginkan pengalaman Next.js standar. Cloudflare Workers cocok bila domain dan trafik sudah dikelola dalam ekosistem Cloudflare.
