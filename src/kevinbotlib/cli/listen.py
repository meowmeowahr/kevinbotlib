# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
KevinbotLib MQTT Listener
Listen to MQTT topics
"""

import click
from loguru import logger
from paho.mqtt import client as mqtt_client

from kevinbotlib.config import KevinbotConfig


@click.command()
@click.argument("topic")
@click.option("--qos", default=0, help="MQTT Quality of Service")
def listen(topic: str, qos: int):
    """Publish a message to a specific MQTT topic"""
    conf = KevinbotConfig()
    client = mqtt_client.Client()
    client.connect(conf.mqtt.host, conf.mqtt.port, conf.mqtt.keepalive)
    client.subscribe(topic, qos)

    def on_message(_, __, msg):
        logger.info(f"Received: Topic: {msg.topic} Msg: '{msg.payload.decode()}' QoS: {msg.qos}")

    client.on_message = on_message
    client.loop_forever()
