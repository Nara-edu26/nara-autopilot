"""Buat halaman unggah TikTok: docs/tiktok/index.html (dijalankan di CI setelah render, sebelum situs terbit).

TikTok tidak bisa diisi otomatis secara publik (Content Posting API untuk aplikasi yang belum diaudit hanya
boleh memposting privat), jadi reel yang sama diunggah manual dari HP. Halaman ini menampilkan reel 7 hari
terakhir + hari ini: tombol unduh video, caption versi TikTok (tombol salin), dan pengingat label konten AI.

Caption TikTok = caption Instagram, kecuali ajakan "Komen KATA" yang dibalas lewat DM otomatis di Instagram
(BOCOR, TEMPLATE, KELAS): di TikTok tidak ada DM otomatis, jadi diarahkan ke Instagram.

Pakai:  python engine/tiktok.py
"""
from __future__ import annotations

import datetime as dt
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, approval_state, iter_posts, load_config, media_dir, now_wib, read_posted, slot_aktif, today_wib  # noqa: E402

OUT = ROOT / "docs" / "tiktok" / "index.html"
IG = "@edukasinarasi"
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
SIMPAN_HARI = 6          # media dihapus 7 hari setelah terbit (evergreen.bersih), jadi tampilkan 6 hari ke belakang


def tgl(d: str) -> str:
    x = dt.date.fromisoformat(d)
    return f"{HARI[x.weekday()]}, {x.day} {BULAN[x.month - 1]}"


def caption_tiktok(post: dict, cfg: dict) -> str:
    dm = [k for k, v in (cfg.get("kata_kunci") or {}).items() if "tidak ada DM" not in v]
    teks = post["caption"].strip()
    if dm:
        teks = re.sub(rf"\b(Komen|Ketik)\s+({'|'.join(map(re.escape, dm))})\b",
                      lambda m: f"{m[1]} {m[2]} di Instagram {IG}", teks)
    tags = " ".join("#" + h.lstrip("#") for h in post.get("hashtags", []))
    parts = [teks, "", cfg["brand"]["signature_caption"]]
    if tags:
        parts.append(tags)
    return "\n".join(parts)


def kartu(post: dict, cfg: dict, posted: dict) -> str:
    pid = post["id"]
    jam = cfg["slot"][post["slot"]]["jam_wib"][:3] + "07"
    waktu = f"{post['date']}T{jam}:00+07:00"
    ig = posted.get(pid, {}).get("permalink", "")
    ig_html = (f"<a href='{html.escape(ig)}' rel='noopener'>lihat di Instagram</a>" if ig else
               "<span class='muted'>terjadwal di Instagram</span>")
    cap = caption_tiktok(post, cfg)
    return f"""
<article class="post" id="{pid}" data-waktu="{waktu}">
  <header>
    <div><b>{jam} WIB · {html.escape(post['slot'])}</b> · {ig_html}</div>
    <label class="done"><input type="checkbox" data-pid="{pid}"> Sudah di TikTok</label>
  </header>
  <div class="belum">Belum terbit di Instagram. Unggah ke TikTok setelah pukul {jam} WIB.</div>
  <div class="isi">
    <video controls preload="none" playsinline poster="../media/{pid}/cover.jpg" src="../media/{pid}/reel.mp4"></video>
    <div class="aksi">
      <a class="btn" href="../media/{pid}/reel.mp4" download="nara-{pid}.mp4">⬇︎ Unduh video</a>
      <button class="btn alt" type="button" data-salin="{pid}">Salin caption</button>
    </div>
    <pre class="cap" id="cap-{pid}">{html.escape(cap)}</pre>
  </div>
</article>"""


def main() -> int:
    cfg = load_config()
    today = today_wib()
    mulai = max((dt.date.fromisoformat(today) - dt.timedelta(days=SIMPAN_HARI)).isoformat(),
                (cfg.get("tiktok") or {}).get("mulai", "0000"))   # sebelum tanggal ini suara Nara masih versi lama
    posted = {r["post_id"]: r for r in read_posted()}
    posts = []
    for p in iter_posts():
        if not (mulai <= p["date"] <= today) or p.get("format") != "reel" or not slot_aktif(cfg, p["slot"]):
            continue
        # hanya yang benar-benar terbit di Instagram; untuk hari ini juga yang masih terjadwal (sudah disetujui)
        if p["id"] not in posted and not (p["date"] == today and approval_state(p) == "disetujui"):
            continue
        if not (media_dir(p["id"]) / "reel.mp4").exists():
            continue
        posts.append(p)
    posts.sort(key=lambda p: (p["date"], ["pagi", "siang", "malam"].index(p["slot"])), reverse=True)

    days, cur = [], None
    for p in posts:
        if p["date"] != cur:
            cur = p["date"]
            days.append(f"<h2>{tgl(cur)}</h2>")
        days.append(kartu(p, cfg, posted))

    page = f"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex">
