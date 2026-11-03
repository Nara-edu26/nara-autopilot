"""Nara tanpa latar untuk video lip-sync: docs/media/_bicara/<id>.mp4 → <id>.masker.mp4 + <id>.depan.mp4.

Dipakai gaya bicara "potong" (engine/bicara.py).
1. Masker kasar dari model IS-Net (isnet-general-use.onnx, ±170 MB, dari rilis rembg di GitHub).
2. Dirapikan: celah latar krem di antara helai rambut dihapus (alpha dari kecerahan di pita tepi rambut),
   dan warna tepi dibersihkan dari sisa krem (depan.mp4), supaya tidak ada garis putih di sekeliling Nara.
Butuh onnxruntime + numpy + Pillow + scipy; tidak dipasang di render biasa.

    python engine/potong.py --id 2026-11-03-malam --model /path/isnet-general-use.onnx
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import MEDIA  # noqa: E402

MODEL_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx"


def _baca(path: Path, fmt: str, ch: int, w: int, h: int) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", fmt, "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.uint8)
    return a.reshape(-1, h, w, ch) if ch > 1 else a.reshape(-1, h, w)


def _tulis(arr: np.ndarray, fmt: str, w: int, h: int, fps: str, dst: Path, crf: int) -> None:
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", fmt, "-s", f"{w}x{h}",
                          "-r", fps, "-i", "-", "-c:v", "libx264", "-crf", str(crf), "-pix_fmt", "yuv420p", str(dst)],
                         stdin=subprocess.PIPE)
    p.stdin.write(arr.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg gagal menulis {dst.name}")


def _info(src: Path) -> tuple[int, int, str]:
    w, h, fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height,r_frame_rate", "-of", "csv=p=0", str(src)],
                               capture_output=True, text=True, check=True).stdout.strip().split(",")
    return int(w), int(h), fps


def rapikan(src: Path, kasar: Path, dst_mask: Path, dst_depan: Path) -> None:
    """Dikerjakan per frame (dialirkan lewat ffmpeg) supaya muat di memori kecil."""
    from scipy import ndimage as ndi
    w, h, fps = _info(src)
    A = _baca(kasar, "gray", 1, w, h)                       # uint8, kecil
    rd = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                          stdout=subprocess.PIPE)
    wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                           "-r", fps, "-i", "-", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(dst_depan)],
                          stdin=subprocess.PIPE)
    M = []
    bahu = int(h * 0.805)                      # di bawah garis ini kardigan/kemeja, bukan rambut
    sm = lambda x: ndi.gaussian_filter(x[::4, ::4], 12)   # noqa: E731
    for k in range(len(A)):
        buf = rd.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        im = np.frombuffer(buf, np.uint8).reshape(h, w, 3).astype(np.float32)
        a = A[k].astype(np.float32) / 255.0
        # warna latar setempat (krem), diburamkan dari piksel latar saja
        wt = (a < 0.05).astype(np.float32)
        ww = sm(wt) + 1e-4
        B = np.stack([sm(im[..., c] * wt) / ww for c in range(3)], -1)
        B = np.repeat(np.repeat(B, 4, 0), 4, 1)[:h, :w]
        fg = a > 0.5
        luar = ndi.binary_dilation(fg, iterations=10)
        pita = luar & ~ndi.binary_erosion(fg, iterations=14, border_value=1)
        d = np.linalg.norm(im - B, axis=-1)
        a2 = np.where(pita, a * (1 - np.clip(1 - (d - 14) / 38, 0, 1)), a)
        # rambut gelap di atas latar terang: alpha dari kecerahan menghapus celah krem di antara helai
        Lb, L = B.mean(-1), im.mean(-1)
        al = np.clip((Lb - L) / np.maximum(Lb - 60, 1) * 1.15, 0, 1)
        rambut = luar & ~ndi.binary_erosion(fg, iterations=45, border_value=1)
        rambut[bahu:] = False
        a2 = np.where(rambut, np.minimum(a2, al), a2)
        a2 = ndi.gaussian_filter(a2, 0.8)
        aa = np.clip(a2, 0.25, 1)[..., None]
        f = np.where((a2 < 0.98)[..., None], np.clip((im - (1 - aa) * B) / aa, 0, 255), im)
        wr.stdin.write(f.astype(np.uint8).tobytes())
        M.append((np.clip(a2, 0, 1) * 255).astype(np.uint8))
    rd.stdout.close()
    rd.wait()
    wr.stdin.close()
    if wr.wait() != 0:
        raise RuntimeError("ffmpeg gagal menulis depan")
    M = np.stack(M).astype(np.float32) / 255.0
    # Amplop kepala-sampai-dada: siluet yang ada di sebagian besar frame (median), dilebarkan ±20 px untuk
    # gerak kepala. Gerakan tangan yang hanya sesaat muncul di luar siluet (dan pecah saat latar dibuang)
    # ikut terbuang, jadi yang tampil hanya kepala sampai dada.
    kecil = np.median(M[:, ::4, ::4], axis=0) > 0.5
    kecil = ndi.binary_dilation(kecil, iterations=5)
    amplop = np.repeat(np.repeat(kecil.astype(np.float32), 4, 0), 4, 1)[:h, :w]
    amplop = np.clip(ndi.gaussian_filter(amplop, 5), 0, 1)
    M *= amplop[None]
    Ms = M.copy()
    Ms[1:-1] = 0.25 * M[:-2] + 0.5 * M[1:-1] + 0.25 * M[2:]
    _tulis((np.clip(Ms, 0, 1) * 255).astype(np.uint8), "gray", w, h, fps, dst_mask, 12)


def masker(src: Path, dst: Path, model: Path) -> None:
    import onnxruntime as ort
    w, h, fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height,r_frame_rate", "-of", "csv=p=0", str(src)],
                               capture_output=True, text=True, check=True).stdout.strip().split(",")
    w, h = int(w), int(h)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
    so = ort.SessionOptions()
    sess = ort.InferenceSession(str(model), so, providers=["CPUExecutionProvider"])
    name = sess.get_inputs()[0].name
    out = []
    for i, f in enumerate(frames):
        x = np.asarray(Image.fromarray(f).resize((1024, 1024), Image.LANCZOS)).astype(np.float32) / 255.0 - 0.5
        o = sess.run(None, {name: x.transpose(2, 0, 1)[None]})[0][0, 0]
        o = (o - o.min()) / (o.max() - o.min() + 1e-8)
        out.append(np.asarray(Image.fromarray((o * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS),
                              dtype=np.float32))
        if i % 25 == 0:
            print(f"  masker {i}/{len(frames)}", flush=True)
    m = np.stack(out)
    sm = m.copy()
    sm[1:-1] = 0.25 * m[:-2] + 0.5 * m[1:-1] + 0.25 * m[2:]      # tepi rambut tidak berkedip
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}",
                          "-r", fps, "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(dst)],
                         stdin=subprocess.PIPE)
    p.stdin.write(np.clip(sm, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg gagal menyimpan masker")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--model", required=True)
    a = ap.parse_args()
    src = MEDIA / "_bicara" / f"{a.id}.mp4"
    if not src.exists():
        sys.exit(f"Video {src} tidak ada")
    kasar = src.with_name(f"{a.id}.kasar.mp4")
    if not kasar.exists():
        masker(src, kasar, Path(a.model))
    rapikan(src, kasar, src.with_name(f"{a.id}.masker.mp4"), src.with_name(f"{a.id}.depan.mp4"))
    print("✓ Nara tanpa latar:", a.id)
