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

from kevinbotlib.config import KevinbotConfig


@click.command()
@click.argument("topic")
@click.argument("message")
@click.option("--count", default=1, help="Number of times to publish message")
@click.option("--interval", default=1.0, help="Time between publishing message")
@click.option("--qos", default=0, help="MQTT Quality of Service")
@click.option("--retain", is_flag=True, help="MQTT Retain")
def pub(topic: str, message: str, count: int, interval: float, qos: int, *, retain: bool):
    """Publish a message to a specific MQTT topic"""
    conf = KevinbotConfig()
    client = mqtt_client.Client()
    client.connect(conf.mqtt.host, conf.mqtt.port, conf.mqtt.keepalive)

    for i in range(count):
        logger.success(f"Published: Topic: {topic} Msg: '{message}' QoS: {qos} Retain: {retain}")
        client.publish(topic, message, qos=qos, retain=retain)
        if i < count - 1:
            time.sleep(interval)
