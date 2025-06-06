import click

from kevinbotlib.cli.hardware.serial import serial


@click.group(context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120})
def hardware():
    """Hardware Interfaces"""


hardware.add_command(serial)
