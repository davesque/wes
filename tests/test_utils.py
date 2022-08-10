from typing import Any, Callable

import pytest

from wes.utils import SlotClass, byte_length, le_bytes, serialize_dict, str_to_int


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


def test_le_bytes() -> None:
    assert list(le_bytes(0xff, 1)) == [0xff]
    assert list(le_bytes(0xff, 2)) == [0xff, 0x00]
    assert list(le_bytes(0x100, 2)) == [0x00, 0x01]
    assert list(le_bytes(0xffff, 2)) == [0xff, 0xff]
    assert list(le_bytes(0x10000, 2)) == [0x00, 0x00]
    assert list(le_bytes(0x10000, 3)) == [0x00, 0x00, 0x01]
    assert list(le_bytes(0x12345, 3)) == [0x45, 0x23, 0x01]


def test_serialize_dict() -> None:
    assert serialize_dict({"b": 2, "a": 1}) == (("a", 1), ("b", 2))


class OneSlot(SlotClass):
    __slots__ = ("foo",)

    foo: Any  # type: ignore


class TwoSlot(SlotClass):
    __slots__ = ("foo", "bar")

    foo: Any  # type: ignore
    bar: Any  # type: ignore


def test_slot_class() -> None:
    for one in (OneSlot(1), OneSlot(foo=1)):
        assert one.foo == 1
        with pytest.raises(AttributeError):
            one.__dict__

    for two in (TwoSlot(1, 2), TwoSlot(1, bar=2), TwoSlot(foo=1, bar=2)):
        assert two.foo == 1
        assert two.bar == 2
        with pytest.raises(AttributeError):
            two.__dict__


@pytest.mark.parametrize(
    "should_throw_error",
    (
        lambda: OneSlot(),
        lambda: TwoSlot(),
        lambda: TwoSlot(1),
        lambda: TwoSlot(foo=1),
        lambda: TwoSlot(bar=1),
    ),
)
def test_slot_class_raises(should_throw_error: Callable[..., Any]) -> None:
    with pytest.raises(TypeError, match="requires a setting for"):
        should_throw_error()
