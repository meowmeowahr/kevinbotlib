# control_console_cli.py

import click


@click.command("console")
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
def controlconsole(verbose: bool, trace: bool):
    """APP: The KevinbotLib Control Console"""
    from kevinbotlib.apps.control_console.control_console import (
        ControlConsoleApplicationRunner,
        ControlConsoleApplicationStartupArguments,
    )

    args = ControlConsoleApplicationStartupArguments(verbose=verbose, trace=trace)
    runner = ControlConsoleApplicationRunner(args)
    runner.run()
