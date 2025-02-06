from kevinbotlib.comm import BaseData


class JoystickData(BaseData):
    data_id: str = "kevinbotlib.dtype.joystick"
    a: bool
    b: bool
    x: bool
    y: bool
    left_stick: tuple[float, float] | list[float]
    right_stick: tuple[float, float] | list[float]
    left_stick_button: bool
    right_stick_button: bool
    left_trigger: float
    right_trigger: float
    left_bumper: bool
    right_bumper: bool
    back: bool
    start: bool

    def get_dict(self) -> dict:
        data = super().get_dict()
        data["a"] = self.a
        data["b"] = self.b
        data["x"] = self.x
        data["y"] = self.y
        data["left_stick"] = self.left_stick
        data["right_stick"] = self.right_stick
        data["left_stick_button"] = self.left_stick_button
        data["right_stick_button"] = self.right_stick_button
        data["left_trigger"] = self.left_trigger
        data["right_trigger"] = self.right_trigger
        data["left_bumper"] = self.left_bumper
        data["right_bumper"] = self.right_bumper
        data["back"] = self.back
        data["start"] = self.start
        return data
