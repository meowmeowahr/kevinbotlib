# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time
import random

from kevinbotlib import SerialEyes, EyeSkin, EyeMotion

eyes = SerialEyes()
eyes.connect("/dev/ttyUSB0", 115200, 5)

eyes.set_skin(EyeSkin.SIMPLE)

eyes.set_motion(EyeMotion.MANUAL)

for i in range(10):
    eyes.set_manual_pos(random.randint(0, 240), random.randint(0, 240))
    time.sleep(1)