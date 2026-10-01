#!/usr/bin/env bash
# Build the apicli desktop app for Linux (dist/apicli/apicli).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Building SPA"
npm --prefix web run build

echo "==> Running PyInstaller"
"${PYTHON:-python3}" -m PyInstaller packaging/apicli.spec \
  --noconfirm --clean \
  --distpath dist --workpath build/pyinstaller

echo "==> Built dist/apicli/apicli"
echo "Requires WebKitGTK at runtime (e.g. libwebkit2gtk on Debian/Ubuntu)."
echo "Optional: wrap dist/apicli into an AppImage with appimagetool."
