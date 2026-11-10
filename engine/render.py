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
from common import MEDIA as MEDIA_DIR, ROOT, iter_posts, load_config, media_dir, media_files, slot_aktif, today_wib  # noqa: E402
from validate import validate_post  # noqa: E402
import suara  # noqa: E402

TEMPLATE = ROOT / "engine" / "templates" / "frame.html"
MUSIC = ROOT / "assets" / "music"
FPS = 30
XFADE = 0.28
LOUD = "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000"   # standar kekerasan media sosial (±-14 LUFS)


def words(fr: dict) -> int:
    txt = " ".join(str(v) for k, v in fr.items() if isinstance(v, str) and k not in ("type", "theme", "nara"))
    txt += " ".join(fr.get("items") or [])
    txt += " " + " ".join(fr.get("options") or [])
    for r in fr.get("rows") or []:          # struk & mutasi: tiap baris dihitung sebagai kata yang dibaca mata
        txt += " " + (" ".join(map(str, r)) if isinstance(r, list) else "")
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
    if fr["type"] == "struk":
        return bool(fr.get("total") or fr.get("note"))
    if fr["type"] == "mutasi":
        return bool(fr.get("saldo"))
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
        g2 = self.cfg.get("gaya_baru") or {}
        self.g2 = g2
        self.cutout = (ROOT / g2["nara"]).as_uri() if g2.get("nara") and (ROOT / g2["nara"]).exists() else ""
        self.seri = None                         # diisi per post (gaya baru bila post punya "seri")
        self.voice = suara.Suara(self.cfg)
        self.animasi = bool(self.cfg["brand"].get("avatar_animasi")) and bool(self.avatar)
        self.bicara = bool(self.cfg["brand"].get("avatar_bicara"))

    def close(self):
        self.browser.close()
        self._pw.stop()

    def shot(self, fmt: str, fr: dict, idx: int, total: int, stage: int, out: Path, jpeg: bool, talker: bool = False):
        w, h = (1080, 1350) if fmt == "carousel" else (1080, 1920)
        self.page.set_viewport_size({"width": w, "height": h})
        b = self.cfg["brand"]
        payload = {"format": fmt, "frame": fr, "index": idx, "total": total, "stage": stage,
                   "signature": b["tanda_tangan"], "closing": b["penutup"],
                   "avatar": self.avatar, "greeting": b.get("sapaan", ""), "role": b.get("peran", ""),
                   "topAvatar": not (fmt == "reel" and self.animasi), "talker": talker}
        if self.seri:
            s = self.seri
            ekspresi = fr.get("ekspresi")
            cut = self.cutout
            if ekspresi and (ROOT / "assets" / "ekspresi" / f"{ekspresi}.png").exists():
                cut = (ROOT / "assets" / "ekspresi" / f"{ekspresi}.png").as_uri()
            payload.update({"seri": s["seri"], "chip": s["chip"], "cutout": cut,
                            "handle": self.g2.get("handle", ""), "labelAi": self.g2.get("label_ai", "")})
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

    def shot_depan(self, fr: dict, total: int, out: Path) -> bool:
        """Gaya baru: benda di frame pembuka saja, latar transparan (ditumpuk di atas Nara yang berbicara)."""
        self.shot("reel", fr, 0, total, 1, out, False, talker=True)
        if not self.page.evaluate("() => lapisanDepan()"):
            return False
        self.page.screenshot(path=str(out), type="png", omit_background=True,
                             clip={"x": 0, "y": 0, "width": 1080, "height": 1920})
        return True

    def geometri_bicara(self, fr: dict) -> dict | None:
        """Posisi Nara berbicara = posisi foto Nara di cover gaya baru (lebar 1000 px, menempel di bawah).
        Kanan: pusat x 810; kiri: pusat x 270. Puncak kepala di y 962 (tinggi foto 958 px)."""
        if not self.seri:
            return None
        sisi = fr.get("nara") or {"tanggal-tua": "kiri"}.get(self.seri["seri"], "kanan")
        return {"cx": 270 if sisi == "kiri" else 810, "puncak": 962}

    def pakai_seri(self, post: dict):
        """Gaya baru aktif bila post punya "seri". Chip di pojok = kicker frame pembuka (mis. "Bedah Gaji #01")."""
        seri = post.get("seri")
        self.seri = {"seri": seri, "chip": post["frames"][0].get("kicker") or
                     (self.g2.get("seri") or {}).get(seri, {}).get("nama", "")} if seri else None

    def carousel(self, post: dict, out: Path):
        frames = post["frames"]
        for i, fr in enumerate(frames):
            self.shot("carousel", fr, i, len(frames), 1, out / f"{i + 1:02d}.jpg", True)

    def reel(self, post: dict, out: Path):
        frames = post["frames"]
        voices = self.voice.frames(post)          # [Path|None] per frame, atau [] tanpa suara
        talk = None
        if self.bicara:
            import bicara
            talk = bicara.clip_for(post["id"], voices[0] if voices else None)
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
                self.shot("reel", fr, i, len(frames), 1, b, False, talker=bool(talk) and i == 0)
                clips.append((b, d))
            self.shot("reel", frames[0], 0, len(frames), 1, out / "cover.jpg", True)
            if talk:
                import bicara
                base = td / "dasar.mp4"
                encode_reel(clips, base, pick_music(post["id"]), cues)
                starts = clip_starts(clips)
                total = sum(d for _, d in clips) - XFADE * (len(clips) - 1)
                end = min(suara.durasi(talk), (starts[1] + XFADE) if len(starts) > 1 else total)
                depan = td / "depan.png"
                geo = self.geometri_bicara(frames[0])
                if not (geo and self.shot_depan(frames[0], len(frames), depan)):
                    depan = None
                bicara.overlay(base, talk, out / "reel.mp4", end, total, td,
                               gaya=self.cfg["brand"].get("bicara_gaya", "potong"), mask=bicara.mask_for(post["id"]),
                               geo=geo, depan=depan)
                return
            if not self.animasi:
                encode_reel(clips, out / "reel.mp4", pick_music(post["id"]), cues)
                return
            box = self.page.evaluate("""() => { const i = document.querySelector('.presenter img');
                if (!i) return null; const r = i.getBoundingClientRect();
                return [r.x + r.width / 2, r.y + r.height / 2, r.width / 2 - 6]; }""")
            import avatar as avatar_anim  # butuh numpy & Pillow; diimpor hanya saat animasi aktif
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
                      f"volume={suara.penguat_db(vf):.1f}dB,adelay={ms}|{ms}[s{j}]")
            labels.append(f"[s{j}]")
        fg.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:normalize=0,"
                  f"atrim=0:{total:.3f},{LOUD}[aout]")
    else:
        fg.append(f"[bed]{LOUD}[aout]")
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
    keep = {k: post.get(k) for k in ("format", "frames", "seri")}
    cfg = load_config()
    keep["_suara"] = suara.sidik(cfg) if post.get("format") == "reel" else ""
    keep["_brand"] = {k: cfg["brand"].get(k) for k in ("avatar", "sapaan", "peran", "avatar_animasi")}
    keep["_anim"] = hashlib.sha1((ROOT / "engine" / "avatar.py").read_bytes()).hexdigest()[:10] \
        if cfg["brand"].get("avatar_animasi") and post.get("format") == "reel" else ""
    keep["_bicara"] = ""
    if cfg["brand"].get("avatar_bicara") and post.get("format") == "reel":
        clip = MEDIA_DIR / "_bicara" / f"{post.get('id')}.mp4"
        mask = MEDIA_DIR / "_bicara" / f"{post.get('id')}.masker.mp4"
        keep["_bicara"] = hashlib.sha1((ROOT / "engine" / "bicara.py").read_bytes()
                                       + str(cfg["brand"].get("bicara_gaya", "potong")).encode()
                                       + (clip.read_bytes() if clip.exists() else b"")
                                       + (mask.read_bytes() if mask.exists() else b"")
                                       + (mask.with_name(f"{post.get('id')}.suara").read_bytes()
                                          if mask.with_name(f"{post.get('id')}.suara").exists() else b"")
                                       + (mask.with_name(f"{post.get('id')}.depan.mp4").read_bytes()
                                          if mask.with_name(f"{post.get('id')}.depan.mp4").exists() else b"")
                                       ).hexdigest()[:12]
    keep["_musik"] = sorted(p.name for p in MUSIC.iterdir()) if MUSIC.exists() else []
    if post.get("seri"):
        g2 = cfg.get("gaya_baru") or {}
        nara = ROOT / g2.get("nara", "-")
        keep["_g2"] = [g2, hashlib.sha1(nara.read_bytes()).hexdigest()[:10] if nara.is_file() else ""]
        eks = sorted({f.get("ekspresi") for f in post.get("frames", []) if f.get("ekspresi")})
        keep["_ekspresi"] = {e: (hashlib.sha1(p.read_bytes()).hexdigest()[:10] if (p := ROOT / "assets" / "ekspresi" / f"{e}.png").is_file() else "")
                             for e in eks}       # file ekspresi ditambah/diganti → post dirender ulang
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
    if cfg.get("tahan_render") and not a.id:
        print("⏸ config.json: tahan_render=true. Render massal ditahan sampai contoh disetujui pemilik.")
        return 0
    everything = list(iter_posts())
    todo = []
    for p in everything:
        if a.id and p["id"] != a.id:
            continue
        if not a.id and (p["date"] < a.dari or (a.sampai and p["date"] > a.sampai)):
            continue
        if p.get("skip") or not slot_aktif(cfg, p["slot"], p["date"]):
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
                r.pakai_seri(p)
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
