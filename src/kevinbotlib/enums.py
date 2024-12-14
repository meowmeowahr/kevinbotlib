from enum import Enum


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


class BmsBatteryStatus(Enum):
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


class EyeCallbackType(Enum):
    """
    Callback triggers for eye data changes
    """

    """Simple Skin Background Color"""
    SimpleBgColor = "simple.bg_color"
    """Simple Skin Iris Color"""
    SimpleIrisColor = "simple.iris_color"
    """Simple Skin Pupil Color"""
    SimplePupilColor = "simple.pupil_color"
    """Simple Skin Iris Size"""
    SimpleIrisSize = "simple.iris_size"
    """Simple Skin Pupil Size"""
    SimplePupilSize = "simple.pupil_size"

    """Metal Skin Background Color"""
    MetalBgColor = "metal.bg_color"
    """Metal Skin Tint"""
    MetalTint = "metal.tint"
    """Metal Skin Iris Size"""
    MetalIrisSize = "metal.iris_size"

    """Neon Skin Background Color"""
    NeonBgColor = "neon.bg_color"
    """Neon Skin Iris Size"""
    NeonIrisSize = "neon.iris_size"
    """Neon Skin Pupil Start Color"""
    NeonPupilStartColor = "neon.fg_color_start"
    """Neon Skin Pupil End Color"""
    NeonPupilEndColor = "neon.fg_color_end"
    """Neon Skin Style"""
    NeonStyle = "neon.style"
