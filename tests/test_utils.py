from das.utils import str_to_int


def test_str_to_int() -> None:
    assert str_to_int("0b101010") == 42
    assert str_to_int("0o52") == 42
    assert str_to_int("0x2a") == 42
    assert str_to_int("42") == 42
    assert str_to_int("0042") == 42
