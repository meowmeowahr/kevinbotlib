# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import EyeMotion, EyeSkin, SerialEyes, MqttKevinbot

eyes = SerialEyes()
eyes.connect("/dev/ttyUSB0", 115200, 5)

eyes.set_skin(EyeSkin.NEON)
eyes.set_motion(EyeMotion.LEFT_RIGHT)

print(f"Skin Name: {eyes.skins.neon.name}")  # noqa: T201

# Save original settings
bg = eyes.skins.neon.bg_color
start = eyes.skins.neon.fg_color_start
end = eyes.skins.neon.fg_color_end

iris_size = eyes.skins.neon.iris_size

style = eyes.skins.neon.style

print(f"Bg Color: {bg}, Start Color: {start}, End Color: {end}")  # noqa: T201
print(f"Iris size: {iris_size}") # noqa: T201
print(f"Style: {style}")  # noqa: T201

time.sleep(1)

# Demo settings

eyes.skins.neon.style = "neon1.png"
eyes.skins.neon.bg_color = "#ffffff"
eyes.skins.neon.fg_color_start = "#ff0000"
eyes.skins.neon.fg_color_end = "#0000ff"

time.sleep(2)

eyes.skins.neon.bg_color = "#000000"
eyes.skins.neon.fg_color_start = "#ffffff"
eyes.skins.neon.fg_color_end = "#00ff00"

time.sleep(2)

eyes.skins.neon.style = "neon2.png"

time.sleep(2)

eyes.skins.neon.style = "neon3.png"

time.sleep(2)

eyes.skins.neon.style = "neon1.png"
eyes.skins.neon.iris_size = 80

time.sleep(2)

eyes.skins.neon.iris_size = 150

time.sleep(2)

eyes.skins.neon.bg_color = bg
eyes.skins.neon.fg_color_start = start
eyes.skins.neon.fg_color_end = end
eyes.skins.neon.iris_size = iris_size
eyes.skins.neon.style = style

# or, use the restore function
# eyes.skins.neon.restore()

time.sleep(2)
