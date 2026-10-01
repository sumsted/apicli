#!/usr/bin/env bash
# Build apicli.icns (macOS) and apicli.png from the pure-Python generator.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "==> Generating 1024px PNG"
"${PYTHON:-python3}" make_icon.py

if command -v iconutil >/dev/null 2>&1 && command -v sips >/dev/null 2>&1; then
  echo "==> Building apicli.iconset"
  rm -rf apicli.iconset
  mkdir apicli.iconset
  for size in 16 32 128 256 512; do
    sips -z "$size" "$size" icons/apicli_1024.png \
      --out "apicli.iconset/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z "$double" "$double" icons/apicli_1024.png \
      --out "apicli.iconset/icon_${size}x${size}@2x.png" >/dev/null
  done
  iconutil -c icns apicli.iconset -o icons/apicli.icns
  rm -rf apicli.iconset
  echo "==> Wrote icons/apicli.icns"
else
  echo "iconutil/sips not found; skipping .icns (macOS only). PNG is sufficient for Linux."
fi
