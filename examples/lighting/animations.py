# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later


import time

from kevinbotlib import Kevinbot, Lighting

robot = Kevinbot()
robot.connect("/dev/ttyAMA2", 921600, 5, 1)

light = Lighting(robot)

light.set_color1(Lighting.Channel.Base, (255, 0, 0))
light.set_color2(Lighting.Channel.Base, (0, 0, 255))
light.set_effect(Lighting.Channel.Base, "color1")
print(f"Effect: {light.get_state().base_effect}")  # noqa: T201

time.sleep(2)

light.set_effect(Lighting.Channel.Base, "color2")
print(f"Effect: {light.get_state().base_effect}")  # noqa: T201

time.sleep(2)

light.set_effect(Lighting.Channel.Base, "flash")
print(f"Effect: {light.get_state().base_effect}")  # noqa: T201

time.sleep(4)

light.set_effect(Lighting.Channel.Base, "fade")
print(f"Effect: {light.get_state().base_effect}")  # noqa: T201

time.sleep(4)

light.set_effect(Lighting.Channel.Base, "jump3")
print(f"Effect: {light.get_state().base_effect}")  # noqa: T201

time.sleep(4)

light.set_effect(Lighting.Channel.Base, "twinkle")
print(f"Effect: {light.get_state().base_effect}")  # noqa: T201

time.sleep(4)

light.set_effect(Lighting.Channel.Base, "swipe")
print(f"Effect: {light.get_state().base_effect}")  # noqa: T201

time.sleep(4)

light.set_effect(Lighting.Channel.Base, "rainbow")
print(f"Effect: {light.get_state().base_effect}")  # noqa: T201

time.sleep(4)

light.set_effect(Lighting.Channel.Base, "magic")
print(f"Effect: {light.get_state().base_effect}")  # noqa: T201

time.sleep(4)

light.set_effect(Lighting.Channel.Base, "fire")
print(f"Effect: {light.get_state().base_effect}")  # noqa: T201

time.sleep(4)
