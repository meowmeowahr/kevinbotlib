# Deployfile Specification

A `Deployfile.toml` is required to deploy code to a remote robot target with KevinbotLib DeployTool.

## Example

```toml
[target]
name = "kevinbotv3"
python_version = "3.13"
glibc_version = "2.40"
arch = "aarch64"
user = "kevinbot"
host = "10.0.0.2"
port = 22
```

## `target`

This section defines properties of the target device.

### `name`

This specifies the target name. The target name is used to create the service file and to identify which set of code is running.

### `python_version`

This identifies what version of python the target is using.

### `glibc_version`

!!! Note
    This key is not currently used, but may be in the future. It is still required to use DeployTool.

This identifies what glibc version the target is running.

### `arch`

Possible values: `aarch64`, `x64`

### `user`

This sets the user which code is deployed to. It is not recommended to use the root user.

### `host`

This defines the IP address or hostname of the robot.

### `port`

This defines the SSH port of the robot.