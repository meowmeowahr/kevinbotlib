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
@click.option(
    "--no-lock",
    is_flag=True,
    help="Disable screen lock inhibitor",
)
def controlconsole(verbose: bool, trace: bool, no_lock: bool):
    """APP: The KevinbotLib Control Console"""
    from kevinbotlib.apps.control_console.control_console import (
        ControlConsoleApplicationRunner,
        ControlConsoleApplicationStartupArguments,
    )

    args = ControlConsoleApplicationStartupArguments(verbose=verbose, trace=trace, nolock=no_lock)
    runner = ControlConsoleApplicationRunner(args)
    runner.run()
