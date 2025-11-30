import sys
import tarfile
import tempfile
import subprocess
from pathlib import Path

import click
import jinja2
import paramiko
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from kevinbotlib.deploytool import deployfile
from kevinbotlib.deploytool.cli.common import check_service_file, confirm_host_key_df, get_private_key
from kevinbotlib.deploytool.cli.spinner import rich_spinner
from kevinbotlib.deploytool.service import CNS_SYSTEMD_USER_SERVICE_TEMPLATE

console = Console()


@click.command("deploy-cns")
@click.option(
    "-d",
    "--df-directory",
    default=".",
    help="Directory of the Deployfile",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
)
@click.option(
    "-w",
    "--cns-wheel",
    help="Path to a pre-built KevinbotLib-CNS wheel. "
         "If omitted, no wheel is uploaded or installed.",
    type=click.Path(file_okay=True, dir_okay=False, exists=True),
)
def deploy_cns_command(df_directory, cns_wheel):
    """Deploy the CNS server to the robot (optionally update wheel)."""

    df_path = Path(df_directory) / "Deployfile.toml"
    if not df_path.exists():
        console.print(f"[red]Deployfile not found in {df_directory}[/red]")
        raise click.Abort

    df = deployfile.read_deployfile(df_path)

    private_key_path, pkey = get_private_key(console, df)
    confirm_host_key_df(console, df, pkey)

    # Connect
    with rich_spinner(console, "Connecting via SSH"):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=df.host, port=df.port, username=df.user, pkey=pkey, timeout=10)
        sftp = ssh.open_sftp()

    remote_cns_dir = f"/home/{df.user}/{df.name}/cns"
    ssh.exec_command(f"mkdir -p {remote_cns_dir}")

    if cns_wheel:
        # Upload user-provided wheel
        wheel_path = Path(cns_wheel).resolve()
        remote_wheel_path = f"{remote_cns_dir}/{wheel_path.name}"

        with rich_spinner(console, "Uploading CNS wheel"):
            sftp.put(str(wheel_path), remote_wheel_path)

        # Install wheel
        install_cmd = (
            f"~/{df.name}/env/bin/python3 -m pip install {remote_wheel_path} "
            f"--force-reinstall"
        )
        with rich_spinner(console, "Installing CNS package"):
            _, stdout, stderr = ssh.exec_command(install_cmd)
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                error = stderr.read().decode()
                console.print(Panel(f"[red]Command failed: {install_cmd}\n\n{error}",
                                    title="Installation Error"))
                raise click.Abort
    else:
        console.print("[yellow]No wheel provided - skipping package upload/installation.[/yellow]")
        console.print("Assuming the environment already contains the required CNS package.")

    template = jinja2.Template(CNS_SYSTEMD_USER_SERVICE_TEMPLATE)
    service_file_content = template.render(
        working_directory=f"/home/{df.user}/{df.name}",
        exec=f"/home/{df.user}/{df.name}/env/bin/cns server -p 4800 -H 0.0.0.0",
    )
    service_file_path = f"/home/{df.user}/.config/systemd/user/cns-server.service"

    with rich_spinner(console, "Installing CNS service"):
        ssh.exec_command(f"mkdir -p /home/{df.user}/.config/systemd/user")

        with sftp.open(service_file_path, "w") as fd:
            fd.write(service_file_content)

        ssh.exec_command(f"chmod 644 {service_file_path}")
        ssh.exec_command("systemctl --user daemon-reload")
        ssh.exec_command("systemctl --user enable cns-server.service")
        ssh.exec_command("systemctl --user restart cns-server.service")

    console.print("[bold green]✔ CNS Server deployed and started successfully[/bold green]")
    ssh.close()
