"""Buat masker (Nara tanpa latar) untuk video lip-sync: docs/media/_bicara/<id>.mp4 → <id>.masker.mp4.

Dipakai gaya bicara "potong" (engine/bicara.py). Model: IS-Net (isnet-general-use.onnx, ±170 MB,
dari rilis rembg di GitHub). Butuh onnxruntime + numpy + Pillow; tidak dipasang di render biasa.

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
    masker(src, src.with_name(f"{a.id}.masker.mp4"), Path(a.model))
    print("✓ masker", a.id)
