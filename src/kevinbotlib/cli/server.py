# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
KevinbotLib Robot Server
Allow accessing KevinbotLib APIs over MQTT and XBee API Mode
"""

import click


@click.command()
def server():
    """Start the Kevinbot MQTT and XBee inferface"""
    click.echo("In the future...")
