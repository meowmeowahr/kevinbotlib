# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

from kevinbotlib.misc import Temperature


class CoreErrors(Enum):
    """These are errors from Kevinbot Core"""

    """No errors are present"""
    OK = 0
    """Error state unknown"""
    UNKNOWN = 1
    """One-Wire bus is shorted"""
    OW_SHORT = 2
    """One-Wire bus error"""
    OW_ERROR = 3
    """One-Wire device not found"""
    OW_DNF = 4
    """LCD Init failed"""
    LCD_INIT_FAIL = 5
    """PCA9685 (servos) init fail"""
    PCA_INIT_FAIL = 6
    """Failure to recieve core tick"""
    TICK_FAIL = 7
    # TODO: Add full error list


class MotorDriveStatus(Enum):
    """The status of each motor in the drivebase"""

    UNKNOWN = 10
    MOVING = 11
    HOLDING = 12
    OFF = 13


class BmsBatteryState(Enum):
    """The status of a single battery attached to the BMS"""

    UNKNOWN = 0
    NORMAL = 1
    UNDER = 2
    OVER = 3
    STOPPED = 4  # Stopped state if BMS driver crashed


@dataclass
class DrivebaseState:
    """The state of the drivebase as a whole"""

    left_power: int = 0
    right_power: int = 0
    amps: list[float] = field(default_factory=lambda: [0, 0])
    watts: list[float] = field(default_factory=lambda: [0, 0])
    status: list[MotorDriveStatus] = field(default_factory=lambda: [MotorDriveStatus.UNKNOWN, MotorDriveStatus.UNKNOWN])


@dataclass
class ServoState:
    """The state of the servo subsystem"""

    angles: list[int] = field(default_factory=lambda: [-1] * 32)


@dataclass
class BMState:
    """The state of the BMS (Battery Management System)"""

    voltages: list[float] = field(default_factory=lambda: [0.0, 0.0])
    raw_voltages: list[float] = field(default_factory=lambda: [0.0, 0.0])
    states: list[BmsBatteryState] = field(default_factory=lambda: [BmsBatteryState.UNKNOWN, BmsBatteryState.UNKNOWN])


@dataclass
class IMUState:
    """The state of the IMU (Inertial Measurement System)"""

    accel: list[int] = field(default_factory=lambda: [-1] * 3)  # X Y Z
    gyro: list[int] = field(default_factory=lambda: [-1] * 3)  # R P Y


@dataclass
class ThermometerState:
    """The state of the DS18B20 Thermometers (does not include BME280)"""

    left_motor: Temperature = field(default_factory=lambda: Temperature(-1))
    right_motor: Temperature = field(default_factory=lambda: Temperature(-1))
    internal: Temperature = field(default_factory=lambda: Temperature(-1))


@dataclass
class EnviroState:
    """The state of the BME280 Envoronmental sensor"""

    temperature: Temperature = field(default_factory=lambda: Temperature(-1))
    humidity: float = 0
    pressure: int = 0


@dataclass
class LightingState:
    """The state of Kevinbot's led segments"""

    camera: int = 0
    head_effect: str = "unknown"
    head_bright: int = 0
    head_update: int = -1
    head_color1: Iterable[int] = (0, 0, 0)
    head_color2: Iterable[int] = (0, 0, 0)
    body_effect: str = "unknown"
    body_bright: int = 0
    body_update: int = -1
    body_color1: Iterable[int] = (0, 0, 0)
    body_color2: Iterable[int] = (0, 0, 0)
    base_effect: str = "unknown"
    base_bright: int = 0
    base_update: int = -1
    base_color1: Iterable[int] = (0, 0, 0)
    base_color2: Iterable[int] = (0, 0, 0)


@dataclass
class KevinbotState:
    """The state of the robot as a whole"""

    connected: bool = False
    enabled: bool = False
    error: CoreErrors = CoreErrors.OK
    uptime: int = 0
    uptime_ms: int = 0
    motion: DrivebaseState = field(default_factory=DrivebaseState)
    servos: ServoState = field(default_factory=ServoState)
    battery: BMState = field(default_factory=BMState)
    imu: IMUState = field(default_factory=IMUState)
    thermal: ThermometerState = field(default_factory=ThermometerState)
    enviro: EnviroState = field(default_factory=EnviroState)
    lighting: LightingState = field(default_factory=LightingState)
