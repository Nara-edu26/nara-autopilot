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


_URUT = ["", "Pertama", "Kedua", "Ketiga", "Keempat", "Kelima", "Keenam", "Ketujuh", "Kedelapan", "Kesembilan"]


def _gabung_daftar(items: list[str]) -> str:
    items = [i.strip().rstrip(".") for i in items if i and i.strip()]
    items = items[:1] + [i[:1].lower() + i[1:] if not i[:2].isupper() else i for i in items[1:]]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + ", sama " + items[-1]


def naskah_frame_alami(fr: dict, i: int, sapaan: str, tag: bool = False) -> str:
    """Seperti naskah_frame, tetapi disambung seperti orang bicara (koma, jeda '…', urutan 'Pertama').
    Tidak menambah klaim baru: kata yang dibaca tetap dari teks frame. tag=True menambah tag emosi
    ElevenLabs v3/v4 (mis. [warmly]) yang tidak ikut diucapkan."""
    t = fr.get("type")
    if t == "cover":
        s = _kalimat(sapaan if i == 0 else "", fr.get("title"))
    elif t == "number":
        lab, val = (fr.get("label") or "").strip().rstrip(".:"), (fr.get("value") or "").strip()
        s = _kalimat(f"{lab}… {val}" if lab and val else (lab or val))
    elif t == "point":
        n = fr.get("n")
        urut = _URUT[int(n)] if str(n).isdigit() and 0 < int(n) < len(_URUT) else ""
        title = (fr.get("title") or "").strip()
        s = _kalimat(f"{urut}, {title[:1].lower() + title[1:]}" if urut else title)
    elif t == "list":
        items = fr.get("items") or []
        s = _kalimat(fr.get("title"), _gabung_daftar(items) if len(items) <= 4 else "")
    elif t == "compare":
        l, r = fr.get("left") or {}, fr.get("right") or {}
        s = _kalimat(fr.get("title"), f"{l.get('h', '')}, {l.get('t', '')}; {r.get('h', '')}, {r.get('t', '')}")
    elif t == "statement":
        s = _kalimat(fr.get("text"))
    elif t == "cta":
        pill = fr.get("pill") if _KATA_KUNCI.search(fr.get("pill") or "") else None
        s = _kalimat(fr.get("title"), pill)
    else:
        s = _kalimat(fr.get("title") or fr.get("text"))
    s = re.sub(r"\b([A-Z]{3,})\b", lambda m: '"' + m[1].lower() + '"', s)   # Komen BOCOR → Komen "bocor"
    s = _kapital(bacaan(s))
    if tag:
        if i == 0:
            s = "[warmly] " + s
        elif t == "cta":
            s = "[cheerfully] " + s
        elif s.rstrip().endswith("?"):
            s = "[curious] " + s
    return s


def _kapital(t: str) -> str:
    """Huruf besar di awal kalimat (setelah angka diubah jadi kata)."""
    return re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m[1] + m[2].upper(), t)


