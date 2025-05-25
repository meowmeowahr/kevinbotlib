import click


@click.command("dashboard", context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120})
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
def dashboard(verbose: bool, trace: bool):
    """APP: The KevinbotLib Dashboard"""
    from kevinbotlib.apps.dashboard.app import (
        DashboardApplicationRunner,
        DashboardApplicationStartupArguments,
    )

    args = DashboardApplicationStartupArguments(verbose=verbose, trace=trace)
    runner = DashboardApplicationRunner(args)
    runner.run()
