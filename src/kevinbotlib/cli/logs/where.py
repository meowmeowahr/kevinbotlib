import click


@click.command("where")
def where():
    """Get the default location of log files"""
    from kevinbotlib.logger import LoggerDirectories
    click.echo(LoggerDirectories.get_logger_directory())