"""Buat halaman tinjau: docs/tinjau/index.html (dijalankan di CI setelah render, sebelum situs diterbitkan).

Halaman ini menampilkan semua post yang belum terbit dalam 15 hari ke depan, lengkap dengan gambar/video,
caption persis seperti yang akan terbit, hitungan angka, dan status persetujuan.
Pemilik membaca halaman ini lalu menekan tombol "Setujui post" di GitHub Actions.

Pakai:  python engine/tinjau.py
"""
from __future__ import annotations

import datetime as dt
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (ROOT, approval_state, build_caption, content_hash, iter_posts, load_config,  # noqa: E402
                    media_dir, media_files, now_wib, read_posted, repo_slug, today_wib)
from validate import frame_texts, validate_post  # noqa: E402

OUT = ROOT / "docs" / "tinjau" / "index.html"
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
STATUS = {
    "menunggu": ("Menunggu persetujuan", "wait"),
    "berubah": ("Isi berubah, setujui ulang", "wait"),
    "disetujui": ("Disetujui", "ok"),
    "dilewati": ("Dilewati, tidak terbit", "skip"),
}


def tgl(d: str) -> str:
    x = dt.date.fromisoformat(d)
    return f"{HARI[x.weekday()]}, {x.day} {BULAN[x.month - 1]} {x.year}"


def angka(x) -> str:
    v = float(x)
    return f"{v:,.0f}".replace(",", ".") if v == int(v) else f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def bold(s: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(s))


def post_card(post: dict, cfg: dict, everything: list[dict]) -> str:
    pid = post["id"]
    state = approval_state(post)
    label, cls = STATUS[state]
    jam = cfg["slot"][post["slot"]]["jam_wib"][:3] + "07"
    errs, warns = validate_post(post, everything)

    files = media_files(post)
    have = all((media_dir(pid) / f).exists() for f in files)
    if have and post["format"] == "carousel":
        media = "<div class='slides'>" + "".join(
            f"<img loading='lazy' src='../media/{pid}/{f}' alt='Slide {i + 1}'>" for i, f in enumerate(files)) + "</div>"
    elif have:
        media = (f"<video controls preload='none' playsinline poster='../media/{pid}/cover.jpg' "
                 f"src='../media/{pid}/reel.mp4'></video>")
    else:
        media = "<p class='note'>Media belum dirender. Teks slide ada di bawah.</p>"

    slides = []
    for i, fr in enumerate(post.get("frames", []), 1):
        parts = " · ".join(bold(t) for _, t in frame_texts(fr))
        slides.append(f"<li><span class='ft'>{html.escape(fr.get('type', ''))}</span> {parts}</li>")

    calcs = []
    for c in post.get("calc") or []:
        calcs.append(f"<li><code>{html.escape(str(c['expr']))}</code> = {angka(c['expect'])}</li>")
    for g in post.get("given") or []:
        calcs.append(f"<li>Angka contoh/diberikan: {angka(g)}</li>")

    problems = "".join(f"<li class='err'>✗ {html.escape(e)} (post ini tidak akan terbit)</li>" for e in errs)
    problems += "".join(f"<li class='warn'>! {html.escape(w)}</li>" for w in warns)

    ulang = (f" · ulang dari {html.escape(post['ulang_dari'])}" if post.get("ulang_dari") else "")
    return f"""
<article class="post {cls}" id="{pid}">
  <header>
    <div><b>{jam} WIB · {html.escape(post['slot'])}</b> · {html.escape(post['format'])} · pola {html.escape(post.get('pattern', '?'))}{ulang}</div>
    <span class="chip {cls}">{label}</span>
  </header>
  <div class="pid">Kode: <code>{pid}</code> <span class="muted">· sidik isi {content_hash(post)[:6]}</span></div>
  {media}
  <h3>Caption (persis seperti terbit)</h3>
  <pre class="cap">{html.escape(build_caption(post, cfg))}</pre>
  <details><summary>Teks tiap slide ({len(slides)})</summary><ol class="frames">{''.join(slides)}</ol></details>
  {"<h3>Cek angka</h3><ul class='calc'>" + ''.join(calcs) + "</ul>" if calcs else ""}
  {"<ul class='probs'>" + problems + "</ul>" if problems else ""}
</article>"""


def main() -> int:
    cfg = load_config()
    today = today_wib()
    end = (dt.date.fromisoformat(today) + dt.timedelta(days=15)).isoformat()
    posted = {r["post_id"] for r in read_posted()}
    everything = list(iter_posts())
    posts = [p for p in everything if today <= p["date"] <= end and p["id"] not in posted]
    posts.sort(key=lambda p: (p["date"], ["pagi", "siang", "malam"].index(p["slot"])))

    counts = {k: 0 for k in STATUS}
    for p in posts:
        counts[approval_state(p)] += 1
    waiting = counts["menunggu"] + counts["berubah"]

    days, cur = [], None
    for p in posts:
        if p["date"] != cur:
            cur = p["date"]
            days.append(f"<h2>{tgl(cur)}</h2>")
        days.append(post_card(p, cfg, everything))

    action = f"https://github.com/{repo_slug(cfg)}/actions/workflows/setujui.yml"
    banner = (f"<div class='todo'><b>{waiting} post menunggu persetujuanmu.</b> Post yang belum disetujui tidak akan terbit.</div>"
              if waiting else "<div class='done'>Semua post di halaman ini sudah ditinjau. Tidak ada yang perlu dilakukan.</div>")
    page = f"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex">
