from io import StringIO

import pytest

from das.exceptions import RenderedError
from das.lexer import Text
from das.parser import File, Label, Op, Parser, Val

# dummy token list to appease anal type checker
dmy = (Text("", 0, 0, 0),)


def test_parse_count() -> None:
    parser = Parser.from_str(
        """
; Counts from 42 to 256 (zero really in 8 bits), then down from 255 to 1
; before halting

lda init

count_up:
  out
  add incr
  jc count_down  ; jump to "count_down" if we overflowed
  jmp count_up

count_down:
  out
  sub incr
  jz end         ; jump to "end" if we hit zero
  jmp count_down

end: hlt

init: 42
incr: 1
"""
    )
    file = parser.parse_file()
    assert file == File(
        (
            Op("lda", "init", dmy),
            Label("count_up", dmy),
            Op("out", None, dmy),
            Op("add", "incr", dmy),
            Op("jc", "count_down", dmy),
            Op("jmp", "count_up", dmy),
            Label("count_down", dmy),
            Op("out", None, dmy),
            Op("sub", "incr", dmy),
            Op("jz", "end", dmy),
            Op("jmp", "count_down", dmy),
            Label("end", dmy),
            Op("hlt", None, dmy),
            Label("init", dmy),
            Val(42, dmy),
            Label("incr", dmy),
            Val(1, dmy),
        )
    )


def test_parse_fib() -> None:
    parser = Parser.from_str(
        """
; Counts up in fibonacci numbers forever (with a lot of overflow)

loop:
  lda a
  out
  add b
  sta a

  lda b
  out
  add a
  sta b

  jmp loop

a: 1
b: 1
"""
    )
    file = parser.parse_file()
    assert file == File(
        (
            Label("loop", dmy),
            Op("lda", "a", dmy),
            Op("out", None, dmy),
            Op("add", "b", dmy),
            Op("sta", "a", dmy),
            Op("lda", "b", dmy),
            Op("out", None, dmy),
            Op("add", "a", dmy),
            Op("sta", "b", dmy),
            Op("jmp", "loop", dmy),
            Label("a", dmy),
            Val(1, dmy),
            Label("b", dmy),
            Val(1, dmy),
        )
    )


def test_parse_unary_with_val() -> None:
    parser = Parser.from_str("lda 1")
    file = parser.parse_file()
    assert file == File((Op("lda", 1, dmy),))


def test_parse_nullary_or_val_invalid() -> None:
    parser = Parser.from_str("!!!")

    with pytest.raises(RenderedError) as excinfo:
        parser.parse_file()

    assert "is not a valid mnemonic or integer" in excinfo.value.msg


def test_parse_unary_invalid_mnemonic() -> None:
    parser = Parser.from_str("!!! blah")

    with pytest.raises(RenderedError) as excinfo:
        parser.parse_file()

    assert "is not a valid mnemonic" in excinfo.value.msg


def test_parse_unary_expected_end_of_line() -> None:
    parser = Parser.from_str("foo bar baz")

    with pytest.raises(RenderedError) as excinfo:
        parser.parse_file()

    assert "expected end of line" in excinfo.value.msg


def test_parse_unary_invalid_op_arg() -> None:
    parser = Parser.from_str("blah !!!")

    with pytest.raises(RenderedError) as excinfo:
        parser.parse_file()

    assert "is not a valid label or integer" in excinfo.value.msg


def test_parser_from_buf() -> None:
    buf = StringIO("foo")
    parser = Parser.from_buf(buf)

    assert parser.parse_file() == File((Op("foo", None, dmy),))


@pytest.mark.parametrize(
    "int_repr,int_val",
    (
        ("1_000_000_000", 1_000_000_000),
        ("0b1000_0000", 0b1000_0000),
        ("0o52_52", 0o52_52),
        ("0x52_52", 0x52_52),
    ),
)
def test_parse_underscore_digit_grouping(int_repr: str, int_val: int) -> None:
    parser = Parser.from_str(int_repr)
    file = parser.parse_file()

    assert file == File((Val(int_val, dmy),))
