# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import Kevinbot

robot = Kevinbot()
robot.connect("/dev/ttyAMA2", 921600, 5, 1)

while True:
    print(f"Left Motor : {robot.get_state().thermal.left_motor} *C ({robot.get_state().thermal.left_motor.f} *F)")  # noqa: T201
    print(f"Right Motor: {robot.get_state().thermal.right_motor} * C ({robot.get_state().thermal.right_motor.f} *F)")  # noqa: T201
    print(f"Internal: {robot.get_state().thermal.internal} *C ({robot.get_state().thermal.internal.f} *F)")  # noqa: T201
    time.sleep(2)
