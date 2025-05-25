import time

import click

from kevinbotlib.logger import Logger, LoggerConfiguration


@click.command()
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose (DEBUG) logging",
)
@click.option(
    "-t",
    "--trace",
    is_flag=True,
    help="Enable tracing (TRACE) logging",
)
@click.option(
    "-d",
    "--dir",
    default="./",
    help="Directory to serve files from (default: current directory)",
)
@click.option(
    "-p",
    "--port",
    default=8000,
    type=int,
    help="Port to serve on (default: 8000)",
)
@click.option(
    "-H",
    "--host",
    default="localhost",
    help="Host to serve on (default: localhost)",
)
def fileserver(verbose: bool, trace: bool, dir: str, port: int, host: str):  # noqa: A002
    """
    Serve files over HTTP
    """
    from kevinbotlib.fileserver.fileserver import FileServer
    from kevinbotlib.logger import Level

    log_level = Level.INFO
    if verbose:
        log_level = Level.DEBUG
    elif trace:
        log_level = Level.TRACE

    logger = Logger()
    logger.configure(LoggerConfiguration(log_level))

    server = FileServer(
        http_port=port,
        directory=dir,
        host=host,
    )
    server.start()

    while True:
        time.sleep(1)
