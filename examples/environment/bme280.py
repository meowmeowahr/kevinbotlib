# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import Kevinbot

robot = Kevinbot()
robot.connect("/dev/ttyAMA2", 921600, 5, 1)

while True:
    print(f"Temp  : {robot.get_state().enviro.temperature} *C ({robot.get_state().enviro.temperature.f} *F)")  # noqa: T201
    print(f"Humi  : {robot.get_state().enviro.humidity} %")  # noqa: T201
    print(f"Pres  : {robot.get_state().enviro.pressure} hPa")  # noqa: T201
    time.sleep(2)
