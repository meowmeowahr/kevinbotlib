# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys

import click
from loguru import logger

import kevinbotlib.server


@click.command()
@click.option("--config", "cfg", help="Manual configuration path")
@click.option("--root-topic", "root", help="MQTT Topic override")
@click.option("--verbose", "verbose", is_flag=True, help="Enable verbose logging")
@click.option("--trace", "trace", is_flag=True, help="Enable extra-verbose trace logging")
def server(
    cfg: str | None,
    root: str | None,
    *,
    verbose: bool,
    trace: bool,
):
    """Start the Kevinbot MQTT and XBee inferface"""

    if trace:
        logger.remove()
        logger.add(sys.stdout, level=5)
    elif verbose:
        logger.remove()
        logger.add(sys.stdout, level=10)

    kevinbotlib.server.bringup(cfg, root)
