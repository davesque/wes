from io import StringIO

import pytest

from das.exceptions import RenderedError
from das.parser import File, Label, Op, Parser, Val


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
        [
            Op("lda", "init", []),
            Label("count_up", []),
            Op("out", None, []),
            Op("add", "incr", []),
            Op("jc", "count_down", []),
            Op("jmp", "count_up", []),
            Label("count_down", []),
            Op("out", None, []),
            Op("sub", "incr", []),
            Op("jz", "end", []),
            Op("jmp", "count_down", []),
            Label("end", []),
            Op("hlt", None, []),
            Label("init", []),
            Val(42, None),  # type: ignore
            Label("incr", []),
            Val(1, None),  # type: ignore
        ]
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
        [
            Label("loop", []),
            Op("lda", "a", []),
            Op("out", None, []),
            Op("add", "b", []),
            Op("sta", "a", []),
            Op("lda", "b", []),
            Op("out", None, []),
            Op("add", "a", []),
            Op("sta", "b", []),
            Op("jmp", "loop", []),
            Label("a", []),
            Val(1, None),  # type: ignore
            Label("b", []),
            Val(1, None),  # type: ignore
        ]
    )


def test_parse_unary_with_val() -> None:
    parser = Parser.from_str("lda 1")
    file = parser.parse_file()
    assert file == File([Op("lda", 1, [])])


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

    assert parser.parse_file() == File([Op("foo", None, [])])
