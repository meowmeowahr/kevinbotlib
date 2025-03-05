from kevinbotlib.util import fullclassname


class Test:
    pass


def test_fullclassname():
    assert fullclassname(str) == "str"
    assert fullclassname(Test) == "tests.test_utils.Test"
