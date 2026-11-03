"""Daftar suara ElevenLabs dan contoh suara Nara (dijalankan dari GitHub Actions, kunci tidak keluar dari secret).

daftar : tulis suara/daftar.json berisi model yang mendukung bahasa Indonesia, suara di akun,
         dan suara perempuan berbahasa Indonesia dari Voice Library.
contoh : buat suara/<nama>.mp3 untuk tiap voice_id yang diberikan, membacakan naskah reel sungguhan.

Pakai:  python engine/suara_contoh.py daftar
        python engine/suara_contoh.py contoh --voice id1,id2,id3 [--model eleven_multilingual_v2] [--post 2026-11-03-siang]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, find_post, load_config  # noqa: E402
import suara  # noqa: E402

API = "https://api.elevenlabs.io"
OUT = ROOT / "suara"


def hdr() -> dict:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("ELEVENLABS_API_KEY tidak ada.")
    return {"xi-api-key": key}


def get(path: str, **params) -> dict:
    r = requests.get(API + path, headers=hdr(), params=params, timeout=60)
    if r.status_code != 200:
        return {"_error": r.status_code, "_body": r.text[:400]}
    return r.json()


def daftar() -> int:
    OUT.mkdir(exist_ok=True)
    out: dict = {}
    models = get("/v1/models")
    if isinstance(models, list):
        out["model_id"] = [
            {"model_id": m.get("model_id"), "name": m.get("name"),
             "indonesia": any((l.get("language_id") or "").lower() in ("id", "ind") for l in m.get("languages", []))}
            for m in models if m.get("can_do_text_to_speech")]
    else:
        out["model_id"] = models
    mine = get("/v1/voices")
    out["suara_akun"] = [{"voice_id": v["voice_id"], "name": v["name"], "category": v.get("category"),
                          "labels": v.get("labels")} for v in mine.get("voices", [])] if "voices" in mine else mine
    lib = []
    cari = os.environ.get("CARI", "").strip()
    queries = [dict(sort="trending"), dict(sort="cloned_by_count")]
    if cari:
        queries = [dict(search=q.strip()) for q in cari.split(",") if q.strip()]
    for q in queries:
        res = get("/v1/shared-voices", language="id", gender="female", page_size=50, **q)
        for v in res.get("voices", []):
            if any(x["voice_id"] == v["voice_id"] for x in lib):
                continue
            lib.append({k: v.get(k) for k in ("voice_id", "public_owner_id", "name", "accent", "age", "descriptive",
                                              "use_case", "category", "language", "locale", "description",
                                              "cloned_by_count", "usage_character_count_1y", "free_users_allowed",
                                              "preview_url")})
        if "_error" in res:
            out.setdefault("galat_library", []).append(res)
    out["library_id_perempuan"] = lib
    (OUT / "daftar.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"model TTS: {len(out['model_id']) if isinstance(out['model_id'], list) else out['model_id']}")
    print(f"suara akun: {len(out['suara_akun']) if isinstance(out['suara_akun'], list) else out['suara_akun']}")
    print(f"library (id, perempuan): {len(lib)}")
    for v in lib[:80]:
        print(f"- {v['name']} | {v['voice_id']} | {v.get('accent')} | {v.get('locale')} | {v.get('age')} | "
              f"{v.get('descriptive')} | {v.get('use_case')} | dipakai {v.get('cloned_by_count')} | "
              f"{(v.get('description') or '')[:220].replace(chr(10), ' ')}")
    return 0


def contoh(voices: list[str], model: str, pid: str) -> int:
    OUT.mkdir(exist_ok=True)
    cfg = load_config()
    post = find_post(pid)
    if not post:
        sys.exit(f"post {pid} tidak ditemukan")
    teks = " ".join(suara.naskah(post, cfg))
    (OUT / "naskah.txt").write_text(teks)
    gagal = 0
    for vid in voices:
        vid = vid.strip()
        if not vid:
            continue
        m = model
        if "@" in vid:
            vid, m = vid.split("@", 1)
        body = {"text": teks, "model_id": m,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.15, "use_speaker_boost": True}}
        if m != "eleven_multilingual_v2":
            body["language_code"] = "id"
        r = requests.post(f"{API}/v1/text-to-speech/{vid}?output_format=mp3_44100_128", json=body,
                          headers={**hdr(), "accept": "audio/mpeg"}, timeout=120)
        nama = re.sub(r"[^A-Za-z0-9_-]+", "-", f"{vid}_{m}")
        if r.status_code == 200:
            (OUT / f"{nama}.mp3").write_bytes(r.content)
            print(f"✓ {vid}: {len(r.content)} byte")
        else:
            gagal += 1
            print(f"✗ {vid}: {r.status_code} {r.text[:300]}")
    print(f"naskah ({len(teks)} karakter): {teks}")
    return 1 if gagal and gagal == len([v for v in voices if v.strip()]) else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("aksi", choices=["daftar", "contoh"])
    ap.add_argument("--voice", default="")
    ap.add_argument("--model", default="eleven_multilingual_v2")
    ap.add_argument("--post", default="2026-11-03-siang")
    a = ap.parse_args()
    sys.exit(daftar() if a.aksi == "daftar" else contoh(a.voice.split(","), a.model, a.post))
