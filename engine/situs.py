"""Isi tautan dari config.json ke halaman situs sebelum diterbitkan (hanya di CI, tidak di-commit)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_config  # noqa: E402


def main() -> int:
    cfg = load_config()
    t = cfg["tautan"]
    rep = {"__TAUTAN_TEMPLATE__": t["template_5_pos"], "__TAUTAN_TOKO__": t["toko"],
           "__TAUTAN_KALKULATOR__": t["kalkulator"], "__EMAIL_KONTAK__": cfg.get("email_kontak", "")}
    n = 0
    for p in (ROOT / "docs").rglob("*.html"):
        s = p.read_text(encoding="utf-8")
        new = s
        for k, v in rep.items():
            new = new.replace(k, v)
        if new != s:
            p.write_text(new, encoding="utf-8")
            n += 1
    print(f"{n} halaman diisi tautan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
