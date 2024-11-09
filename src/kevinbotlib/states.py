# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CoreErrors(Enum):
    """
    Kevinbot Core Error States
    """

    OK = 0
    """No errors are present"""
    UNKNOWN = 1
    """Error state unknown"""
    OW_SHORT = 2
    """One-Wire bus is shorted"""
    OW_ERROR = 3
    """One-Wire bus error"""
    OW_DNF = 4
    """One-Wire device not found"""
    LCD_INIT_FAIL = 5
    """LCD Init failed"""
    PCA_INIT_FAIL = 6
    """PCA9685 (servos) init fail"""
    TICK_FAIL = 7
    """Failure to recieve core tick"""
    QUEUE_OVERRUN = 8
    """Serial queue overrun"""
    ESTOP = 9
    """Core is in E-Stop state"""
    BME_CHIP_ID = 10
    """Error getting environment sensor chip id"""
    BME_CALIB_NVM = 11
    """Error with environment sensor calibration"""
    BME_CALIB_TP = 12
    """Error with environment sensor calibration"""
    BME_CALIB_HUM = 13
    """Error with environment sensor calibration"""
    BME_THP = 14
    """Error with environment sensor"""
    BME_MEAS_TIMEOUT = 15
    """Timeout with environment sensor measurement"""
    BME_NOT_NORMAL_MODE = 16
    """Environemnt sensor is not in normal mode"""
    BATT1_UV = 17
    """Battery #1 Undervoltage"""
    BATT1_OV = 18
    """Battery #1 Overvoltage"""
    BATT2_UV = 19
    """Battery #2 Undervoltage"""
    BATT2_OV = 20
    """Battery #2 Overvoltage"""
    BATT_UV = 21
    """Battery Undervoltage (single battery mode)"""
    BATT_OV = 22
    """Battery Overvoltage (single battery mode)"""


class MotorDriveStatus(Enum):
    """
    The status of each motor in the drivebase
    """

    UNKNOWN = 10
    """Motor status is unknown"""
    MOVING = 11
    """Motor is rotating"""
    HOLDING = 12
    """Motor is holding at position"""
    OFF = 13
    """Motor is off"""


class BmsBatteryState(Enum):
    """
    The status of a single battery attached to the BMS
    """

    UNKNOWN = 0
    """State is unknown (usually at bootup)"""
    NORMAL = 1
    """Battery is normal"""
    UNDER = 2
    """Battery is undervoltage"""
    OVER = 3
    """Battery is overvoltage"""
    STOPPED = 4  # Stopped state if BMS driver crashed
    """BMS has crashed or stopped"""


class DrivebaseState(BaseModel):
    """The state of the drivebase as a whole"""

    left_power: int = 0
    """Current power of the left motor"""
    right_power: int = 0
    """Current power of the right motor"""
    amps: list[float] = Field(default_factory=lambda: [0, 0])
    """Current amps for both motors"""
    watts: list[float] = Field(default_factory=lambda: [0, 0])
    """Current watts for both motors"""
    status: list[MotorDriveStatus] = Field(default_factory=lambda: [MotorDriveStatus.UNKNOWN, MotorDriveStatus.UNKNOWN])
    """Current status for both motors"""


class ServoState(BaseModel):
    """The state of the servo subsystem"""

    angles: list[int] = Field(default_factory=lambda: [-1] * 32)
    """Servo angles"""


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


class EyeSkin(Enum):
    """
    Eye Skins for the eye system
    """

    TV_STATIC = 0
    """TV Static-style random colors"""
    SIMPLE = 1
    """Simple skin with variable pupil, iris, and background"""
    METAL = 2
    """Skin with fancy pupil and iris over an aluminum background"""
    NEON = 3
    """Neon skin"""


class EyeMotion(Enum):
    """
    Motion modes for the eye system
    """

    DISABLE = 0
    """No motion"""
    LEFT_RIGHT = 1
    """Smooth left to right and back"""
    JUMP = 2
    """Jumpy left to right and back"""
    MANUAL = 3
    """Allow manual control of pupil position"""


class States(BaseModel):
    page: EyeSkin = EyeSkin.SIMPLE
    motion: EyeMotion = EyeMotion.LEFT_RIGHT
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
    model_config = ConfigDict(str_strip_whitespace=True, str_min_length=1)

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
    dead_cids: list[str] = []
    cid_heartbeats: dict[str, float] = {}
    last_driver_cid: str | None = None
    driver_cid: str | None = None
    last_drive_command_time: datetime | None = None
    timestamp: datetime | None = None
