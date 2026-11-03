"""Nara berbicara (video lip-sync) di pojok kanan bawah, hanya selama frame pembuka.

Video lip-sync dibuat di luar mesin ini (mis. ElevenLabs Image & Video › Lip sync) dari foto Nara dan
suara pembuka reel yang sama persis, lalu disimpan sebagai docs/media/_bicara/<id post>.mp4.
Kalau file itu tidak ada, reel dibuat seperti biasa (suara + tulisan).

Audio reel tetap dari mesin ini; audio video lip-sync tidak dipakai. Karena masukan lip-sync adalah
potongan suara yang dimulai dari detik 0 reel, gerak bibir otomatis sejajar.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from common import MEDIA

FOLDER = MEDIA / "_bicara"
SIZE = 340                        # sisi kotak avatar (px)
X, Y = 1080 - 140 - SIZE, 1480 - SIZE   # kanan bawah area aman (di kiri kolom tombol IG, di atas caption)
RADIUS = 44
BORDER = 6
CREAM = (243, 237, 226, 255)


def clip_for(pid: str) -> Path | None:
    p = FOLDER / f"{pid}.mp4"
    return p if p.exists() and p.stat().st_size > 10_000 else None


def _assets(td: Path) -> tuple[Path, Path]:
    s = SIZE * 4
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, s - 1, s - 1), radius=RADIUS * 4, fill=255)
    mask = mask.resize((SIZE, SIZE), Image.LANCZOS)
    mpath = td / "masker.png"
    mask.save(mpath)
    tot = SIZE + 2 * BORDER
    ring = Image.new("RGBA", (tot * 4, tot * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(ring)
    d.rounded_rectangle((0, 0, tot * 4 - 1, tot * 4 - 1), radius=(RADIUS + BORDER) * 4, fill=CREAM)
    d.rounded_rectangle((BORDER * 4, BORDER * 4, (tot - BORDER) * 4 - 1, (tot - BORDER) * 4 - 1),
                        radius=RADIUS * 4, fill=(0, 0, 0, 0))
    ring = ring.resize((tot, tot), Image.LANCZOS)
    # bayangan lembut
    shadow = Image.new("RGBA", (tot + 40, tot + 40), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((20, 26, tot + 20, tot + 26), radius=RADIUS + BORDER, fill=(0, 0, 0, 70))
    from PIL import ImageFilter
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    shadow.alpha_composite(ring, (20, 20))
    rpath = td / "bingkai.png"
    shadow.save(rpath)
    return mpath, rpath


def overlay(base: Path, talk: Path, dst: Path, end: float, total: float, td: Path) -> None:
    """Tumpuk video bicara di [0, end] dengan muncul 0,2 dtk dan hilang 0,3 dtk."""
    mpath, rpath = _assets(td)
    fo = max(0.3, end - 0.3)
    fg = (
        f"[1:v]trim=0:{end:.3f},setpts=PTS-STARTPTS,fps=30,scale={SIZE}:{SIZE}:force_original_aspect_ratio=increase,"
        f"crop={SIZE}:{SIZE},format=rgba[tv];"
        f"[2:v]format=gray,scale={SIZE}:{SIZE}[m];"
        f"[tv][m]alphamerge,fade=t=in:st=0:d=0.2:alpha=1,fade=t=out:st={fo:.3f}:d=0.3:alpha=1[tm];"
        f"[3:v]format=rgba,loop=-1:1:0,trim=0:{end:.3f},setpts=PTS-STARTPTS,fps=30,"
        f"fade=t=in:st=0:d=0.2:alpha=1,fade=t=out:st={fo:.3f}:d=0.3:alpha=1[ring];"
        f"[0:v][ring]overlay=x={X - BORDER - 20}:y={Y - BORDER - 20}:eof_action=pass[b1];"
        f"[b1][tm]overlay=x={X}:y={Y}:eof_action=pass,format=yuv420p[v]"
    )
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(base), "-i", str(talk), "-loop", "1", "-i", str(mpath),
           "-i", str(rpath), "-filter_complex", fg, "-map", "[v]", "-map", "0:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-profile:v", "high", "-r", "30",
           "-c:a", "copy", "-movflags", "+faststart", "-t", f"{total:.3f}", str(dst)]
    subprocess.run(cmd, check=True)
