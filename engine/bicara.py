"""Nara berbicara (video lip-sync) di kanan bawah, hanya selama frame pembuka.

Video lip-sync dibuat di luar mesin ini (ElevenLabs Image & Video › Lip sync) dari foto Nara dan
suara pembuka reel yang sama persis, lalu disimpan sebagai docs/media/_bicara/<id post>.mp4.
Kalau file itu tidak ada, reel dibuat seperti biasa (suara + tulisan).

Audio reel tetap dari mesin ini; audio video lip-sync tidak dipakai. Karena masukan lip-sync adalah
potongan suara yang dimulai dari detik 0 reel, gerak bibir otomatis sejajar.

Gaya (config.json brand.bicara_gaya):
- "potong": Nara tanpa latar, besar, muncul dari tepi bawah. Butuh masker _bicara/<id>.masker.mp4
  (dibuat engine/potong.py). Tanpa masker → jatuh ke "pudar".
- "pudar": video lebih besar dengan tepi memudar ke latar, tanpa bingkai.
- "kotak": kotak membulat berbingkai krem (versi pertama).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from common import MEDIA

FOLDER = MEDIA / "_bicara"
TOP = 1135                        # batas atas area Nara (teks frame pembuka berakhir ±1120 px)
CX = 690                          # pusat horizontal Nara (di kiri kolom tombol Instagram)
CREAM = (243, 237, 226, 255)


def clip_for(pid: str, pembuka: Path | None = None) -> Path | None:
    """Klip hanya dipakai bila dibuat dari suara pembuka yang sama dengan reel ini (_bicara/<id>.suara
    berisi nama file suara frame 0). Suara berganti → gerak bibir tidak cocok → klip dilewati."""
    p = FOLDER / f"{pid}.mp4"
    if not (p.exists() and p.stat().st_size > 10_000) or pembuka is None:
        return None
    tag = FOLDER / f"{pid}.suara"
    if not tag.exists() or tag.read_text().strip() != Path(pembuka).name:
        print(f"! {pid}: klip Nara berbicara dibuat dari suara lain; dilewati sampai klip baru dipasang.")
        return None
    return p


def mask_for(pid: str) -> Path | None:
    p = FOLDER / f"{pid}.masker.mp4"
    return p if p.exists() and p.stat().st_size > 1_000 else None


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _enc(total: float, dst: Path) -> list[str]:
    return ["-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-profile:v", "high",
            "-r", "30", "-c:a", "copy", "-movflags", "+faststart", "-t", f"{total:.3f}", str(dst)]


def _fades(end: float) -> str:
    fo = max(0.3, end - 0.3)
    return f"fade=t=in:st=0:d=0.25:alpha=1,fade=t=out:st={fo:.3f}:d=0.3:alpha=1"


def _trim(end: float) -> str:
    return f"trim=0:{end:.3f},setpts=PTS-STARTPTS,fps=30"


# --- gaya "potong" ------------------------------------------------------------------------------
def _bbox_top(mask: Path) -> float:
    """Bagian atas kepala (0..1 dari tinggi klip), diambil dari gabungan masker semua frame."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mask), "-vf", "scale=270:270,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    n = len(raw) // (270 * 270)
    rows = [0] * 270
    for k in range(n):
        f = raw[k * 270 * 270:(k + 1) * 270 * 270]
        for r in range(270):
            if rows[r] == 0 and max(f[r * 270:(r + 1) * 270]) > 128:
                rows[r] = 1
    return (rows.index(1) / 270) if 1 in rows else 0.0


def _potong(base: Path, talk: Path, mask: Path, dst: Path, end: float, total: float) -> None:
    top = _bbox_top(mask)
    size = int(min(900, (1920 - TOP) / max(0.5, 1 - top)))
    size -= size % 2
    x0, y0 = CX - size // 2, 1920 - size
    rise = 50
    y = f"'{y0}+{rise}*pow(max(0,1-t/0.35),2)'"
    fg = (
        f"[1:v]{_trim(end)},scale={size}:{size},format=rgba[tv];"
        # masker dikikis ±2 px dan dipertegas supaya sisa latar krem di tepi rambut tidak jadi lingkaran terang
        f"[2:v]{_trim(end)},scale={size}:{size},format=gray,erosion,erosion,"
        f"lutyuv=y='clip((val-45)*255/190,0,255)',split[m1][m2];"
        f"[tv][m1]alphamerge,{_fades(end)}[tm];"
        # bayangan lembut di belakang Nara supaya tidak terlihat 'tertempel'
        f"[m2]boxblur=22:2,lutyuv=y=val*0.32[sm];"
        f"color=c=0x1d2414:s={size}x{size}:r=30:d={end:.3f},format=rgba[sc];"
        f"[sc][sm]alphamerge,{_fades(end)}[sh];"
        f"[0:v][sh]overlay=x={x0 - 14}:y={y}:eval=frame:eof_action=pass[b1];"
        f"[b1][tm]overlay=x={x0}:y={y}:eval=frame:eof_action=pass,format=yuv420p[v]"
    )
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(base), "-i", str(talk), "-i", str(mask),
          "-filter_complex", fg, *_enc(total, dst)])


