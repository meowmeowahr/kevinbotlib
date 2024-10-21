# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from kevinbotlib import Drivebase, Kevinbot

robot = Kevinbot()
robot.connect("/dev/ttyAMA2", 921600, 5, 1)

drive = Drivebase(robot)

input("LIFT THE WHEELS OFF THE GROUND FOR THIS TEST!!! [Return] to start test")

robot.request_enable()  # Ask the core to enable
while not robot.get_state().enabled:  # Wait until the core is enabled
    time.sleep(0.01)

time.sleep(1) # Wait for data to arrive
drive.drive_at_power(0.2, 0.2)
time.sleep(3)
drive.drive_at_power(0.5, 0.2)
time.sleep(3)
drive.drive_at_power(0.2, 0.5)
time.sleep(3)
drive.drive_at_power(0.05, 0.05)
time.sleep(3)
# Will auto-stop on disconnect
# drive.stop()
