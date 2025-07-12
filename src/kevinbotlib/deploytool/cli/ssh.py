import click
import rich
import rich.table
import rich.tree

from kevinbotlib.deploytool.cli.init import attempt_read_project_name
from kevinbotlib.deploytool.cli.ssh_apply_key import apply_key_command
from kevinbotlib.deploytool.cli.test import ssh_test_command
from kevinbotlib.deploytool.sshkeys import SSHKeyManager


@click.group("ssh")
def ssh_group():
    """SSH Key Enrollment Tools"""


@click.command
@click.option(
    "--name",
    prompt="Robot project name",
    help="Name of the robot project to be associated with the new keys",
    type=str,
    default=attempt_read_project_name(),
)
def init(name: str):
    """Initialize a new local SSH RSA private and public key"""
    manager = SSHKeyManager("KevinbotLibDeployTool")

    if name in manager.list_keys():
        click.confirm(f"Key for '{name}' already exists. Do you want to overwrite it?", abort=True)

    keys = manager.generate_key(name)

    # Fancy printing
    tree = rich.tree.Tree("\nRSA Keys")
    tree.add(f"Private Key - {keys[0]}")
    tree.add(f"Public Key - {keys[1]}")
    rich.print(tree)


@click.command
@click.argument("name", type=str)
@click.option("-y", "--yes", help="Disable confirmation prompt", is_flag=True)
def remove(name: str, *, yes: bool):
    """Remove a local SSH RSA private and public key"""
    if not yes:
        click.confirm(f"Are you sure you want to remove private and public keys for {name}?", abort=True)

    manager = SSHKeyManager("KevinbotLibDeployTool")
    if not manager.remove_key(name):
        click.echo(f"Key {name} doesn't exist, not deleting", err=True)


@click.command("list")
def list_keys():
    """List all stored SSH RSA keys"""
    manager = SSHKeyManager("KevinbotLibDeployTool")

    # Get the list of key names
    keys = manager.list_keys()

    if not keys:
        click.echo("No keys found.")
        return

    # Create a table using rich
    table = rich.table.Table()

    # Add columns to the table
    table.add_column("Key Name", justify="left", style="cyan", no_wrap=True)
    table.add_column("Private Key Path", justify="left", style="magenta", overflow="fold")
    table.add_column("Public Key Path", justify="left", style="magenta", overflow="fold")
    # Add rows for each key
    for key_name, (private, public) in keys.items():
        table.add_row(key_name, private, public)

    # Print the table
    rich.print(table)


# Add commands to the group
ssh_group.add_command(init)
ssh_group.add_command(remove)
ssh_group.add_command(list_keys)
ssh_group.add_command(apply_key_command)
ssh_group.add_command(ssh_test_command)
