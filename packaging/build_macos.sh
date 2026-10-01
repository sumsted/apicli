#!/usr/bin/env bash
# Build the apicli desktop app for macOS (.app, and .dmg if create-dmg/hdiutil).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Building SPA"
npm --prefix web run build

echo "==> Running PyInstaller"
"${PYTHON:-python3}" -m PyInstaller packaging/apicli.spec \
  --noconfirm --clean \
  --distpath dist --workpath build/pyinstaller

APP="dist/apicli.app"
echo "==> Built $APP"

if command -v hdiutil >/dev/null 2>&1; then
  echo "==> Creating dist/apicli.dmg"
  rm -f dist/apicli.dmg
  hdiutil create -volname apicli -srcfolder "$APP" -ov -format UDZO dist/apicli.dmg
  echo "==> Built dist/apicli.dmg"
fi

echo "Note: the bundle is unsigned. On first launch, right-click the app and"
echo "choose Open to bypass Gatekeeper."
