"""Suara Nara untuk reel (ElevenLabs).

Aktif bila config.json `suara.aktif` true, `suara.voice_id` terisi, dan secret ELEVENLABS_API_KEY tersedia.
Setiap frame reel dibacakan dari teks frame itu sendiri (tidak ada kalimat baru selain sapaan pembuka),
jadi isi suara = isi yang sudah ditinjau pemilik.

File suara disimpan di docs/media/_suara/<sidik>.mp3 (ikut branch `media`), sehingga render ulang
tidak memakai kredit lagi.

Uji teks tanpa memanggil API:  python engine/suara.py --id 2026-11-03-siang
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import MEDIA, env, find_post, load_config  # noqa: E402

CACHE = MEDIA / "_suara"
VERSI_TEKS = 3          # naikkan bila aturan pembacaan berubah, supaya suara dibuat ulang
API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128"

# --- angka ke kata (bahasa Indonesia) ---------------------------------------------------------
_SATUAN = ["nol", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan",
           "sepuluh", "sebelas"]


def terbilang(n: int) -> str:
    if n < 0:
        return "minus " + terbilang(-n)
    if n < 12:
        return _SATUAN[n]
    if n < 20:
        return _SATUAN[n - 10] + " belas"
    if n < 100:
        return (_SATUAN[n // 10] + " puluh" + (" " + _SATUAN[n % 10] if n % 10 else ""))
    if n < 200:
        return "seratus" + (" " + terbilang(n - 100) if n > 100 else "")
    if n < 1000:
        return _SATUAN[n // 100] + " ratus" + (" " + terbilang(n % 100) if n % 100 else "")
    if n < 2000:
        return "seribu" + (" " + terbilang(n - 1000) if n > 1000 else "")
    for besar, nama in ((10 ** 12, "triliun"), (10 ** 9, "miliar"), (10 ** 6, "juta"), (10 ** 3, "ribu")):
        if n >= besar:
            depan, sisa = divmod(n, besar)
            return terbilang(depan) + " " + nama + (" " + terbilang(sisa) if sisa else "")
    return str(n)


def _angka(txt: str) -> str:
    """'280.000' → 'dua ratus delapan puluh ribu'; '4,5' → 'empat koma lima'."""
    bulat, _, koma = txt.partition(",")
    n = int(bulat.replace(".", "")) if bulat else 0
    out = terbilang(n)
    if koma:
        out += " koma " + " ".join(_SATUAN[int(c)] for c in koma if c.isdigit())
    return out


_SUFIKS = {"rb": "ribu", "ribu": "ribu", "jt": "juta", "juta": "juta", "miliar": "miliar", "m": "miliar"}
_NUM = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?"


def bacaan(teks: str) -> str:
    """Ubah teks frame menjadi kalimat yang enak dibacakan mesin suara."""
    t = teks.replace("**", "").replace("\n", " ")
    t = re.sub(r"\b(1[0-2])\.(1[0-2])\b", lambda m: f"{_angka(m[1])} {_angka(m[2])}", t)   # 11.11, 12.12
    t = re.sub(rf"Rp\s?({_NUM})\s*(rb|ribu|jt|juta|miliar)\b",
               lambda m: f"{_angka(m[1])} {_SUFIKS[m[2]]}", t)
    t = re.sub(rf"Rp\s?({_NUM})", lambda m: _angka(m[1]), t)   # cara orang bicara: "35 ribu", tanpa "rupiah"
    t = re.sub(rf"({_NUM})\s?%", lambda m: f"{_angka(m[1])} persen", t)
    t = re.sub(r"\bke-1\b", "pertama", t)
    t = re.sub(rf"\bke-({_NUM})", lambda m: "ke" + _angka(m[1]), t)
    t = re.sub(rf"({_NUM})\s*(rb|jt)\b", lambda m: f"{_angka(m[1])} {_SUFIKS[m[2]]}", t)
    for a, b in ((" × ", " kali "), ("×", " kali "), (" ÷ ", " dibagi "), ("÷", " dibagi "),
                 (" = ", " sama dengan "), (" + ", " ditambah "), (" − ", " dikurangi "),
                 ("/hari", " per hari"), ("/bulan", " per bulan"), ("/minggu", " per minggu"),
                 (" & ", " dan "), ("±", "sekitar "), ("→", ","), ("·", ","), ("“", '"'), ("”", '"')):
        t = t.replace(a, b)
    t = re.sub(r"\btgl\b", "tanggal", t)
    t = re.sub(r"\bvs\b", "lawan", t)
    t = re.sub(_NUM, lambda m: _angka(m[0]), t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _kalimat(*bagian: str | None) -> str:
    out = []
    for b in bagian:
        b = (b or "").strip()
        if not b:
            continue
        if b[-1] not in ".!?…":
            b += "."
        out.append(b)
    return " ".join(out)


_KATA_KUNCI = re.compile(r"\b(BOCOR|TEMPLATE|KELAS|SUDAH)\b|\bkomen\b|\bketik\b", re.I)


def naskah_frame(fr: dict, i: int, sapaan: str, lengkap: bool = False) -> str:
    """Mode ringkas (bawaan): hanya judul/angka utama tiap frame, supaya reel tetap pendek dan
    kredit ElevenLabs Starter (±30 rb karakter/bulan) cukup. Mode lengkap ikut membaca isi."""
    t = fr.get("type")
    isi = (lambda k: fr.get(k)) if lengkap else (lambda k: None)
    if t == "cover":
        s = _kalimat(sapaan if i == 0 else "", fr.get("title"), isi("sub"))
    elif t == "number":
        s = _kalimat(fr.get("label"), fr.get("value"), isi("note"))
    elif t == "point":
        n = fr.get("n")
        s = _kalimat(terbilang(int(n)).capitalize() if str(n).isdigit() else "", fr.get("title"), isi("body"))
    elif t == "list":
        items = fr.get("items") or []
        s = _kalimat(fr.get("title"), *(items if lengkap or len(items) <= 4 else []))
    elif t == "compare":
        l, r = fr.get("left") or {}, fr.get("right") or {}
        s = _kalimat(fr.get("title"), f"{l.get('h', '')}: {l.get('t', '')}", f"{r.get('h', '')}: {r.get('t', '')}")
    elif t == "statement":
        s = _kalimat(fr.get("text"), isi("sub"))
    elif t == "cta":
        pill = fr.get("pill") if _KATA_KUNCI.search(fr.get("pill") or "") else None
        s = _kalimat(fr.get("title"), isi("body"), pill)
    else:
        s = _kalimat(fr.get("title") or fr.get("text"))
    return _kapital(bacaan(s))


def _kapital(t: str) -> str:
    """Huruf besar di awal kalimat (setelah angka diubah jadi kata)."""
    return re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m[1] + m[2].upper(), t)


def naskah(post: dict, cfg: dict) -> list[str]:
    sapaan = cfg.get("suara", {}).get("sapaan", "")
    lengkap = cfg.get("suara", {}).get("mode") == "lengkap"
    lines = [naskah_frame(fr, i, sapaan, lengkap) for i, fr in enumerate(post["frames"])]
    if lines and post["frames"][-1].get("type") == "cta":
        lines[-1] = _kalimat(lines[-1], bacaan(cfg["brand"].get("penutup", "")))
    return lines


# --- pengaturan & sidik ------------------------------------------------------------------------
def aktif(cfg: dict) -> bool:
    s = cfg.get("suara", {})
    return bool(s.get("aktif") and s.get("voice_id") and env("ELEVENLABS_API_KEY"))


def sidik(cfg: dict) -> str:
    """Berubah bila suara dinyalakan/dimatikan atau pengaturannya diganti → reel dirender ulang."""
    s = cfg.get("suara", {})
    raw = json.dumps({"on": aktif(cfg), "v": s.get("voice_id"), "m": s.get("model"), "s": s.get("sapaan"),
                      "x": VERSI_TEKS}, sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def durasi(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(path)], capture_output=True, text=True, check=True).stdout
    return float(out.strip())


class Suara:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        s = cfg.get("suara", {})
        self.on = aktif(cfg)
        self.voice = s.get("voice_id", "")
        self.model = s.get("model") or "eleven_multilingual_v2"
        self.key = env("ELEVENLABS_API_KEY")
        self.gagal = False
        if s.get("aktif") and not self.on:
            print("i Suara Nara belum aktif: voice_id kosong atau ELEVENLABS_API_KEY belum dipasang. "
                  "Reel dibuat dengan musik saja.")

    def _buat(self, teks: str) -> Path:
        name = hashlib.sha1(f"{self.model}|{self.voice}|{teks}".encode()).hexdigest()[:20] + ".mp3"
        path = CACHE / name
        if path.exists() and path.stat().st_size > 1000:
            return path
        body = {"text": teks, "model_id": self.model,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.15,
                                   "use_speaker_boost": True}}
        if "v2_5" in self.model or "flash" in self.model or "turbo" in self.model:
            body["language_code"] = "id"
        r = requests.post(API.format(voice=self.voice), json=body, timeout=120,
                          headers={"xi-api-key": self.key, "accept": "audio/mpeg"})
        if r.status_code != 200:
            raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
        return path

    def frames(self, post: dict) -> list[Path | None]:
        """Satu file suara per frame. [] bila suara mati atau gagal (reel tetap jadi dengan musik)."""
        self.gagal = False
        if not self.on or post.get("format") != "reel":
            return []
        try:
            return [self._buat(t) if t else None for t in naskah(post, self.cfg)]
        except Exception as e:  # noqa: BLE001
            self.gagal = True
            print(f"! {post.get('id')}: suara gagal dibuat ({e}). Reel dibuat tanpa suara dan dicoba lagi besok.")
            return []


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    a = ap.parse_args()
    p = find_post(a.id)
    if not p:
        sys.exit(f"Post {a.id} tidak ditemukan")
    cfg = load_config()
    lines = naskah(p, cfg)
    for i, line in enumerate(lines):
        print(f"[{i}] {line}")
    print(f"\n{sum(len(x) for x in lines)} karakter")
