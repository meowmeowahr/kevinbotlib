# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import MqttEyes, MqttKevinbot, EyeSkin, EyeMotion

robot = MqttKevinbot()
robot.connect("kevinbot", "localhost", 1883)

eyes = MqttEyes(robot)

eyes.set_skin(EyeSkin.SIMPLE)

eyes.set_motion(EyeMotion.DISABLE)
time.sleep(3)

eyes.set_motion(EyeMotion.LEFT_RIGHT)
time.sleep(3)

eyes.set_motion(EyeMotion.JUMP)
time.sleep(3)
