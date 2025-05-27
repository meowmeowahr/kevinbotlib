import click


@click.command("logviewer")
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
def log_viewer(verbose: bool, trace: bool):
    """APP: The KevinbotLib Log Downloader"""
    from kevinbotlib.apps.log_viewer.log_viewer import (
        LogViewerApplicationRunner,
        LogViewerApplicationStartupArguments,
    )

    args = LogViewerApplicationStartupArguments(verbose=verbose, trace=trace)
    runner = LogViewerApplicationRunner(args)
    runner.run()
