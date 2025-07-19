# KevinbotLib DeployTool

KevinbotLib DeployTool allows you to deploy robot code to a networked robot over SSH/SFTP.

## Target Requirements

* Linux with systemd
* A non-root user account
* User account with linger-login enabled
* Target Python version of 3.11 or greater (can be installed at a custom location)

## Code Requirements

* Must use uv and hatch
* uv and hatch must be added as local requirements and locally installed
* Code entrypoint in `./src/__main__.py`
