import click

from kevinbotlib_cns.cli import server


@click.group(context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120})
def cns():
    """Communication & Networking Services"""


cns.add_command(server)
