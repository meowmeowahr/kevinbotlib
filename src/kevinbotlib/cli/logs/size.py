import click

from kevinbotlib.apps.log_downloader.util import sizeof_fmt


@click.command("size")
@click.option(
    "-b",
    "--bytes",
    "use_bytes",
    is_flag=True,
    help="Output in raw bytes",
)
def size(use_bytes: bool):
    """Get the total size of all log files in the default logging location"""
    from kevinbotlib.logger import LoggerDirectories
    if use_bytes:
        click.echo(int(LoggerDirectories.get_directory_size(LoggerDirectories.get_logger_directory()) * 1024 * 1024))
    else:
        click.echo(
            sizeof_fmt(int(LoggerDirectories.get_directory_size(LoggerDirectories.get_logger_directory()) * 1024 * 1024))
        )