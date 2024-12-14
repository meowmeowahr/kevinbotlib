# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import EyeCallbackType, EyeSkin, SerialEyes

eyes = SerialEyes()
eyes.connect("/dev/ttyUSB0", 115200, 5)

eyes.set_skin(EyeSkin.SIMPLE)
eyes.skins.simple.restore()

eyes.register_callback(EyeCallbackType.SimpleBgColor, print)

eyes.skins.simple.bg_color = "#ffffff"
time.sleep(1)
eyes.skins.simple.bg_color = "#ffff00"
time.sleep(1)
eyes.skins.simple.bg_color = "#ff00ff"
time.sleep(1)
eyes.skins.simple.bg_color = "#00ffff"
time.sleep(1)

eyes.unregister_callbacks(EyeCallbackType.SimpleBgColor)
eyes.skins.simple.restore()

time.sleep(2)
