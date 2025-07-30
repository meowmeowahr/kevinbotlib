import datetime
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import click
import paramiko
import pygit2
import toml
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

from kevinbotlib import __about__
from kevinbotlib.deploytool.cli.common import check_service_file, confirm_host_key_df, get_private_key, verbosity_option
from kevinbotlib.deploytool.cli.spinner import rich_spinner
from kevinbotlib.deploytool.deployfile import read_deployfile

console = Console()


@click.command("deploy")
@click.option(
    "-d",
    "--directory",
    default=".",
    help="Directory of the Deployfile and robot code",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
)
@click.option(
    "-W",
    "--custom-wheels",
    default=[],
    help="Custom wheels to install on the remote system",
    type=click.Path(file_okay=True, dir_okay=False, readable=True),
    multiple=True,
)
@click.option(
    "-N",
    "--no-service-start",
    is_flag=True,
)
@verbosity_option()
def deploy_code_command(directory, custom_wheels: list, verbose: int, *, no_service_start: bool):
    """Package and deploy the robot code to the target system."""
    deployfile_path = Path(directory) / "Deployfile.toml"
    if not deployfile_path.exists():
        console.print(f"[red]Deployfile not found in {directory}[/red]")
        raise click.Abort

    df = read_deployfile(deployfile_path)
    if custom_wheels:
        console.print(f"Will install custom wheels: {custom_wheels}")

    # check for src/name/__main__.py
    src_path = Path(directory) / "src" / df.name.replace("-", "_")
    if not (src_path / "__main__.py").exists():
        console.print(f"[red]Robot code is invalid: must contain {src_path / '__main__.py'}[/red]")
        raise click.Abort

    # check for pyproject.toml
    pyproject_path = Path(directory) / "pyproject.toml"
    if not pyproject_path.exists():
        console.print(f"[red]Robot code is invalid: pyproject.toml not found in {directory}[/red]")
        raise click.Abort

    private_key_path, pkey = get_private_key(console, df)

    confirm_host_key_df(console, df, pkey)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Generate manifest
        try:
            repo = pygit2.Repository(os.path.join(directory, ".git"))
            head_ref = repo.head
            head_name = repo.head.name  # e.g., 'refs/heads/main' or 'HEAD' (if detached)

            current_branch = head_name.split("/")[-1] if head_name.startswith("refs/heads/") else None

            latest_commit = repo[head_ref.target]

            # Check if the working directory is dirty (has uncommitted changes)
            status = repo.status()
            is_dirty = bool(status)

            current_tag = None
            if not is_dirty:
                for ref in repo.references:
                    if ref.startswith("refs/tags/"):
                        tag_ref = repo.references[ref]
                        tag_obj = repo[tag_ref.target]
                        tag_target = tag_obj.target if isinstance(tag_obj, pygit2.Tag) else tag_obj.oid
                        if tag_target == latest_commit.id:
                            current_tag = ref.split("/")[-1]
                            break
        except pygit2.GitError:
            current_tag = None
            current_branch = None
            latest_commit = None
            is_dirty = True

        manifest = {
            "deploytool": __about__.__version__,
            "timestamp": datetime.datetime.now(datetime.UTC).timestamp(),
            "git": {
                "branch": current_branch if current_branch else None,
                "tag": current_tag,
                "commit": str(latest_commit.id) + ("-dirty" if is_dirty else "") if latest_commit else None,
            },
            "robot": df.name,
        }

        with open(tmp_path / "manifest.json", "w") as f:
            f.write(json.dumps(manifest))

        # Build a wheel
        wheel_task = None
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            wheel_task = progress.add_task("Building wheel", total=None)
            result = None
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "hatch", "build", "-t", "wheel"],
                    cwd=directory,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                wheel_file = result.stderr.splitlines()[-1]
                if not wheel_file:
                    console.print("[red]Failed to determine wheel file location.[/red]")
                    raise click.Abort
                wheel_path = Path(directory) / wheel_file
            except subprocess.CalledProcessError as e:
                panel = Panel(
                    f"[bold red]{e!r}[/bold red]\n{result.stdout if result else ''}{result.stderr if result else ''}",
                    title="Failed to build wheel",
                )
                console.print(panel)
                raise click.Abort from e
            progress.update(wheel_task, completed=100)

        tarball_path = tmp_path / "robot_code.tar.gz"

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            tar_task = progress.add_task("Creating code tarball", total=None)
            project_root = Path(directory)
            with tarfile.open(tarball_path, "w:gz") as tar:
                src_path = project_root / "src"
                if src_path.exists():
                    tar.add(src_path, arcname="src", filter=_exclude_pycache)
                    progress.update(tar_task, advance=1)

                assets_path = project_root / "assets"
                if assets_path.exists():
                    tar.add(assets_path, arcname="assets", filter=_exclude_pycache)
                    progress.update(tar_task, advance=1)

                deploy_path = project_root / "deploy"
                if deploy_path.exists():
                    tar.add(deploy_path, arcname="deploy", filter=_exclude_pycache)
                    progress.update(tar_task, advance=1)

                pyproject_path = project_root / "pyproject.toml"
                if pyproject_path.exists():
                    tar.add(pyproject_path, arcname="pyproject.toml")
                    progress.update(tar_task, advance=1)
                    # this is to be compatible with hatchling
                    pyproject = toml.load(pyproject_path)
                    if "project" in pyproject and "readme" in pyproject["project"]:
                        readme_path = project_root / pyproject["project"]["readme"]
                        if readme_path.exists():
                            tar.add(readme_path, arcname=readme_path.name, filter=_exclude_pycache)
                            progress.update(tar_task, advance=1)

                # Include manifest
                tar.add(tmp_path / "manifest.json", arcname="deploy/manifest.json")

                # Include built wheel
                if not wheel_path.exists():
                    console.print("[red]No wheel found in build output![/red]")
                    raise click.Abort
                tar.add(wheel_path, arcname=wheel_path.parts[-1])

                # custom wheels
                if custom_wheels:
                    # add wheels to cwheels directory in the tarball
                    tar.add(wheel_path, arcname=f"cwheels/{wheel_path.parts[-1]}")
                    progress.update(tar_task, advance=1)
                for wheel in custom_wheels:
                    cwheel_path = Path(wheel).resolve()
                    if not cwheel_path.exists():
                        console.print(f"[red]Custom wheel not found: {cwheel_path}[/red]")
                        raise click.Abort
                    tar.add(cwheel_path, arcname=f"cwheels/{cwheel_path.parts[-1]}")
                    progress.update(tar_task, advance=1)

            progress.update(tar_task, completed=100)

        with rich_spinner(console, "Connecting via SFTP", success_message="SFTP connection established"):
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # noqa: S507 # * this is ok, because the user is asked beforehand
            pkey = paramiko.RSAKey.from_private_key_file(private_key_path)
            ssh.connect(hostname=df.host, port=df.port, username=df.user, pkey=pkey)
            sftp = ssh.open_sftp()

        remote_code_dir = f"$HOME/{df.name}/robot"
        remote_tarball_path = f"/home/{df.user}/{df.name}/robot_code.tar.gz"

        sftp_makedirs(sftp, f"/home/{df.user}/{df.name}")

        if check_service_file(df, ssh):
            with rich_spinner(console, "Stopping robot code", success_message="Robot code stopped"):
                ssh.exec_command(f"systemctl stop --user {df.name}.service")
        else:
            console.print(
                f"[yellow]No service file found for {df.name} — run `kevinbotlib-deploytool robot service install` to add it.[/yellow]"
            )

        # Delete old code on the remote
        with rich_spinner(console, "Deleting old code on remote", success_message="Old code deleted"):
            ssh.exec_command(f"rm -rf {remote_code_dir}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            TextColumn("ETA:"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            upload_task = progress.add_task("Uploading code tarball", total=tarball_path.stat().st_size)
            with tarball_path.open("rb") as fsrc:
                try:
                    with sftp.open(remote_tarball_path, "wb") as fdst:
                        while True:
                            chunk = fsrc.read(32768)
                            if not chunk:
                                break
                            fdst.write(chunk)
                            progress.update(upload_task, advance=len(chunk))
                except FileNotFoundError as e:
                    console.print(f"[red]Remote path not found: {remote_tarball_path}[/red]")
                    raise click.Abort from e

        with rich_spinner(console, "Extracting code on remote", success_message="Code extracted"):
            ssh.exec_command(f"mkdir -p {remote_code_dir} && tar -xzf {remote_tarball_path} -C {remote_code_dir}")
            ssh.exec_command(f"rm {remote_tarball_path}")

        # Install custom wheels with pip
        if custom_wheels:
            for wheel in custom_wheels:
                wheel_name = Path(wheel).name
                cmd = f"~/{df.name}/env/bin/python3 -m pip install {remote_code_dir}/cwheels/{wheel_name} {'-' + 'v' * verbose if verbose else ''} && ~/{df.name}/env/bin/python3 -m pip install {remote_code_dir}/cwheels/{wheel_name} {'-' + 'v' * verbose if verbose else ''} --force-reinstall --no-deps"
                _, stdout, stderr = ssh.exec_command(cmd)
                with console.status(f"[bold green]Installing custom wheel {wheel_name}...[/bold green]"):
                    while not stdout.channel.exit_status_ready():
                        line = stdout.readline()
                        if line:
                            console.print(line.strip())
                exit_code = stdout.channel.recv_exit_status()
                if exit_code != 0:
                    error = stderr.read().decode()
                    console.print(
                        Panel(
                            f"[red]Command failed: {cmd}\n\n{error}",
                            title="Command Error",
                        )
                    )
                    raise click.Abort

        # Install code via pip
        cmd = f"~/{df.name}/env/bin/python3 -m pip install {remote_code_dir}/{wheel_path.parts[-1]} {'-' + 'v'*verbose if verbose else ''} && ~/{df.name}/env/bin/python3 -m pip install {remote_code_dir}/{wheel_path.parts[-1]} {'-' + 'v'*verbose if verbose else ''} --force-reinstall --no-deps"
        _, stdout, stderr = ssh.exec_command(cmd)
        with console.status("[bold green]Installing code...[/bold green]"):
            while not stdout.channel.exit_status_ready():
                line = stdout.readline()
                if line:
                    console.print(line.strip())
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            error = stderr.read().decode()
            console.print(Panel(f"[red]Command failed: {cmd}\n\n{error}", title="Command Error"))
            raise click.Abort

        # Restart the robot code
        if not no_service_start:
            if check_service_file(df, ssh):
                with rich_spinner(console, "Starting robot code", success_message="Robot code started"):
                    ssh.exec_command(f"systemctl start --user {df.name}.service")
            else:
                console.print(
                    f"[yellow]No service file found for {df.name} — run `kevinbotlib-deploytool robot service install` to add it.[/yellow]"
                )

        console.print(f"[bold green]\u2714 Robot code deployed to {remote_code_dir}[/bold green]")
        ssh.close()


def _exclude_pycache(tarinfo):
    if "__pycache__" in tarinfo.name or tarinfo.name.endswith(".pyc"):
        return None
    return tarinfo


def sftp_makedirs(sftp, path):
    parts = Path(path).parts
    current = ""
    for part in parts:
        current = f"{current}/{part}" if current else part
        try:
            sftp.stat(current)
        except OSError:
            sftp.mkdir(current)
