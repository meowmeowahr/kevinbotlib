# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import EyeSkin, MqttEyes, MqttKevinbot

robot = MqttKevinbot()
robot.connect()

eyes = MqttEyes(robot)

eyes.set_skin(EyeSkin.TV_STATIC)
time.sleep(2)

eyes.set_skin(EyeSkin.SIMPLE)
time.sleep(2)

eyes.set_skin(EyeSkin.METAL)
time.sleep(2)

eyes.set_skin(EyeSkin.NEON)
time.sleep(2)
