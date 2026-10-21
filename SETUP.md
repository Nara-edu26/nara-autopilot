# Panduan pasang Nara Autopilot

Total ±2 jam, sekali saja. Kerjakan berurutan; tiap langkah ada cara mengecek bahwa langkah itu berhasil. Selesaikan paling lambat Minggu, 25 Oktober 2026, karena post pertama terjadwal Senin, 26 Oktober, pukul 07.07 WIB.

Nama menu di Meta dan GitHub kadang berubah. Kalau tulisan di layar sedikit berbeda, cari menu dengan arti yang sama.

---

## 1. Akun yang dibutuhkan (15 menit)

- **Instagram Nara**: akun baru khusus Nara, diubah ke akun profesional (Pengaturan → Jenis akun dan alat → Beralih ke akun profesional → Kreator). Di Edit profil, nyalakan label profil AI bila tersedia.
- **GitHub**: daftar gratis di github.com.
- **Meta for Developers**: masuk ke developers.facebook.com dengan akun Facebook pribadimu.
- **Lynk**: daftar gratis di lynk.id.

Bio Instagram:
```
Karakter AI yang bantu gajimu cukup sampai gajian berikutnya.
Setiap hari: angka, bukan motivasi.
Komen BOCOR di post mana pun → kalkulator gratis.
```
Foto profil: `assets/profil-nara.png`.

## 2. Unggah repo ke GitHub (15 menit)

1. Di GitHub: **New repository** → nama `nara-autopilot` → **Public** (wajib publik: GitHub Pages dan menit Actions gratis tanpa batas hanya untuk repo publik) → Create.
2. Unggah isi folder `nara-autopilot` (termasuk folder tersembunyi `.github`). Cara termudah di Mac, buka Terminal:
   ```bash
   cd ~/Downloads/nara-autopilot
   git init -b main && git add . && git commit -m "Nara autopilot"
   git remote add origin https://github.com/Nara-edu26/nara-autopilot.git
   git push -u origin main
   ```
   Atau pakai aplikasi GitHub Desktop: File → Add local repository → Publish repository (hilangkan centang "Keep this code private").
3. **Cek:** di halaman repo terlihat folder `.github`, `content`, `docs`, `engine`.

## 3. Isi config.json (5 menit)

Di GitHub, buka `config.json` → ikon pensil. Ganti:
- `Nara-edu26` (3 tempat) dengan username GitHub-mu.
- `email_kontak` boleh dikosongkan: halaman privasi mengarahkan ke DM Instagram Nara.
- `tautan.toko` dan `tautan.template_5_pos` diisi setelah langkah 8 (boleh diubah nanti).

Commit langsung ke `main`.

## 4. Aktifkan GitHub Pages dan izin Actions (5 menit)

1. Settings → Pages → Build and deployment → Source: **GitHub Actions**.
2. Settings → Actions → General → Workflow permissions: **Read and write permissions** → Save.
3. Tab Actions → pilih **Render & situs** → Run workflow. Tunggu ±6 menit sampai centang hijau.
4. **Cek:** buka `https://nara-edu26.github.io/nara-autopilot/`, lalu `/kalkulator/`, lalu `/media/2026-10-26-pagi/01.jpg`. Ketiganya harus terbuka.

## 5. Token Instagram (20 menit)

1. developers.facebook.com → My Apps → **Create app**. Pilih kasus penggunaan yang mengelola konten Instagram (Instagram API dengan login Instagram). Nama aplikasi: `Nara Autopilot`.
2. Di bagian **API setup with Instagram login**: tambahkan akun Instagram Nara, lalu **Generate token**. Login sebagai Nara dan setujui izin: `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_insights`, `instagram_business_manage_comments`.
3. Salin token yang muncul (berlaku 60 hari; sistem memperpanjangnya tiap Senin).
4. Di GitHub: Settings → Secrets and variables → Actions → **New repository secret**:
   - Nama `IG_ACCESS_TOKEN`, isi token tadi.
5. Buat token GitHub untuk perpanjangan otomatis: github.com/settings/personal-access-tokens → **Generate new token** (fine-grained) → Repository access: hanya `nara-autopilot` → Permissions → Secrets: **Read and write** → masa berlaku 1 tahun. Simpan sebagai secret `GH_PAT`.
6. **Cek:** Actions → **Perpanjang token** → Run workflow → hijau.

Token jangan pernah ditempel di file, chat, atau tangkapan layar.

## 6. Uji terbit (15 menit)