def naskah(post: dict, cfg: dict, gaya: str | None = None) -> list[str]:
    """gaya: None/"ringkas" (bawaan), "lengkap", "alami", "alami_tag" (alami + tag emosi v3/v4)."""
    s = cfg.get("suara", {})
    sapaan = s.get("sapaan", "")
    gaya = gaya or s.get("mode") or "ringkas"
    if gaya.startswith("alami"):
        lines = [naskah_frame_alami(fr, i, sapaan, gaya == "alami_tag") for i, fr in enumerate(post["frames"])]
    else:
        lines = [naskah_frame(fr, i, sapaan, gaya == "lengkap") for i, fr in enumerate(post["frames"])]
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
                      "x": VERSI_TEKS, "g": s.get("mode"), "vs": s.get("voice_settings"),
                      "1": bool(s.get("sekali_jalan"))}, sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def penguat_db(path: Path, target: float = -17.0) -> float:
    """Gain (dB) supaya rata-rata kekerasan suara ±target dBFS. Suara tiap pengisi suara berbeda kerasnya.
    Potongan dari pembacaan sekali jalan (<sidik>-f<n>.mp3) sudah disamakan saat dipotong → 0."""
    if re.search(r"-f\d+\.mp3$", Path(path).name):
        return 0.0
    err = subprocess.run(["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    for line in err.splitlines():
        if "mean_volume:" in line:
            mean = float(line.split("mean_volume:")[1].split("dB")[0])
            return max(-6.0, min(15.0, target - mean))
    return 0.0


def durasi(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(path)], capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def _jeda_terdekat(path: Path, perkiraan: float, kiri: float = 0.6, kanan: float = 0.3) -> float:
    """Waktu alignment ElevenLabs bisa meleset 0,1–0,3 dtk; potong di titik paling sunyi di sekitarnya
    (tengah bagian sunyi), supaya tidak memotong awal/akhir kata."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    hop, win = 160, 480
    a, b = max(0, int((perkiraan - kiri) * 100)), int((perkiraan + kanan) * 100)
    e = np.array([20 * np.log10(np.sqrt(np.mean(x[i * hop:i * hop + win] ** 2)) + 1e-9)
                  for i in range(a, min(b, (len(x) - win) // hop))])
    if not len(e):
        return perkiraan
    k = int(np.argmin(e))
    lo = hi = k
    while lo > 0 and e[lo - 1] < e[k] + 4:
        lo -= 1
    while hi < len(e) - 1 and e[hi + 1] < e[k] + 4:
        hi += 1
    return (a + (lo + hi) / 2) * hop / 16000 + win / 2 / 16000


BAWAAN = {"stability": 0.5, "similarity_boost": 0.75, "style": 0.15, "use_speaker_boost": True}


class Suara:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        s = cfg.get("suara", {})
        self.on = aktif(cfg)
        self.voice = s.get("voice_id", "")
        self.model = s.get("model") or "eleven_multilingual_v2"
        self.vs = s.get("voice_settings") or BAWAAN
        self.sekali = bool(s.get("sekali_jalan"))
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
        body = {"text": teks, "model_id": self.model, "voice_settings": self.vs}
        if self.model != "eleven_multilingual_v2":
            body["language_code"] = "id"
        r = requests.post(API.format(voice=self.voice), json=body, timeout=120,
                          headers={"xi-api-key": self.key, "accept": "audio/mpeg"})
        if r.status_code != 200:
            raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
        return path

    def _sekali(self, lines: list[str]) -> list[Path | None]:
        """Seluruh naskah dibacakan sekali jalan (intonasi menyambung seperti orang bicara), lalu dipotong
        per frame di tengah jeda antar-frame memakai waktu per huruf dari ElevenLabs."""
        isi = [(i, t) for i, t in enumerate(lines) if t]
        teks = " ".join(t for _, t in isi)
        key = hashlib.sha1(f"{self.model}|{self.voice}|{json.dumps(self.vs, sort_keys=True)}|{teks}"
                           .encode()).hexdigest()[:20]
        full, meta = CACHE / f"{key}.mp3", CACHE / f"{key}.json"
        segs = {i: CACHE / f"{key}-f{i}.mp3" for i, _ in isi}
        out: list[Path | None] = [segs.get(i) for i in range(len(lines))]
        if all(p.exists() and p.stat().st_size > 500 for p in segs.values()):
            return out
        if not (full.exists() and meta.exists()):
            body = {"text": teks, "model_id": self.model, "voice_settings": self.vs}
            if self.model != "eleven_multilingual_v2":
                body["language_code"] = "id"
            r = requests.post(API.replace("?", "/with-timestamps?").format(voice=self.voice), json=body, timeout=180,
                              headers={"xi-api-key": self.key, "accept": "application/json"})
            if r.status_code != 200:
                raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
            d = r.json()
            import base64
            CACHE.mkdir(parents=True, exist_ok=True)
            full.write_bytes(base64.b64decode(d["audio_base64"]))
            meta.write_text(json.dumps({"teks": teks, "alignment": d["alignment"]}, ensure_ascii=False))
        al = json.loads(meta.read_text())["alignment"]
        st, en = al["character_start_times_seconds"], al["character_end_times_seconds"]
        total = durasi(full)
        # batas potong: tengah jeda antara huruf terakhir frame sebelumnya dan huruf ucapan pertama frame ini
        batas, off, akhir_prev = [], 0, None
        for i, t in isi:
            a = off
            if t.startswith("["):                    # lewati tag emosi, mis. "[warmly] "
                a = off + t.index("]") + 1
            while a < off + len(t) - 1 and teks[a] == " ":
                a += 1
            batas.append(0.0 if akhir_prev is None else (akhir_prev + st[a]) / 2)
            akhir_prev = en[off + len(t) - 1]
            off += len(t) + 1
        batas = [0.0] + [_jeda_terdekat(full, b) for b in batas[1:]]
        batas.append(total)
        gain = penguat_db(full)
        for (i, _), b0, b1 in zip(isi, batas, batas[1:]):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(full), "-af",
                            f"atrim=start={b0:.3f}:end={b1:.3f},asetpts=PTS-STARTPTS,volume={gain:.1f}dB,"
                            f"afade=t=in:d=0.02,afade=t=out:st={max(0.0, b1 - b0 - 0.04):.3f}:d=0.04",
                            "-c:a", "libmp3lame", "-b:a", "128k", str(segs[i])], check=True)
        return out

    def frames(self, post: dict) -> list[Path | None]:
        """Satu file suara per frame. [] bila suara mati atau gagal (reel tetap jadi dengan musik)."""
        self.gagal = False
        if not self.on or post.get("format") != "reel":
            return []
        try:
            if self.sekali:
                return self._sekali(naskah(post, self.cfg))
            return [self._buat(t) if t else None for t in naskah(post, self.cfg)]
        except Exception as e:  # noqa: BLE001
            self.gagal = True
            print(f"! {post.get('id')}: suara gagal dibuat ({e}). Reel dibuat tanpa suara dan dicoba lagi besok.")
            return []


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--pembuka", action="store_true", help="cetak file suara frame pembuka (membuatnya bila perlu)")
    a = ap.parse_args()
    p = find_post(a.id)
    if not p:
        sys.exit(f"Post {a.id} tidak ditemukan")
    cfg = load_config()
    if a.pembuka:
        v = Suara(cfg).frames(p)
        if not v or not v[0]:
            sys.exit("suara pembuka tidak bisa dibuat")
        print(v[0])
        sys.exit(0)
    lines = naskah(p, cfg)
    for i, line in enumerate(lines):
        print(f"[{i}] {line}")
    print(f"\n{sum(len(x) for x in lines)} karakter")
