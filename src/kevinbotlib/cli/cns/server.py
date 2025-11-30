import sys
import time

import click
from kevinbotlib_cns.server import CNSServer
from loguru import logger


@click.command("server")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose logging (DEBUG)",
)
@click.option(
    "-p",
    "--port",
    default=4800,
    type=int,
    help="Port to serve on (default: 4800)",
)
@click.option(
    "-H",
    "--host",
    default="0.0.0.0",
    help="Host to serve on (default: 0.0.0.0)",
)
def server(verbose: bool, port: int, host: str):
    """Start a CNS Server."""
    logger.remove()
    if verbose:
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.add(sys.stderr, level="INFO")

    cns_server = CNSServer()
    cns_server.start(port=port, host=host)

    try:
        while True:
            time.sleep(1)
    finally:
        cns_server.stop()

