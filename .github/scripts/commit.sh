#!/usr/bin/env bash
# Pakai: commit.sh "pesan commit" path1 path2 ...
# Commit perubahan (jika ada) lalu push ke main, dengan rebase + coba ulang bila bentrok.
set -euo pipefail
msg="$1"; shift
git config user.name  "nara-autopilot[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -- "$@" 2>/dev/null || true
if git diff --cached --quiet; then
  echo "Tidak ada perubahan untuk di-commit."
  exit 0
fi
git commit -m "$msg"
for i in 1 2 3 4 5; do
  if git pull --rebase --autostash origin main && git push origin HEAD:main; then
    echo "✓ Terkirim."
    exit 0
  fi
  echo "Bentrok, coba lagi ($i)…"; sleep $((i * 5))
done
echo "✗ Gagal push setelah 5 kali."; exit 1
