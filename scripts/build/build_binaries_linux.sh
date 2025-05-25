echo " █████   ████                       ███             █████               █████    █████        ███  █████        ███████████              ███  ████      █████"
echo "░░███   ███░                       ░░░             ░░███               ░░███    ░░███        ░░░  ░░███        ░░███░░░░░███            ░░░  ░░███     ░░███ "
echo " ░███  ███     ██████  █████ █████ ████  ████████   ░███████   ██████  ███████   ░███        ████  ░███████     ░███    ░███ █████ ████ ████  ░███   ███████"
echo " ░███████     ███░░███░░███ ░░███ ░░███ ░░███░░███  ░███░░███ ███░░███░░░███░    ░███       ░░███  ░███░░███    ░██████████ ░░███ ░███ ░░███  ░███  ███░░███ "
echo " ░███░░███   ░███████  ░███  ░███  ░███  ░███ ░███  ░███ ░███░███ ░███  ░███     ░███        ░███  ░███ ░███    ░███░░░░░███ ░███ ░███  ░███  ░███ ░███ ░███ "
echo " ░███ ░░███  ░███░░░   ░░███ ███   ░███  ░███ ░███  ░███ ░███░███ ░███  ░███ ███ ░███      █ ░███  ░███ ░███    ░███    ░███ ░███ ░███  ░███  ░███ ░███ ░███ "
echo " █████ ░░████░░██████   ░░█████    █████ ████ █████ ████████ ░░██████   ░░█████  ███████████ █████ ████████     ███████████  ░░████████ █████ █████░░████████"
echo "░░░░░   ░░░░  ░░░░░░     ░░░░░    ░░░░░ ░░░░ ░░░░░ ░░░░░░░░   ░░░░░░     ░░░░░  ░░░░░░░░░░░ ░░░░░ ░░░░░░░░     ░░░░░░░░░░░    ░░░░░░░░ ░░░░░ ░░░░░  ░░░░░░░░ "
echo

pyinstaller scripts/build/kevinbotlib_dashboard.spec --noconfirm
pyinstaller scripts/build/kevinbotlib_console.spec --noconfirm
pyinstaller scripts/build/kevinbotlib_log_downloader.spec --noconfirm
pyinstaller scripts/build/kevinbotlib_log_viewer.spec --noconfirm
pyinstaller scripts/build/kevinbotlib.spec --noconfirm

mkdir dist/all/
mv dist/kevinbotlib_dashboard/kevinbotlib_dashboard dist/all/kevinbotlib_dashboard
mv dist/kevinbotlib_console/kevinbotlib_console dist/all/kevinbotlib_console
mv dist/kevinbotlib_log_downloader/kevinbotlib_log_downloader dist/all/kevinbotlib_log_downloader
mv dist/kevinbotlib_log_viewer/kevinbotlib_log_viewer dist/all/kevinbotlib_log_viewer
mv dist/kevinbotlib/kevinbotlib dist/all/kevinbotlib

mkdir -p dist/all/_internal
cp -r dist/kevinbotlib_dashboard/_internal/. dist/all/_internal
cp -r dist/kevinbotlib_console/_internal/. dist/all/_internal
cp -r dist/kevinbotlib_log_downloader/_internal/. dist/all/_internal
cp -r dist/kevinbotlib_log_viewer/_internal/. dist/all/_internal
cp -r dist/kevinbotlib/_internal/. dist/all/_internal

cp BINARY-LICENSE dist/all/BINARY-LICENSE