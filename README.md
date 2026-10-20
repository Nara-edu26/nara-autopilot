# Nara Autopilot

Sistem otomatis untuk akun Instagram **Nara · pemandu AI**: tiga post sehari, tanpa syuting, tanpa biaya langganan tambahan.

```
 Claude (tugas terjadwal mingguan, langganan Claude yang sudah ada)
   │  baca laporan performa + rencana 100 hari → tulis 21 post (JSON) → validasi → push
   ▼
 GitHub repo publik (gratis)
   ├─ Render & situs   : JSON → carousel JPEG + reel MP4 → GitHub Pages (media + kalkulator)
   ├─ Terbit           : 07.07 · 12.07 · 19.07 WIB → Instagram API (label AI otomatis)
   ├─ Metrik harian    : reach, simpan, share, komentar → data/laporan.md
   └─ Perpanjang token : tiap Senin, token Instagram tidak pernah mati
   ▼
 Instagram ── komentar BOCOR / TEMPLATE ──► Meta Business Suite kirim DM (gratis)
   ▼
 Kalkulator Kebocoran (gratis) ──► Template 5 Pos Rp29.000 di Lynk ──► Kursus (Jan 2027)
```

## Biaya

| Komponen | Biaya |
|---|---|
| GitHub Actions + Pages (repo publik) | Rp0 |
| Instagram API | Rp0 |
| Meta Business Suite (DM otomatis) | Rp0 |
| Pembuat konten: Claude | langganan yang sudah kamu punya |
| Lynk (toko) | Rp0 tetap; 5% per transaksi + Rp5.000 per penarikan |

## Yang tetap manual

- Pemasangan sekali di awal: ±2 jam (lihat `SETUP.md`).
- Mengunggah produk baru ke Lynk saat ada ide yang kamu setujui: ±15 menit per produk.
- Menarik uang dari Lynk, dan (disarankan) membalas komentar yang bukan kata kunci.
- Membuat token baru kalau token Instagram mati (misalnya setelah ganti kata sandi) dan memperbarui GH_PAT setahun sekali.

## Folder

| Path | Isi |
|---|---|
| `content/queue/` | Antrean post, satu file JSON per tanggal |
| `engine/` | Validator, renderer, publisher, metrik, laporan, evergreen |
| `docs/` | Situs GitHub Pages: halaman bio, kalkulator, kebijakan privasi |
| `data/` | Catatan terbit, metrik, komentar, laporan (diisi otomatis) |
| `claude/` | Panduan konten, rencana 100 hari, instruksi tugas mingguan |
| `assets/music/` | Opsional: musik bebas royalti untuk reel |

## Rem darurat

- Hentikan semua posting: ubah `"jeda": false` jadi `true` di `config.json`.
- Lewati satu post: tambahkan `"skip": true` pada post itu di `content/queue/`.

## Menjalankan di komputer sendiri

```bash
pip install -r engine/requirements.txt && python -m playwright install chromium
python engine/validate.py --semua
python engine/render.py --id 2026-10-26-pagi
python engine/publish.py --slot pagi --tanggal 2026-10-26 --uji
```
