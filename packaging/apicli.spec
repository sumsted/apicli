"""PyInstaller spec for the apicli desktop app.

Bundles the Python core, the FastAPI server, pywebview, and the prebuilt SPA in
``web/dist``. Textual and the tree-sitter stack are excluded because the web/
desktop UI does not use them.

Build:  pyinstaller packaging/apicli.spec --noconfirm
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent
DIST = ROOT / "web" / "dist"

if not DIST.is_dir():
    raise SystemExit(
        f"Missing {DIST}. Run `npm --prefix web run build` before packaging."
    )

datas = [(str(DIST), "web/dist")]

hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("fastapi")
    + collect_submodules("starlette")
    + ["anyio._backends._asyncio"]
)

excludes = [
    "textual",
    "rich",
    "tree_sitter",
    "tree_sitter_languages",
    "pygments",
    "markdown_it",
    "pytest",
    "tkinter",
    "test",
]

icon = ROOT / "packaging" / "icons" / "apicli.icns"
icon_arg = str(icon) if icon.exists() else None

a = Analysis(
    [str(ROOT / "packaging" / "entrypoint.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="apicli",
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="apicli",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="apicli.app",
        icon=icon_arg,
        bundle_identifier="com.scott.apicli",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleName": "apicli",
            "CFBundleDisplayName": "apicli",
        },
    )
