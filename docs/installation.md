# Installation

!!! info
    KevinbotLib requires Python 3.10 or newer.

## Install with pip

Run the following in a virtual environment for the base version.

```console
pip install kevinbotlib
```

!!! note
    Some Linux systems require adding the user to the `dialout` group to access serial-connected hardware

    Run the following command to add yourself to the group:
    ```console
    sudo usermod -a -G dialout $USER
    ```

## Verify installation

You can check the installed version of KevinbotLb by running the following command:

```console
kevinbotlib --version
```

You should see something like this `KevinbotLib, version 1.0.0-alpha.7`
