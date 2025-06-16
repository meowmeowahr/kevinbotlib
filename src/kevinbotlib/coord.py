import math
from enum import IntEnum

from pydantic.dataclasses import dataclass


class AngleUnit(IntEnum):
    """
    Enumeration of angle units.
    """

    Radian = 0
    """Radians"""
    Degree = 1
    """Degrees"""


class Angle2d:
    """
    Class representing an angle on a 2d plane.
    """

    def __init__(self, angle: float, unit: AngleUnit = AngleUnit.Radian) -> None:
        """
        Create the angle.

        Args:
            angle: Angle in degrees or radians.
            unit: Angle initialization unit.
        """
        self._angle = angle if unit == AngleUnit.Radian else math.radians(angle)

    @property
    def degrees(self) -> float:
        """
        Get the angle in degrees.

        Returns:
            Degrees.
        """
        return math.degrees(self._angle)

    @property
    def radians(self) -> float:
        """
        Get the angle in radians.

        Returns:
            Radians.
        """
        return self._angle


class Angle3d:
    """
    Class representing an angle in a 3d space.
    """

    def __init__(self, yaw: float, pitch: float, roll: float, unit: AngleUnit = AngleUnit.Radian) -> None:
        """
        Create the angle.
        Args:
            yaw: Yaw angle in degrees or radians.
            pitch: Pitch angle in degrees or radians.
            roll: Roll angle in degrees or radians.
            unit: Angle initialization unit.
        """
        self._yaw = yaw if unit == AngleUnit.Radian else math.radians(yaw)
        self._pitch = pitch if unit == AngleUnit.Radian else math.radians(pitch)
        self._roll = roll if unit == AngleUnit.Radian else math.radians(roll)

    @property
    def values_degrees(self) -> list[float]:
        """
        Get yaw, pitch, and roll angles in degrees.

        Returns:
            Angles.
        """
        return [math.degrees(self._yaw), math.degrees(self._pitch), math.degrees(self._roll)]

    @property
    def values_radians(self) -> list[float]:
        """
        Get yaw, pitch, and roll angles in radians.

        Returns:
            Angles.
        """
        return [self._yaw, self._pitch, self._roll]

    @property
    def yaw(self) -> float:
        """
        Get the yaw angle in radians.

        Returns:
            Radians.
        """
        return self._yaw

    @property
    def pitch(self) -> float:
        """
        Get the pitch angle in radians.

        Returns:
            Radians.
        """
        return self._pitch

    @property
    def roll(self) -> float:
        """
        Get the roll angle in radians.

        Returns:
            Radians.
        """
        return self._roll


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
    orientation: Angle2d = Angle2d(0.0)
    """Orientation"""


@dataclass
class Pose3d:
    """
    Class representing a 3d pose.
    """

    transform: Coord3d
    """Transformation"""
    orientation: Angle3d = Angle3d(0.0, 0.0, 0.0)
    """Orientation"""
