# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import random
import time

from kevinbotlib import EyeMotion, EyeSkin, SerialEyes

eyes = SerialEyes()
eyes.connect("/dev/ttyUSB0", 115200, 5)

eyes.set_skin(EyeSkin.SIMPLE)

eyes.set_motion(EyeMotion.MANUAL)

for _i in range(10):
    eyes.set_manual_pos(random.randint(0, 240), random.randint(0, 240))  # noqa: S311
    time.sleep(1)
