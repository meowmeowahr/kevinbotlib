from pathlib import Path

import click
import paramiko
from rich.console import Console

from kevinbotlib.deploytool import deployfile
from kevinbotlib.deploytool.cli.common import confirm_host_key_df
from kevinbotlib.deploytool.cli.spinner import rich_spinner
from kevinbotlib.deploytool.sshkeys import SSHKeyManager

console = Console()


@click.command("delete")
@click.option(
    "-d",
    "--df-directory",
    default=".",
    help="Directory of the Deployfile",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
)
def delete_robot_command(df_directory: str):
    """Delete the robot code on the remote system."""
    df = deployfile.read_deployfile(Path(df_directory) / "Deployfile.toml")

    key_manager = SSHKeyManager("KevinbotLibDeployTool")
    key_info = key_manager.list_keys()
    if df.name not in key_info:
        console.print(
            f"[red]Key '{df.name}' not found in key manager. Use `kevinbotlib ssh init` to create a new key[/red]"
        )
        raise click.Abort

    private_key_path, _ = key_info[df.name]

    # Load private key
    try:
        pkey = paramiko.RSAKey.from_private_key_file(private_key_path)
    except Exception as e:
        console.print(f"[red]Failed to load private key: {e}[/red]")
        raise click.Abort from e

    confirm_host_key_df(console, df, pkey)

    with rich_spinner(console, "Connecting to remote host"):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # noqa: S507 # * this is ok, because the user is asked beforehand
            ssh.connect(hostname=df.host, port=df.port, username=df.user, pkey=pkey, timeout=10)

            check_cmd = f"test -d $HOME/{df.name}/robot && echo exists || echo missing"
            _, stdout, _ = ssh.exec_command(check_cmd)
            result = stdout.read().decode().strip()

            if result != "exists":
                console.print(f"[yellow]No robot code found at $HOME/{df.name}/robot — nothing to delete.[/yellow]")
                return

            console.print(f"[bold red]Deleting robot code at $HOME/{df.name}/robot...[/bold red]")
            ssh.exec_command(f"rm -rf $HOME/{df.name}/robot")
            console.print("[bold green]✔ Robot code deleted successfully[/bold green]")

            ssh.close()

        except Exception as e:
            console.print(f"[red]SSH operation failed: {e}[/red]")
            raise click.Abort from e
