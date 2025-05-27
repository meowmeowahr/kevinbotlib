# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['../../src/kevinbotlib/apps/log_downloader/log_downloader.py'],
    pathex=[],
    binaries=[],
    datas=[('../../src/kevinbotlib/ui/base.qss', '.')],
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
    name='kevinbotlib_log_downloader',
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
    icon=['../../resources/kevinbotlib/app_icons/log-downloader-small.png'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='kevinbotlib_log_downloader',
)
app = BUNDLE(coll,
         name='KevinbotLib Log Downloader.app',
         icon='../../resources/kevinbotlib/app_icons/macos/log-downloader/AppIcon.icns',
         bundle_identifier=None)