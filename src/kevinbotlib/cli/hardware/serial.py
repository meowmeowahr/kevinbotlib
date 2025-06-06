import click
import rich.console
import rich.tree


@click.group(context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120})
def serial():
    """Serial Hardware"""

@click.command("enumerate")
@click.option(
    "-R",
    "--raw",
    is_flag=True,
    help="Output non-formatted raw data",
)
def enumerate_s_dev(raw: bool):
    """Enumerate the connected serial devices"""
    from kevinbotlib.hardware.interfaces.serial import SerialIdentification


    for dev in SerialIdentification.list_device_info():
        if raw:
            click.echo(dev)
        else:
            console = rich.console.Console()
            tree = rich.tree.Tree("[bold]" + dev.device)
            tree.add(f"[magenta]Name:[/] {dev.name}", highlight=True)
            tree.add(f"[magenta]True Path:[/] {dev.device_path}", highlight=True)
            tree.add(f"[magenta]Manufacturer:[/] {dev.manufacturer}", highlight=True)
            tree.add(f"[magenta]Description:[/] {dev.description}", highlight=True)
            tree.add(f"[magenta]PID:[/] {dev.pid}", highlight=True)
            tree.add(f"[magenta]HWID:[/] {dev.hwid}", highlight=True)
            console.print(tree)

serial.add_command(enumerate_s_dev)