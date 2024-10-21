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
    """The status of each motor in the drrivebase"""

    UNKNOWN = 10
    MOVING = 11
    HOLDING = 12
    OFF = 13


@dataclass
class DrivebaseState:
    """The state of the drivebase as a whole"""

    left_power: int = 0
    right_power: int = 0
    amps: list[float] = field(default_factory=lambda: [0, 0])
    watts: list[float] = field(default_factory=lambda: [0, 0])
    status: list[MotorDriveStatus] = field(default_factory=lambda: [MotorDriveStatus.UNKNOWN, MotorDriveStatus.UNKNOWN])


@dataclass
class KevinbotState:
    """The state of the robot as a whole"""

    connected: bool = False
    enabled: bool = False
    error: CoreErrors = CoreErrors.OK
    motion: DrivebaseState = field(default_factory=DrivebaseState)
