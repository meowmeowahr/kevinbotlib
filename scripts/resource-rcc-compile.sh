#!/bin/bash
pyside6-rcc resources/kevinbotlib/theme_resources.qrc -o src/kevinbotlib/ui/resources_rc.py
pyside6-rcc resources/kevinbotlib/controlconsole_resources.qrc -o src/kevinbotlib/apps/control_console/resources_rc.py
sed -i -e 's/PySide6/qtpy/g' src/kevinbotlib/ui/resources_rc.py
sed -i -e 's/PySide6/qtpy/g' src/kevinbotlib/apps/control_console/resources_rc.py
echo 'RCC Resources Compiled'