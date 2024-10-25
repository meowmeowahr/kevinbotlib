# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later


from kevinbotlib.misc import Temperature


def test_c_to_f():
    assert Temperature(25).f == 77.0


def test_f_to_c():
    assert Temperature.from_f(77) == 25.0
