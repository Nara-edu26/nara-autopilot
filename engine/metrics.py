"""Ambil angka performa dari Instagram setiap hari dan simpan ke data/.

data/metrics.csv   satu baris per post per hari (snapshot)
data/akun.csv      follower & jumlah post per hari
data/komentar.csv  teks komentar (tanpa username) untuk bahan ide konten & produk
"""
from __future__ import annotations

import csv
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, env, load_config, now_wib, read_posted, today_wib  # noqa: E402
from ig import IG, IGError  # noqa: E402

M_FIELDS = ["snapshot", "post_id", "media_id", "format", "pola", "slot", "umur_jam",
            "reach", "views", "likes", "comments", "shares", "saved", "total_interactions", "avg_watch_ms"]
FULL = {"carousel": ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions"],
        "reel": ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions", "ig_reels_avg_watch_time"]}
MINI = ["reach", "likes", "comments", "shares", "saved"]


def append(path: Path, fields: list[str], rows: list[dict]) -> None:
    if not rows:
        return
    new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def main() -> int:
    token = env("IG_ACCESS_TOKEN")
    if not token:
        print("IG_ACCESS_TOKEN belum diisi; metrik dilewati.")
        return 0
    cfg = load_config()
    api = IG(token, cfg["instagram"]["api_host"], cfg["instagram"].get("api_versi", ""))
    DATA.mkdir(exist_ok=True)
    snap = today_wib()
    now = now_wib()

    try:
        me = api.me()
    except IGError as e:
        print(f"✗ Tidak bisa membaca akun: {e}")
        return 1
    append(DATA / "akun.csv", ["tanggal", "followers", "media"],
           [{"tanggal": snap, "followers": me.get("followers_count", ""), "media": me.get("media_count", "")}])

    rows, kom = [], []
    seen_kom = set()
    kpath = DATA / "komentar.csv"
    if kpath.exists():
        with kpath.open(encoding="utf-8") as fh:
            seen_kom = {(r["post_id"], r["waktu"]) for r in csv.DictReader(fh)}
    allow_comments = True
    for p in read_posted():
        if not p.get("media_id"):
            continue
        try:
            t = dt.datetime.fromisoformat(p["waktu_terbit"])
        except ValueError:
            continue
        age_h = (now - t).total_seconds() / 3600
        if age_h > 24 * 45:
            continue
        fmt = p["format"]
        try:
            ins = api.insights(p["media_id"], FULL[fmt])
        except IGError:
            try:
                ins = api.insights(p["media_id"], MINI)
            except IGError as e:
                print(f"! {p['post_id']}: insight tidak tersedia ({e.message})")
                continue
        rows.append({"snapshot": snap, "post_id": p["post_id"], "media_id": p["media_id"], "format": fmt,
                     "pola": p["pola"], "slot": p["slot"], "umur_jam": round(age_h),
                     "avg_watch_ms": ins.pop("ig_reels_avg_watch_time", ""), **ins})
        if allow_comments and age_h <= 24 * 8:
            try:
                for c in api.comments(p["media_id"]):
                    key = (p["post_id"], c.get("timestamp", ""))
                    if key in seen_kom:
                        continue
                    seen_kom.add(key)
                    kom.append({"post_id": p["post_id"], "waktu": c.get("timestamp", ""),
                                "teks": (c.get("text") or "").replace("\n", " ")[:300]})
            except IGError as e:
                print(f"! komentar dilewati (izin instagram_business_manage_comments?): {e.message}")
                allow_comments = False

    append(DATA / "metrics.csv", M_FIELDS, rows)
    append(kpath, ["post_id", "waktu", "teks"], kom)
    print(f"✓ {len(rows)} post diperbarui, {len(kom)} komentar baru, follower {me.get('followers_count')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
