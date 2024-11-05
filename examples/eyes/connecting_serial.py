# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import SerialEyes

robot = SerialEyes()
robot.connect("/dev/ttyUSB0", 115200, 2)

while True:
    time.sleep(1)
