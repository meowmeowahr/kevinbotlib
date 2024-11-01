# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from kevinbotlib import MqttKevinbot

robot = MqttKevinbot()
robot.connect()

robot.e_stop()
