# Command Line Modules


## `deploytool init`

Generate a new [Deployfile](deployfile.md)


### Options

Unprovided arguments will require user input before the `Deployfile.toml` is generated.

<div class="grid cards" markdown>

- :material-robot:{ .lg .middle } __Robot Name__

    ---

    `--name`: Name of the robot to be deployed. Must not contain spaces or special characters.


- :material-account:{ .lg .middle } __SSH Username__

    ---

    `--ssh-user`: Set the username for SSH deployment.

- :material-network:{ .lg .middle } __SSH Host__

    ---

    `--ssh-host`: Hostname of IP address for SSH deployment.

- :material-network:{ .lg .middle } __SSH Port__

    ---

    `--ssh-port`: Port for SSH deployment.

- :material-language-python:{ .lg .middle } __Target Python Version__

    ---

    `--python-version`: Python version of the target. Must be between 3.11 and 4.0.

- :material-language-c:{ .lg .middle } __Target glibc Version__

    ---

    `--glibc-version`: glibc version of the target.

- :material-chip:{ .lg .middle } __Target Architecture__

    ---

    `--arch`: CPU architecture of the target. Can be `x64`, `aarch64`, and `armhf`.

- :material-folder:{ .lg .middle } __Deployfile destination__

    ---

    `--dest-dir`: Destination directory for the `Deployfile.toml` output.

</div>

## `deploytool ssh` (Group)

### `deploytool ssh init`

Initialize a new robot SSH private and public key.

!!! Info
    SSH keys will be stored globally, and available for all projects. Accidentally committing your SSH keys is not a risk.

#### Options

Unprovided arguments will require user input before the keys are generated.

<div class="grid cards" markdown>

- :material-robot:{ .lg .middle } __Robot Name__

    ---

    `--name`: Name of the robot to generate keys for. Must not contain spaces or special characters.

</div>

### `deploytool ssh remove [NAME]`

Remove an SSH key pain.

#### Positional Arguments

<div class="grid cards" markdown>

- :material-robot:{ .lg .middle } __Robot Name__

    ---

    `NAME`: Name of the robot to delete keys for. Must not contain spaces or special characters.

</div>

### `deploytool ssh list`

List out SSH public and private key paths.
Output will be table formatted and colorized.

### `deploytool ssh apply-key`

Apply an SSH public key to a remote robot.

#### Options

Unprovided arguments will require user input before the `Deployfile.toml` is generated.

<div class="grid cards" markdown>

- :material-robot:{ .lg .middle } __Key Name__

    ---

    `--name`: Name of the SSH key pair. Must not contain spaces or special characters.

- :material-account:{ .lg .middle } __SSH Username__

    ---

    `--user`: Username to apply the SSH key using.

- :material-form-textbox-password:{ .lg .middle } __SSH Password__

    ---

    `--password`: Password for SSH user.

- :material-network:{ .lg .middle } __SSH Host__

    ---

    `--host`: Hostname of IP address for SSH.

- :material-network:{ .lg .middle } __SSH Port__

    ---

    `--port`: Port for SSH.

</div>

### `deploytool ssh test`

Test the SSH connection to a robot.

#### Options

Unprovided arguments will require user input before the test starts.

<div class="grid cards" markdown>

- :material-robot:{ .lg .middle } __Key Name__

    ---

    `--key-name`: Name of the SSH key pair. Must not contain spaces or special characters.

- :material-account:{ .lg .middle } __SSH Username__

    ---

    `--user`: Username to apply the SSH key using.

- :material-network:{ .lg .middle } __SSH Host__

    ---

    `--host`: Hostname of IP address for SSH.

- :material-network:{ .lg .middle } __SSH Port__

    ---

    `--port`: Port for SSH.

</div>

## `deploytool test`

Test Deployfile by connecting to a robot.

#### Options

Unprovided arguments will require user input before the test starts.

<div class="grid cards" markdown>

- :material-folder:{ .lg .middle } __Deploy Directory__

    ---

    `-d` *or* `--directory`: Optional. Path to the directory containing the Deployfile.toml. Defaults to the current working directory.

</div>
