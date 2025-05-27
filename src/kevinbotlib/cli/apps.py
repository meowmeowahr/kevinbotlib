import click

from kevinbotlib.cli.console import controlconsole
from kevinbotlib.cli.dashboard import dashboard
from kevinbotlib.cli.log_downloader import log_downloader
from kevinbotlib.cli.log_viewer import log_viewer


@click.group(context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120})
def apps():
    """KevinbotLib Graphical Applications"""


apps.add_command(controlconsole)
apps.add_command(dashboard)
apps.add_command(log_downloader)
apps.add_command(log_viewer)
