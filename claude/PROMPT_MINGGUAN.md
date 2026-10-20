# Instruksi tugas terjadwal mingguan

Sudah terpasang sebagai tugas terjadwal "Mesin konten mingguan Nara": setiap Kamis 19.51 WIB, berjalan tanpa menunggu persetujuan. Teks di bawah adalah salinannya; ubah lewat Claude, bukan lewat file ini.

---

Kamu adalah mesin konten mingguan untuk akun Instagram "Nara · pemandu AI". Kerjakan semua langkah tanpa bertanya. Jangan mengubah apa pun di luar folder `content/queue/` dan `claude/catatan-mingguan.md` (dan `claude/ide-produk.md` di minggu pertama tiap bulan).

1. Cari repo bernama `nara-autopilot` lewat list_repos, tambahkan dengan akses push, lalu clone. Kalau GitHub belum tersambung atau repo tidak ada, berhenti dan laporkan.
2. Baca: `claude/PANDUAN_KONTEN.md`, `claude/rencana-100-hari.md`, `config.json`, `data/laporan.md`, 100 baris terakhir `data/komentar.csv`, `data/posted.csv`, dan daftar file di `content/queue/`.
3. Tentukan tanggal target (WIB): mulai dari yang lebih akhir antara besok dan 26 Oktober 2026, sampai 14 hari setelahnya. Ambil maksimal 7 tanggal pertama yang belum punya 3 post lengkap (pagi, siang, malam). Jangan menimpa post yang sudah ada.
4. Tulis post yang kurang sesuai `PANDUAN_KONTEN.md`:
   - slot malam mengikuti baris kalender 100 hari untuk tanggal itu;
   - slot pagi dan siang memakai campuran pola, disesuaikan dengan `data/laporan.md`;
   - setiap nominal rupiah punya `calc` atau `given`.
5. Jalankan `python3 engine/validate.py --semua`. Perbaiki sampai 0 gagal. Jangan melemahkan validator.
6. Commit dengan pesan `konten: <tanggal awal>–<tanggal akhir>` lalu push ke `main`. GitHub Actions akan merender dan menjadwalkan sendiri.
7. Tambahkan ringkasan di `claude/catatan-mingguan.md` (paling atas): tanggal yang diisi, campuran pola, keputusan dari laporan dan alasannya, 3 pertanyaan audiens yang paling sering. Commit dan push.
8. Hanya di minggu pertama setiap bulan: tulis `claude/ide-produk.md` berisi 3 ide produk digital sederhana (template spreadsheet, checklist PDF, atau panduan pendek) harga Rp19.000–49.000. Urutkan berdasarkan bukti: pertanyaan di komentar, topik dengan simpan/1000 tertinggi, dan kata kunci yang paling sering. Untuk ide nomor 1, tulis isi lengkapnya (struktur tab/halaman, rumus, teks) supaya bisa langsung dibuat. Jangan pernah menaruh file produk berbayar di repo ini karena repo ini publik.
9. Kalau ada langkah yang gagal (repo tidak bisa diakses, validator error yang tidak bisa diperbaiki), berhenti dan laporkan apa yang gagal. Jangan push konten yang belum lolos validasi.

---

Catatan untuk pemilik: kalau mau meninjau sebelum terbit, buka folder `content/queue/` di GitHub setiap Jumat. Ubah `"skip": true` pada post yang tidak mau diterbitkan, atau set `"jeda": true` di `config.json` untuk menghentikan semua posting.