<title>Tinjau post Nara</title>
<style>
:root{{--olive:#6B7B4F;--olive-dark:#4E5A39;--cream:#F3EDE2;--paper:#FBF8F2;--ink:#2B2B26;--muted:#6E6B5E;--line:#DDD5C4;--ok:#2F7D4A;--wait:#B26A00;--skip:#8A8578;--err:#B3261E;color-scheme:light}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--olive:#7F9160;--olive-dark:#A9BB86;--cream:#1E1F1A;--paper:#272822;--ink:#ECE6D8;--muted:#A8A493;--line:#3A3B33;--ok:#6CC08A;--wait:#F0A64A;--skip:#A8A493;--err:#F2827A;color-scheme:dark}}}}
:root[data-theme="dark"]{{--olive:#7F9160;--olive-dark:#A9BB86;--cream:#1E1F1A;--paper:#272822;--ink:#ECE6D8;--muted:#A8A493;--line:#3A3B33;--ok:#6CC08A;--wait:#F0A64A;--skip:#A8A493;--err:#F2827A;color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--cream);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;padding:24px 16px 64px}}
main{{max-width:760px;margin:0 auto}}
h1{{font-size:26px;margin:0 0 4px}} h2{{font-size:18px;margin:32px 0 10px;color:var(--olive-dark)}} h3{{font-size:13px;margin:14px 0 6px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}}
.muted,.note{{color:var(--muted)}}
.how{{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:14px 0}}
.how ol{{margin:6px 0 0;padding-left:20px}} .how li{{margin:4px 0}}
a.btn{{display:inline-block;background:var(--olive);color:#F3EDE2;text-decoration:none;font-weight:700;border-radius:10px;padding:10px 14px;margin-top:8px}}
.todo,.done{{border-radius:12px;padding:12px 14px;margin:10px 0;font-weight:600}}
.todo{{background:color-mix(in srgb,var(--wait) 14%,transparent);color:var(--ink)}} .done{{background:color-mix(in srgb,var(--ok) 14%,transparent)}}
.post{{background:var(--paper);border:1px solid var(--line);border-left:5px solid var(--wait);border-radius:14px;padding:14px;margin:12px 0}}
.post.ok{{border-left-color:var(--ok)}} .post.skip{{border-left-color:var(--skip);opacity:.75}}
.post header{{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:center}}
.chip{{font-size:12px;font-weight:700;border-radius:999px;padding:3px 10px;color:#fff;background:var(--wait)}} .chip.ok{{background:var(--ok)}} .chip.skip{{background:var(--skip)}}
.pid{{font-size:13px;margin:6px 0 10px}} code{{font-size:13px;background:color-mix(in srgb,var(--ink) 8%,transparent);border-radius:6px;padding:1px 6px}}
.slides{{display:flex;gap:8px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:6px}}
.slides img{{width:min(260px,72vw);aspect-ratio:4/5;object-fit:cover;border-radius:10px;scroll-snap-align:start;flex:none;border:1px solid var(--line)}}
video{{width:min(300px,80vw);aspect-ratio:9/16;border-radius:12px;background:#000;display:block}}
pre.cap{{white-space:pre-wrap;word-wrap:break-word;font:inherit;background:var(--cream);border-radius:10px;padding:10px 12px;margin:0}}
.frames{{padding-left:20px;font-size:14px}} .frames li{{margin:4px 0}} .ft{{font-size:11px;text-transform:uppercase;color:var(--muted)}}
.calc{{padding-left:20px;margin:0}} .probs{{list-style:none;padding:0;margin:10px 0 0}} .err{{color:var(--err);font-weight:600}} .warn{{color:var(--wait)}}
details summary{{cursor:pointer;margin-top:10px;color:var(--olive-dark);font-weight:600}}
</style>
</head>
<body>
<main>
<h1>Tinjau post Nara</h1>
<div class="muted">Diperbarui {now_wib().strftime('%d-%m-%Y %H.%M')} WIB · {len(posts)} post belum terbit, s.d. {tgl(end)}</div>
{banner}
<section class="how">
<b>Cara menyetujui (±15 menit, sekali seminggu)</b>
<ol>
<li>Baca setiap post berlabel <b>Menunggu</b>: gambar atau video, caption, dan cek angka.</li>
<li>Kalau ada yang tidak cocok, catat kodenya (contoh <code>2026-10-27-siang</code>). Post itu tidak akan terbit.</li>
<li>Buka tombol di bawah → klik <b>Run workflow</b> → isi kolom <b>lewati</b> dengan kode yang tidak disetujui (kosongkan kalau semua oke) → klik <b>Run workflow</b> hijau.</li>
</ol>
<a class="btn" href="{action}" rel="noopener">Setujui post di GitHub →</a>
<div class="muted" style="margin-top:8px;font-size:13px">Atau tulis ke Claude: "setuju semua" atau "setuju, kecuali &lt;kode&gt;". Persetujuan ini memenuhi kewajiban tinjauan manusia untuk konten AI (POJK 6/2026).</div>
</section>
{''.join(days) if days else "<p class='note'>Belum ada post di antrean untuk 15 hari ke depan.</p>"}
</main>
</body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"Halaman tinjau: {len(posts)} post, {waiting} menunggu → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
