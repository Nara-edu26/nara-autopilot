"""Ubah post JSON menjadi media siap unggah.

carousel -> media/<id>/01.jpg ... NN.jpg   (1080x1350, JPEG)
reel     -> media/<id>/reel.mp4 + cover.jpg (1080x1920, H.264/AAC, 30 fps)

Reel dibuat dari frame yang sama: tiap frame muncul dua tahap (judul dulu, lalu angka/isi),
diberi transisi halus dan garis progres di atas. Frame pembuka menampilkan wajah Nara (config brand.avatar).
Musik: file di assets/music/, satu dipilih otomatis per post. Suara Nara: bila config suara.aktif,
suara.voice_id terisi, dan secret ELEVENLABS_API_KEY ada, setiap frame dibacakan (lihat suara.py);
durasi frame menyesuaikan panjang suara dan musik dikecilkan di bawahnya. Tanpa kunci, reel tetap jadi
dengan musik saja.

Pakai:  python engine/render.py                 (render semua post mulai hari ini yang medianya belum ada)
        python engine/render.py --id 2026-10-26-pagi --paksa
        python engine/render.py --sampai 2026-11-08 (batasi tanggal)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, iter_posts, load_config, media_dir, media_files, slot_aktif, today_wib  # noqa: E402
from validate import validate_post  # noqa: E402
import suara  # noqa: E402
import avatar as avatar_anim  # noqa: E402

TEMPLATE = ROOT / "engine" / "templates" / "frame.html"
MUSIC = ROOT / "assets" / "music"
FPS = 30
XFADE = 0.28


def words(fr: dict) -> int:
    txt = " ".join(str(v) for k, v in fr.items() if isinstance(v, str) and k not in ("type", "theme"))
    txt += " ".join(fr.get("items") or [])
    for side in ("left", "right"):
        if isinstance(fr.get(side), dict):
            txt += " " + " ".join(fr[side].values())
    return len(txt.replace("**", "").split())


def frame_duration(fr: dict, i: int) -> float:
    if "dur" in fr:
        return float(fr["dur"])
    if i == 0:
        return 2.6                      # hook: cepat, langsung terbaca
    if fr["type"] == "cta":
        return 3.4
    return max(2.4, min(5.2, 1.4 + 0.30 * words(fr)))


def has_reveal(fr: dict) -> bool:
    return fr["type"] in ("number", "point", "list", "compare", "statement", "cta")


class Renderer:
    def __init__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch()
        self.page = self.browser.new_page(device_scale_factor=1)
        self.page.goto(TEMPLATE.as_uri())
        self.cfg = load_config()
        av = self.cfg["brand"].get("avatar")
        self.avatar = (ROOT / av).as_uri() if av and (ROOT / av).exists() else ""
        self.voice = suara.Suara(self.cfg)
        self.animasi = bool(self.cfg["brand"].get("avatar_animasi")) and bool(self.avatar)

    def close(self):
        self.browser.close()
        self._pw.stop()

    def shot(self, fmt: str, fr: dict, idx: int, total: int, stage: int, out: Path, jpeg: bool):
        w, h = (1080, 1350) if fmt == "carousel" else (1080, 1920)
        self.page.set_viewport_size({"width": w, "height": h})
        b = self.cfg["brand"]
        payload = {"format": fmt, "frame": fr, "index": idx, "total": total, "stage": stage,
                   "signature": b["tanda_tangan"], "closing": b["penutup"],
                   "avatar": self.avatar, "greeting": b.get("sapaan", ""), "role": b.get("peran", ""),
                   "topAvatar": not (fmt == "reel" and self.animasi)}
        self.page.evaluate("d => renderFrame(d)", payload)
        self.page.evaluate("() => document.fonts.ready")
        self.page.evaluate("() => Promise.all([...document.images].map(i => i.complete ? 1 :"
                           " new Promise(r => { i.onload = i.onerror = r; })))")
        if self.avatar:   # tata letak dihitung ulang setelah foto termuat
            self.page.evaluate("() => fit()")
        clip = {"x": 0, "y": 0, "width": w, "height": h}
        if jpeg:
            self.page.screenshot(path=str(out), type="jpeg", quality=92, clip=clip)
        else:
            self.page.screenshot(path=str(out), type="png", clip=clip)

    def carousel(self, post: dict, out: Path):
        frames = post["frames"]
        for i, fr in enumerate(frames):
            self.shot("carousel", fr, i, len(frames), 1, out / f"{i + 1:02d}.jpg", True)

    def reel(self, post: dict, out: Path):
        frames = post["frames"]
        voices = self.voice.frames(post)          # [Path|None] per frame, atau [] tanpa suara
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            clips: list[tuple[Path, float]] = []
            cues: list[tuple[Path, int]] = []      # (file suara, indeks klip pertama frame itu)
            for i, fr in enumerate(frames):
                d = frame_duration(fr, i)
                v = voices[i] if voices else None
                if v:
                    d = max(d, suara.durasi(v) + 0.55)
                    cues.append((v, len(clips)))
                if i > 0 and has_reveal(fr):
                    a = td / f"{i:02d}a.png"
                    self.shot("reel", fr, i, len(frames), 0, a, False)
                    clips.append((a, 0.9))
                    d = max(1.6, d - 0.9 + XFADE)
                b = td / f"{i:02d}b.png"
                self.shot("reel", fr, i, len(frames), 1, b, False)
                clips.append((b, d))
            self.shot("reel", frames[0], 0, len(frames), 1, out / "cover.jpg", True)
            if not self.animasi:
                encode_reel(clips, out / "reel.mp4", pick_music(post["id"]), cues)
                return
            box = self.page.evaluate("""() => { const i = document.querySelector('.presenter img');
                if (!i) return null; const r = i.getBoundingClientRect();
                return [r.x + r.width / 2, r.y + r.height / 2, r.width / 2 - 6]; }""")
            base = td / "dasar.mp4"
            encode_reel(clips, base, pick_music(post["id"]), cues)
            starts = clip_starts(clips)
            total = sum(d for _, d in clips) - XFADE * (len(clips) - 1)
            cover_end = (starts[1] + XFADE / 2) if len(starts) > 1 else total
            sec_cues = [(v, starts[k] + 0.18) for v, k in cues]
            avatar_anim.animate(base, out / "reel.mp4", ROOT / self.cfg["brand"]["avatar"], sec_cues, total,
                                tuple(box) if box else None, cover_end)


def pick_music(pid: str) -> Path | None:
    if not MUSIC.exists():
        return None
    tracks = sorted([p for p in MUSIC.iterdir() if p.suffix.lower() in (".mp3", ".m4a", ".aac", ".wav")])
    if not tracks:
        return None
    return tracks[int(hashlib.sha1(pid.encode()).hexdigest(), 16) % len(tracks)]


def clip_starts(clips: list[tuple[Path, float]]) -> list[float]:
    """Detik mulai tiap klip di video jadi (klip saling bertumpuk XFADE detik)."""
    out, t = [], 0.0
    for _, d in clips:
        out.append(t)
        t += d - XFADE
    return out


def encode_reel(clips: list[tuple[Path, float]], dst: Path, music: Path | None,
                cues: list[tuple[Path, int]] | None = None):
    cues = cues or []
    args = ["ffmpeg", "-y", "-loglevel", "error"]
    for p, d in clips:
        args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", str(p)]
    total = sum(d for _, d in clips) - XFADE * (len(clips) - 1)
    fg, last, offset = [], "0:v", 0.0
    for i in range(1, len(clips)):
        offset += clips[i - 1][1] - XFADE
        tag = f"v{i}"
        fg.append(f"[{last}][{i}:v]xfade=transition=fade:duration={XFADE}:offset={offset:.3f}[{tag}]")
        last = tag
    # garis progres tipis olive-muda di tepi atas
    fg.append(f"color=c=0xC9D1B5:s=1080x10:r={FPS}:d={total:.3f}[bar]")
    fg.append(f"[{last}][bar]overlay=x='-w+w*t/{total:.3f}':y=0:shortest=1,format=yuv420p[vout]")
    n = len(clips)
    # alas audio: musik (diulang bila kurang panjang) atau senyap
    if music:
        args += ["-stream_loop", "-1", "-i", str(music)]
        vol = 0.14 if cues else 0.9
        fg.append(f"[{n}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,volume={vol},"
                  f"afade=t=in:d=0.4,afade=t=out:st={max(0, total - 1.2):.3f}:d=1.2,"
                  f"aresample=48000,aformat=channel_layouts=stereo[bed]")
    else:
        args += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        fg.append(f"[{n}:a]anull[bed]")
    if cues:
        starts = clip_starts(clips)
        labels = ["[bed]"]
        for j, (vf, k) in enumerate(cues):
            args += ["-i", str(vf)]
            ms = int((starts[k] + 0.18) * 1000)
            fg.append(f"[{n + 1 + j}:a]aresample=48000,aformat=channel_layouts=stereo,"
                      f"adelay={ms}|{ms}[s{j}]")
            labels.append(f"[s{j}]")
        fg.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:normalize=0,"
                  f"atrim=0:{total:.3f}[aout]")
    else:
        fg.append("[bed]anull[aout]")
    args += ["-filter_complex", ";".join(fg), "-map", "[vout]", "-map", "[aout]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-profile:v", "high", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-movflags", "+faststart",
             "-t", f"{total:.3f}", str(dst)]
    subprocess.run(args, check=True)


def needs_render(post: dict) -> bool:
    d = media_dir(post["id"])
    if not all((d / f).exists() for f in media_files(post)):
        return True
    stamp = d / "sumber.sha1"
    return not stamp.exists() or stamp.read_text().strip() != content_hash(post)


def content_hash(post: dict) -> str:
    keep = {k: post.get(k) for k in ("format", "frames")}
    cfg = load_config()
    keep["_suara"] = suara.sidik(cfg) if post.get("format") == "reel" else ""
    keep["_brand"] = {k: cfg["brand"].get(k) for k in ("avatar", "sapaan", "peran", "avatar_animasi")}
    keep["_anim"] = hashlib.sha1((ROOT / "engine" / "avatar.py").read_bytes()).hexdigest()[:10] \
        if cfg["brand"].get("avatar_animasi") and post.get("format") == "reel" else ""
    keep["_musik"] = sorted(p.name for p in MUSIC.iterdir()) if MUSIC.exists() else []
    tpl = TEMPLATE.read_bytes()
    return hashlib.sha1(json.dumps(keep, sort_keys=True).encode() + tpl).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id")
    ap.add_argument("--dari", default=today_wib())
    ap.add_argument("--sampai")
    ap.add_argument("--paksa", action="store_true")
    a = ap.parse_args()

    cfg = load_config()
    everything = list(iter_posts())
    todo = []
    for p in everything:
        if a.id and p["id"] != a.id:
            continue
        if not a.id and (p["date"] < a.dari or (a.sampai and p["date"] > a.sampai)):
            continue
        if p.get("skip") or not slot_aktif(cfg, p["slot"]):
            continue
        if a.paksa or needs_render(p):
            todo.append(p)
    if not todo:
        print("Tidak ada yang perlu dirender.")
        return 0

    r = Renderer()
    failed = 0
    try:
        for p in todo:
            errs, _ = validate_post(p, everything)
            if errs:
                print(f"✗ {p['id']} dilewati, gagal validasi:\n  - " + "\n  - ".join(errs))
                failed += 1
                continue
            out = media_dir(p["id"])
            if out.exists():
                shutil.rmtree(out)
            out.mkdir(parents=True)
            try:
                (r.carousel if p["format"] == "carousel" else r.reel)(p, out)
                # suara gagal → cap sengaja tidak cocok, supaya render berikutnya mencoba lagi
                (out / "sumber.sha1").write_text("ulang-suara" if r.voice.gagal else content_hash(p))
                print(f"✓ {p['id']} ({p['format']}, {len(p['frames'])} frame)")
            except Exception as e:  # noqa: BLE001
                failed += 1
                shutil.rmtree(out, ignore_errors=True)
                print(f"✗ {p['id']} gagal dirender: {e}")
    finally:
        r.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
