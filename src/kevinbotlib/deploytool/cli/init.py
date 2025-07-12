import os

import click
import toml
from rich.console import Console
from rich.syntax import Syntax


def create_deployfile(data, dest_dir="."):
    """Create a Deployfile.toml at the specified destination directory and display it."""
    deployfile_path = os.path.join(dest_dir, "Deployfile.toml")

    # Ensure destination directory exists
    os.makedirs(dest_dir, exist_ok=True)

    if os.path.exists(deployfile_path):
        click.echo(f"Warning: '{deployfile_path}' already exists.")
        click.confirm("Do you want to overwrite it?", default=True, abort=True)

    # Convert data to TOML string
    toml_string = toml.dumps(data)

    # Write to file
    with open(deployfile_path, "w") as f:
        f.write(toml_string)
    click.echo(f"Deployfile created at {deployfile_path}\n")

    # Pretty-print with Rich
    console = Console()
    syntax = Syntax(toml_string, "toml", theme="ansi_dark", line_numbers=False)
    console.print(syntax)


def validate_version(_ctx, _param, value, min_version=None, max_version=None):
    """Validate version numbers with optional min and max constraints."""
    try:
        major, minor = map(int, value.split(".")[:2])
        version = (major, minor)
    except ValueError as e:
        msg = f"Invalid version format '{value}'. Use X.Y (e.g., 3.10)"
        raise click.BadParameter(msg) from e

    if min_version and version < min_version:
        msg = f"Version must be >= {'.'.join(map(str, min_version))}"
        raise click.BadParameter(msg)
    if max_version and version >= max_version:
        msg = f"Version must be < {'.'.join(map(str, max_version))}"
        raise click.BadParameter(msg)
    if major < 0 or minor < 0:
        msg = "Version numbers cannot be negative"
        raise click.BadParameter(msg)

    return value


def attempt_read_project_name() -> str | None:
    """Attempt to read the project name from pyproject.toml if it exists."""
    pyproject_path = os.path.join(os.getcwd(), "pyproject.toml")
    if not os.path.exists(pyproject_path):
        return None

    try:
        with open(pyproject_path) as f:
            pyproject_data = toml.load(f)
            return pyproject_data.get("project", {}).get("name")
    except (toml.TomlDecodeError, KeyError):
        return None


@click.command()
@click.option(
    "--name", prompt="Robot project name", help="Robot project name", type=str, default=attempt_read_project_name()
)
@click.option("--ssh-user", prompt="SSH deploy user", help="Target SSH user", type=str)
@click.option("--ssh-host", prompt="SSH deploy host", help="Target SSH host")
@click.option("--ssh-port", prompt="SSH deploy port", help="Target SSH port", type=int, default=22)
@click.option(
    "--python-version",
    prompt="Python version",
    help="Target Python version (3.10 <= version < 4.0)",
    default="3.10",
    callback=lambda ctx, param, value: validate_version(ctx, param, value, (3, 10), (4, 0)),
)
@click.option(
    "--glibc-version",
    prompt="glibc version",
    help="Target glibc version",
    default="2.36",
    callback=lambda ctx, param, value: validate_version(ctx, param, value),
)
@click.option(
    "--arch",
    prompt="Target Architecture",
    type=click.Choice(["x64", "aarch64", "armhf"], case_sensitive=False),
    help="Target architecture",
    default="x64",
)
@click.option(
    "--dest-dir",
    default=".",
    help="Destination directory for Deployfile",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
)
def init(
    name: str,
    ssh_user: str,
    ssh_host: str,
    ssh_port: int,
    python_version: str,
    glibc_version: str,
    arch: str,
    dest_dir: str,
):
    """Initialize a new Deployfile"""

    if ssh_port < 1 or ssh_port > 65535:  # noqa: PLR2004
        msg = "SSH port must be between 1 and 65535"
        raise click.BadParameter(msg)

    deployfile_data = {
        "target": {
            "name": name,
            "python_version": python_version,
            "glibc_version": glibc_version,
            "arch": arch.lower(),
            "user": ssh_user,
            "host": ssh_host,
            "port": ssh_port,
        }
    }

    create_deployfile(deployfile_data, dest_dir)
