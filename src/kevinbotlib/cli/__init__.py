"""
KevinbotLib Command-line Interface
"""

import click

from kevinbotlib.__about__ import __version__
from kevinbotlib.cli.fileserver import fileserver
from kevinbotlib.cli.console import controlconsole


@click.group(context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120})
@click.version_option(version=__version__, prog_name="KevinbotLib")
def cli():
    """
    \b
    ██╗  ██╗███████╗██╗   ██╗██╗███╗   ██╗██████╗  ██████╗ ████████╗██╗     ██╗██████╗
    ██║ ██╔╝██╔════╝██║   ██║██║████╗  ██║██╔══██╗██╔═══██╗╚══██╔══╝██║     ██║██╔══██╗
    █████╔╝ █████╗  ██║   ██║██║██╔██╗ ██║██████╔╝██║   ██║   ██║   ██║     ██║██████╔╝
    ██╔═██╗ ██╔══╝  ╚██╗ ██╔╝██║██║╚██╗██║██╔══██╗██║   ██║   ██║   ██║     ██║██╔══██╗
    ██║  ██╗███████╗ ╚████╔╝ ██║██║ ╚████║██████╔╝╚██████╔╝   ██║   ███████╗██║██████╔╝
    ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝    ╚═╝   ╚══════╝╚═╝╚═════╝
    """


def main():  # no cov
    cli.add_command(controlconsole)
    cli.add_command(fileserver)
    cli(prog_name="kevinbotlib")


if __name__ == "__main__":
    main()
