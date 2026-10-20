"""Fungsi bersama untuk semua skrip Nara Autopilot."""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "content" / "queue"
DATA = ROOT / "data"
MEDIA = ROOT / "docs" / "media"   # di CI, folder ini diisi dari branch `media`
WIB = dt.timezone(dt.timedelta(hours=7))
SLOTS = ("pagi", "siang", "malam")

POSTED_CSV = DATA / "posted.csv"
POSTED_FIELDS = ["post_id", "tanggal", "slot", "format", "pola", "media_id", "permalink",
                 "waktu_terbit", "label_ai", "ulang_dari"]


def load_config() -> dict:
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def now_wib() -> dt.datetime:
    return dt.datetime.now(WIB)


def today_wib() -> str:
    return now_wib().date().isoformat()


def post_id(date: str, slot: str) -> str:
    return f"{date}-{slot}"


def iter_queue(min_date: str | None = None):
    """Hasilkan (path, day_dict) untuk semua file antrean, terurut tanggal."""
    for p in sorted(QUEUE.glob("*.json")):
        day = json.loads(p.read_text(encoding="utf-8"))
        if min_date and day.get("date", "") < min_date:
            continue
        yield p, day


def iter_posts(min_date: str | None = None):
    """Hasilkan dict post lengkap dengan id/date terisi."""
    for _, day in iter_queue(min_date):
        for post in day.get("posts", []):
            post = dict(post)
            post["date"] = day["date"]
            post["id"] = post_id(day["date"], post["slot"])
            yield post


def find_post(pid: str) -> dict | None:
    for post in iter_posts():
        if post["id"] == pid:
            return post
    return None


def build_caption(post: dict, cfg: dict) -> str:
    tags = " ".join("#" + h.lstrip("#") for h in post.get("hashtags", []))
    parts = [post["caption"].strip(), "", cfg["brand"]["signature_caption"]]
    if tags:
        parts.append(tags)
    return "\n".join(parts)


def read_posted() -> list[dict]:
    if not POSTED_CSV.exists():
        return []
    with POSTED_CSV.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def append_posted(row: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    new = not POSTED_CSV.exists()
    with POSTED_CSV.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=POSTED_FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in POSTED_FIELDS})


def media_dir(pid: str) -> Path:
    return MEDIA / pid


def media_files(post: dict) -> list[str]:
    """Nama file media yang harus ada untuk post ini (relatif terhadap media/<id>/)."""
    if post["format"] == "carousel":
        return [f"{i + 1:02d}.jpg" for i in range(len(post["frames"]))]
    return ["reel.mp4", "cover.jpg"]


def env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    return v if v not in (None, "") else default
