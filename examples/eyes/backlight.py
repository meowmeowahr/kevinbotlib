# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import MqttKevinbot
from kevinbotlib.eyes import MqttEyes

robot = MqttKevinbot()
robot.connect()

eyes = MqttEyes(robot)

for i in range(100):
    eyes.set_backlight(i / 100)
    time.sleep(0.05)
