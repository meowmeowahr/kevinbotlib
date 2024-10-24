# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later


class Temperature(float):
    """Extended float class that can convert it's value from Celcius to Farenheit"""

    @property
    def f(self) -> float:
        """Convert value to Farenheit

        Returns:
            float: Value in F
        """
        return self.__float__() * 1.8 + 32

    @staticmethod
    def from_f(f: float) -> "Temperature":
        """Convert a Farenheit value to a Temperature object

        Args:
            f (float): Temp in Farenheit

        Returns:
            Temperature: Celcius, convertable
        """
        return Temperature((f - 32) * 5 / 9)
