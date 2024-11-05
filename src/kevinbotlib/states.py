# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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


class DrivebaseState(BaseModel):
    """The state of the drivebase as a whole"""

    left_power: int = 0
    right_power: int = 0
    amps: list[float] = Field(default_factory=lambda: [0, 0])
    watts: list[float] = Field(default_factory=lambda: [0, 0])
    status: list[MotorDriveStatus] = Field(default_factory=lambda: [MotorDriveStatus.UNKNOWN, MotorDriveStatus.UNKNOWN])


class ServoState(BaseModel):
    """The state of the servo subsystem"""

    angles: list[int] = Field(default_factory=lambda: [-1] * 32)


class BMState(BaseModel):
    """The state of the BMS (Battery Management System)"""

    voltages: list[float] = Field(default_factory=lambda: [0.0, 0.0])
    raw_voltages: list[float] = Field(default_factory=lambda: [0.0, 0.0])
    states: list[BmsBatteryState] = Field(default_factory=lambda: [BmsBatteryState.UNKNOWN, BmsBatteryState.UNKNOWN])


class IMUState(BaseModel):
    """The state of the IMU (Inertial Measurement System)"""

    accel: list[int] = Field(default_factory=lambda: [-1] * 3)  # X Y Z
    gyro: list[int] = Field(default_factory=lambda: [-1] * 3)  # R P Y


class ThermometerState(BaseModel):
    """The state of the DS18B20 Thermometers (does not include BME280)"""

    left_motor: float = -1
    right_motor: float = -1
    internal: float = -1


class EnviroState(BaseModel):
    """The state of the BME280 Envoronmental sensor"""

    temperature: float = -1
    humidity: float = 0
    pressure: int = 0


class LightingState(BaseModel):
    """The state of Kevinbot's led segments"""

    camera: int = 0
    head_effect: str = "unknown"
    head_bright: int = 0
    head_update: int = -1
    head_color1: list[int] = Field(default=[0, 0, 0], min_length=3)
    head_color2: list[int] = Field(default=[0, 0, 0], min_length=3)
    body_effect: str = "unknown"
    body_bright: int = 0
    body_update: int = -1
    body_color1: list[int] = Field(default=[0, 0, 0], min_length=3)
    body_color2: list[int] = Field(default=[0, 0, 0], min_length=3)
    base_effect: str = "unknown"
    base_bright: int = 0
    base_update: int = -1
    base_color1: list[int] = Field(default=[0, 0, 0], min_length=3)
    base_color2: list[int] = Field(default=[0, 0, 0], min_length=3)


class KevinbotState(BaseModel):
    """The state of the robot as a whole"""

    connected: bool = False
    enabled: bool = False
    error: CoreErrors = CoreErrors.OK
    estop: bool = False
    uptime: int = 0
    uptime_ms: int = 0
    motion: DrivebaseState = Field(default_factory=DrivebaseState)
    servos: ServoState = Field(default_factory=ServoState)
    battery: BMState = Field(default_factory=BMState)
    imu: IMUState = Field(default_factory=IMUState)
    thermal: ThermometerState = Field(default_factory=ThermometerState)
    enviro: EnviroState = Field(default_factory=EnviroState)
    lighting: LightingState = Field(default_factory=LightingState)


class States(BaseModel):
    page: int = 3
    motion: int = 1
    error: int = 0


class LogoFormat(BaseModel):
    logo_time: int = 2


class Display(BaseModel):
    speed: int = 82000000
    backlight: int = 100
    backlight_pin: int = 16


class Motions(BaseModel):
    speed: int = 78
    left_point: tuple[int, int] = (80, 120)
    center_point: tuple[int, int] = (120, 120)
    right_point: tuple[int, int] = (160, 120)
    pos: tuple[int, int] = (105, 129)


class SimpleSkin(BaseModel):
    bg_color: str = "#0022FF"
    iris_color: str = "#FFFFFF"
    pupil_color: str = "#000000"
    iris_size: int = 105
    pupil_size: int = 86


class MetalSkin(BaseModel):
    bg_color: str = "#ffffff"
    iris_size: int = 200
    tint: int = 171


class NeonSkin(BaseModel):
    bg_color: str = "#000000"
    iris_size: int = 100
    fg_color_start: str = "#0000FF"
    fg_color_end: str = "#00FF00"
    style: str = "neon1.png"


class Skins(BaseModel):
    simple: SimpleSkin = SimpleSkin()
    metal: MetalSkin = MetalSkin()
    neon: NeonSkin = NeonSkin()


class Comms(BaseModel):
    port: str = "/dev/ttyS0"
    baud: int = 115200


class EyeSettings(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        str_min_length=1
    )

    states: States = States()
    logo_format: LogoFormat = LogoFormat()
    display: Display = Display()
    motions: Motions = Motions()
    skins: Skins = Skins()
    comms: Comms = Comms()

class KevinbotEyesState(BaseModel):
    """The state of the eye system"""

    connected: bool = False
    settings: EyeSettings = EyeSettings()


class KevinbotServerState(BaseModel):
    """The state system used internally in the Kevinbot Server"""

    mqtt_connected: bool = False
    clients: int = 0
    connected_cids: list[str] = []
    last_driver_cid: str | None = None
    driver_cid: str | None = None
