from enum import IntEnum

from pydantic.dataclasses import Field, dataclass


class AngleUnit(IntEnum):
    """
    Enumeration of angle units.
    """

    Radian = 0
    """Radians"""
    Degree = 1
    """Degrees"""


@dataclass
class Angle2d:
    radians: float


@dataclass
class Angle3d:
    yaw: float = Field(..., description="Yaw in radians")
    pitch: float = Field(..., description="Pitch in radians")
    roll: float = Field(..., description="Roll in radians")


@dataclass
class Coord2d:
    """
    Class representing a 2d coordinate.
    """

    x: float
    """X coordinate."""
    y: float
    """Y coordinate."""


@dataclass
class Coord3d:
    """
    Class representing a 3d coordinate.
    """

    x: float
    """X coordinate."""
    y: float
    """Y coordinate."""
    z: float
    """Z coordinate."""


@dataclass
class Pose2d:
    """
    Class representing a 2d pose.
    """

    transform: Coord2d
    """Transformation"""
    orientation: Angle2d = Field(default_factory=lambda: Angle2d(0.0))
    """Orientation"""


@dataclass
class Pose3d:
    """
    Class representing a 3d pose.
    """

    transform: Coord3d
    """Transformation"""
    orientation: Angle3d = Field(default_factory=lambda: Angle3d(0.0, 0.0, 0.0))
    """Orientation"""
