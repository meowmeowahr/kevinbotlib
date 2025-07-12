from pathlib import Path

import click
import paramiko
from rich.console import Console

from kevinbotlib.deploytool import deployfile
from kevinbotlib.deploytool.cli.common import confirm_host_key, confirm_host_key_df
from kevinbotlib.deploytool.cli.spinner import rich_spinner
from kevinbotlib.deploytool.sshkeys import SSHKeyManager

console = Console()


@click.command("test")
@click.option("--host", prompt=True, help="Remote SSH host")
@click.option("--port", default=22, show_default=True, help="Remote SSH port")
@click.option("--user", prompt=True, help="SSH username")
@click.option("--key-name", prompt=True, help="SSH key name to use")
def ssh_test_command(host, port, user, key_name):
    """Test SSH connection to the remote host"""
    key_manager = SSHKeyManager("KevinbotLibDeployTool")
    key_info = key_manager.list_keys()
    if key_name not in key_info:
        console.print(f"[red]Key '{key_name}' not found in key manager.[/red]")
        raise click.Abort

    private_key_path, _ = key_info[key_name]

    # Load the private key
    try:
        pkey = paramiko.RSAKey.from_private_key_file(private_key_path)
    except Exception as e:
        console.print(f"[red]Failed to load private key: {e}[/red]")
        raise click.Abort from e

    confirm_host_key(console, host, user, port)

    with rich_spinner(console, "Connecting via SSH", success_message="SSH Connection Test Completed"):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # noqa: S507 # * this is ok, because the user is asked beforehand
            ssh.connect(hostname=host, port=port, username=user, pkey=pkey, timeout=10)

            _, stdout, _ = ssh.exec_command("echo Hello from $(hostname) 👋")
            output = stdout.read().decode().strip()

            console.print(f"[bold green]Success! SSH test output:[/bold green] {output}")
            ssh.close()
        except Exception as e:
            console.print(f"[red]SSH connection failed: {e!r}[/red]")
            raise click.Abort from e


@click.command("test")
@click.option(
    "-d",
    "--directory",
    default=".",
    help="Directory of the Deployfile",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
)
def deployfile_test_command(directory: str):
    """Test the SSH connection"""

    # Load Deployfile
    df = deployfile.read_deployfile(Path(directory) / "Deployfile.toml")

    key_manager = SSHKeyManager("KevinbotLibDeployTool")
    key_info = key_manager.list_keys()
    if df.name not in key_info:
        console.print(
            f"[red]Key '{df.name}' not found in key manager. Use `kevinbotlib ssh init` to create a new key`[/red]"
        )
        raise click.Abort

    private_key_path, _ = key_info[df.name]

    # Load the private key
    try:
        pkey = paramiko.RSAKey.from_private_key_file(private_key_path)
    except Exception as e:
        console.print(f"[red]Failed to load private key: {e}[/red]")
        raise click.Abort from e

    confirm_host_key_df(console, df, pkey)

    with rich_spinner(console, "Fetching data via SSH"):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # noqa: S507 # * this is ok, because the user is asked beforehand
            ssh.connect(hostname=df.host, port=df.port, username=df.user, pkey=pkey, timeout=10)

            # cpu arch
            check_cpu_arch(df, ssh)

            # glibc version
            check_glibc_ver(df, ssh)

            # python
            # check if the venv exists
            check_env(df, ssh)

            # check if the python version matches
            check_py_ver(df, ssh)

            ssh.close()
        except Exception as e:
            if isinstance(e, click.Abort):
                raise click.Abort from e
            console.print(f"[red]SSH connection failed: {e!r}[/red]")
            raise click.Abort from e


def check_py_ver(df, ssh):
    _, stdout, _ = ssh.exec_command(f"$HOME/{df.name}/env/bin/python --version")
    python_version = stdout.read().decode().strip().split(" ")[-1]
    console.print(f"[bold magenta]Remote Python version:[/bold magenta] {python_version}")
    if ".".join(python_version.split(".")[:2]) == ".".join(df.python_version.split(".")[:2]):
        console.print(
            f"[bold green]Remote robot environment Python version matches Deployfile:[/bold green] {'.'.join(python_version.split('.')[:2])}=={'.'.join(df.python_version.split('.')[:2])}"
        )
    else:
        console.print(
            f"[bold yellow]Remote robot environment Python version does not match Deployfile:[/bold yellow] {'.'.join(python_version.split('.')[:2])}!={'.'.join(df.python_version.split('.')[:2])}"
        )


def check_glibc_ver(df, ssh):
    _, stdout, _ = ssh.exec_command("ldd --version")
    glibc_version = stdout.read().decode().strip().splitlines()[0].split(" ")[-1]
    console.print(f"[bold magenta]Remote glibc version:[/bold magenta] {glibc_version}")

    if glibc_version == df.glibc_version:
        console.print(
            f"[bold green]Remote glibc version matches Deployfile:[/bold green] {glibc_version}=={df.glibc_version}"
        )
    else:
        console.print(
            f"[bold yellow]Remote glibc version does not match Deployfile:[/bold yellow] {glibc_version}!={df.glibc_version}"
        )


def check_cpu_arch(df, ssh):
    _, stdout, _ = ssh.exec_command("uname -m")
    cpu_arch = stdout.read().decode().strip()
    console.print(f"[bold magenta]Remote CPU architecture:[/bold magenta] {cpu_arch}")
    if cpu_arch == df.arch:
        console.print(f"[bold green]Remote CPU architecture matches Deployfile:[/bold green] {cpu_arch}=={df.arch}")
    else:
        console.print(
            f"[bold yellow]Remote CPU architecture does not match Deployfile:[/bold yellow] {cpu_arch}!={df.arch}"
        )


def check_env(df, ssh):
    _, stdout, _ = ssh.exec_command(f"ls $HOME/{df.name}/env")
    venv_exists = stdout.read().decode().strip()
    if not venv_exists:
        console.print("[bold red]Remote robot virtual environment does not exist[/bold red]")
        raise click.Abort
