# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
KevinbotLib Command-line Interface
"""

import click

from kevinbotlib.__about__ import __version__
from kevinbotlib.cli.config import config
from kevinbotlib.cli.listen import listen
from kevinbotlib.cli.pub import pub
from kevinbotlib.cli.server import server


@click.group(context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120})
@click.version_option(version=__version__, prog_name="KevinbotLib")
def cli():
    """
    \b
    ██╗  ██╗███████╗██╗   ██╗██╗███╗   ██╗██████╗  ██████╗ ████████╗
    ██║ ██╔╝██╔════╝██║   ██║██║████╗  ██║██╔══██╗██╔═══██╗╚══██╔══╝
    █████╔╝ █████╗  ██║   ██║██║██╔██╗ ██║██████╔╝██║   ██║   ██║
    ██╔═██╗ ██╔══╝  ╚██╗ ██╔╝██║██║╚██╗██║██╔══██╗██║   ██║   ██║
    ██║  ██╗███████╗ ╚████╔╝ ██║██║ ╚████║██████╔╝╚██████╔╝   ██║
    ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝    ╚═╝
    """


# Add commands to the main CLI group
cli.add_command(server)
cli.add_command(listen)
cli.add_command(pub)
cli.add_command(config)


def main():  # no cov
    cli(prog_name="kevinbot")


if __name__ == "__main__":
    main()
