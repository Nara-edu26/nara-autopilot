"""Setujui post yang sudah ditinjau pemilik (POJK 6/2026: konten AI diverifikasi manusia sebelum terbit).

Dijalankan lewat workflow "Setujui post" (tombol Run workflow di tab Actions), setelah pemilik membaca
halaman tinjau: <pages_base_url>/tinjau/

- Semua post yang belum terbit, berstatus "menunggu" atau "berubah", dalam 15 hari ke depan → disetujui.
- ID yang ditulis di --lewati → ditandai skip (tidak diterbitkan).
- Persetujuan menyimpan sidik jari isi post. Kalau isi post diubah setelah disetujui,
  statusnya kembali "berubah" dan post tidak akan terbit sampai disetujui lagi.

Pakai:  python engine/setujui.py
        python engine/setujui.py --lewati "2026-10-27-siang, 2026-10-29-pagi"
        python engine/setujui.py --uji      (lihat saja, tidak mengubah file)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (approval_state, content_hash, env, iter_queue, now_wib, post_id, read_posted,  # noqa: E402
                    today_wib)


def summary(msg: str) -> None:
    print(msg)
    path = env("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(msg + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lewati", default="", help="ID post yang TIDAK disetujui, pisahkan koma/spasi")
    ap.add_argument("--hari", type=int, default=15)
    ap.add_argument("--oleh", default="")
    ap.add_argument("--uji", action="store_true")
    a = ap.parse_args()

    today = today_wib()
    end = (dt.date.fromisoformat(today) + dt.timedelta(days=a.hari)).isoformat()
    posted = {r["post_id"] for r in read_posted()}
    lewati = {x.strip() for x in re.split(r"[,\s]+", a.lewati or "") if x.strip()}
    oleh = a.oleh or env("GITHUB_ACTOR") or "pemilik"
    stamp = now_wib().isoformat(timespec="minutes")

    # ID salah ketik di 'lewati' bisa membuat post yang mau ditolak malah ikut disetujui.
    # Jadi kalau ada ID yang tidak dikenal, batalkan semuanya.
    known = {post_id(day["date"], p["slot"]) for _, day in iter_queue(today) for p in day.get("posts", [])}
    unknown = sorted(lewati - known)
    if unknown:
        summary(f"✗ Dibatalkan, tidak ada yang disetujui. ID di kolom 'lewati' tidak ditemukan: {', '.join(unknown)}.\n"
                "Salin persis dari halaman tinjau (contoh: 2026-10-27-siang), lalu jalankan lagi.")
        return 1

    rows = []
    for path, day in iter_queue(today):
        if day["date"] > end:
            continue
        changed = False
        for post in day.get("posts", []):
            pid = post_id(day["date"], post["slot"])
            if pid in posted:
                continue
            if pid in lewati:
                if not post.get("skip"):
                    post["skip"] = True
                    changed = True
                rows.append((pid, "⏭ dilewati"))
                continue
            state = approval_state(post)
            if state == "dilewati":
                rows.append((pid, "⏭ sudah dilewati sebelumnya"))
            elif state == "disetujui":
                rows.append((pid, "✓ sudah disetujui sebelumnya"))
            else:
                post["disetujui"] = {"hash": content_hash(post), "pada": stamp, "oleh": oleh}
                changed = True
                rows.append((pid, "✓ disetujui" + (" (isi berubah, disetujui ulang)" if state == "berubah" else "")))
        if changed and not a.uji:
            path.write_text(json.dumps(day, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary(f"## Persetujuan post ({'UJI, tidak disimpan' if a.uji else 'disimpan'})\n")
    summary(f"Oleh: {oleh} · {stamp} WIB · rentang {today} s.d. {end}\n")
    summary("| Post | Status |\n|---|---|")
    for pid, st in rows:
        summary(f"| {pid} | {st} |")
    if not rows:
        summary("| (tidak ada post yang menunggu) | |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
