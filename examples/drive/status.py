# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import Drivebase, Kevinbot

robot = Kevinbot()
robot.connect("/dev/ttyAMA2", 921600, 5, 1)

drive = Drivebase(robot)

robot.request_enable()  # Ask the core to enable
while not robot.get_state().enabled:  # Wait until the core is enabled
    time.sleep(0.01)

time.sleep(1) # Wait for data to arrive

print(f"Speeds: {drive.get_powers()}")
print(f"Watts: {drive.get_watts()}")
print(f"Amps: {drive.get_amps()}")
