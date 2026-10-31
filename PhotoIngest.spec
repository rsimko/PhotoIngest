# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

ttkbootstrap_datas = collect_data_files("ttkbootstrap")

exiftool_lib_datas = [
    ("bin/lib", "bin/lib"),
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[
        ("bin/exiftool", "bin"),
    ],
    datas=[
        ("config/settings.json", "config"),
        ("config/templates.json", "config"),
        ("PhotoIngest.icns", "."),
        ("PhotoIngest.png", "."),
        ("bin/exiftool", "bin"),
    ] + exiftool_lib_datas + ttkbootstrap_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PhotoIngest",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="PhotoIngest.icns",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PhotoIngest",
)

app = BUNDLE(
    coll,
    name="PhotoIngest.app",
    icon="PhotoIngest.icns",
    bundle_identifier="com.rsimko.photoingest",
)