# --- gaya "pudar" -------------------------------------------------------------------------------
def _pudar(base: Path, talk: Path, dst: Path, end: float, total: float, td: Path) -> None:
    size = 780
    x0, y0 = CX - size // 2, TOP
    s = 520
    m = Image.new("L", (s, s), 0)
    pad = int(s * 0.14)
    ImageDraw.Draw(m).ellipse((pad, pad - int(s * 0.06), s - pad, s - pad + int(s * 0.16)), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(s * 0.09))
    ramp = Image.linear_gradient("L").resize((s, s))           # 0 di atas → 255 di bawah
    ramp = ramp.point(lambda v: min(255, v * 7))               # pudar habis di ±14% teratas
    from PIL import ImageChops
    m = ImageChops.multiply(m, ramp).resize((size, size), Image.LANCZOS)
    mpath = td / "pudar.png"
    m.save(mpath)
    fg = (
        f"[1:v]{_trim(end)},scale={size}:{size},format=rgba[tv];"
        f"[2:v]format=gray,scale={size}:{size}[m];"
        f"[tv][m]alphamerge,{_fades(end)}[tm];"
        f"[0:v][tm]overlay=x={x0}:y={y0}:eof_action=pass,format=yuv420p[v]"
    )
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(base), "-i", str(talk), "-loop", "1", "-i", str(mpath),
          "-filter_complex", fg, *_enc(total, dst)])


# --- gaya "kotak" (versi pertama) ---------------------------------------------------------------
KSIZE, RADIUS, BORDER = 340, 44, 6


def _kotak(base: Path, talk: Path, dst: Path, end: float, total: float, td: Path) -> None:
    X, Y = 1080 - 140 - KSIZE, 1480 - KSIZE
    s = KSIZE * 4
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, s - 1, s - 1), radius=RADIUS * 4, fill=255)
    mpath = td / "masker.png"
    mask.resize((KSIZE, KSIZE), Image.LANCZOS).save(mpath)
    tot = KSIZE + 2 * BORDER
    ring = Image.new("RGBA", (tot * 4, tot * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(ring)
    d.rounded_rectangle((0, 0, tot * 4 - 1, tot * 4 - 1), radius=(RADIUS + BORDER) * 4, fill=CREAM)
    d.rounded_rectangle((BORDER * 4, BORDER * 4, (tot - BORDER) * 4 - 1, (tot - BORDER) * 4 - 1),
                        radius=RADIUS * 4, fill=(0, 0, 0, 0))
    ring = ring.resize((tot, tot), Image.LANCZOS)
    shadow = Image.new("RGBA", (tot + 40, tot + 40), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((20, 26, tot + 20, tot + 26), radius=RADIUS + BORDER, fill=(0, 0, 0, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    shadow.alpha_composite(ring, (20, 20))
    rpath = td / "bingkai.png"
    shadow.save(rpath)
    fg = (
        f"[1:v]{_trim(end)},scale={KSIZE}:{KSIZE}:force_original_aspect_ratio=increase,crop={KSIZE}:{KSIZE},format=rgba[tv];"
        f"[2:v]format=gray,scale={KSIZE}:{KSIZE}[m];"
        f"[tv][m]alphamerge,{_fades(end)}[tm];"
        f"[3:v]format=rgba,loop=-1:1:0,{_trim(end)},{_fades(end)}[ring];"
        f"[0:v][ring]overlay=x={X - BORDER - 20}:y={Y - BORDER - 20}:eof_action=pass[b1];"
        f"[b1][tm]overlay=x={X}:y={Y}:eof_action=pass,format=yuv420p[v]"
    )
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(base), "-i", str(talk), "-loop", "1", "-i", str(mpath),
          "-i", str(rpath), "-filter_complex", fg, *_enc(total, dst)])


def overlay(base: Path, talk: Path, dst: Path, end: float, total: float, td: Path,
            gaya: str = "potong", mask: Path | None = None) -> None:
    """Tumpuk video bicara di [0, end]: muncul 0,25 dtk, hilang 0,3 dtk."""
    if gaya == "potong" and mask:
        depan = mask.with_name(mask.name.replace(".masker.mp4", ".depan.mp4"))   # warna tepi sudah dibersihkan
        _potong(base, depan if depan.exists() else talk, mask, dst, end, total)
    elif gaya == "kotak":
        _kotak(base, talk, dst, end, total, td)
    else:
        _pudar(base, talk, dst, end, total, td)
