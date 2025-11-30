"""
Internal command-line interface for KevinbotLib Deploy Tool
"""

# SPDX-FileCopyrightText: 2025-present meowmeowahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-or-later

import click

from kevinbotlib.deploytool.cli.deploy_code import deploy_code_command
from kevinbotlib.deploytool.cli.cns_deploy import deploy_cns_command
from kevinbotlib.deploytool.cli.init import init
from kevinbotlib.deploytool.cli.robot import robot_group
from kevinbotlib.deploytool.cli.ssh import ssh_group
from kevinbotlib.deploytool.cli.test import deployfile_test_command
from kevinbotlib.deploytool.cli.venv import venv_group


@click.group()
@click.version_option()
def cli():
    """KevinbotLib Deploy Tool"""


cli.add_command(init)
cli.add_command(ssh_group)
cli.add_command(robot_group)
cli.add_command(venv_group)
cli.add_command(deploy_code_command)
cli.add_command(deployfile_test_command)
cli.add_command(deploy_cns_command)
