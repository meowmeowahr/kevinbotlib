from kevinbotlib.misc import Temperature


def test_c_to_f():
    assert Temperature(25).f == 77.0


def test_f_to_c():
    assert Temperature.from_f(77) == 25.0
