# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import MqttKevinbot

robot = MqttKevinbot()
robot.connect()

while True:
    print(robot.ts)  # noqa: T201
    time.sleep(1)
