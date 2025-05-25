pyside6-rcc.exe resources/kevinbotlib/theme_resources.qrc -o src/kevinbotlib/ui/resources_rc.py
pyside6-rcc.exe resources/kevinbotlib/controlconsole_resources.qrc -o src/kevinbotlib/apps/control_console/resources_rc.py
pyside6-rcc.exe resources/kevinbotlib/dashboard_resources.qrc -o src/kevinbotlib/apps/dashboard/resources_rc.py
pyside6-rcc.exe resources/kevinbotlib/logdownloader_resources.qrc -o src/kevinbotlib/apps/log_downloader/resources_rc.py
pyside6-rcc.exe resources/kevinbotlib/logviewer_resources.qrc -o src/kevinbotlib/apps/log_viewer/resources_rc.py
(Get-Content src/kevinbotlib/ui/resources_rc.py) -replace 'PySide6', 'qtpy' | Set-Content src/kevinbotlib/ui/resources_rc.py
(Get-Content src/kevinbotlib/apps/control_console/resources_rc.py) -replace 'PySide6', 'qtpy' | Set-Content src/kevinbotlib/apps/control_console/resources_rc.py
(Get-Content src/kevinbotlib/apps/dashboard/resources_rc.py) -replace 'PySide6', 'qtpy' | Set-Content src/kevinbotlib/apps/dashboard/resources_rc.py
(Get-Content src/kevinbotlib/apps/log_downloader/resources_rc.py) -replace 'PySide6', 'qtpy' | Set-Content src/kevinbotlib/apps/log_downloader/resources_rc.py
(Get-Content src/kevinbotlib/apps/log_viewer/resources_rc.py) -replace 'PySide6', 'qtpy' | Set-Content src/kevinbotlib/apps/log_viewer/resources_rc.py
Write-Output 'RCC Resources Compiled'