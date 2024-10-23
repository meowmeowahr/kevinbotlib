# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later


import time

from kevinbotlib import Kevinbot, Lighting

robot = Kevinbot()
robot.connect("/dev/ttyAMA2", 921600, 5, 1)

light = Lighting(robot)

light.set_color1(Lighting.Channel.Base, (255, 0, 0))
light.set_effect(Lighting.Channel.Base, "color1")
print(f"Color: {light.get_state().base_color1}")  # noqa: T201

time.sleep(1)

light.set_color1(Lighting.Channel.Base, (0, 255, 0))
print(f"Color: {light.get_state().base_color1}")  # noqa: T201

time.sleep(1)

light.set_color1(Lighting.Channel.Base, (0, 0, 255))
print(f"Color: {light.get_state().base_color1}")  # noqa: T201

time.sleep(1)
light.set_color1(Lighting.Channel.Base, (0, 0, 0))
print(f"Color: {light.get_state().base_color1}")  # noqa: T201
