import click

from kevinbotlib.deploytool.cli.venv_create import create_venv_command
from kevinbotlib.deploytool.cli.venv_delete import delete_venv_command


@click.group("venv")
def venv_group():
    """Remote virtual environment management"""


venv_group.add_command(create_venv_command)
venv_group.add_command(delete_venv_command)
