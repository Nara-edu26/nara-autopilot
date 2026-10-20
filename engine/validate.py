"""Penjaga mutu otomatis. Post yang gagal di sini TIDAK dirender dan TIDAK diterbitkan.

Yang dicek:
  1. Struktur: format, slot, jumlah frame, panjang teks, frame pertama/terakhir.
  2. Angka: setiap nominal rupiah di teks harus punya hitungan di `calc` (atau terdaftar di `given`),
     dan setiap hitungan di `calc` dihitung ulang di sini. Ini mencegah kasus "kunci jawaban salah"
     yang merusak kepercayaan akun AI.
  3. Bahasa terlarang: janji untung, rekomendasi produk investasi, merek nyata.
  4. Duplikat: judul sampul terlalu mirip dengan post lain.

Pakai:  python engine/validate.py            (cek semua post mulai hari ini)
        python engine/validate.py --semua    (cek seluruh antrean)
"""
from __future__ import annotations

import ast
import operator
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SLOTS, iter_posts, today_wib  # noqa: E402

FORMATS = {"carousel": (3, 10), "reel": (3, 7)}
POLA = set("ABCDEFS")
FRAME_TYPES = {"cover", "number", "point", "list", "compare", "statement", "cta"}
MAX_LEN = {"title": 90, "sub": 140, "kicker": 40, "label": 60, "eq": 80, "value": 24, "note": 160,
           "body": 220, "text": 160, "pill": 40, "item": 90, "h": 40, "t": 150}

BLOKIR = [
    r"pasti untung", r"dijamin", r"jaminan untung", r"cuan pasti", r"auto kaya", r"kaya mendadak",
    r"bebas risiko", r"tanpa risiko", r"return \d+ ?%", r"profit \d+ ?%",
    r"beli saham", r"saham (apa|ini|terbaik)", r"rekomendasi (saham|reksa ?dana|kripto|crypto)",
    r"\bkripto\b", r"\bcrypto\b", r"bitcoin", r"\bforex\b", r"\btrading\b", r"\bslot\b", r"judi",
    r"reksa ?dana terbaik", r"investasi terbaik", r"passive income",
    r"aku (manusia|orang sungguhan)",
]
MEREK = [r"\bgopay\b", r"\bovo\b", r"\bdana\b(?! darurat| pensiun)", r"\bshopee", r"tokopedia", r"\bbca\b",
         r"\bbri\b", r"mandiri", r"\bbni\b", r"kredivo", r"akulaku", r"spaylater", r"netflix", r"spotify",
         r"starbucks", r"grab", r"gojek"]

MULT = {"ribu": 1_000, "rb": 1_000, "k": 1_000, "juta": 1_000_000, "jt": 1_000_000, "miliar": 1_000_000_000}
RE_RP = re.compile(r"Rp\s?(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?\s*(ribu|rb|juta|jt|miliar)?\b", re.I)
RE_WORD = re.compile(r"(?<![\d.,])(\d+)(?:,(\d+))?\s*(ribu|juta)\b", re.I)


def money_values(text: str) -> list[tuple[str, float]]:
    out = []
    spans = []
    for m in RE_RP.finditer(text):
        whole = int(m.group(1).replace(".", ""))
        dec = float("0." + m.group(2)) if m.group(2) else 0.0
        mult = MULT.get((m.group(3) or "").lower(), 1)
        out.append((m.group(0), (whole + dec) * mult))
        spans.append(m.span())
    for m in RE_WORD.finditer(text):
        if any(a <= m.start() < b for a, b in spans):
            continue
        whole = int(m.group(1))
        dec = float("0." + m.group(2)) if m.group(2) else 0.0
        out.append((m.group(0), (whole + dec) * MULT[m.group(3).lower()]))
    return out


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.Pow: operator.pow}


def safe_eval(expr: str) -> float:
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "round" and len(n.args) in (1, 2):
            return round(*[ev(a) for a in n.args])
        raise ValueError(f"ekspresi tidak diizinkan: {ast.dump(n)[:60]}")
    return ev(ast.parse(expr.replace("×", "*").replace("÷", "/").replace("x", "*"), mode="eval"))


def literals(expr: str) -> list[float]:
    return [float(n.value) for n in ast.walk(ast.parse(expr.replace("×", "*").replace("÷", "/").replace("x", "*"), mode="eval"))
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))]


def frame_texts(fr: dict) -> list[tuple[str, str]]:
    out = []
    for k in ("kicker", "title", "sub", "label", "eq", "value", "note", "body", "text", "pill"):
        if fr.get(k):
            out.append((k, str(fr[k])))
    for it in fr.get("items", []) or []:
        out.append(("item", str(it)))
    for side in ("left", "right"):
        if isinstance(fr.get(side), dict):
            out.append(("h", str(fr[side].get("h", ""))))
            out.append(("t", str(fr[side].get("t", ""))))
    return out


def norm_title(s: str) -> set[str]:
    s = re.sub(r"\*\*|[^\w\s]", " ", s.lower())
    stop = {"yang", "dan", "di", "ke", "itu", "ini", "kamu", "aku", "kok", "ya", "dari", "untuk", "jadi", "=", "x"}
    return {w for w in s.split() if w not in stop and len(w) > 1}


