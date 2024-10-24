<p align="center">
  <img src="docs/media/icon.svg" alt="Kevinbot v3 logo" width=120/>
</p>

# KevinbotLib

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch)
[![PyPI - Version](https://img.shields.io/pypi/v/kevinbotlib.svg)](https://pypi.org/project/kevinbotlib)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kevinbotlib.svg)](https://pypi.org/project/kevinbotlib)

-----

**Communicate with Kevinbot v3 Hardware**

KevinbotLib incldes all the necessary classes for communicating with and controlling Kevinbot v3 hardware. It also contains an interface over MQTT to allow multiple clients on-robot as well as off-robot. Your code stays mostly the same whether you are communicating directly over serial, or using MQTT.

## Table of Contents

- [Installation](#installation)
- [Developing](#developing)
- [License](#license)

## Installation

```console
pip install kevinbotlib
```

## Developing

### Set up module in development mode

* Install hatch
  
  [Hatch Installation](https://hatch.pypa.io/1.12/install/) (I recommend using pipx)
* Clone this repo

  ```console
  git clone https://github.com/meowmeowahr/kevinbotlib && cd kevinbotlib
  ```
* Create env
  ```console
  hatch env create
  ```
* Activate env

  ```console
  hatch shell
  ```

### Formatting

Formatting is done through ruff. You can run the formatter using:

```console
hatch fmt
```

## License

`kevinbotlib` is distributed under the terms of the [GPL-3.0-or-later](https://spdx.org/licenses/GPL-3.0-or-later.html) license.
