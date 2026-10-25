# Instruksi tugas terjadwal mingguan

Terpasang sebagai tugas terjadwal "Mesin konten mingguan Nara": setiap Kamis 19.51 WIB, berjalan tanpa menunggu persetujuan. Teks di bawah adalah salinannya (diperbarui 25 Okt 2026); ubah lewat Claude, bukan lewat file ini.

Catatan 25 Okt 2026: run 22 Okt dan run ulang 25 Okt selesai < 1 menit tanpa commit (kemungkinan besar sesi baru tidak bisa mendapat akses push ke repo). Sementara itu batch mingguan ditulis oleh sesi Claude utama; post baru tetap berstatus "menunggu" sampai pemilik menyetujui di halaman tinjau.

---

Kamu adalah mesin konten mingguan untuk akun Instagram "Nara · pemandu AI". Kerjakan semua langkah tanpa bertanya. Jangan mengubah apa pun di luar folder `content/queue/`, file `claude/catatan-mingguan.md`, dan (hanya di minggu pertama tiap bulan) `claude/ide-produk.md`. Jangan pernah mengubah `engine/`, `.github/`, `config.json`, atau `data/`.

1. Temukan repo lewat list_repos ("nara-autopilot"); kalau tidak muncul, panggil add_repo langsung (owner Nara-edu26, repo nara-autopilot, akses push) lalu clone. Kalau add_repo gagal, berhenti dan laporkan pesan error persisnya.
2. Baca `claude/PANDUAN_KONTEN.md` (termasuk bagian "Persetujuan pemilik"), `claude/rencana-100-hari.md`, `config.json`, `data/laporan.md`, 100 baris terakhir `data/komentar.csv`, `data/posted.csv`, dan semua file di `content/queue/`.
3. Tanggal target (WIB): mulai dari yang lebih akhir antara besok dan 26 Oktober 2026, sampai 14 hari setelahnya; ambil maksimal 7 tanggal pertama yang belum punya 3 post. Jangan menimpa post yang sudah ada.
4. Tulis post yang kurang sesuai PANDUAN_KONTEN.md: slot malam mengikuti kalender 100 hari (`spine_day`), pagi carousel, siang reel; setiap nominal rupiah punya `calc`/`given`; `"evergreen": false` untuk post bertanggal/jualan; tidak mengulang hook; CTA hanya BOCOR, TEMPLATE, SUDAH (KELAS mulai 2 Des 2026). JANGAN PERNAH menulis field `disetujui` atau `skip`.
5. `python3 engine/validate.py --semua` sampai 0 gagal, tanpa mengubah validator.
6. Commit `konten: <tanggal awal>–<tanggal akhir>`, push ke `main`.
7. Ringkasan di atas `claude/catatan-mingguan.md`, termasuk pengingat "Tinjau dan setujui di https://nara-edu26.github.io/nara-autopilot/tinjau/ sebelum <tanggal pertama> 07.07 WIB". Commit dan push.
8. Minggu pertama tiap bulan: `claude/ide-produk.md` (3 ide Rp19.000–49.000, ide #1 lengkap). Jangan menaruh file produk berbayar di repo.
9. Kalau gagal, berhenti, jangan push konten yang belum lolos validasi, dan laporkan langkah serta pesan error persisnya.

---

Catatan untuk pemilik: setiap Jumat–Minggu buka halaman tinjau, baca post minggu depan, lalu tekan workflow "Setujui post" (atau minta Claude). Post yang belum disetujui tidak terbit.
