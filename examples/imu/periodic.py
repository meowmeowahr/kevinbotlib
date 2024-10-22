# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import Kevinbot

robot = Kevinbot()
robot.connect("/dev/ttyAMA2", 921600, 5, 1)

while True:
    print(f"Gyro : {robot.get_state().imu.gyro}")  # noqa: T201
    print(f"Accel: {robot.get_state().imu.accel}")  # noqa: T201
    time.sleep(1)
