# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later


from kevinbotlib import Kevinbot, Lighting

robot = Kevinbot()
robot.connect("/dev/ttyAMA2", 921600, 5, 1)

light = Lighting(robot)

print(f"State: {light.get_state()}")  # noqa: T201
