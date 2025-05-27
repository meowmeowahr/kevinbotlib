#!/bin/bash
pyside6-rcc resources/kevinbotlib/theme_resources.qrc -o src/kevinbotlib/ui/resources_rc.py --no-compress
pyside6-rcc resources/kevinbotlib/controlconsole_resources.qrc -o src/kevinbotlib/apps/control_console/resources_rc.py --no-compress
pyside6-rcc resources/kevinbotlib/dashboard_resources.qrc -o src/kevinbotlib/apps/dashboard/resources_rc.py --no-compress
pyside6-rcc resources/kevinbotlib/logdownloader_resources.qrc -o src/kevinbotlib/apps/log_downloader/resources_rc.py --no-compress
pyside6-rcc resources/kevinbotlib/logviewer_resources.qrc -o src/kevinbotlib/apps/log_viewer/resources_rc.py --no-compress
sed -i -e 's/PySide6/qtpy/g' src/kevinbotlib/ui/resources_rc.py
sed -i -e 's/PySide6/qtpy/g' src/kevinbotlib/apps/control_console/resources_rc.py
sed -i -e 's/PySide6/qtpy/g' src/kevinbotlib/apps/dashboard/resources_rc.py
sed -i -e 's/PySide6/qtpy/g' src/kevinbotlib/apps/log_downloader/resources_rc.py
sed -i -e 's/PySide6/qtpy/g' src/kevinbotlib/apps/log_viewer/resources_rc.py
echo 'RCC Resources Compiled'