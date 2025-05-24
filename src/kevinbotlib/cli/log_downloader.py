import click


@click.command("logdownloader")
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
def log_downloader(verbose: bool, trace: bool):
    """APP: The KevinbotLib Log Downloader"""
    from kevinbotlib.apps.log_downloader.log_downloader import (
        LogDownloaderApplicationRunner,
        LogDownloaderApplicationStartupArguments,
    )

    args = LogDownloaderApplicationStartupArguments(verbose=verbose, trace=trace)
    runner = LogDownloaderApplicationRunner(args)
    runner.run()
