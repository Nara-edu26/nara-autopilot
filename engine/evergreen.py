"""Jaring pengaman antrean + pembersih media.

isi   : slot kosong dalam N hari ke depan diisi ulang dengan post lama berperforma baik
        (umur ≥ 90 hari, reach di atas median, bukan pola S, tidak ditandai evergreen=false).
        Jadi akun tetap posting walau Claude belum menulis batch minggu ini.
bersih: hapus folder media yang sudah terbit > 7 hari lalu (Instagram sudah menyimpan salinannya),
        supaya situs GitHub Pages tetap di bawah batas 1 GB.

Pakai:  python engine/evergreen.py isi --hari 3
        python engine/evergreen.py bersih
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, MEDIA, QUEUE, SLOTS, iter_posts, load_config, read_posted, today_wib  # noqa: E402


def isi(hari: int) -> int:
    cfg = load_config()
    gap_days = int(cfg["evergreen"]["boleh_ulang_setelah_hari"])
    today = dt.date.fromisoformat(today_wib())
    posts = {p["id"]: p for p in iter_posts()}
    posted = read_posted()
    posted_ids = {r["post_id"] for r in posted}

    perf = {}
    rp = DATA / "ringkasan_post.csv"
    if rp.exists():
        with rp.open(encoding="utf-8") as fh:
            perf = {r["post_id"]: float(r.get("reach") or 0) for r in csv.DictReader(fh)}
    reaches = sorted(v for v in perf.values() if v > 0)
    cutoff = reaches[int(len(reaches) * cfg["evergreen"]["minimal_persentil_reach"] / 100)] if reaches else 0

    last_used: dict[str, dt.date] = {}
    for r in posted:
        src = r.get("ulang_dari") or r["post_id"]
        d = dt.date.fromisoformat(r["tanggal"])
        last_used[src] = max(last_used.get(src, d), d)

    def candidates(fmt: str):
        out = []
        for pid in posted_ids:
            p = posts.get(pid)
            if not p or p.get("ulang_dari") or p.get("evergreen") is False or p["pattern"] == "S":
                continue
            if p["format"] != fmt or perf.get(pid, 0) < cutoff:
                continue
            if (today - last_used.get(pid, today)).days < gap_days:
                continue
            out.append((perf.get(pid, 0), pid))
        return [pid for _, pid in sorted(out, reverse=True)]

    added = 0
    for k in range(hari):
        date = (today + dt.timedelta(days=k)).isoformat()
        for slot in SLOTS:
            if f"{date}-{slot}" in posts:
                continue
            fmt = cfg["slot"][slot]["format_default"]
            pool = candidates(fmt) or candidates("reel" if fmt == "carousel" else "carousel")
            if not pool:
                print(f"! {date}-{slot} kosong dan belum ada konten evergreen yang memenuhi syarat.")
                continue
            src = posts[pool[0]]
            new = {k2: v for k2, v in src.items() if k2 not in ("id", "date", "skip")}
            new.update({"slot": slot, "ulang_dari": src["id"]})
            path = QUEUE / f"{date}.json"
            day = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"date": date, "posts": []}
            day["posts"].append(new)
            path.write_text(json.dumps(day, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            last_used[src["id"]] = dt.date.fromisoformat(date)
            posts[f"{date}-{slot}"] = {**new, "id": f"{date}-{slot}", "date": date}
            added += 1
            print(f"+ {date}-{slot} diisi ulang dari {src['id']}")
    print(f"{added} slot diisi evergreen.")
    return 0


def bersih(simpan_hari: int = 7) -> int:
    if not MEDIA.exists():
        return 0
    today = dt.date.fromisoformat(today_wib())
    posted = {r["post_id"]: dt.date.fromisoformat(r["tanggal"]) for r in read_posted()}
    removed = 0
    for d in MEDIA.iterdir():
        if not d.is_dir():
            continue
        try:
            when = posted.get(d.name) or dt.date.fromisoformat(d.name[:10])
        except ValueError:
            continue
        if (today - when).days > simpan_hari:
            shutil.rmtree(d)
            removed += 1
    print(f"{removed} folder media lama dihapus.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("aksi", choices=["isi", "bersih"])
    ap.add_argument("--hari", type=int, default=3)
    a = ap.parse_args()
    sys.exit(isi(a.hari) if a.aksi == "isi" else bersih())
