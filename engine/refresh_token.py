"""Perpanjang token Instagram (berlaku 60 hari) dan simpan kembali ke GitHub Secrets.

Butuh secret GH_PAT (fine-grained token dengan izin Secrets: Read and write untuk repo ini).
Tanpa GH_PAT, token tetap diperpanjang di sisi Instagram, tetapi secret tidak bisa diperbarui;
workflow akan gagal supaya kamu mendapat email peringatan.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import env, load_config  # noqa: E402
from ig import IG, IGError  # noqa: E402


def main() -> int:
    token = env("IG_ACCESS_TOKEN")
    if not token:
        print("IG_ACCESS_TOKEN belum diisi.")
        return 1
    cfg = load_config()
    try:
        res = IG(token, cfg["instagram"]["api_host"]).refresh_token()
    except IGError as e:
        print(f"✗ Gagal memperpanjang token: {e}")
        if e.token_mati:
            print("Token sudah mati. Buat token baru (SETUP.md langkah 4) lalu perbarui secret IG_ACCESS_TOKEN.")
        return 1
    new = res["access_token"]
    days = int(res.get("expires_in", 0)) // 86400
    print(f"::add-mask::{new}")
    print(f"✓ Token diperpanjang, berlaku sekitar {days} hari lagi.")
    if new == token:
        return 0
    pat, repo = env("GH_PAT"), env("GITHUB_REPOSITORY")
    if not (pat and repo):
        print("✗ Token baru berbeda, tapi GH_PAT belum diisi sehingga secret tidak bisa diperbarui.")
        return 1
    subprocess.run(["gh", "secret", "set", "IG_ACCESS_TOKEN", "--repo", repo, "--body", new],
                   check=True, env={**os.environ, "GH_TOKEN": pat})
    print("✓ Secret IG_ACCESS_TOKEN diperbarui.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
