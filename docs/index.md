# Welcome to KevinbotLib

![Kevinbot logo](media/icon.svg#only-dark){: style="height:128px;width:128px"}
![Kevinbot logo](media/icon-black.svg#only-light){: style="height:128px;width:128px"}

[![PyPI - Version](https://img.shields.io/pypi/v/kevinbotlib.svg?style=for-the-badge)](https://pypi.org/project/kevinbotlib)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kevinbotlib.svg?style=for-the-badge)](https://pypi.org/project/kevinbotlib)
![PyPI - License](https://img.shields.io/pypi/l/kevinbotlib?style=for-the-badge)
![Pepy Total Downloads](https://img.shields.io/pepy/dt/kevinbotlib?style=for-the-badge)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=for-the-badge)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json&style=for-the-badge)](https://github.com/astral-sh/uv)
[![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg?style=for-the-badge)](https://github.com/pypa/hatch)
![Codacy grade](https://img.shields.io/codacy/grade/0a806fcc04e441538d3c92d42ab3f7ca?style=for-the-badge)

-----

KevinbotLib is a modular robot control system integrating a high-speed server-client communication system, robust logging, gamepad inputs, and more.

## Features

### The Command Scheduler

* A way to asynchronously run robot tasks
* Commands can be grouped to run sequentially or in parallel if desired
* Commands can be executed at a set interval

### The Communication System

* Uses [Redis](https://redis.io/open-source/) for set/get and pub/sub communication
* Data can be easily sent from robot to client or vice versa
* Data is synchronized between all clients
* Out-of-the-box ready-made sendables for builtin primitive types
* Create custom sendables based on [pydantic](https://github.com/pydantic/pydantic) models

### The Vision Pipeline System

* Create vision pipelines based on [OpenCV](https://opencv.org/)
* Pre-made sendables for video frames
* Pre-made encoders and decoders for the communication system

### Robust Logging

* Logging is based on [loguru](https://github.com/Delgan/loguru)
* Automatic file rotations
* Logs to `stdout`, an inbuilt file server over HTTP, and/or files.

### Gamepad Inputs

* Based on [SDL2](https://github.com/py-sdl/py-sdl2)
* Builtin-support for all Game Controllers supported under the SDL2 GameController API
* Joystick data sender and receiver through the communication system

### The Control Console

* Operate a KevinbotLib robot through a simple GUI interface
* Supports up to 8 gamepad devices (up to 32 buttons each)
* View live robot telemetry
* View battery voltage (planned)
* Change robot state and OpModes
* Monitor robot system metrics

!!! Warning "Development"
    This project is in the early stage of development. There are many missing functions that will be supported in the future.
