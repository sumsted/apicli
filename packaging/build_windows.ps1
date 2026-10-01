# Build the apicli desktop app for Windows (dist/apicli/apicli.exe).
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "==> Building SPA"
npm --prefix web run build

Write-Host "==> Running PyInstaller"
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
& $Python -m PyInstaller packaging/apicli.spec `
  --noconfirm --clean `
  --distpath dist --workpath build/pyinstaller

Write-Host "==> Built dist/apicli/apicli.exe"
Write-Host "Wrap dist/apicli into an installer (e.g. Inno Setup) if desired."
