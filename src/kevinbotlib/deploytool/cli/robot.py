import click

from kevinbotlib.deploytool.cli.deploy_code import deploy_code_command
from kevinbotlib.deploytool.cli.robot_delete import delete_robot_command
from kevinbotlib.deploytool.cli.robot_service import service_group


@click.group("robot")
def robot_group():
    """Robot code management tools"""


robot_group.add_command(delete_robot_command)
robot_group.add_command(deploy_code_command)
robot_group.add_command(service_group)
