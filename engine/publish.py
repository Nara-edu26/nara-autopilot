"""Terbitkan satu post ke Instagram sesuai slot.

Dipanggil GitHub Actions 3x sehari. Slot ditentukan dari jadwal cron yang memicu,
atau dari argumen --slot. Tanpa IG_ACCESS_TOKEN, berjalan sebagai uji kering (tidak menerbitkan).

Pakai:  python engine/publish.py --slot pagi
        python engine/publish.py --slot malam --tanggal 2026-10-26 --uji
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (SLOTS, append_posted, approval_state, build_caption, env, find_post, iter_posts,  # noqa: E402
                    load_config, media_files, now_wib, post_id, read_posted, repo_slug, today_wib)
from ig import IG, IGError  # noqa: E402
from validate import validate_post  # noqa: E402

CRON_SLOT = {"7 0 * * *": "pagi", "7 5 * * *": "siang", "7 12 * * *": "malam"}


def summary(msg: str) -> None:
    print(msg)
    path = env("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(msg + "\n")


def wait_public(urls: list[str], tries: int = 8) -> None:
    for u in urls:
        for i in range(tries):
            try:
                r = requests.head(u, timeout=20, allow_redirects=True)
                if r.status_code == 200:
                    break
            except requests.RequestException:
                pass
            if i == tries - 1:
                raise RuntimeError(f"Media belum bisa diakses publik: {u}\n"
                                   "Cek workflow 'Render & situs' sudah sukses dan GitHub Pages aktif.")
            time.sleep(30)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", choices=SLOTS)
    ap.add_argument("--tanggal", default=None)
    ap.add_argument("--uji", action="store_true", help="uji kering, tidak menerbitkan")
    a = ap.parse_args()

    cfg = load_config()
    slot = a.slot or CRON_SLOT.get(env("CRON_SCHEDULE", ""), "")
    if not slot:
        summary("Slot tidak diketahui. Pakai --slot pagi|siang|malam.")
        return 2
    if cfg.get("jeda"):
        summary("⏸ config.json: jeda=true. Tidak ada yang diterbitkan.")
        return 0
    if not a.tanggal:
        # Cron GitHub bisa telat. Kalau jadwal malam baru jalan lewat tengah malam,
        # post tetap milik tanggal kemarin, bukan tanggal hari ini.
        now = now_wib()
        jam_slot = int(cfg["slot"][slot]["jam_wib"][:2])
        tgl = now.date() - dt.timedelta(days=1) if now.hour < jam_slot - 1 else now.date()
        a.tanggal = tgl.isoformat()

    if a.tanggal < cfg.get("hari_1", "0000-00-00") and not a.uji:
        summary(f"⏳ Belum mulai: posting otomatis dimulai {cfg['hari_1']}. Tidak ada yang diterbitkan.")
        return 0

    pid = post_id(a.tanggal, slot)
    if any(r["post_id"] == pid for r in read_posted()):
        summary(f"✓ {pid} sudah terbit sebelumnya. Tidak ada yang dilakukan.")
        return 0

    post = find_post(pid)
    if post and post.get("skip"):
        summary(f"⏭ {pid} dilewati pemilik saat tinjauan. Tidak ada yang diterbitkan.")
        return 0
    if not post:
        summary(f"✗ Antrean kosong untuk {pid}. Isi content/queue/{a.tanggal}.json "
                "atau jalankan workflow 'Render & situs' supaya slot kosong diisi konten evergreen.")
        return 1
    errs, _ = validate_post(post, list(iter_posts()))
    if errs:
        summary(f"✗ {pid} gagal validasi, tidak diterbitkan:\n- " + "\n- ".join(errs))
        return 1

    # Tinjauan manusia wajib sebelum terbit (POJK 6/2026). Gagal di sini sengaja membuat workflow merah,
    # supaya GitHub mengirim email pengingat ke pemilik.
    state = approval_state(post)
    if cfg.get("wajib_tinjau", True) and state != "disetujui":
        why = ("isinya berubah setelah disetujui" if state == "berubah" else "belum disetujui pemilik")
        base_url = cfg["pages_base_url"].rstrip("/")
        msg = (f"✋ {pid} TIDAK diterbitkan: {why}.\n\n"
               f"1. Baca post-nya di {base_url}/tinjau/\n"
               f"2. Setujui di https://github.com/{repo_slug(cfg)}/actions/workflows/setujui.yml "
               "(tombol Run workflow), atau minta Claude menyetujuinya untukmu.\n"
               "Setelah disetujui, slot berikutnya terbit normal. Slot yang sudah lewat bisa diterbitkan "
               "dengan tombol Re-run jobs di halaman run yang gagal ini (di hari yang sama).")
        if a.uji:
            summary("(uji kering) " + msg)
        else:
            summary(msg)
            return 1

    base = cfg["pages_base_url"].rstrip("/")
    files = media_files(post)
    urls = {f: f"{base}/media/{pid}/{f}" for f in files}
    caption = build_caption(post, cfg)
    token = env("IG_ACCESS_TOKEN")
    uji = a.uji or not token

    if uji:
        summary(f"🧪 UJI KERING {pid} ({post['format']}, pola {post['pattern']})\n\nCaption:\n{caption}\n\nMedia:\n"
                + "\n".join(urls.values()))
        return 0

    wait_public(list(urls.values()))
    api = IG(token, cfg["instagram"]["api_host"], cfg["instagram"].get("api_versi", ""))
    label = bool(cfg.get("label_ai", True))
    try:
        me = api.me()
        ig_id = me.get("user_id") or me["id"]

        def make_container(with_label: bool) -> str:
            ai = True if with_label else None
            if post["format"] == "carousel":
                kids = [api.create(ig_id, image_url=urls[f], is_carousel_item=True) for f in files]
                for k in kids:
                    api.wait(k, timeout=180)
                return api.create(ig_id, media_type="CAROUSEL", children=",".join(kids),
                                  caption=caption, is_ai_generated=ai)
            return api.create(ig_id, media_type="REELS", video_url=urls["reel.mp4"], cover_url=urls["cover.jpg"],
                              caption=caption, share_to_feed=cfg["instagram"].get("share_reel_ke_feed", True),
                              is_ai_generated=ai)

        try:
            cid = make_container(label)
        except IGError as e:
            if label and "is_ai_generated" in e.message:
                summary("! Parameter label AI ditolak API; diterbitkan tanpa label. Bio & caption tetap menyebut AI.")
                label = False
                cid = make_container(False)
            else:
                raise
        api.wait(cid, timeout=900)
        media_id = api.publish(ig_id, cid)
        info = api.media_info(media_id)
    except IGError as e:
        hint = ("\nToken kedaluwarsa/dicabut. Buat token baru (SETUP.md langkah 4) dan perbarui secret IG_ACCESS_TOKEN."
                if e.token_mati else "")
        summary(f"✗ Gagal menerbitkan {pid}: {e}{hint}")
        return 1

    append_posted({
        "post_id": pid, "tanggal": a.tanggal, "slot": slot, "format": post["format"], "pola": post["pattern"],
        "media_id": media_id, "permalink": info.get("permalink", ""), "waktu_terbit": now_wib().isoformat(timespec="minutes"),
        "label_ai": str(label).lower(), "ulang_dari": post.get("ulang_dari", ""),
    })
    summary(f"✓ Terbit {pid}: {info.get('permalink', media_id)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
