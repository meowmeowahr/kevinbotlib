# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import SerialEyes
from kevinbotlib.states import Skin

eyes = SerialEyes()
eyes.connect("/dev/ttyUSB0", 115200, 5)

eyes.set_skin(Skin.TV_STATIC)
time.sleep(2)

eyes.set_skin(Skin.SIMPLE)
time.sleep(2)

eyes.set_skin(Skin.METAL)
time.sleep(2)

eyes.set_skin(Skin.NEON)
time.sleep(2)