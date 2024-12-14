# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Final

from kevinbotlib import __about__
from kevinbotlib.core import Drivebase, Lighting, MqttKevinbot, SerialKevinbot, Servo, Servos
from kevinbotlib.exceptions import HandshakeTimeoutException
from kevinbotlib.eyes import EyeCallbackType, KevinbotEyesState, MqttEyes, SerialEyes
from kevinbotlib.models import (
    BmsBatteryStatus,
    BMState,
    CoreErrors,
    DrivebaseState,
    EyeMotion,
    EyeSkin,
    IMUState,
    KevinbotState,
    MotorDriveStatus,
    ServoState,
    ThermometerState,
)

version: Final[str] = __about__.__version__

__all__ = [
    "SerialKevinbot",
    "MqttKevinbot",
    "Drivebase",
    "Servo",
    "Servos",
    "Lighting",
    "KevinbotState",
    "DrivebaseState",
    "SerialEyes",
    "MqttEyes",
    "KevinbotEyesState",
    "EyeSkin",
    "EyeMotion",
    "EyeCallbackType",
    "ServoState",
    "BMState",
    "IMUState",
    "ThermometerState",
    "MotorDriveStatus",
    "BmsBatteryStatus",
    "CoreErrors",
    "HandshakeTimeoutException",
]
