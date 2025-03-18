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
    "-p",
    "--port",
    default=8765,
    type=int,
    help="Port to serve on (default: 8765)",
)
@click.option(
    "-H",
    "--host",
    default="localhost",
    help="Host to serve on (default: localhost)",
)
def server(verbose: bool, trace: bool, port: int, host: str):
    """
    KevinbotLib Communication Test Server
    """
    from kevinbotlib.comm import CommunicationServer
    from kevinbotlib.logger import Level

    log_level = Level.INFO
    if verbose:
        log_level = Level.DEBUG
    elif trace:
        log_level = Level.TRACE

    logger = Logger()
    logger.configure(LoggerConfiguration(log_level))

    logger.warning("This communication server is for testing purposes ONLY!")

    server = CommunicationServer(
        port=port,
        host=host,
    )
    server.serve()
