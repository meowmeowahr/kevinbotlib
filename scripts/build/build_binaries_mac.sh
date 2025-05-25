#!/bin/bash

# Banner
echo " █████   ████                       ███             █████               █████    █████        ███  █████        ███████████              ███  ████      █████"
echo "░░███   ███░                       ░░░             ░░███               ░░███    ░░███        ░░░  ░░███        ░░███░░░░░███            ░░░  ░░███     ░░███ "
echo " ░███  ███     ██████  █████ █████ ████  ████████   ░███████   ██████  ███████   ░███        ████  ░███████     ░███    ░███ █████ ████ ████  ░███   ███████"
echo " ░███████     ███░░███░░███ ░░███ ░░███ ░░███░░███  ░███░░███ ███░░███░░░███░    ░███       ░░███  ░███░░███    ░██████████ ░░███ ░███ ░░███  ░███  ███░░███ "
echo " ░███░░███   ░███████  ░███  ░███  ░███  ░███ ░███  ░███ ░███░███ ░███  ░███     ░███        ░███  ░███ ░███    ░███░░░░░███ ░███ ░███  ░███  ░███ ░███ ░███ "
echo " ░███ ░░███  ░███░░░   ░░███ ███   ░███  ░███ ░███  ░███ ░███░███ ░███  ░███ ███ ░███      █ ░███  ░███ ░███    ░███    ░███ ░███ ░███  ░███  ░███ ░███ ░███ "
echo " █████ ░░████░░██████   ░░█████    █████ ████ █████ ████████ ░░██████   ░░█████  ███████████ █████ ████████     ███████████  ░░████████ █████ █████░░████████"
echo "░░░░░   ░░░░  ░░░░░░     ░░░░░    ░░░░░ ░░░░ ░░░░░ ░░░░░░░░   ░░░░░░     ░░░░░  ░░░░░░░░░░░ ░░░░░ ░░░░░░░░     ░░░░░░░░░░░    ░░░░░░░░ ░░░░░ ░░░░░  ░░░░░░░░ "
echo

# PyInstaller builds
pyinstaller scripts/build/kevinbotlib_dashboard.spec --noconfirm
pyinstaller scripts/build/kevinbotlib_console.spec --noconfirm
pyinstaller scripts/build/kevinbotlib_log_downloader.spec --noconfirm
pyinstaller scripts/build/kevinbotlib_log_viewer.spec --noconfirm
pyinstaller scripts/build/kevinbotlib.spec --noconfirm

# Move builds to dist/all
mkdir -p dist/all
mv "dist/KevinbotLib Dashboard.app" dist/all/
mv "dist/KevinbotLib Control Console.app" dist/all/
mv "dist/KevinbotLib Log Downloader.app" dist/all/
mv "dist/KevinbotLib Log Viewer.app" dist/all/
cp BINARY-LICENSE dist/apps/BINARY-LICENSE

# CLI binaries
mkdir -p dist/cli
mv dist/kevinbotlib/kevinbotlib dist/cli/kevinbotlib
mv dist/kevinbotlib/_internal dist/cli/_internal
cp BINARY-LICENSE dist/cli/BINARY-LICENSE

# Package CLI as tar.gz
PKNAMECLI="kevinbotlib-cli-tools-macos-$(arch).tar.gz"
tar -czvf dist/$PKNAMECLI -C dist/cli/ .

# Package Apps as DMG
PKNAMEAPPS="kevinbotlib-apps-macos-$(arch).dmg"
mkdir -p dist/apps
cp -R dist/all/*.app dist/apps/

# Create DMG
hdiutil create -volname "KevinbotLib Apps" -srcfolder dist/apps -ov -format UDZO dist/$PKNAMEAPPS

echo "CLI packaged as $PKNAMECLI"
echo "Apps packaged as $PKNAMEAPPS"
