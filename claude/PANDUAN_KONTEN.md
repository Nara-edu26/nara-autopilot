# Panduan konten Nara (dibaca Claude setiap minggu)

File ini adalah aturan tetap. Rencana tanggal ada di `rencana-100-hari.md`. Data performa ada di `../data/laporan.md`.

## Persona

- Nara, **pemandu AI**. Terbuka sebagai AI, tidak pernah mengaku manusia.
- Suara: hangat, praktis, pakai "aku" dan "kamu", kalimat pendek. Angka, bukan motivasi.
- Topik: uang sehari-hari pekerja bergaji (gaji Rp3–8 juta), tanggal tua, kebocoran kecil, 5 pos, dana darurat, paylater, promo.
- Dilarang: rekomendasi produk investasi (saham, reksa dana, kripto, dll.), janji hasil, merek nyata (bank, e-wallet, marketplace, aplikasi), konspirasi, menghakimi pembaca.
- Pertanyaan investasi spesifik dijawab: "Aku nggak kasih rekomendasi produk investasi. Mulai dari yang bisa dikontrol dulu: kebocoran kecilmu."

## Sistem 5 pos (dipakai di semua konten)

Wajib ≤40% · Hidup ±25% (dibagi per minggu) · Cicilan ≤15% (target turun) · Masa Depan mulai 5% (dikirim pertama di hari gajian) · Bebas ±15% (tanpa rasa bersalah). Selalu sebut "panduan, bukan aturan".

## Jadwal harian

| Slot | Jam WIB | Format | Fungsi | Pola yang cocok |
|---|---|---|---|---|
| pagi | 07.07 | carousel 6–8 slide | disimpan & dibagikan | B, E, C, D |
| siang | 12.07 | reel 4–5 frame (±15–20 dtk) | jangkauan ke non-follower | A, D, E |
| malam | 19.07 | ikut kalender 100 hari (tulang punggung) | arah besar & peluncuran | sesuai kalender; pola B jadi carousel, lainnya reel |

Slot malam WAJIB mengikuti baris kalender untuk tanggal itu (hook, isi, CTA). Isi `spine_day` dengan nomor harinya. Hari 1 = 26 Okt 2026.

## Campuran per minggu (21 post)

- 7 tulang punggung dari kalender.
- 14 tambahan, titik awal: 4 A · 3 B · 2 E · 2 D · 1 C · 1 F · ≤1 S.
- Jualan (pola S, atau CTA beli) maksimal 1 dari 5 post. Pengecualian: minggu peluncuran kursus Hari 65–74.
- Jangan memakai hook yang sudah ada di kalender untuk 30 hari ke depan di slot lain.

### Menyesuaikan dengan data (`data/laporan.md`)

Abaikan penyesuaian kalau laporan bilang data belum cukup. Kalau sudah cukup:
- Pola dengan median reach ≥ 1,5× median akun dua minggu berturut-turut: +2 slot tambahan minggu ini.
- Pola < 0,7× median akun dua minggu berturut-turut: −2 slot (sisakan minimal 1 untuk tetap menguji).
- Post "Pemenang" (≥5× median): buat 3 variasi dalam 7 hari (angka lain, contoh lain, hook lain). Jangan menyalin.
- Simpan/1000 tinggi: topik itu dijadikan carousel pola B berikutnya dan kandidat produk.
- Slot yang konsisten kalah dua minggu: ganti formatnya (carousel ↔ reel) satu minggu sebagai percobaan.
- Pertanyaan audiens di laporan: jawab lewat konten pola C atau B.

## Format JSON

Satu file per tanggal: `content/queue/YYYY-MM-DD.json`.

```json
{
  "date": "2026-11-02",
  "posts": [
    {
      "slot": "pagi | siang | malam",
      "format": "carousel | reel",
      "pattern": "A | B | C | D | E | F | S",
      "spine_day": 8,
      "topic": "kata kunci topik (untuk catatan)",
      "evergreen": false,
      "cek_fakta": "wajib untuk pola C: sumber atau 'tanpa klaim angka penelitian'",
      "frames": [ ... ],
      "caption": "3–5 baris pendek, tanpa hashtag, tanpa tanda tangan",
      "hashtags": ["3 sampai 5", "tanpa #"],
      "calc": [{"expr": "25000*22", "expect": 550000}],
      "given": [200000]
    }
  ]
}
```

- `evergreen: false` untuk post yang terikat tanggal (hitung mundur, 11.11, "Hari X dari 100", jualan). Post evergreen boleh diulang otomatis setelah 90 hari.
- Tanda tangan "— Nara, pemandu AI" dan hashtag ditambahkan otomatis.

### Tipe frame

Frame pertama selalu `cover` (hook). Frame terakhir selalu `cta`. Carousel 3–10 frame, reel 3–7 frame. `**teks**` = sorotan warna (pakai 1 sorotan per frame).

| type | field | batas karakter |
|---|---|---|
| cover | kicker (opsional), title, sub (opsional) | kicker 40, title 90, sub 140 |
| number | label, eq, value, note (opsional) | label 60, eq 80, value 24, note 160 |
| point | n (opsional), title, body | title 90, body 220 |
| list | title, items (2–6), marks (opsional) | item 90 |
| compare | title, left{h,t}, right{h,t} | h 40, t 150 |
| statement | text, sub (opsional), theme (opsional: cream) | text 160, sub 140 |
| cta | title, body, pill | title 90, body 220, pill 40 |

Kalimat penutup "Satu langkah dulu, ya." otomatis muncul di frame `cta`.

Di reel, frame `number`, `point`, `list`, `compare`, `statement`, `cta` muncul dua tahap (judul dulu, lalu isi). Pakai ini untuk efek kaget: tulis hitungan di `eq`, hasilnya di `value`.

### Aturan angka (dicek mesin, post gagal kalau dilanggar)

- Setiap nominal rupiah di frame dan caption ("Rp25.000", "Rp1,8 juta", "25 ribu") harus muncul sebagai hasil (`expect`) atau angka di dalam `expr` pada `calc`, atau terdaftar di `given`.
- Setiap `calc` dihitung ulang mesin. Pembulatan: `round(1000000/66, -2)`.
- Harga contoh harus wajar untuk kota besar Indonesia tahun 2026 dan disebut sebagai contoh.
- Data lembaga (OJK, BPS, BI) hanya boleh dipakai dengan sumber di `cek_fakta`, dan dicek dulu lewat pencarian web.

### Kata kunci CTA

| Kata | Hasil | Sejak |
|---|---|---|
| BOCOR | DM berisi Kalkulator Kebocoran | Hari 1 |
| TEMPLATE | DM berisi tautan Template 5 Pos (Rp29.000) | 30 Okt |
| SUDAH | tanda tantangan selesai, tanpa DM | Hari 1 |
| KELAS | daftar tunggu kursus | Hari 38 (2 Des), hanya setelah otomasinya dipasang |

## Cek sebelum push

1. `python3 engine/validate.py --semua` → 0 gagal.
2. Baca ulang setiap hook: apakah orang berhenti menggulir dalam 1 detik? Apakah ada angka rupiah atau situasi yang dikenali?
3. Tidak ada janji, tidak ada merek, tidak ada nasihat investasi.
