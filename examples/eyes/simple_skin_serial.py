# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import EyeSkin, SerialEyes

eyes = SerialEyes()
eyes.connect("/dev/ttyUSB0", 115200, 5)

eyes.set_skin(EyeSkin.SIMPLE)

print(f"Skin Name: {eyes.skins.simple.name}")  # noqa: T201

# Save original settings
bg = eyes.skins.simple.bg_color
iris = eyes.skins.simple.iris_color
pupil = eyes.skins.simple.pupil_color

iris_size = eyes.skins.simple.iris_size
pupil_size = eyes.skins.simple.pupil_size

print(f"Bg Color: {bg}, Iris Color: {iris}, Pupil Color: {pupil}")
print(f"Iris size: {iris_size}, Pupil size: {pupil_size}")

time.sleep(2)
