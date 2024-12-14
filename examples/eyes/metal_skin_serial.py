# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import EyeMotion, EyeSkin, SerialEyes

eyes = SerialEyes()
eyes.connect("/dev/ttyUSB0", 115200, 5)

eyes.set_skin(EyeSkin.METAL)
eyes.set_motion(EyeMotion.LEFT_RIGHT)

print(f"Skin Name: {eyes.skins.simple.name}")  # noqa: T201

# Save original settings
bg = eyes.skins.metal.bg_color
tint = eyes.skins.metal.tint
iris_size = eyes.skins.metal.iris_size

print(f"Bg Color: {bg}, Iris Tint: {tint}")  # noqa: T201
print(f"Iris size: {iris_size}")  # noqa: T201

time.sleep(1)

# Demo settings

eyes.skins.metal.bg_color = "#ffffff"
eyes.skins.metal.tint = 100

time.sleep(2)

eyes.skins.simple.bg_color = "#ff0000"
eyes.skins.metal.tint = 200

time.sleep(2)

eyes.skins.metal.tint = 250
eyes.skins.metal.iris_size = 80

time.sleep(2)

eyes.skins.metal.tint = 250
eyes.skins.metal.iris_size = 140

time.sleep(2)

eyes.skins.metal.bg_color = bg
eyes.skins.metal.tint = tint
eyes.skins.metal.iris_size = iris_size

# or, use the restore function
# eyes.metal.simple.restore()

time.sleep(2)
