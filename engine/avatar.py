"""Avatar Nara bergerak di sudut reel, mengikuti suara.

Bukan lip-sync: wajah tidak membuka mulut. Yang bergerak:
- "napas" (skala naik-turun pelan) dan sedikit miring kiri-kanan,
- cincin dan cahaya di sekeliling foto yang membesar saat Nara bicara,
- lencana gelombang suara kecil yang naik-turun mengikuti suara.

Di frame pembuka avatar menutup foto besar di blok "Hai, aku Nara", lalu bergeser mengecil ke sudut kanan atas
saat frame berganti. Envelope dihitung dari file suara (bukan musik), jadi avatar diam saat tidak ada suara.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

FPS = 30
SR = 16000
CANVAS = 440                      # ukuran sprite (persegi)
CORNER = (868, 300, 96)           # pusat x, pusat y, jari-jari di sudut kanan atas
CREAM = (243, 237, 226)
OLIVE = (78, 90, 57)
SAGE = (201, 209, 181)


def _pcm(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def envelope(cues: list[tuple[Path, float]], total: float) -> np.ndarray:
    """Kekerasan suara per frame video (0..1)."""
    n = int(math.ceil(total * FPS)) + 1
    track = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for path, start in cues:
        a = _pcm(path)
        i = int(start * SR)
        j = min(len(track), i + len(a))
        track[i:j] += a[: j - i]
    hop = SR // FPS
    rms = np.array([math.sqrt(float(np.mean(track[k * hop:(k + 1) * hop] ** 2)) + 1e-12) for k in range(n)])
    ref = np.percentile(rms[rms > 1e-4], 90) if np.any(rms > 1e-4) else 1.0
    e = np.clip(rms / (ref + 1e-9), 0, 1.2)
    out = np.zeros_like(e)
    for k in range(n):                       # naik cepat, turun pelan
        prev = out[k - 1] if k else 0.0
        out[k] = e[k] if e[k] > prev else prev * 0.82 + e[k] * 0.18
    return out


def _round_face(src: Path, size: int = 640) -> Image.Image:
    im = Image.open(src).convert("RGB")
    s = min(im.size)
    im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2))
    im = im.resize((size, size), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    im.putalpha(mask.resize((size, size), Image.LANCZOS))
    return im


def _ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def sprite(face: Image.Image, t: float, e: float, r: float) -> Image.Image:
    c = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    mid = CANVAS / 2
    breathe = 1 + 0.012 * math.sin(2 * math.pi * t / 3.4)
    rr = r * breathe * (1 + 0.035 * e)
    # cahaya lembut
    glow = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    g = rr + 6 + 14 * e
    ImageDraw.Draw(glow).ellipse((mid - g, mid - g, mid + g, mid + g), fill=SAGE + (int(60 + 100 * e),))
    c = Image.alpha_composite(c, glow.filter(ImageFilter.GaussianBlur(7 + 4 * e)))
    # cincin
    d = ImageDraw.Draw(c)
    w = 4 + 5 * e
    d.ellipse((mid - rr - w, mid - rr - w, mid + rr + w, mid + rr + w), fill=CREAM + (255,))
    d.ellipse((mid - rr - w * 0.45, mid - rr - w * 0.45, mid + rr + w * 0.45, mid + rr + w * 0.45), fill=OLIVE + (255,))
    # wajah, sedikit miring
    size = max(8, int(round(rr * 2)))
    f = face.resize((size, size), Image.LANCZOS).rotate(1.6 * math.sin(2 * math.pi * t / 4.6), resample=Image.BICUBIC)
    c.alpha_composite(f, (int(mid - size / 2), int(mid - size / 2)))
    # lencana gelombang suara di kanan bawah
    bw, bh = rr * 0.62, rr * 0.36
    bx, by = mid + rr * 0.42, mid + rr * 0.58
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((bx - bw / 2, by - bh / 2, bx + bw / 2, by + bh / 2), radius=bh / 2, fill=OLIVE + (255,),
                        outline=CREAM + (255,), width=max(2, int(rr * 0.03)))
    n = 4
    gap = bw * 0.62 / n
    for k in range(n):
        phase = math.sin(2 * math.pi * (t * 2.3 + k * 0.27))
        h = bh * (0.18 + 0.55 * min(1.0, e) * (0.55 + 0.45 * abs(phase)))
        x = bx - bw * 0.31 + gap * (k + 0.5)
        d.rounded_rectangle((x - gap * 0.22, by - h / 2, x + gap * 0.22, by + h / 2), radius=gap * 0.22, fill=CREAM + (255,))
    return c


def animate(base: Path, dst: Path, face_src: Path, cues: list[tuple[Path, float]], total: float,
            cover_box: tuple[float, float, float] | None, cover_end: float) -> None:
    """Tumpuk avatar bergerak di atas video dasar. cover_box = (pusat x, pusat y, jari-jari) foto di frame pembuka."""
    env = envelope(cues, total)
    face = _round_face(face_src)
    cx1, cy1, r1 = CORNER
    cx0, cy0, r0 = cover_box or CORNER
    t0, t1 = max(0.0, cover_end - 0.35), cover_end + 0.35
    n = len(env)

    def pos(t: float) -> tuple[float, float, float]:
        k = _ease((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
        return cx0 + (cx1 - cx0) * k, cy0 + (cy1 - cy0) * k, r0 + (r1 - r0) * k

    # posisi per frame dikirim lewat ekspresi x,y (patah-patah linier) supaya cukup sprite kecil yang dialirkan
    def expr(i: int) -> str:
        v0, v1 = pos(0)[i] - CANVAS / 2, pos(t1 + 1)[i] - CANVAS / 2
        return (f"if(lt(t,{t0:.3f}),{v0:.1f},if(lt(t,{t1:.3f}),"
                f"{v0:.1f}+({v1 - v0:.1f})*(3*pow((t-{t0:.3f})/{t1 - t0:.3f},2)-2*pow((t-{t0:.3f})/{t1 - t0:.3f},3)),{v1:.1f}))")

    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(base),
           "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{CANVAS}x{CANVAS}", "-r", str(FPS), "-i", "pipe:0",
           "-filter_complex", f"[0:v][1:v]overlay=x='{expr(0)}':y='{expr(1)}':eof_action=pass:format=auto,format=yuv420p[v]",
           "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-profile:v", "high",
           "-r", str(FPS), "-c:a", "copy", "-movflags", "+faststart", "-t", f"{total:.3f}", str(dst)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for i in range(n):
            t = i / FPS
            _, _, r = pos(t)
            p.stdin.write(sprite(face, t, float(env[i]), r).tobytes())
    finally:
        p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg gagal menumpuk avatar")
