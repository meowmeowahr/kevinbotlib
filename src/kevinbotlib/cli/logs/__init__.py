import click

from kevinbotlib.cli.logs.size import size
from kevinbotlib.cli.logs.where import where


@click.group(context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120})
def logs():
    """Log File Tools"""


logs.add_command(where)
logs.add_command(size)
