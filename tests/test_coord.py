import math

from kevinbotlib.coord import (
    Angle2d,
    Angle3d,
    AngleUnit,
    Coord2d,
    Coord3d,
    Pose2d,
    Pose3d,
)


def test_2d():
    coord2d = Coord2d(1, 2)
    assert coord2d.x == 1
    assert coord2d.y == 2

    angle2d = Angle2d.from_value(2.0)
    assert angle2d.radians == 2.0
    assert angle2d.degrees == math.degrees(2.0)

    pose2d = Pose2d(Coord2d(1, 2), Angle2d.from_value(3.0))
    assert pose2d.transform.x == 1
    assert pose2d.transform.y == 2
    assert pose2d.orientation.radians == 3.0
    assert pose2d.orientation.degrees == math.degrees(3.0)


def test_3d():
    coord3d = Coord3d(1, 2, 3)
    assert coord3d.x == 1
    assert coord3d.y == 2
    assert coord3d.z == 3

    angle3d = Angle3d.from_values(2.0, 3.0, 1.0)
    assert angle3d.yaw == 2.0
    assert angle3d.pitch == 3.0
    assert angle3d.roll == 1.0
    assert angle3d.values_degrees == [math.degrees(2.0), math.degrees(3.0), math.degrees(1.0)]
    assert angle3d.values_radians == [2.0, 3.0, 1.0]

    pose3d = Pose3d(Coord3d(1, 2, 3), Angle3d.from_values(4.0, 5.0, 6.0))
    assert pose3d.transform.x == 1
    assert pose3d.transform.y == 2
    assert pose3d.transform.z == 3
    assert pose3d.orientation.yaw == 4.0
    assert pose3d.orientation.pitch == 5.0
    assert pose3d.orientation.roll == 6.0
    assert pose3d.orientation.values_degrees == [math.degrees(4.0), math.degrees(5.0), math.degrees(6.0)]
    assert pose3d.orientation.values_radians == [4.0, 5.0, 6.0]


def test_equality():
    angle1 = Angle2d.from_value(1.0)
    angle2 = Angle2d.from_value(1.0)
    angle3 = Angle2d.from_value(2.0)
    assert angle1 == angle2
    assert angle1 != angle3

    angle1 = Angle3d.from_values(1.0, 2.0, 3.0)
    angle2 = Angle3d.from_values(1.0, 2.0, 3.0)
    angle3 = Angle3d.from_values(2.0, 3.0, 1.0)
    assert angle1 == angle2
    assert angle1 != angle3


def test_angle_unit():
    angle1 = Angle2d.from_value(1.0)
    angle2 = Angle2d.from_value(math.degrees(1.0), AngleUnit.Degree)
    assert angle1 == angle2

    angle1 = Angle3d.from_values(1.0, 2.0, 3.0)
    angle2 = Angle3d.from_values(math.degrees(1.0), math.degrees(2.0), math.degrees(3.0), AngleUnit.Degree)
    assert angle1 == angle2


def test_model():
    assert Angle2d.from_value(1.0).model_dump() == {"radians": 1.0}
