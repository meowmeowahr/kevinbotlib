# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import Kevinbot

robot = Kevinbot()
robot.connect("/dev/ttyAMA2", 921600, 5, 1)

while True:
    print(f"Uptime (s) : {robot.get_state().uptime}")  # noqa: T201
    print(f"Uptime (ms): {robot.get_state().uptime_ms}")  # noqa: T201
    time.sleep(1)