1. Actions → **Terbit** → Run workflow → slot `pagi`, tanggal `2026-10-26`, centang **uji** → Run. **Cek:** ringkasan menampilkan caption dan alamat media.
2. Post sungguhan pertama, Minggu 25 Oktober malam: jalankan lagi dengan slot `pagi`, tanggal `2026-10-26`, **tanpa** centang uji. Post carousel "5 tanda gajimu bocor" terbit. Slot pagi tanggal 26 akan otomatis dilewati karena sudah terbit.
3. **Cek visibilitas publik:** buka profil Nara dari browser yang tidak login Instagram, atau dari akun lain. Post harus terlihat dengan keterangan info AI.
4. Kalau post hanya terlihat olehmu: di dashboard aplikasi Meta, ubah mode aplikasi ke **Live**. Isian yang diminta: URL kebijakan privasi `https://nara-edu26.github.io/nara-autopilot/privasi.html`, kategori, dan ikon (pakai `assets/profil-nara.png`).

## 7. DM otomatis gratis lewat Meta Business Suite (20 menit)

1. business.facebook.com → hubungkan akun Instagram Nara. Kalau diminta Halaman Facebook, buat Halaman gratis bernama Nara.
2. Kotak masuk → **Otomatisasi** → buat otomasi **komentar ke pesan** (comment to message) untuk Instagram:
   - Kata kunci: `BOCOR`, `Bocor`, `bocor` (pencocokan bisa peka huruf besar-kecil, jadi masukkan ketiganya).
   - Pesan:
     ```
     Halo, ini Nara, pemandu AI.
     Ini Kalkulator Kebocoran-nya: https://nara-edu26.github.io/nara-autopilot/kalkulator/
     Tulis 3 kebiasaan kecil, harganya, dan berapa kali sebulan. Dua menit selesai.
     Kalau totalnya bikin kaget, itu wajar. Pilih satu yang paling besar dan potong setengahnya dulu bulan ini.
     Satu langkah dulu, ya.
     ```
3. Buat otomasi kedua untuk `TEMPLATE`, `Template`, `template`:
   ```
   Halo, ini Nara, pemandu AI.
   Ini tautan Template 5 Pos: TAUTAN-LYNK
   Spreadsheet yang membagi gajimu ke 5 pos dan menghitung jatah aman per hari sampai gajian. Rp29.000 sekali beli, bisa dibuka di Google Sheets dan Excel.
   Mau coba hitung kebocoranmu dulu? Kalkulatornya gratis: https://nara-edu26.github.io/nara-autopilot/kalkulator/
   Satu langkah dulu, ya.
   ```
4. Buat juga otomasi **kata kunci khusus** di DM untuk kata yang sama, supaya orang yang mengirim DM "BOCOR" juga dapat balasan.
5. **Cek:** dari akun Instagram lain, komen `BOCOR` di post uji. DM harus masuk.
6. Kalau fitur komentar-ke-pesan tidak muncul di akunmu: biarkan otomasi DM kata kunci saja, lalu minta Claude mengganti CTA di antrean menjadi "DM aku kata BOCOR".

## 8. Produk di Lynk (15 menit)

Ikuti `LISTING-LYNK.md` di folder produk (terpisah dari repo ini, jangan diunggah ke GitHub karena repo ini publik). Setelah tayang, tempel tautan produk dan toko ke `config.json`. Situs akan memperbarui tautannya sendiri di render berikutnya.

Link di bio Instagram: `https://nara-edu26.github.io/nara-autopilot/`.

## 9. Mesin konten mingguan (5 menit)

Tugas terjadwal "Mesin konten mingguan Nara" sudah terpasang di akun Claude-mu: setiap Kamis 19.51 WIB, berjalan tanpa menunggu persetujuan. Ia mencari repo bernama `nara-autopilot` sendiri, jadi yang perlu kamu lakukan hanya:

1. Di claude.ai: Settings → Connectors → hubungkan **GitHub**, dan beri akses ke repo `nara-autopilot`.
2. Pastikan langkah 2 (repo sudah di-push) selesai sebelum Kamis malam.

Kalau GitHub belum tersambung saat tugas berjalan, tugas berhenti dan melaporkan apa yang kurang; tidak ada yang rusak. Antrean awal sudah berisi 21 post (26 Okt–1 Nov), dan workflow Terbit tidak menerbitkan apa pun sebelum 26 Oktober.

## 10. Pemeliharaan

| Kapan | Apa | Waktu |
|---|---|---|
| Jumat (opsional) | Lihat `content/queue/` minggu depan; tandai `"skip": true` bila ada yang tidak cocok | 10 menit |
| Tiap minggu | Baca `data/laporan.md` dan `claude/catatan-mingguan.md` | 5 menit |
| Awal bulan | Baca `claude/ide-produk.md`; kalau setuju, minta Claude membuat produknya lalu unggah ke Lynk | 30 menit |
| Kapan saja email "workflow failed" masuk | Buka Actions, baca ringkasan merah. Penyebab paling umum: token mati (ulangi langkah 5) | 10 menit |
| Oktober 2027 | Perbarui `GH_PAT` | 5 menit |

GitHub mengirim email otomatis setiap kali workflow gagal, jadi kamu tidak perlu memantau setiap hari.
