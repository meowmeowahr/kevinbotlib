Write-Output "KevinbotLib Build"

# Run PyInstaller builds
pyinstaller scripts/build/kevinbotlib_dashboard.spec --noconfirm
pyinstaller scripts/build/kevinbotlib_console.spec --noconfirm
pyinstaller scripts/build/kevinbotlib_log_downloader.spec --noconfirm
pyinstaller scripts/build/kevinbotlib_log_viewer.spec --noconfirm
pyinstaller scripts/build/kevinbotlib.spec --noconfirm

# Create output directory
$distAll = "dist/all"
New-Item -ItemType Directory -Force -Path $distAll | Out-Null

# Move built executables
Move-Item -Force dist/kevinbotlib_dashboard/kevinbotlib_dashboard.exe $distAll/kevinbotlib_dashboard.exe
Move-Item -Force dist/kevinbotlib_console/kevinbotlib_console.exe $distAll/kevinbotlib_console.exe
Move-Item -Force dist/kevinbotlib_log_downloader/kevinbotlib_log_downloader.exe $distAll/kevinbotlib_log_downloader.exe
Move-Item -Force dist/kevinbotlib_log_viewer/kevinbotlib_log_viewer.exe $distAll/kevinbotlib_log_viewer.exe
Move-Item -Force dist/kevinbotlib/kevinbotlib.exe $distAll/kevinbotlib.exe

# Merge all _internal folders into one
$internalDir = "$distAll/_internal"
New-Item -ItemType Directory -Force -Path $internalDir | Out-Null

Copy-Item -Recurse -Force dist/kevinbotlib_dashboard/_internal/* $internalDir -ErrorAction SilentlyContinue
Copy-Item -Recurse -Force dist/kevinbotlib_console/_internal/* $internalDir -ErrorAction SilentlyContinue
Copy-Item -Recurse -Force dist/kevinbotlib_log_downloader/_internal/* $internalDir -ErrorAction SilentlyContinue
Copy-Item -Recurse -Force dist/kevinbotlib_log_viewer/_internal/* $internalDir -ErrorAction SilentlyContinue
Copy-Item -Recurse -Force dist/kevinbotlib/_internal/* $internalDir -ErrorAction SilentlyContinue

# Copy binary license file
Copy-Item BINARY-LICENSE $distAll/BINARY-LICENSE

# Create ZIP archive (GLIBC version not used here)
$zipName = "kevinbotlib-windows-x64.zip"
Compress-Archive -Path "$distAll\*" -DestinationPath "dist\$zipName" -Force

Write-Output "Packaged into dist\$zipName"
