# Pemantau Buyback Antam

Skrip ringan untuk mengambil harga buyback Antam 1 gram, mencatat riwayatnya ke `history.csv`, dan memperbarui riwayat otomatis lewat GitHub Actions.

## Sumber data

1. API komunitas [Logam Mulia API](https://github.com/iamutaki/logam-mulia-api), endpoint Logam Mulia.
2. Cadangan arsip CSV [Momen Emas](https://gold.hafidznrg.my.id/data/csv/logammulia-antam.csv).

Harga yang dicatat adalah harga per gram yang dilaporkan sumber. Arsip cadangan dapat tertinggal dari harga saat ini. Periksa `price_date` dan `source` sebelum menjadikannya patokan transaksi; tarif final tetap mengikuti ANTAM.

## Menjalankan di komputer

Butuh Python 3.10 atau lebih baru. Tidak perlu memasang paket tambahan.

```bash
python track_price.py
```

Hasil terbaru tampil di terminal dan ditambahkan sebagai baris baru ke `history.csv`.

## Memasang di GitHub

1. Buat repository baru di GitHub, misalnya `antam-buyback-tracker`.
2. Unggah seluruh isi folder ini ke repository tersebut.
3. Buka tab **Actions** dan aktifkan workflow jika GitHub meminta.
4. Untuk mengambil harga saat itu juga, pilih **Update ANTAM buyback price** lalu **Run workflow**.

Workflow juga berjalan otomatis setiap hari sekitar pukul **10.30 dan 13.30 WIB**. GitHub dapat menjalankan jadwal beberapa menit terlambat.

## Web app

Folder ini juga berisi dashboard web responsif dan bisa dipasang di layar utama ponsel: `index.html`, `styles.css`, `app.js`, `manifest.webmanifest`, `sw.js`, dan `icon.svg`. Dashboard membaca `history.csv` dari folder yang sama.

Tombol **Perbarui harga** membuka workflow GitHub Actions. Setelah dijalankan, workflow memperbarui `history.csv`; muat ulang dashboard untuk melihat catatan terbaru.

## Kolom riwayat

- `fetched_at_wib`: waktu skrip mengambil data.
- `price_date`: tanggal harga menurut sumber.
- `freshness`: `tanggal_sesuai` jika tanggal sumber sama dengan hari pengambilan; selain itu `perlu_dicek`.
- `source`: sumber yang berhasil dipakai.
- `buyback_rp_per_gram`: harga buyback per gram dalam rupiah.
- `sell_rp_per_gram`: harga jual jika sumber menyediakannya.
