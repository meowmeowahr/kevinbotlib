# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import SerialEyes

eyes = SerialEyes()
eyes.connect("/dev/ttyUSB0", 115200, 5)

for i in range(4):
    eyes.set_skin(i)
    time.sleep(2)