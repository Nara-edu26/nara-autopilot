"""Ringkas performa jadi keputusan. Hasilnya dibaca Claude setiap minggu sebelum menulis konten baru.

data/ringkasan_post.csv  angka terbaru per post (dipakai juga untuk memilih konten evergreen)
data/laporan.md          ringkasan per pola, format, slot + pemenang, yang kalah, dan pertanyaan audiens
"""
from __future__ import annotations

import csv
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, iter_posts, read_posted, today_wib  # noqa: E402


def num(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def med(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else 0.0


def main() -> int:
    posted = {r["post_id"]: r for r in read_posted()}
    latest: dict[str, dict] = {}
    mpath = DATA / "metrics.csv"
    if mpath.exists():
        with mpath.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                latest[r["post_id"]] = r          # file berurutan waktu, jadi baris terakhir = terbaru
    titles = {p["id"]: (p["frames"][0].get("title", "") if p.get("frames") else "") for p in iter_posts()}

    rows = []
    for pid, m in latest.items():
        reach = num(m.get("reach"))
        rows.append({
            "post_id": pid, "format": m["format"], "pola": m["pola"], "slot": m["slot"],
            "umur_jam": int(num(m["umur_jam"])), "reach": int(reach), "views": int(num(m.get("views"))),
            "saved": int(num(m.get("saved"))), "shares": int(num(m.get("shares"))),
            "comments": int(num(m.get("comments"))), "likes": int(num(m.get("likes"))),
            "simpan_per_1000": round(num(m.get("saved")) / reach * 1000, 1) if reach else 0,
            "share_per_1000": round(num(m.get("shares")) / reach * 1000, 1) if reach else 0,
            "ulang_dari": posted.get(pid, {}).get("ulang_dari", ""),
            "judul": re.sub(r"\*\*", "", titles.get(pid, ""))[:80],
        })
    DATA.mkdir(exist_ok=True)
    with (DATA / "ringkasan_post.csv").open("w", encoding="utf-8", newline="") as fh:
        fields = list(rows[0].keys()) if rows else ["post_id"]
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["post_id"]))

    matang = [r for r in rows if r["umur_jam"] >= 72]
    L = [f"# Laporan performa Nara · {today_wib()}", ""]
    L.append(f"Post terbit: {len(posted)} · punya data: {len(rows)} · sudah ≥72 jam (dinilai): {len(matang)}")
    akun = DATA / "akun.csv"
    if akun.exists():
        with akun.open(encoding="utf-8") as fh:
            a = list(csv.DictReader(fh))
        if a:
            f0, f1 = a[0], a[-1]
            L.append(f"Follower: {f1['followers']} (awal data {f0['tanggal']}: {f0['followers']}).")
    L.append("")
    if len(matang) < 6:
        L += ["Data belum cukup untuk mengambil keputusan (butuh minimal 6 post berumur ≥72 jam).",
              "Lanjutkan campuran pola sesuai rencana 100 hari.", ""]
    else:
        base = med([r["reach"] for r in matang])
        L += [f"Median reach akun: **{base:,.0f}**", ""]
        for key, judul in (("pola", "Per pola"), ("format", "Per format"), ("slot", "Per slot")):
            g = defaultdict(list)
            for r in matang:
                g[r[key]].append(r)
            L += [f"## {judul}", "", "| " + key + " | n | median reach | × median akun | simpan/1000 | share/1000 |",
                  "|---|---|---|---|---|---|"]
            for k, rs in sorted(g.items(), key=lambda kv: -med([r["reach"] for r in kv[1]])):
                mr = med([r["reach"] for r in rs])
                L.append(f"| {k} | {len(rs)} | {mr:,.0f} | {mr / base if base else 0:.2f} | "
                         f"{med([r['simpan_per_1000'] for r in rs]):.1f} | {med([r['share_per_1000'] for r in rs]):.1f} |")
            L.append("")
        win = [r for r in matang if base and r["reach"] >= 5 * base]
        L += ["## Pemenang (reach ≥ 5× median) → buat 3 variasi dalam 7 hari", ""]
        L += [f"- {r['post_id']} [{r['pola']}/{r['format']}] reach {r['reach']:,}: {r['judul']}" for r in win] or ["- belum ada"]
        L += ["", "## 5 teratas menurut simpan per 1.000 reach (bahan carousel & produk)", ""]
        for r in sorted(matang, key=lambda r: -r["simpan_per_1000"])[:5]:
            L.append(f"- {r['post_id']} [{r['pola']}] simpan/1000 {r['simpan_per_1000']}: {r['judul']}")
        L += ["", "## 5 terbawah menurut reach", ""]
        for r in sorted(matang, key=lambda r: r["reach"])[:5]:
            L.append(f"- {r['post_id']} [{r['pola']}/{r['format']}/{r['slot']}] reach {r['reach']:,}: {r['judul']}")
        L.append("")

    kpath = DATA / "komentar.csv"
    if kpath.exists():
        with kpath.open(encoding="utf-8") as fh:
            ks = list(csv.DictReader(fh))
        kw = Counter()
        for k in ks:
            for w in ("BOCOR", "TEMPLATE", "KELAS", "SUDAH"):
                if w.lower() in k["teks"].lower():
                    kw[w] += 1
        qs = [k["teks"] for k in ks[-400:] if "?" in k["teks"] and len(k["teks"]) > 12][-15:]
        L += ["## Kata kunci di komentar (semua waktu)", ""]
        L += [f"- {w}: {n}" for w, n in kw.most_common()] or ["- belum ada"]
        L += ["", "## Pertanyaan audiens terbaru (bahan konten & ide produk)", ""]
        L += [f"- {q}" for q in qs] or ["- belum ada"]
        L.append("")

    (DATA / "laporan.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
