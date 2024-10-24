import time

import click
from loguru import logger
from paho.mqtt import client as mqtt_client


@click.command()
@click.argument("topic")
@click.argument("message")
@click.option("--count", default=1, help="Number of times to publish message")
@click.option("--interval", default=1.0, help="Time between publishing message")
@click.option("--qos", default=0, help="MQTT Quality of Service")
@click.option("--retain", is_flag=True, help="MQTT Retain")
def pub(topic: str, message: str, count: int, interval: float, qos: int, *, retain: bool):
    """Publish a message to a specific MQTT topic"""
    client = mqtt_client.Client()
    for i in range(count):
        logger.success(f"Published: Topic: {topic} Msg: '{message}' QoS: {qos} Retain: {retain}")
        if i < count - 1:
            time.sleep(interval)