<title>Unggah ke TikTok</title>
<style>
:root{{--olive:#6B7B4F;--olive-dark:#4E5A39;--cream:#F3EDE2;--paper:#FBF8F2;--ink:#2B2B26;--muted:#6E6B5E;--line:#DDD5C4;--ok:#2F7D4A;--wait:#B26A00;color-scheme:light}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--olive:#7F9160;--olive-dark:#A9BB86;--cream:#1E1F1A;--paper:#272822;--ink:#ECE6D8;--muted:#A8A493;--line:#3A3B33;--ok:#6CC08A;--wait:#F0A64A;color-scheme:dark}}}}
:root[data-theme="dark"]{{--olive:#7F9160;--olive-dark:#A9BB86;--cream:#1E1F1A;--paper:#272822;--ink:#ECE6D8;--muted:#A8A493;--line:#3A3B33;--ok:#6CC08A;--wait:#F0A64A;color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--cream);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;padding:24px 16px 64px}}
main{{max-width:760px;margin:0 auto}}
h1{{font-size:26px;margin:0 0 4px}} h2{{font-size:18px;margin:28px 0 10px;color:var(--olive-dark)}}
.muted{{color:var(--muted)}} a{{color:var(--olive-dark)}}
.how{{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:14px 0}}
.how ol{{margin:6px 0 0;padding-left:20px}} .how li{{margin:5px 0}}
.btn{{display:inline-block;background:var(--olive);color:#F3EDE2;text-decoration:none;font:inherit;font-weight:700;border:0;border-radius:10px;padding:11px 14px;cursor:pointer}}
.btn.alt{{background:transparent;color:var(--olive-dark);border:2px solid var(--olive)}}
.post{{background:var(--paper);border:1px solid var(--line);border-left:5px solid var(--olive);border-radius:14px;padding:14px;margin:12px 0}}
.post header{{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}}
.post.selesai{{border-left-color:var(--ok);opacity:.6}} .post.nanti{{border-left-color:var(--wait)}}
.post.nanti .isi{{display:none}} .belum{{display:none;color:var(--wait);font-weight:600}} .post.nanti .belum{{display:block}}
.done{{font-size:14px;font-weight:600;display:flex;gap:6px;align-items:center;cursor:pointer}} .done input{{width:20px;height:20px}}
video{{width:min(300px,80vw);aspect-ratio:9/16;border-radius:12px;background:#000;display:block}}
.aksi{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}}
pre.cap{{white-space:pre-wrap;word-wrap:break-word;font:inherit;background:var(--cream);border-radius:10px;padding:10px 12px;margin:0}}
.ai{{background:color-mix(in srgb,var(--wait) 14%,transparent);border-radius:10px;padding:8px 10px;margin-top:8px;font-weight:600}}
</style>
</head>
<body>
<main>
<h1>Unggah ke TikTok</h1>
<div class="muted">Reel yang sama dengan Instagram · diperbarui {now_wib().strftime('%d-%m-%Y %H.%M')} WIB</div>
<section class="how">
<b>Cara unggah (±2 menit per video, dari HP)</b>
<ol>
<li>Tekan <b>Unduh video</b>, lalu <b>Salin caption</b>.</li>
<li>Buka TikTok → <b>+</b> → <b>Unggah</b> → pilih video yang baru diunduh → <b>Berikutnya</b>.</li>
<li>Tempel caption di kolom deskripsi.</li>
<li>Buka <b>Opsi lainnya</b> → nyalakan <b>Konten buatan AI</b> (AI-generated content).</li>
<li>Tekan <b>Posting</b>, lalu centang <b>Sudah di TikTok</b> di halaman ini.</li>
</ol>
<div class="ai">Label konten buatan AI wajib dinyalakan di setiap video: Nara adalah karakter AI yang realistis.</div>
<div class="muted" style="margin-top:8px;font-size:13px">Ajakan "Komen BOCOR/TEMPLATE/KELAS" diarahkan ke Instagram {IG}, karena DM otomatis hanya ada di sana.
Video tersedia 7 hari setelah terbit. Centang hanya tersimpan di perangkat ini.</div>
</section>
{''.join(days) if days else "<p class='muted'>Belum ada reel yang siap diunggah.</p>"}
</main>
<script>
(function(){{
  function simpan(k,v){{try{{localStorage.setItem(k,v)}}catch(e){{}}}}
  function baca(k){{try{{return localStorage.getItem(k)}}catch(e){{return null}}}}
  var now = Date.now();
  document.querySelectorAll('.post').forEach(function(el){{
    if (Date.parse(el.dataset.waktu) > now) el.classList.add('nanti');
  }});
  document.querySelectorAll('input[data-pid]').forEach(function(cb){{
    var k = 'tiktok-' + cb.dataset.pid, post = document.getElementById(cb.dataset.pid);
    cb.checked = baca(k) === '1'; post.classList.toggle('selesai', cb.checked);
    cb.addEventListener('change', function(){{ simpan(k, cb.checked ? '1' : '0'); post.classList.toggle('selesai', cb.checked); }});
  }});
  document.querySelectorAll('[data-salin]').forEach(function(b){{
    b.addEventListener('click', function(){{
      var t = document.getElementById('cap-' + b.dataset.salin).textContent, asli = b.textContent;
      function ok(){{ b.textContent = 'Tersalin ✓'; setTimeout(function(){{ b.textContent = asli; }}, 1800); }}
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(t).then(ok, function(){{ cadangan(t); ok(); }});
      }} else {{ cadangan(t); ok(); }}
    }});
  }});
  function cadangan(t){{ var a = document.createElement('textarea'); a.value = t; document.body.appendChild(a); a.select();
    try {{ document.execCommand('copy'); }} catch(e) {{}} document.body.removeChild(a); }}
}})();
</script>
</body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"Halaman TikTok: {len(posts)} reel → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
