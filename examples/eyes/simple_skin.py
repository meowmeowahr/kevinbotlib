# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import EyeMotion, EyeSkin, MqttEyes, MqttKevinbot

robot = MqttKevinbot()
robot.connect()

eyes = MqttEyes(robot)

eyes.set_skin(EyeSkin.SIMPLE)
eyes.set_motion(EyeMotion.LEFT_RIGHT)

print(f"Skin Name: {eyes.skins.simple.name}")  # noqa: T201

# Save original settings
bg = eyes.skins.simple.bg_color
iris = eyes.skins.simple.iris_color
pupil = eyes.skins.simple.pupil_color

iris_size = eyes.skins.simple.iris_size
pupil_size = eyes.skins.simple.pupil_size

print(f"Bg Color: {bg}, Iris Color: {iris}, Pupil Color: {pupil}")  # noqa: T201
print(f"Iris size: {iris_size}, Pupil size: {pupil_size}")  # noqa: T201

time.sleep(1)

# Demo settings

eyes.skins.simple.bg_color = "#ffffff"
eyes.skins.simple.pupil_color = "#ff0000"
eyes.skins.simple.iris_color = "#000000"

time.sleep(2)

eyes.skins.simple.bg_color = "#ff0000"
eyes.skins.simple.pupil_color = "#000000"
eyes.skins.simple.iris_color = "#ffffff"

time.sleep(2)

eyes.skins.simple.iris_size = 120
eyes.skins.simple.pupil_size = 90

time.sleep(2)

eyes.skins.simple.iris_size = 80
eyes.skins.simple.pupil_size = 50

time.sleep(2)

eyes.skins.simple.bg_color = bg
eyes.skins.simple.iris_color = iris
eyes.skins.simple.pupil_color = pupil
eyes.skins.simple.iris_size = iris_size
eyes.skins.simple.pupil_size = pupil_size

# or, use the restore function
# eyes.skins.simple.restore()

time.sleep(2)
