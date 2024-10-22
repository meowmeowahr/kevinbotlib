# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from kevinbotlib import Kevinbot

robot = Kevinbot()
robot.connect("/dev/ttyAMA2", 921600, 5, 1)

yaw_data, pitch_data, roll_data, time_data = [], [], [], []

fig, ax = plt.subplots()
ax.set_xlim(0, 10)
ax.set_ylim(0, 180)

(line_yaw,) = ax.plot([], [], label="Yaw")
(line_pitch,) = ax.plot([], [], label="Pitch")
(line_roll,) = ax.plot([], [], label="Roll")
ax.legend()

start_time = time.time()


def update(_):
    current_time = time.time() - start_time
    gyro = robot.get_state().imu.gyro

    time_data.append(current_time)
    roll_data.append(gyro[0])
    pitch_data.append(gyro[1])
    yaw_data.append(gyro[2])

    line_yaw.set_data(time_data, yaw_data)
    line_pitch.set_data(time_data, pitch_data)
    line_roll.set_data(time_data, roll_data)

    ax.set_xlim(max(0, current_time - 10), current_time)

    return line_yaw, line_pitch, line_roll


ani = FuncAnimation(fig, update, interval=10, cache_frame_data=False, blit=True)

plt.xlabel("Time (s)")
plt.ylabel("Gyro (degrees)")
plt.show()
