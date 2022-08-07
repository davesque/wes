from wes.utils import byte_length, serialize_dict, str_to_int


def test_str_to_int() -> None:
    assert str_to_int("0b101010") == 42
    assert str_to_int("0o52") == 42
    assert str_to_int("0x2a") == 42
    assert str_to_int("42") == 42
    assert str_to_int("0042") == 42


def test_byte_length() -> None:
    assert byte_length(2**8 - 1) == 1
    assert byte_length(2**8) == 2
    assert byte_length(2**16 - 1) == 2
    assert byte_length(2**16) == 3
    assert byte_length(2**24 - 1) == 3
    assert byte_length(2**24) == 4


def test_serialize_dict() -> None:
    assert serialize_dict({"b": 2, "a": 1}) == (("a", 1), ("b", 2))
