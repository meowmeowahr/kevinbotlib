<p align="center">
  <img src="https://github.com/meowmeowahr/kevinbotlib/raw/main/docs/media/icon.svg" alt="Kevinbot v3 logo" width=120/>
</p>

# KevinbotLib

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch)
[![PyPI - Version](https://img.shields.io/pypi/v/kevinbotlib.svg)](https://pypi.org/project/kevinbotlib)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kevinbotlib.svg)](https://pypi.org/project/kevinbotlib)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/0a806fcc04e441538d3c92d42ab3f7ca)](https://app.codacy.com/gh/meowmeowahr/kevinbotlib/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

-----

**The KevinbotLib Robot Development Framework**

KevinbotLib includes many utility classes for developing robots, such as communication, joystick input, logging, and more. KevinbotLib also includes out-of-the-box applications to interact and control KevinbotLib robots.

## Table of Contents

- [KevinbotLib](#kevinbotlib)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
  - [Developing](#developing)
    - [Set up module in development mode](#set-up-module-in-development-mode)
    - [Formatting](#formatting)
  - [License](#license)

## Installation

```console
pip install kevinbotlib
```

## Developing

### Set up module in development mode

- Install hatch
  
  [Hatch Installation](https://hatch.pypa.io/1.12/install/) (I recommend using pipx)
- Clone this repo

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

`kevinbotlib` is distributed under the terms of the [LGPL-3.0-or-later](https://spdx.org/licenses/LGPL-3.0-or-later.html) license.

All KevinbotLib binaries are distributed under the terms of the [GPL-3.0-or-later](https://spdx.org/licenses/GPL-3.0-or-later.html) license due to the inclusion of several GPL dependencies.
