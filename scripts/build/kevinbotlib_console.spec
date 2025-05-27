# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['../../src/kevinbotlib/apps/control_console/control_console.py'],
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
    name='kevinbotlib_console',
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
    icon=['../../resources/kevinbotlib/app_icons/console.png'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='kevinbotlib_console',
)
app = BUNDLE(coll,
         name='KevinbotLib Control Console.app',
         icon='../../resources/kevinbotlib/app_icons/macos/console/AppIcon.icns',
         bundle_identifier=None)