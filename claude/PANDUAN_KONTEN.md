# Panduan konten Nara (dibaca Claude setiap minggu)

File ini adalah aturan tetap. Rencana tanggal ada di `rencana-100-hari.md`. Data performa ada di `../data/laporan.md`.

## GAYA BARU (berlaku sejak 13 Nov 2026, disetujui pemilik 10 Nov 2026)

Bagian ini mengalahkan aturan lama di bawahnya bila bertentangan.

- **1 reel per hari, slot malam (19.07 WIB).** Slot siang nonaktif mulai 13 Nov 2026 (`"nonaktif_mulai"` di config.json); slot pagi tetap nonaktif. Jangan tulis post siang atau pagi untuk tanggal ≥ 13 Nov.
- **Setiap post wajib punya `"seri"`**, diputar berurutan supaya grid berganti warna: `bedah` (krem) → `tim` (kuning) → `tanggal-tua` (hitam) → `bedah` → …
  - **bedah** — "Bedah Gaji #NN": gaji + kota + situasi → struk pengeluaran → sisa → rencana 5 Pos. CTA: BEDAH. Kicker = "Bedah Gaji #NN" (nomor lanjut dari post bedah terakhir di antrean).
  - **tim** — "Kamu tim mana?": dilema uang yang memancing debat (kirim ortu, kondangan, naik gaji, patungan…). Cover pakai `obj` polling A/B(/C). CTA: "Komen A atau B", tanpa kata kunci.
  - **tanggal-tua** — saldo menipis, cicilan, paylater, hari-hari sebelum gajian. Cover pakai `obj` mutasi rekening. CTA: BOCOR atau TEMPLATE.
- **Cover = hook langsung + benda nyata + Nara besar.** Tanpa sapaan "Hai, aku Nara" (suara juga langsung masuk ke hook). Hook ≤ 70 karakter, satu sorotan `**…**`, berisi angka rupiah atau situasi yang dikenali.
- **Reel 5 frame** (cover, 3 isi, cta). Durasi jadi ±20–30 dtk karena dibacakan.
- **Kalender 100 hari tidak lagi wajib**; pakai hanya sebagai sumber topik. `spine_day` tidak perlu diisi.
- **Topik pengeluaran kecil (kopi, parkir, ongkir, dll.) maksimal 1 dari 7 post.** Prioritas: kos/kontrakan, kirim ortu, paylater/cicilan, kondangan, naik gaji, gaji pertama, bonus akhir tahun, sebelum/sesudah gajian, dana darurat.
- **Jualan (pola S atau CTA TEMPLATE) maksimal 1 dari 5 post.**

### Angka di seri bedah
- Sampai ada kiriman pengikut, semua kasus adalah **simulasi**: tulis "Simulasi" di benda (judul struk/mutasi) dan kalimat "Angka di atas simulasi, bukan data orang sungguhan." di caption (validator memberi peringatan bila caption tidak menyebut simulasi/contoh/kiriman).
- Kasus dari pengikut (lewat DM BEDAH) hanya dipakai setelah pemilik meneruskannya dan pengirim setuju. Samarkan: bulatkan angka ke Rp50 ribu terdekat, tanpa nama, tanpa kantor, kota boleh. Caption: "Kiriman pengikut, dipakai dengan izin, angka dibulatkan."
- Rencana 5 Pos selalu ditulis "panduan, bukan aturan". Masa Depan dikirim di hari gajian, bukan dari sisa.

### Field gaya baru
| field | di mana | isi |
|---|---|---|
| `seri` | post | `bedah` / `tim` / `tanggal-tua` |
| `obj` | frame cover | benda: `{"type":"struk","title","rows":[[label,nilai],"---",…],"total":[label,nilai]}` · `{"type":"mutasi","title","rows":[[label,tanggal,"+/-nilai"],…],"saldo":[label,nilai]}` · `{"type":"poll","options":[2–3 teks ≤24],"ask"}` |
| `struk` | tipe frame | `title`, `head`, `rows` (2–7), `total` (opsional, muncul tahap 2), `note` (opsional) |
| `mutasi` | tipe frame | `title`, `head`, `rows` (2–7), `saldo` |
| `poll` | tipe frame | `title`, `options`, `ask` |
| `ekspresi` | frame mana pun | `kaget` / `tertawa` / `berpikir` / `khawatir` (gambar di `assets/ekspresi/`); cover dan cta wajib diisi, variasikan antar-hari |
| `nara` | frame | `kanan` / `kiri` / `tidak` (default: bedah & tim kanan, tanggal-tua kiri) |

Nilai di `rows`/`total`/`saldo` ditulis tanpa "Rp" (mis. `"-1.500.000"`), tapi tetap dicek mesin terhadap `calc`/`given` seperti nominal lain. Suara membacakan judul + total/saldo saja; baris rincian dibaca mata.

### Kata kunci baru
| Kata | Hasil | Sejak |
|---|---|---|
| BEDAH | DM otomatis meminta gaji bersih, kota, biaya tempat tinggal (tanpa nama/rekening) untuk seri Bedah Gaji | 13 Nov 2026 |

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
| pagi | 07.07 | NONAKTIF sejak 3 Nov 2026 (median reach 10; `"aktif": false` di config.json). Jangan tulis post pagi. | – | – |
| siang | 12.07 | reel 4–5 frame (±15–20 dtk) | jangkauan ke non-follower | A, D, E |
| malam | 19.07 | ikut kalender 100 hari (tulang punggung) | arah besar & peluncuran | sesuai kalender; pola B jadi carousel, lainnya reel |

Slot malam WAJIB mengikuti baris kalender untuk tanggal itu (hook, isi, CTA). Isi `spine_day` dengan nomor harinya. Hari 1 = 26 Okt 2026.

## Campuran per minggu (14 post, sejak 3 Nov 2026)

- 7 tulang punggung dari kalender (malam).
- 7 tambahan di slot siang (reel), titik awal: 2 A · 2 D · 2 E · ≤1 S. Pola B dan C masuk lewat slot malam bila kalender memintanya.
- Suara: reel dibacakan otomatis dari teks frame (judul, angka utama, ajakan). Tulis judul frame sebagai kalimat lisan yang enak didengar; hindari singkatan yang sulit dibaca mesin.

Catatan lama (sebelum 3 Nov): 21 post, 4 A · 3 B · 2 E · 2 D · 1 C · 1 F · ≤1 S.
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

## Persetujuan pemilik (wajib, POJK 6/2026)

Konten keuangan buatan AI wajib diverifikasi manusia sebelum terbit. Mesin konten hanya menulis post; yang menyetujui selalu pemilik.
- Jangan pernah menambah, mengubah, atau menghapus field `disetujui` atau `skip`. Post baru selalu ditulis tanpa field itu (status "menunggu").
- Jangan mengubah post yang sudah ada. Mengubah isi post yang sudah disetujui membatalkan persetujuannya, dan post itu tidak terbit.
- Pemilik membaca halaman tinjau (`<pages_base_url>/tinjau/`) lalu menekan workflow "Setujui post". Post yang belum disetujui tidak terbit, dan workflow Terbit sengaja gagal supaya pemilik mendapat email pengingat.
- Setiap batch mingguan harus sudah ada di repo paling lambat Kamis malam, supaya pemilik punya Jumat–Minggu untuk meninjau.
