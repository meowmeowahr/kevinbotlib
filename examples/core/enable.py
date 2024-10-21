# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import Kevinbot

robot = Kevinbot()
robot.connect("/dev/ttyAMA2", 921600, 5, 1)

robot.request_enable()  # Ask the core to enable
while not robot.get_state().enabled:  # Wait until the core is enabled
    time.sleep(0.01)

time.sleep(3)

robot.request_disable()  # Ask the core to disable
while robot.get_state().enabled:  # Wait until the core is disabled
    time.sleep(0.01)

time.sleep(3)  # Let the user see that the robot is disabled before disconnecting
