# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
KevinbotLib MQTT Publisher
Publish a message to a specific MQTT topic
"""

from pathlib import Path

import click
from loguru import logger

from kevinbotlib.config import ConfigLocation, KevinbotConfig


@click.group(context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120})
def config():
    """Set, get, and create configuration files"""


@click.command("get", help="Get the value of a configuration entry")
def c_get():
    pass


@click.command("set", help="Set the value of a configuration entry")
def c_set():
    pass


def validate_single_flag(system, user):
    """Ensure only one flag is passed"""
    if system and user:
        raise click.BadOptionUsage("system/user", "Use only --system or --user")  # noqa: EM101


def get_config(system, user, manual: str | None = None):
    """Determine the correct configuration class based on system/user flags."""
    if manual:
        return KevinbotConfig(ConfigLocation.MANUAL, manual)
    if system:
        return KevinbotConfig(ConfigLocation.SYSTEM)
    if user:
        return KevinbotConfig(ConfigLocation.USER)
    return KevinbotConfig(ConfigLocation.AUTO)  # Default to AUTO


@click.command("path")
@click.option("--system", is_flag=True, help="Use global config path")
@click.option("--user", is_flag=True, help="Use user config path")
@click.option("--config", "cfg", help="Manual configuration path")
def c_path(system, user, cfg):
    """Echo out a configuration file path"""
    validate_single_flag(system, user)
    logger.disable("kevinbotlib.config")  # hush warnings
    click.echo(get_config(system, user, cfg).config_path)


@click.command("echo")
@click.option("--system", is_flag=True, help="Use global config path")
@click.option("--user", is_flag=True, help="Use user config path")
@click.option("--config", "cfg", help="Manual configuration path")
def c_echo(system, user, cfg):
    """Echo out a configuration file"""
    validate_single_flag(system, user)
    logger.disable("kevinbotlib.config")  # hush warnings

    if cfg and not Path(cfg).exists():
        logger.critical(f"Path {cfg} does not exist")
        return

    path = get_config(system, user, cfg).config_path

    if path and path.exists():
        with open(path, encoding="utf-8") as f:
            click.echo(f.read())
    else:
        click.echo(
            "#@# Configuration is auto-generated. Use `kevinbot config save` to create a configuration file\n\n"
            + KevinbotConfig(ConfigLocation.NONE).dump()
        )


config.add_command(c_get)
config.add_command(c_set)
config.add_command(c_path)
config.add_command(c_echo)
