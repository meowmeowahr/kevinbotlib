# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass, field
from enum import Enum


class CoreErrors(Enum):
    """These are errors from Kevinbot Core"""

    OK = 0
    UNKNOWN = 1
    OW_SHORT = 2
    OW_ERROR = 3
    OW_DNF = 4
    LCD_INIT_FAIL = 5
    PCA_INIT_FAIL = 6
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
class KevinbotState:
    """The state of the robot as a whole"""

    connected: bool = False
    enabled: bool = False
    error: CoreErrors = CoreErrors.OK
    motion: DrivebaseState = field(default_factory=DrivebaseState)
    servos: ServoState = field(default_factory=ServoState)
    battery: BMState = field(default_factory=BMState)
    imu: IMUState = field(default_factory=IMUState)
