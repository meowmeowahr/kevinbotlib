# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import click

import kevinbotlib.server


@click.command()
@click.option("--config", "cfg", help="Manual configuration path")
@click.option("--core-port", "core_port", help="Core serial port (Config override)")
@click.option("--core-baud", "core_baud", type=int, help="Core Baud rate (Config override)")
@click.option("--xbee-port", "xbee_port", help="XBee serial port (Config override)")
@click.option("--xbee-api", "xbee_api", type=int, help="XBee API mode (Config override)")
@click.option("--xbee-baud", "xbee_baud", type=int, help="XBee Baud rate (Config override)")
@click.option("--verbose", "verbose", is_flag=True, help="Enable verbose logging")
@click.option("--trace", "trace", is_flag=True, help="Enable extra-verbose trace logging")
def server(cfg: str | None, core_port: str | None, core_baud: int | None, xbee_port: str | None, xbee_api: int | None, xbee_baud: int | None, *, verbose: bool, trace: bool):
    """Start the Kevinbot MQTT and XBee inferface"""
    kevinbotlib.server.bringup(cfg, core_port, core_baud, xbee_port, xbee_api, xbee_baud, verbose=verbose, trace=trace)
