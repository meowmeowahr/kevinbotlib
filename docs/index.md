# Welcome to KevinbotLib

![Kevinbot logo](media/icon.svg#only-dark){: style="height:128px;width:128px"}
![Kevinbot logo](media/icon-black.svg#only-light){: style="height:128px;width:128px"}

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=for-the-badge)](https://github.com/astral-sh/ruff)
[![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg?style=for-the-badge)](https://github.com/pypa/hatch)
[![PyPI - Version](https://img.shields.io/pypi/v/kevinbotlib.svg?style=for-the-badge)](https://pypi.org/project/kevinbotlib)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kevinbotlib.svg?style=for-the-badge)](https://pypi.org/project/kevinbotlib)

KevinbotLib is a robot control system for Kevinbot v3 and the [Kevinbot Core](https://github.com/meowmeowahr/KevinbotV3-HW-Core). You can easily and safely control Kevinbot's drivebase, servos, lighting, and more. It also continuously polls sensor data. It can operate in two modes: Direct Serial, and MQTT with the Kevinbot Server.

### Features

* **Multiple Control Interfaces**
    * Direct Serial mode
    * MQTT networked mode (with KevinbotLib Server)


* **Comprehensive Subsystem Control**
    * Drivebase with power and state monitoring
    * Servo control
    * Multi-zone lighting system with effects
    * Continuous sensor polling
    * Battery management and monitoring
    * IMU support (gyroscope and accelerometer)


* **Developer-Friendly Design**
    * Simple MQTT API
    * Extensive configuration options
    * Real-time state tracking
    * Built-in safety features
    * Detailed logging and debugging
    * Python 3.13 support


* **Robust Architecture**
    * Thread-safe communication
    * Event-based callback system
    * Auto-reconnection handling
    * Multiple client support via MQTT

!!! warning "Development"
    This project is in the early stage of development. There are many missing functions that will be supported in the future.
