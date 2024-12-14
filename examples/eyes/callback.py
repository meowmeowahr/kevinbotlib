# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import EyeSkin, MqttEyes, MqttKevinbot

robot = MqttKevinbot()
robot.connect()

eyes = MqttEyes(robot)

eyes.set_skin(EyeSkin.SIMPLE)
eyes.skins.simple.restore()

eyes.skins.register_callback("simple.bg_color", print)

eyes.skins.simple.bg_color = "#ffffff"
time.sleep(1)
eyes.skins.simple.bg_color = "#ffff00"
time.sleep(1)
eyes.skins.simple.bg_color = "#ff00ff"
time.sleep(1)
eyes.skins.simple.bg_color = "#00ffff"
time.sleep(1)

eyes.skins.unregister_callbacks("simple.bg_color")
eyes.skins.simple.restore()

time.sleep(2)
