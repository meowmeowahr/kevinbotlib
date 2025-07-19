# Command Line Tools

![Banner Logo](../media/cli-banner-dark.svg#only-dark)
![Banner Logo](../media/cli-banner-light.svg#only-light)

The KevinbotLib command-line tools are automatically installed using [`pip`](../installation.md#install-with-pip).

## `apps` (Group)

The apps group contains all KevinbotLib graphical utilities.

### `apps console`

[KevinbotLib Control Console](../apps/console/index.md) can be launched with the below command:

```console
kevinbotlib apps console
```

#### Options

<div class="grid cards" markdown>

- :material-text:{ .lg .middle } __Verbose Logging__

    ---

    `-v` *or* `--verbose`: Enables verbose-level logging


- :material-text:{ .lg .middle } __Trace Logging__

    ---

    `-t` *or* `--trace`: Enables trace-level logging

- :material-lock-open:{ .lg .middle } __Disable Screen Lock Inhibit__

    ---

    `--no-lock`: Disables the screen lock inhibitor when running the console

</div>

### `apps dashboard`

[KevinbotLib Dashboard](../apps/dashboard/index.md) can be launched with the below command:

```console
kevinbotlib apps dashboard
```

#### Options

<div class="grid cards" markdown>

- :material-text:{ .lg .middle } __Verbose Logging__

    ---

    `-v` *or* `--verbose`: Enables verbose-level logging


- :material-text:{ .lg .middle } __Trace Logging__

    ---

    `-t` *or* `--trace`: Enables trace-level logging

</div>

### `apps logdownloader`

[KevinbotLib Log Downloader](../apps/logdownloader/index.md) can be launched with the below command:

```console
kevinbotlib apps logdownloader
```

#### Options

<div class="grid cards" markdown>

- :material-text:{ .lg .middle } __Verbose Logging__

    ---

    `-v` *or* `--verbose`: Enables verbose-level logging


- :material-text:{ .lg .middle } __Trace Logging__

    ---

    `-t` *or* `--trace`: Enables trace-level logging

</div>

### `apps logviewer`

[KevinbotLib Log Viewer](../apps/logviewer/index.md) can be launched with the below command:

```console
kevinbotlib apps logviewer
```

#### Options

<div class="grid cards" markdown>

- :material-text:{ .lg .middle } __Verbose Logging__

    ---

    `-v` *or* `--verbose`: Enables verbose-level logging


- :material-text:{ .lg .middle } __Trace Logging__

    ---

    `-t` *or* `--trace`: Enables trace-level logging

</div>

## `fileserver`

The [KevinbotLib File Server](../fileserver.md) can be launched using the following command:

```console
kevinbotlib fileserver
```

### Options

<div class="grid cards" markdown>

- :material-text:{ .lg .middle } __Verbose Logging__

    ---

    `-v` *or* `--verbose`: Enables verbose-level logging


- :material-text:{ .lg .middle } __Trace Logging__

    ---

    `-t` *or* `--trace`: Enables trace-level logging

- :material-folder:{ .lg .middle } __Directory__

    ---

    `-d` *or* `--dir`: Sets the directory for the file server. Defaults to the current working directory.

- :material-upload-network:{ .lg .middle } __Server Port__

    ---

    `-d` *or* `--dir`: Sets the port to serve on. Defaults to `8000`.

- :material-ip-network:{ .lg .middle } __Server Host__

    ---

    `-d` *or* `--dir`: Sets the host to serve on. Defaults to `localhost`.

</div>

## `hardware serial` (Group)

The serial group contains utilities for serial device enumeration.

### `hardware serial enumerate`

The `kevinbotlib hardware serial enumerate` command will detect any connected Serial devices.

### Options

<div class="grid cards" markdown>

- :material-text:{ .lg .middle } __Raw Output__

    ---

    `-R` *or* `--raw`: Enables raw plain-text output
</div>

## `logs` (Group)

The logs group contains tools for managing log files

### `logs where`

The `kevinbotlib logs where` command will detect output the default location for local log storage.

### Options

*No Options*

### `logs size`

The `kevinbotlib logs size` command output the size of the default logging directory

### Options

<div class="grid cards" markdown>

- :material-harddisk:{ .lg .middle } __Bytes__

    ---

    `-b` *or* `--bytes`: Output raw number of bytes
</div>

## `deploytool`

The `deploytool` group contains the commands to deploy to a robot over SSH/SFTP.

View more information [here](../deploytool/index.md)

## `deploy`

Alias to [`deploytool`](#deploytool)