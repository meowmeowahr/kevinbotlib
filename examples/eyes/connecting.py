# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import MqttEyes, MqttKevinbot

robot = MqttKevinbot()
robot.connect()

eyes = MqttEyes(robot)

while True:
    time.sleep(1)
