import math
from enum import IntEnum

from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass


class AngleUnit(IntEnum):
    """
    Enumeration of angle units.
    """

    Radian = 0
    """Radians"""
    Degree = 1
    """Degrees"""


class Angle2d(BaseModel):
    radians: float

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if isinstance(value, cls):
            return value
        msg = "Angle2d expects construction via .from_value()"
        raise TypeError(msg)

    @classmethod
    def from_value(cls, angle: float, unit: AngleUnit = AngleUnit.Radian) -> "Angle2d":
        """
        Construct the angle
        Args:
            angle: Angle in radians or degrees.
            unit: Angle unit.

        Returns:
            Angle2d instance.
        """
        radians = angle if unit == AngleUnit.Radian else math.radians(angle)
        return cls(radians=radians)

    @property
    def degrees(self) -> float:
        """
        Get the angle in degrees.

        Returns:
            Degrees.
        """
        return math.degrees(self.radians)


class Angle3d(BaseModel):
    yaw: float = Field(..., description="Yaw in radians")
    pitch: float = Field(..., description="Pitch in radians")
    roll: float = Field(..., description="Roll in radians")

    @classmethod
    def from_values(cls, yaw: float, pitch: float, roll: float, unit: AngleUnit = AngleUnit.Radian) -> "Angle3d":
        """
        Create an Angle3d instance with angles in the specified unit.

        Args:
            yaw: Yaw angle in radians or degrees.
            pitch: Pitch angle in radians or degrees.
            roll: Roll angle in radians or degrees.
            unit: Angle unit. Defaults to AngleUnit.Radian.

        Returns:
            Angle3d instance.
        """
        if unit == AngleUnit.Degree:
            yaw, pitch, roll = map(math.radians, (yaw, pitch, roll))
        return cls(yaw=yaw, pitch=pitch, roll=roll)

    @property
    def values_degrees(self) -> list[float]:
        """
        Get yaw, pitch, and roll angles in degrees.

        Returns:
            Angles
        """
        return [math.degrees(self.yaw), math.degrees(self.pitch), math.degrees(self.roll)]

    @property
    def values_radians(self) -> list[float]:
        """
        Get yaw, pitch, and roll angles in radians.

        Returns:
            Radians
        """
        return [self.yaw, self.pitch, self.roll]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Angle3d):
            return NotImplemented
        return self.values_radians == other.values_radians


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