def validate_post(post: dict, others: list[dict]) -> tuple[list[str], list[str]]:
    E, W = [], []
    pid = post.get("id", "?")
    fmt = post.get("format")
    if post.get("slot") not in SLOTS:
        E.append(f"slot harus salah satu dari {SLOTS}")
    if fmt not in FORMATS:
        E.append("format harus 'carousel' atau 'reel'")
        return E, W
    if post.get("pattern") not in POLA:
        E.append("pattern harus salah satu dari A B C D E F S")
    frames = post.get("frames") or []
    lo, hi = FORMATS[fmt]
    if not lo <= len(frames) <= hi:
        E.append(f"{fmt} butuh {lo}-{hi} frame, ada {len(frames)}")
    if frames and frames[0].get("type") != "cover":
        E.append("frame pertama harus 'cover' (hook)")
    if frames and frames[-1].get("type") != "cta":
        E.append("frame terakhir harus 'cta'")

    all_text = []
    for i, fr in enumerate(frames, 1):
        if fr.get("type") not in FRAME_TYPES:
            E.append(f"frame {i}: tipe '{fr.get('type')}' tidak dikenal")
            continue
        if fr["type"] == "cover" and not fr.get("title"):
            E.append(f"frame {i}: cover butuh 'title'")
        if fr["type"] == "number" and not fr.get("value"):
            E.append(f"frame {i}: number butuh 'value'")
        if fr["type"] == "list" and not (2 <= len(fr.get("items") or []) <= 6):
            E.append(f"frame {i}: list butuh 2-6 items")
        if fr["type"] == "compare" and not (isinstance(fr.get("left"), dict) and isinstance(fr.get("right"), dict)):
            E.append(f"frame {i}: compare butuh left{{h,t}} dan right{{h,t}}")
        for k, t in frame_texts(fr):
            plain = t.replace("**", "")
            if len(plain) > MAX_LEN.get(k, 200):
                E.append(f"frame {i}: '{k}' {len(plain)} karakter (maks {MAX_LEN[k]}): {plain[:50]}…")
            all_text.append(plain)

    cap = post.get("caption", "")
    if not cap.strip():
        E.append("caption kosong")
    if len(cap) > 1800:
        E.append(f"caption {len(cap)} karakter (maks 1800 sebelum tanda tangan & hashtag)")
    if "#" in cap:
        E.append("jangan tulis hashtag di caption; pakai field 'hashtags'")
    if re.search(r"^\s*[—-]\s*Nara", cap, re.M):
        E.append("tanda tangan ditambahkan otomatis; hapus dari caption")
    tags = post.get("hashtags") or []
    if not 3 <= len(tags) <= 5:
        E.append(f"hashtags harus 3-5, ada {len(tags)}")
    all_text.append(cap)

    # --- angka ---
    allowed: list[float] = []
    for c in post.get("calc") or []:
        try:
            got = safe_eval(str(c["expr"]))
        except Exception as e:  # noqa: BLE001
            E.append(f"calc '{c.get('expr')}' tidak bisa dihitung: {e}")
            continue
        tol = float(c.get("toleransi", 0.5))
        if abs(got - float(c["expect"])) > tol:
            E.append(f"HITUNGAN SALAH: {c['expr']} = {got:,.2f}, bukan {c['expect']:,}")
        allowed.append(float(c["expect"]))
        allowed += literals(str(c["expr"]))
    allowed += [float(g) for g in post.get("given") or []]
    for t in all_text:
        for raw, val in money_values(t):
            if not any(abs(val - a) < 0.5 for a in allowed):
                E.append(f"nominal '{raw}' ({val:,.0f}) tidak punya hitungan di calc/given")

    # --- bahasa ---
    blob = "\n".join(all_text).lower()
    for pat in BLOKIR:
        if re.search(pat, blob):
            E.append(f"kata terlarang: /{pat}/")
    for pat in MEREK:
        if re.search(pat, blob):
            W.append(f"menyebut merek nyata: /{pat}/ (sebaiknya diganti istilah umum)")
    if post.get("pattern") == "C" and not post.get("cek_fakta"):
        W.append("pola C sebaiknya punya 'cek_fakta' (sumber atau catatan bahwa tidak ada klaim angka)")

    # --- duplikat ---
    if frames and frames[0].get("title") and not post.get("ulang_dari"):
        me = norm_title(frames[0]["title"])
        for o in others:
            if o["id"] == pid or not o.get("frames") or o.get("ulang_dari"):
                continue
            them = norm_title(o["frames"][0].get("title", ""))
            if me and them:
                j = len(me & them) / len(me | them)
                if j >= 0.75:
                    E.append(f"judul sampul terlalu mirip {o['id']} (kemiripan {j:.0%})")
    return E, W


def main(argv: list[str]) -> int:
    semua = "--semua" in argv
    start = None if semua else today_wib()
    everything = list(iter_posts())
    targets = [p for p in everything if semua or p["date"] >= start]
    bad = 0
    for p in targets:
        E, W = validate_post(p, everything)
        if E or W:
            print(f"\n{p['id']} [{p.get('format')}/{p.get('pattern')}]")
        for e in E:
            print(f"  ✗ {e}")
        for w in W:
            print(f"  ! {w}")
        bad += bool(E)
    print(f"\n{len(targets)} post dicek, {bad} gagal.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
