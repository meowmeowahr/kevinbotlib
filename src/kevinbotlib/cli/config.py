# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
KevinbotLib MQTT Publisher
Publish a message to a specific MQTT topic
"""

import time

import click
from loguru import logger
from paho.mqtt import client as mqtt_client

from kevinbotlib.config import KevinbotConfig, ConfigLocation


@click.group(context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120})
def config():
    """Set, get, and create configuration files"""
    

@click.command("get", help="Get the value of a configuration entry")
def c_get():
    pass

@click.command("set", help="Set the value of a configuration entry")
def c_set():
    pass

@click.command("path")
@click.option("--system", is_flag=True, help="Use global config path")
@click.option("--user", is_flag=True, help="Use user config path")
def c_path(system, user):
    """Echo out a configuration file path"""
    logger.disable("kevinbotlib.config") # hush warnings
    if system:
        click.echo(KevinbotConfig(ConfigLocation.SYSTEM).config_path)
    elif user:
        click.echo(KevinbotConfig(ConfigLocation.USER).config_path)
    else:
        click.echo(KevinbotConfig(ConfigLocation.AUTO).config_path)

@click.command("echo")
@click.option("--system", is_flag=True, help="Use global config path")
@click.option("--user", is_flag=True, help="Use user config path")
def c_echo(system, user):
    """Echo out a configuration file"""
    logger.disable("kevinbotlib.config") # hush warnings
    if system:
        path = KevinbotConfig(ConfigLocation.SYSTEM).config_path
    elif user:
        path = KevinbotConfig(ConfigLocation.USER).config_path
    else:
        path = KevinbotConfig(ConfigLocation.NONE).config_path

    if path and path.exists():
        with open(path, "r", encoding="utf-8") as f:
            click.echo(f.read())
    else:
        click.echo("#@# Configuration is auto-generated. Use `kevinbot config save` to create a configuration file\n\n" + KevinbotConfig(ConfigLocation.NONE).dump())

config.add_command(c_get)
config.add_command(c_set)
config.add_command(c_path)
config.add_command(c_echo)
