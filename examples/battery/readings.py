# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import Kevinbot

robot = Kevinbot()
robot.connect("/dev/ttyAMA2", 921600, 5, 1)

time.sleep(3)  # Wait to get data

print(f"Voltages: {robot.get_state().battery.voltages}")  # noqa: T201
print(f"Raw Voltages: {robot.get_state().battery.raw_voltages}")  # noqa: T201
print(f"States: {robot.get_state().battery.states}")  # noqa: T201
